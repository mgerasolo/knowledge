"""Flask-free query embedding and SurrealDB retrieval."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
from time import perf_counter
from typing import Any, Callable, Iterable

import requests

try:
    from .config import Config
    from .corpus import PersonalityCorpus
    from .surreal_client import SurrealClient
except ImportError:
    from config import Config
    from corpus import PersonalityCorpus
    from surreal_client import SurrealClient


class RetrievalError(RuntimeError):
    """Embedding or retrieval failed without leaking upstream details."""


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[dict[str, Any]]
    chunks_searched: int
    coverage_percent: float
    embedding_ms: int
    database_ms: int


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(value[:10])
            except ValueError:
                return None
    return None


def freshness_score(
    published_at: Any,
    *,
    today: date | None = None,
    horizon_days: int = 730,
) -> float:
    """Linear freshness: 1 today/future, 0 at or beyond the horizon."""
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    published = _as_date(published_at)
    if published is None:
        return 0.0
    age = ((today or datetime.now(timezone.utc).date()) - published).days
    return max(0.0, min(1.0, 1.0 - max(age, 0) / horizon_days))


def recency_weighted_score(
    cosine: float,
    published_at: Any,
    *,
    today: date | None = None,
    rec_boost: float = 0.15,
    horizon_days: int = 730,
) -> float:
    if rec_boost < 0:
        raise ValueError("rec_boost must be non-negative")
    return float(cosine) * (
        1.0
        + rec_boost
        * freshness_score(published_at, today=today, horizon_days=horizon_days)
    )


class LiteLLMClient:
    """Minimal OpenAI-compatible client used by retrieval and composition."""

    def __init__(self, config: type[Config] = Config, session: Any = requests):
        self.config = config
        self.session = session

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.LITELLM_API_KEY:
            headers["Authorization"] = f"Bearer {self.config.LITELLM_API_KEY}"
        return headers

    def embed(self, text: str) -> list[float]:
        payload = {
            "model": self.config.EMBEDDING_MODEL,
            "input": f"{self.config.EMBEDDING_QUERY_PREFIX}{text[:8000]}",
        }
        try:
            response = self.session.post(
                self.config.LITELLM_URL,
                headers=self._headers(),
                json=payload,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            vector = response.json()["data"][0]["embedding"]
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            raise RetrievalError("question embedding failed") from exc
        if not isinstance(vector, list) or len(vector) != self.config.EMBEDDING_DIM:
            raise RetrievalError(
                f"embedding dimension mismatch (expected {self.config.EMBEDDING_DIM})"
            )
        try:
            converted = [float(value) for value in vector]
        except (TypeError, ValueError) as exc:
            raise RetrievalError("embedding contains nonnumeric values") from exc
        if not all(math.isfinite(value) for value in converted):
            raise RetrievalError("embedding contains non-finite values")
        return converted

    def chat(self, model: str, messages: list[dict[str, str]], **options: Any) -> dict:
        body: dict[str, Any] = {"model": model, "messages": messages}
        body.update(options)
        try:
            response = self.session.post(
                self.config.chat_url(),
                headers=self._headers(),
                json=body,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", model),
            }
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            raise RetrievalError(f"chat request failed for model {model}") from exc


def _first_count(result: Any) -> int:
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return int(result[0].get("count", 0))
    return 0


class Retriever:
    """Retrieve corpus-scoped chunks and rerank them with freshness."""

    def __init__(
        self,
        db: SurrealClient,
        llm: LiteLLMClient,
        config: type[Config] = Config,
        clock: Callable[[], float] = perf_counter,
    ):
        self.db = db
        self.llm = llm
        self.config = config
        self.clock = clock

    def retrieve(self, query: str, corpus: PersonalityCorpus) -> RetrievalResult:
        start = self.clock()
        vector = self.llm.embed(query)
        embedded_at = self.clock()
        variables = {"corpus": corpus.video_ids}
        coverage = self.db.result(
            """
            SELECT count() AS count, count(embedding) AS embedded
            FROM segment WHERE video_youtube_id IN $corpus GROUP ALL;
            """,
            variables,
        )
        total = embedded = 0
        if isinstance(coverage, list) and coverage and isinstance(coverage[0], dict):
            try:
                total = int(coverage[0].get("count", 0))
                embedded = int(coverage[0].get("embedded", 0))
            except (TypeError, ValueError) as exc:
                raise RetrievalError("invalid embedding coverage response") from exc
            if total < 0 or embedded < 0 or embedded > total:
                raise RetrievalError("invalid embedding coverage response")
        coverage_percent = round(100.0 * embedded / total, 2) if total else 0.0

        candidate_limit = max(self.config.TOP_K * 4, self.config.TOP_K)
        rows = self.db.result(
            """
            SELECT id, text, chunk_index, start_time, end_time, duration,
                   published_at, domain, video_youtube_id,
                   vector::similarity::cosine(embedding, $qvec) AS cosine
            FROM segment
            WHERE video_youtube_id IN $corpus AND embedding IS NOT NONE
            ORDER BY cosine DESC LIMIT $limit;
            """,
            {**variables, "qvec": vector, "limit": candidate_limit},
        )
        if not isinstance(rows, list):
            rows = []
        today = datetime.now(timezone.utc).date()
        ranked: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["id"] = str(item.get("id", ""))
            try:
                item["cosine"] = float(item.get("cosine") or 0.0)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(item["cosine"]):
                continue
            if item["cosine"] < self.config.MIN_COSINE:
                continue
            item["final_score"] = recency_weighted_score(
                item["cosine"],
                item.get("published_at"),
                today=today,
                rec_boost=self.config.REC_BOOST,
                horizon_days=self.config.REC_HORIZON_DAYS,
            )
            ranked.append(item)
        ranked.sort(key=lambda item: item["final_score"], reverse=True)
        finished = self.clock()
        return RetrievalResult(
            chunks=ranked[: self.config.TOP_K],
            chunks_searched=len(rows),
            coverage_percent=coverage_percent,
            embedding_ms=round((embedded_at - start) * 1000),
            database_ms=round((finished - embedded_at) * 1000),
        )
