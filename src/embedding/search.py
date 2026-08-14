"""Semantic search over segment embeddings in SurrealDB.

Query shape validated against the live server (SurrealDB 3.2, HNSW index):
    SELECT ..., vector::distance::knn() AS dist FROM segment
    WHERE [domain = '...' AND] embedding <|K,EF|> [vector]
    ORDER BY dist ASC LIMIT K;
Distance is cosine (index DIST COSINE), so similarity score = 1 - dist.
"""
import json

from config import Config
from embedder import get_embedding
from surreal_client import surreal_query, statement_errors, escape_string


class EmbeddingUnavailable(RuntimeError):
    """The query could not be embedded — gateway down or key missing.
    Callers should surface this as a retryable 503, never a 500."""


# HNSW over-fetch ceiling: filters (domain/min_score) discard rows AFTER the
# KNN retrieval, so we fetch more than `limit` — but bounded, because K is
# also the per-query graph-search cost.
MAX_K = 200


def _rows(payload):
    """Rows from a raw /sql payload, or RuntimeError. SurrealDB answers HTTP
    200 with {"status": "ERR"} inside for rejected statements — a non-None
    payload is NOT success (that assumption caused the 2026-08-05 outage)."""
    if payload is None:
        raise RuntimeError("SurrealDB unreachable or returned a non-200 response")
    errors = statement_errors(payload)
    if errors:
        raise RuntimeError("; ".join(errors))
    stmt = payload[0]
    rows = stmt.get("result") or []
    return rows if isinstance(rows, list) else []


def semantic_search(query_text: str, domain: str = None, limit: int = 10,
                    min_score: float = 0.4) -> dict:
    """Meaning-based segment search. Returns {"results": [...], "model": alias}.

    Raises EmbeddingUnavailable when the query can't be embedded, and
    RuntimeError when SurrealDB fails — the route layer maps both to 503.
    """
    vec = get_embedding(query_text, kind="query")
    if vec is None:
        raise EmbeddingUnavailable(
            "embedding gateway unavailable or no API key configured")

    post_filtering = bool(domain) or (min_score or 0) > 0
    k = min(max(limit * 4, limit), MAX_K) if post_filtering else min(limit, MAX_K)
    ef = max(100, k)

    conditions = []
    if domain:
        conditions.append(f"domain = '{escape_string(domain)}'")
    conditions.append(f"embedding <|{k},{ef}|> {json.dumps(vec)}")

    knn_query = (
        "SELECT video_youtube_id, chunk_index, start_time, end_time, text, "
        "domain, vector::distance::knn() AS dist FROM segment "
        f"WHERE {' AND '.join(conditions)} ORDER BY dist ASC LIMIT {k};"
    )
    rows = _rows(surreal_query(knn_query))

    results = []
    for r in rows:
        score = round(1.0 - float(r.get("dist", 1.0)), 4)
        if min_score and score < min_score:
            continue
        results.append({
            "video_youtube_id": r.get("video_youtube_id"),
            "chunk_index": r.get("chunk_index"),
            "start_time": r.get("start_time"),
            "end_time": r.get("end_time"),
            "text": r.get("text"),
            "domain": r.get("domain"),
            "score": score,
        })
        if len(results) >= limit:
            break

    if results:
        ids = sorted({r["video_youtube_id"] for r in results
                      if r["video_youtube_id"]})
        ids_str = ", ".join(f"'{escape_string(v)}'" for v in ids)
        vids = _rows(surreal_query(
            f"SELECT youtube_id, title FROM video "
            f"WHERE youtube_id IN [{ids_str}];"))
        titles = {v.get("youtube_id"): v.get("title") for v in vids}
        for r in results:
            r["video_title"] = titles.get(r["video_youtube_id"], "Unknown")

    return {"results": results, "model": Config.EMBEDDING_MODEL}
