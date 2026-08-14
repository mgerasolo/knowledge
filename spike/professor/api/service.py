"""Flask-free orchestration for one Professor question."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

try:
    from .composition import CitationIntegrityError, DISCLAIMER, Composer, cited_numbers
    from .config import Config
    from .corpus import PersonalityCorpus
    from .retrieval import RetrievalError, Retriever
    from .surreal_client import SurrealClient, SurrealError
except ImportError:
    from composition import CitationIntegrityError, DISCLAIMER, Composer, cited_numbers
    from config import Config
    from corpus import PersonalityCorpus
    from retrieval import RetrievalError, Retriever
    from surreal_client import SurrealClient, SurrealError


class AskValidationError(ValueError):
    """Client input does not satisfy the ask contract."""


class LoggingError(RuntimeError):
    """A mandatory professor_log record could not be persisted."""


def validate_history(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 50:
        raise AskValidationError("history must be a list of at most 50 turns")
    normalized = []
    for turn in value:
        if not isinstance(turn, dict):
            raise AskValidationError("each history turn must be an object")
        role, content = turn.get("role"), turn.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            raise AskValidationError("history turns require role user/assistant and non-empty content")
        if len(content) > 12000:
            raise AskValidationError("history turn content exceeds 12000 characters")
        normalized.append({"role": role, "content": content.strip()})
    return normalized


def estimate_cost(usage: dict[str, Any], config: type[Config] = Config) -> float:
    prompt = int(usage.get("prompt_tokens", 0) or 0)
    completion = int(usage.get("completion_tokens", 0) or 0)
    return round(
        (prompt * config.INPUT_COST_PER_MILLION + completion * config.OUTPUT_COST_PER_MILLION)
        / 1_000_000,
        8,
    )


class ProfessorService:
    """Coordinate rewriting, retrieval, composition, citations, and audit logging."""

    def __init__(
        self,
        corpus: PersonalityCorpus,
        db: SurrealClient,
        retriever: Retriever,
        composer: Composer,
        config: type[Config] = Config,
        clock: Callable[[], float] = perf_counter,
    ):
        self.corpus = corpus
        self.db = db
        self.retriever = retriever
        self.composer = composer
        self.config = config
        self.clock = clock

    def _citations(self, tiers: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, dict]:
        citations: dict[str, dict] = {}
        videos = self.corpus.by_id
        for number in cited_numbers(tiers):
            chunk = chunks[number - 1]
            video_id = str(chunk.get("video_youtube_id", ""))
            video = videos.get(video_id)
            start = float(chunk.get("start_time") or 0.0)
            if chunk.get("start_time") is None or not math.isfinite(start):
                raise CitationIntegrityError(f"citation has invalid start_time: {video_id}")
            if video is None:
                raise CitationIntegrityError(f"citation video is outside corpus: {video_id}")
            if start < 0 or (
                video.duration_seconds is not None and start > video.duration_seconds
            ):
                raise CitationIntegrityError(f"citation timestamp is outside video: {video_id}")
            end_value = chunk.get("end_time")
            end = float(end_value) if end_value is not None else start
            if not math.isfinite(end) or end < start or (
                video.duration_seconds is not None and end > video.duration_seconds
            ):
                raise CitationIntegrityError(f"citation has invalid end_time: {video_id}")
            citations[str(number)] = {
                "video_id": video_id,
                "start_time": start,
                "end_time": end,
                "title": video.title,
                "url": f"https://youtube.com/watch?v={video_id}&t={max(0, int(start))}s",
                "quote": str(chunk.get("text", "")).strip(),
            }
        return citations

    def _write_log(self, record: dict[str, Any]) -> bool:
        try:
            self.db.write("CREATE professor_log CONTENT $record;", {"record": record})
            return True
        except SurrealError:
            return False

    def ask(
        self,
        personality_id: str,
        question: str,
        history: Any = None,
    ) -> dict[str, Any]:
        request_id = str(uuid4())
        started = self.clock()
        rewrite_ms = retrieval_ms = composition_ms = 0
        safe_question = question.strip() if isinstance(question, str) else ""
        query = safe_question
        turns: list[dict[str, str]] = []
        usage: dict[str, int] = {}
        models: list[str] = []
        retrieval = None
        answer: dict[str, Any] | None = None
        error: str | None = None
        rewrite_error: str | None = None
        logged = False

        try:
            if personality_id != self.corpus.personality_id:
                raise AskValidationError("unknown personality_id")
            if not safe_question:
                raise AskValidationError("question must be a non-empty string")
            if len(safe_question) > 12000:
                raise AskValidationError("question exceeds 12000 characters")
            question = safe_question
            turns = validate_history(history)
            rewrite_started = self.clock()
            if turns:
                try:
                    query, rewrite_usage = self.composer.rewrite(question, turns)
                    usage.update({key: int(value or 0) for key, value in rewrite_usage.items()})
                    models.append(self.config.CHAT_MODEL)
                except RetrievalError as exc:
                    rewrite_error = f"{type(exc).__name__}: {exc}"
                    query = question
            rewrite_ms = round((self.clock() - rewrite_started) * 1000)

            retrieval_started = self.clock()
            retrieval = self.retriever.retrieve(query, self.corpus)
            retrieval_ms = round((self.clock() - retrieval_started) * 1000)

            composition_started = self.clock()
            composed = self.composer.compose(question, retrieval.chunks, self.corpus)
            composition_ms = round((self.clock() - composition_started) * 1000)
            for key, value in composed.usage.items():
                usage[key] = usage.get(key, 0) + int(value or 0)
            models.extend(composed.models)
            cost = estimate_cost(usage, self.config)
            answer = {
                "tiers": composed.tiers,
                "citations": self._citations(composed.tiers, retrieval.chunks),
                "disclaimer": DISCLAIMER,
                "meta": {
                    "model": self.config.CHAT_MODEL,
                    "chunks_searched": retrieval.chunks_searched,
                    "retrieval_ms": retrieval_ms,
                    "coverage_percent": retrieval.coverage_percent,
                    "cost_estimate_usd": cost,
                    "request_id": request_id,
                    "latency_ms": {
                        "rewrite": rewrite_ms,
                        "embedding": retrieval.embedding_ms,
                        "database": retrieval.database_ms,
                        "composition": composition_ms,
                        "total": round((self.clock() - started) * 1000),
                    },
                },
            }
            return_value = answer
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            chunks = retrieval.chunks if retrieval else []
            record = {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "personality": personality_id,
                "question": safe_question,
                "retrieval_query": query,
                "history_length": len(turns),
                "rewrite_error": rewrite_error,
                "retrieved_chunks": [
                    {
                        "id": str(chunk.get("id", "")),
                        "cosine": chunk.get("cosine"),
                        "final_score": chunk.get("final_score"),
                    }
                    for chunk in chunks
                ],
                "coverage_percent": retrieval.coverage_percent if retrieval else 0.0,
                "answer": answer,
                "error": error,
                "models": models,
                "token_usage": usage,
                "cost_estimate_usd": estimate_cost(usage, self.config),
                "latency_ms": {
                    "rewrite": rewrite_ms,
                    "retrieval": retrieval_ms,
                    "embedding": retrieval.embedding_ms if retrieval else 0,
                    "database": retrieval.database_ms if retrieval else 0,
                    "composition": composition_ms,
                    "total": round((self.clock() - started) * 1000),
                },
            }
            logged = self._write_log(record)
            if answer is not None:
                answer["meta"]["log_saved"] = logged

        if answer is not None and not logged:
            raise LoggingError("mandatory professor_log write failed")
        return return_value
