# Semantic Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) — tasks are interdependent with live-service verification steps.

**Goal:** Meaning-based search over the 317k-segment transcript corpus, exposed on the consumer API, with embeddings generated automatically for all future ingests.

**Architecture:** Vectors live in SurrealDB next to the segments (Matt decision 2026-08-13); the embedding service owns embedding generation + KNN queries and implements the currently-stubbed `POST /api/search`; the Admin API adds `GET /videos/api/semantic-search` as a thin proxy so consumers keep one host. Everything model-specific (alias, dimension, prefixes) is configuration, because the model choice (local `jarvis-embed` vs cloud `embeddings`) is still pending Matt's side-by-side.

**Tech Stack:** Python/Flask (existing services), SurrealDB 3.2 HNSW vector index (syntax spike-validated on the live server 2026-08-14), LiteLLM gateway for embeddings, pytest.

**Spec:** The task brief in `.claude/GAPS.md` #1 + the session's anchor prompt (scope items 1–6). Failure-first behaviors specified there: gateway down mid-backfill → resume, not restart; query embedding fails → 503 retryable; empty/short query → 400; domain filter with no matches → 200 empty.

## Global Constraints

- Model-agnostic: `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_DOC_PREFIX`, `EMBEDDING_QUERY_PREFIX` are env config; no dimension or model name hardcoded outside defaults.
- Real data only in tests: fixtures are REAL segments + REAL vectors captured from the live corpus/model, committed with capture date (Tier-4 frozen fixtures). No invented values.
- Docs never print exact live counts (MISTAKES.md #4 standing directive) — scope language only.
- Consumer guide bump to 2.2.0 lands in the SAME merge as the endpoint.
- Internal 10.0.0.x calls exempt from the 2s external-API delay, but backfill batches politely (64/request, brief pause).
- SurrealQL KNN (validated): `DEFINE INDEX segment_embedding_idx ON segment FIELDS embedding HNSW DIMENSION <dim> DIST COSINE TYPE F16 EFC 150 M 16` · `WHERE embedding <|K,EF|> [vec]` · `vector::distance::knn() AS dist` · similarity = 1 − dist.
- Existing HNSW index is DIMENSION 1536 F32 over an all-NULL column — redefining is a cheap DDL while nothing is embedded. Memory at F16/768: ~0.6 GB inside SurrealDB's 4 GB cap (1.5 GB used today).

## File Structure

| File | Responsibility |
|---|---|
| `src/embedding/config.py` (modify) | + `EMBEDDING_DIM`, `EMBEDDING_DOC_PREFIX`, `EMBEDDING_QUERY_PREFIX` |
| `src/embedding/embedder.py` (modify) | `get_embedding(text, kind)` applies prefix; `get_embeddings(texts, kind)` batch; ingest counts failures instead of hiding them |
| `src/embedding/search.py` (create) | `semantic_search(query, domain, limit, min_score)` — KNN query build, score mapping, title join; raises `EmbeddingUnavailable` |
| `src/embedding/app.py` (modify) | Implement `POST /api/search` (replace 501 stub) |
| `src/admin/config.py` (modify) | + `EMBEDDING_SERVICE_URL` |
| `src/admin/api/videos.py` (modify) | + `GET /api/semantic-search` proxy route |
| `src/transcript-service/config.py` + `fetcher.py` (modify) | `EMBED_ON_INGEST` (default true) replaces hardcoded `skip_embeddings: True` |
| `scripts/backfill_embeddings.py` (create) | Resumable backfill; index-dimension guard; `--redefine-index` |
| `docker-compose.yml` (modify) | New env plumbing for all three services |
| `tests/python/embedding_loader.py` (create) | Import embedding-service modules without clobbering admin's `config` module |
| `tests/python/test_embedder.py`, `test_semantic_search.py`, `test_search_route_embedding.py`, `test_search_route_admin.py`, `test_backfill.py` (create) | TDD suites |
| `tests/python/fixtures/real_segments_2026-08-14.json` (create) | Frozen real segments + real 768-dim vectors from the live model, capture-dated |
| `docs/CONSUMER_GUIDE.md`, `CLAUDE.md`, `.claude/GAPS.md` (modify) | 2.2.0 bump · tech-stack truth · close gaps #1/#3 |

## Module loader (locked design — Task 1 creates it)

Both services have a top-level `config.py`; `sys.path` tricks would cross-wire them in one pytest run. `tests/python/embedding_loader.py`:

```python
"""Load embedding-service modules under their own names without letting the
service's top-level `config` module collide with src/admin's `config`
(both are bare top-level modules; whichever lands in sys.modules first
would otherwise be silently reused by the other service's imports)."""
import importlib.util
import sys
from pathlib import Path

EMB = Path(__file__).resolve().parents[2] / 'src' / 'embedding'


def _exec(modname, filename):
    spec = importlib.util.spec_from_file_location(modname, EMB / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def load():
    """Returns (config, embedder, search, app) modules, isolated."""
    saved = {k: sys.modules.get(k) for k in ('config', 'surreal_client',
                                             'embedder', 'search',
                                             'mcp_transcript')}
    try:
        cfg = _exec('config', 'config.py')
        _exec('surreal_client', 'surreal_client.py')
        emb = _exec('embedder', 'embedder.py')
        srch = _exec('search', 'search.py')
        appm = _exec('emb_app', 'app.py')
    finally:
        for k, v in saved.items():
            if v is not None:
                sys.modules[k] = v
            else:
                sys.modules.pop(k, None)
    return cfg, emb, srch, appm
```

Caveat this design accepts: modules loaded this way keep references to THEIR config object; tests monkeypatch `emb.Config` / `srch.Config` attributes directly, never `os.environ`-then-reimport.

---

### Task 1: Test scaffolding + frozen real-data fixture

**Files:** Create `tests/python/embedding_loader.py` (code above), `tests/python/fixtures/real_segments_2026-08-14.json`.

- [ ] Capture fixture from the live corpus + live model (run against Banner, commit output): 6 real segments (2 domains) with their real 768-dim `jarvis-embed` vectors + 2 real query vectors ("what the Bible teaches about building wealth", "using AI agents to automate repetitive work"), shape: `{"captured": "2026-08-14", "model": "nomic-embed-text-v2-moe", "dim": 768, "segments": [{"id","text","domain","video_youtube_id","start_time","end_time","chunk_index","embedding"}], "queries": [{"text","embedding"}]}`.
- [ ] Commit: `test: real-data fixture + isolated embedding-service module loader`

### Task 2: Embedder — prefixes, batching, honest failure counts

**Interfaces produced:** `get_embedding(text: str, kind: str = "document") -> list|None` · `get_embeddings(texts: list[str], kind: str = "document") -> list[list|None]` (order-preserving, one gateway call per 64) · `embed_video(...)` result gains `"embeddings_failed": int`.

- [ ] Failing tests in `test_embedder.py`: doc/query prefix applied to gateway payload input; no double-prefix; `kind="query"` uses query prefix; batch preserves order and splits at 64; missing key → all-None without HTTP call; `embed_video` with failing gateway still writes segments and reports `embeddings_generated: false, embeddings_failed: N` (surreal writes mocked).
- [ ] Implement in `embedder.py` + config fields.
- [ ] Commit: `feat(embedding): prefix-aware batched embeddings with honest failure counts`

### Task 3: `search.py` — KNN query + scoring

**Interfaces produced:**
```python
class EmbeddingUnavailable(RuntimeError): ...
def semantic_search(query_text, domain=None, limit=10, min_score=0.4) -> dict
# returns {"results": [{video_youtube_id, video_title, chunk_index, start_time,
#           end_time, text, domain, score}], "model": Config.EMBEDDING_MODEL}
```
Internals: over-fetch `k = clamp(limit*4, limit, 200)` when domain/min_score filtering, `EF = max(100, k)`; query shape exactly as spike-validated; `score = round(1 - dist, 4)`; drop `score < min_score`; truncate to `limit`; title join `SELECT youtube_id, title FROM video WHERE youtube_id IN [...]`.

- [ ] Failing tests in `test_semantic_search.py` (mock `surreal_client.surreal_query`, mock `embedder.get_embedding` returning fixture query vector): built SurrealQL contains `<|k,ef|>` + `vector::distance::knn()`; domain filter escaped and ANDed before KNN; distance→score mapping (use fixture vectors' real cosine distances); min_score drops rows; empty rows → `results: []`; `get_embedding` None → raises `EmbeddingUnavailable`; SurrealDB statement ERR → RuntimeError.
- [ ] Implement `search.py`.
- [ ] Commit: `feat(embedding): SurrealDB HNSW semantic search module`

### Task 4: Embedding service `POST /api/search` (replace the 501 stub)

Contract: missing/short (<3 chars) query → 400 `{error, success: false}` · `EmbeddingUnavailable` → 503 `{error, success: false, retryable: true}` · SurrealDB failure → 503 `{retryable: true}` · success → 200 `{success: true, query, results, count, model}` (empty results is a 200).

- [ ] Failing tests in `test_search_route_embedding.py` via Flask test client (search.semantic_search mocked per case).
- [ ] Implement route in `app.py`; remove the TODO stub; bump service `version` string to 1.1.0 in `/` payload.
- [ ] Commit: `feat(embedding): implement POST /api/search — semantic search live`

### Task 5: Admin API `GET /videos/api/semantic-search`

Contract: `?q=` required, <3 chars → 400 · `?domain=`, `?limit=` (default 20 cap 50), `?min_score=` (default 0.4, `0` disables) passed through · embedding service unreachable/non-JSON/its 5xx → 503 `{error, source: 'embedding-service', retryable: true}` · its 400 → 400 passthrough · 200 → passthrough envelope (same keys as keyword search plus `score`/`model`). Proxy: `requests.post(f"{Config.EMBEDDING_SERVICE_URL}/api/search", json=payload, timeout=35)`.

- [ ] Failing tests in `test_search_route_admin.py` (mock `requests.post` inside `api.videos`; follow existing `sys.path.insert` admin pattern).
- [ ] Implement route + `EMBEDDING_SERVICE_URL` in `src/admin/config.py`.
- [ ] Commit: `feat(admin): consumer semantic-search endpoint proxying the embedding service`

### Task 6: Backfill script

`scripts/backfill_embeddings.py` — env-driven like `reindex_from_files.py`. Core loop: `SELECT id, text FROM segment WHERE embedding = NONE AND string::len(text) > 0 LIMIT 500` → batch-embed (64/gateway call, doc prefix, small politeness pause) → batched `UPDATE <id> SET embedding = [...]` (50 statements/request), statement-status-checked → repeat until empty. Resumable BY CONSTRUCTION (state lives in the DB predicate). Gateway failure → exponential backoff ×5 then exit code 3 with progress preserved. Index guard: parse `INFO FOR TABLE segment` index def; `DIMENSION != EMBEDDING_DIM` → refuse with message; `--redefine-index` drops/recreates at `EMBEDDING_DIM` F16 only when embedded-count is 0 (`--force` overrides). `--limit N` smoke mode. Ends by printing embedded/remaining counts.

- [ ] Failing tests in `test_backfill.py` for the pure pieces: batch-update statement builder (escapes ids, chunks at 50), dimension parser on the real index-def string from the live server, backoff sequence (monkeypatched sleep), remaining-count parser.
- [ ] Implement script.
- [ ] Commit: `feat(scripts): resumable idempotent embedding backfill with index guard`

### Task 7: Ingest path embeds by default

- [ ] Failing test: `transcript-service` fetcher builds `/api/embed` payload with `skip_embeddings: False` when `EMBED_ON_INGEST=true` (default), `True` when env false. (transcript-service has its own bare `config.py` — reuse the loader pattern with its path.)
- [ ] Implement: `Config.EMBED_ON_INGEST` + fetcher payload change; delete the "no semantic search consumes embeddings yet" comment.
- [ ] Commit: `feat(ingest): embed new segments at ingest time`

### Task 8: Compose plumbing

- [ ] `docker-compose.yml`: embedding + admin-api + transcript-service get the new env vars (`EMBEDDING_MODEL` `${EMBEDDING_MODEL:-embeddings}`, `EMBEDDING_DIM` `${EMBEDDING_DIM:-1536}`, prefixes default empty, `EMBEDDING_SERVICE_URL: http://knowledge-embedding:5030`, `EMBED_ON_INGEST` `${EMBED_ON_INGEST:-true}`). Model-specific values land in Banner's `.env` after Matt's decision, not in the compose file.
- [ ] Commit: `chore(deploy): env plumbing for semantic search`

### Task 9: GATE — model decision, then index + backfill + live verify

Blocked on: gateway key (H2-34) → OpenAI side-by-side → Matt picks. Then:
- [ ] Write chosen values into Banner's `.env` (never printed): `EMBEDDING_MODEL`, `EMBEDDING_DIM`, prefixes, `LITELLM_API_KEY` from Infisical.
- [ ] Deploy: Banner checkout pull → `docker compose build embedding admin-api transcript-service && docker compose up -d`.
- [ ] `backfill_embeddings.py --redefine-index --limit 200` smoke → verify 200 embedded + a live search returns sane results.
- [ ] Full run (~30–45 min local); kill/resume test mid-run (ctrl-c one batch, rerun, confirm it continues where it left off).
- [ ] Coverage check: `count(embedding = NONE AND string::len(text) > 0) == 0`.
- [ ] Live verify through the public URL: `GET https://knowledge.nextlevelfoundry.com/enroll/videos/api/semantic-search?q=...` for a strong query, a filtered query, a junk query (400), and an off-topic query (low/empty results).

### Task 10: Docs — same merge

- [ ] `docs/CONSUMER_GUIDE.md`: version 2.2.0 + changelog row; §2 "semantic search does not exist" reversed; §3 documents `GET /videos/api/semantic-search` params + envelope + score semantics + min_score guidance; scope language only, no live counts. `verified:` = the date the live Quickstart re-ran.
- [ ] `CLAUDE.md` tech-stack table: Qdrant row → SurrealDB reality (closes GAPS.md #3), Hulk reference already wrong → align with current deploy targets while touching the table.
- [ ] `.claude/GAPS.md`: close #1 and #3 with the verification evidence inline.
- [ ] Commit: `docs: consumer guide 2.2.0 — semantic search shipped; tech stack corrected`

### Task 11: Validation gate + land

- [ ] Codex adversarial review + independent test run (background, per project rule) → PASS required.
- [ ] PR → merge → fast-forward the shared checkouts (Stark main + Banner deploy checkout) → remove worktree.
