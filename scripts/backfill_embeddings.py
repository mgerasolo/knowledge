#!/usr/bin/env python3
"""Backfill embeddings for every segment that doesn't have one.

Resumable BY CONSTRUCTION: the work queue is the database predicate
`embedding = NONE`, so a killed run loses nothing — rerun and it continues
exactly where it stopped. Idempotent for the same reason: embedded segments
drop out of the predicate.

Failure behavior (deliberate):
- Embedding gateway down mid-run → exponential backoff (5 tries), then exit
  code 3 with all completed work preserved. Rerun when the gateway is back.
- SurrealDB write rejected → exit code 2 immediately (a rejected write at
  this layer means schema/index trouble, not something to retry past).
- Index dimension mismatch → refuses to start. Writing 768-dim vectors into
  a 1536-dim index doesn't error — it silently breaks retrieval, which is
  exactly how this project lost two weeks in 2026-08. `--redefine-index`
  drops and recreates the index at EMBEDDING_DIM (only while the embedding
  column is empty, unless --force).

Usage:
    backfill_embeddings.py                    # embed everything missing
    backfill_embeddings.py --limit 200        # smoke run
    backfill_embeddings.py --redefine-index   # align index dim first
Env: SURREAL_URL/USER/PASS/NS/DB, LITELLM_URL, LITELLM_API_KEY,
     EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_DOC_PREFIX
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

import requests

SURREAL_URL = os.getenv("SURREAL_URL", "http://10.0.0.33:5040")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "changeme")
SURREAL_NS = os.getenv("SURREAL_NS", "knowledge")
SURREAL_DB = os.getenv("SURREAL_DB", "transcripts")

LITELLM_URL = os.getenv("LITELLM_URL", "http://10.0.0.27:2764/v1/embeddings")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "embeddings")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
EMBEDDING_DOC_PREFIX = os.getenv("EMBEDDING_DOC_PREFIX", "")

INDEX_NAME = "segment_embedding_idx"
GATEWAY_BATCH = 64
UPDATES_PER_REQUEST = 50
PAUSE_BETWEEN_GATEWAY_CALLS = 0.1   # polite to the shared GPU host


# --------------------------------------------------------------------------
# SurrealDB
# --------------------------------------------------------------------------

def surreal(query: str, timeout: int = 300):
    """POST a query. Returns the raw statement list, or None on transport
    failure / non-200."""
    try:
        r = requests.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            auth=(SURREAL_USER, SURREAL_PASS),
            data=query.encode("utf-8"),
            timeout=timeout,
        )
    except Exception as e:
        print(f"  surreal transport error: {e}", flush=True)
        return None
    if not r.ok:
        print(f"  surreal HTTP {r.status_code}: {r.text[:200]}", flush=True)
        return None
    try:
        return r.json()
    except Exception:
        return None


def statement_errors(payload) -> list:
    if not isinstance(payload, list):
        return ["unexpected response shape from SurrealDB"]
    return [str(s.get("result", "unknown"))
            for s in payload
            if isinstance(s, dict) and s.get("status") == "ERR"]


def rows_of(payload):
    """Rows of the first statement, or None if anything failed."""
    if payload is None or statement_errors(payload):
        return None
    rows = payload[0].get("result") or []
    return rows if isinstance(rows, list) else []


def count_from_payload(payload):
    """Count out of `SELECT count() ... GROUP ALL`, or None on failure."""
    rows = rows_of(payload)
    if rows is None:
        return None
    if rows and isinstance(rows[0], dict):
        return rows[0].get("count", 0)
    return 0


# --------------------------------------------------------------------------
# Pure pieces (unit-tested)
# --------------------------------------------------------------------------

def index_dimension(indexes: dict):
    """DIMENSION of the segment embedding index from `INFO FOR TABLE`
    output, or None if no such index exists."""
    for name, definition in (indexes or {}).items():
        if "FIELDS embedding" in str(definition):
            m = re.search(r"DIMENSION (\d+)", str(definition))
            if m:
                return int(m.group(1))
    return None


_PLAIN_ID = re.compile(r"^[A-Za-z0-9_]+:[A-Za-z0-9_]+$")


def update_statements(rows: list) -> list:
    """One UPDATE per {id, embedding} row. Plain ids (the md5-hex ones this
    project generates) go inline; anything else goes through type::thing()
    so a hostile or ⟨quoted⟩ id can't break out of the statement."""
    stmts = []
    for r in rows:
        rid = str(r["id"])
        vec = json.dumps(r["embedding"])
        if _PLAIN_ID.match(rid):
            stmts.append(f"UPDATE {rid} SET embedding = {vec};")
        else:
            table, _, raw = rid.partition(":")
            raw = raw.strip("⟨⟩").replace("\\", "\\\\").replace("'", "\\'")
            table = table.replace("\\", "\\\\").replace("'", "\\'")
            stmts.append(
                f"UPDATE type::thing('{table}', '{raw}') SET embedding = {vec};")
    return stmts


def chunked_requests(statements: list, per_request: int = UPDATES_PER_REQUEST) -> list:
    """Join statements into request-sized bundles (one line each)."""
    return ["\n".join(statements[i:i + per_request])
            for i in range(0, len(statements), per_request)]


def with_retries(fn, tries: int = 5, base_delay: float = 2.0):
    """Call fn() until it returns non-None. Exponential backoff between
    attempts; no sleep after the final failure. Returns fn's result or None."""
    for attempt in range(tries):
        result = fn()
        if result is not None:
            return result
        if attempt < tries - 1:
            delay = base_delay * (2 ** attempt)
            print(f"  retrying in {delay:.0f}s...", flush=True)
            time.sleep(delay)
    return None


# --------------------------------------------------------------------------
# Gateway
# --------------------------------------------------------------------------

def gateway_embed(texts: list) -> list | None:
    """One gateway call for up to GATEWAY_BATCH texts. None on failure."""
    try:
        r = requests.post(
            LITELLM_URL,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {LITELLM_API_KEY}"},
            json={"model": EMBEDDING_MODEL,
                  "input": [EMBEDDING_DOC_PREFIX + t[:8000] for t in texts]},
            timeout=120,
        )
        if r.ok:
            data = sorted(r.json()["data"], key=lambda d: d["index"])
            vecs = [d["embedding"] for d in data]
            if len(vecs) == len(texts):
                return vecs
            print(f"  gateway returned {len(vecs)} vectors for {len(texts)} texts",
                  flush=True)
            return None
        print(f"  gateway HTTP {r.status_code}: {r.text[:200]}", flush=True)
    except Exception as e:
        print(f"  gateway error: {e}", flush=True)
    return None


# --------------------------------------------------------------------------
# Index guard
# --------------------------------------------------------------------------

def ensure_index(redefine: bool, force: bool) -> bool:
    payload = surreal("INFO FOR TABLE segment;")
    if payload is None or statement_errors(payload):
        print("FATAL: cannot read segment table info")
        return False
    indexes = (payload[0].get("result") or {}).get("indexes", {})
    dim = index_dimension(indexes)

    if dim == EMBEDDING_DIM:
        print(f"index ok: {INDEX_NAME} DIMENSION {dim}")
        return True

    state = f"DIMENSION {dim}" if dim else "missing"
    if not redefine:
        print(f"FATAL: vector index is {state} but EMBEDDING_DIM={EMBEDDING_DIM}."
              f" Vectors written into a mismatched index silently break"
              f" retrieval. Rerun with --redefine-index to fix.")
        return False

    embedded = count_from_payload(
        surreal("SELECT count() FROM segment WHERE embedding != NONE GROUP ALL;"))
    if embedded is None:
        print("FATAL: could not count embedded segments")
        return False
    if embedded > 0 and not force:
        print(f"FATAL: refusing to redefine the index — {embedded} segments"
              f" already carry vectors (presumably at DIMENSION {dim})."
              f" Those vectors would be orphaned. Re-embed from scratch"
              f" (clear embeddings first) or pass --force if you know better.")
        return False

    print(f"redefining index: {state} -> DIMENSION {EMBEDDING_DIM} (F16)")
    err = statement_errors(surreal(f"""
        REMOVE INDEX IF EXISTS {INDEX_NAME} ON segment;
        DEFINE INDEX {INDEX_NAME} ON segment FIELDS embedding
            HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F16 EFC 150 M 16;
    """))
    if err:
        print(f"FATAL: index redefine failed: {err[0]}")
        return False
    print("index redefined.")
    return True


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------

def remaining_count():
    return count_from_payload(surreal(
        "SELECT count() FROM segment "
        "WHERE embedding = NONE AND string::len(text) > 0 GROUP ALL;"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="stop after embedding N segments (smoke runs)")
    ap.add_argument("--batch", type=int, default=500,
                    help="segments fetched from SurrealDB per cycle")
    ap.add_argument("--redefine-index", action="store_true",
                    help="drop + recreate the vector index at EMBEDDING_DIM")
    ap.add_argument("--force", action="store_true",
                    help="redefine even if vectors already exist")
    args = ap.parse_args()

    if not LITELLM_API_KEY:
        print("FATAL: LITELLM_API_KEY is not set — refusing to run a backfill"
              " that would silently produce zero embeddings.")
        return 1

    if not ensure_index(args.redefine_index, args.force):
        return 1

    todo = remaining_count()
    if todo is None:
        print("FATAL: cannot count remaining segments")
        return 1
    print(f"segments needing embeddings: {todo}")
    print(f"model={EMBEDDING_MODEL} dim={EMBEDDING_DIM} "
          f"doc_prefix={EMBEDDING_DOC_PREFIX!r}")
    print("-" * 64, flush=True)

    done = 0
    started = time.time()

    while True:
        if args.limit and done >= args.limit:
            print(f"--limit {args.limit} reached")
            break

        fetch = min(args.batch, args.limit - done) if args.limit else args.batch
        rows = rows_of(surreal(
            "SELECT id, text FROM segment "
            "WHERE embedding = NONE AND string::len(text) > 0 "
            f"LIMIT {fetch};"))
        if rows is None:
            print("FATAL: fetch failed")
            return 2
        if not rows:
            print("nothing left to embed")
            break

        # Embed, gateway-batch at a time, with backoff. A batch that fails
        # all retries aborts the RUN but loses no work.
        vectors = []
        for i in range(0, len(rows), GATEWAY_BATCH):
            chunk = [str(r["text"]) for r in rows[i:i + GATEWAY_BATCH]]
            vecs = with_retries(lambda c=chunk: gateway_embed(c))
            if vecs is None:
                print("FATAL: embedding gateway kept failing — run is safe to"
                      " rerun; it will resume here. (exit 3)")
                return 3
            vectors.extend(vecs)
            time.sleep(PAUSE_BETWEEN_GATEWAY_CALLS)

        bad_dim = [v for v in vectors if len(v) != EMBEDDING_DIM]
        if bad_dim:
            print(f"FATAL: gateway returned {len(bad_dim)} vectors of dimension"
                  f" {len(bad_dim[0])}, expected {EMBEDDING_DIM}. EMBEDDING_MODEL"
                  f" and EMBEDDING_DIM disagree — fix the config; nothing was"
                  f" written this cycle.")
            return 1

        updates = update_statements(
            [{"id": r["id"], "embedding": v} for r, v in zip(rows, vectors)])
        for req in chunked_requests(updates):
            err = statement_errors(surreal(req))
            if err:
                print(f"FATAL: segment update rejected: {err[0]} (exit 2)")
                return 2

        done += len(rows)
        rate = done / max(1e-9, time.time() - started)
        left = max(0, todo - done)
        print(f"[{done}/{todo}] {rate:.0f} segments/s "
              f"eta={left / max(rate, 1e-9) / 60:.1f}m", flush=True)

    remaining = remaining_count()
    print("-" * 64)
    print(f"embedded this run : {done}")
    print(f"still missing     : {remaining if remaining is not None else 'unknown'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
