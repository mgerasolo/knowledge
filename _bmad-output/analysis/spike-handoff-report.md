# Pre-Alpha Spike: Handoff Report

**Date:** 2026-01-30
**Executor:** Claude (spike agent)
**Prompt:** `_bmad-output/pre-alpha-spike-prompt.md`
**Status:** Complete (17 of 200 videos pending retry due to rate limiting)

---

## Executive Summary

The spike successfully validated YouTube transcript ingestion, vector embedding, and semantic search. 183 videos across 4 channels were fully ingested into PostgreSQL + Qdrant, producing 6,186 searchable transcript segments. Semantic search returns relevant results with cosine similarity scores of 0.69-0.78. The pipeline works end-to-end.

Several critical assumptions in the spike prompt were wrong. Each is documented with corrections and production recommendations.

---

## What Was Built

| Component | Location | Status |
|-----------|----------|--------|
| Ingestion pipeline | `spike/src/ingest.ts` | Working |
| YouTube API client | `spike/src/youtube/transcript.ts` | Working (channel info, video listing, video details, transcript fetching) |
| Transcript fetcher | `spike/src/youtube/transcript.ts:299-420` | Working (Python API primary, yt-dlp fallback) |
| Embedding client | `spike/src/embeddings/client.ts` | Working (LiteLLM proxy to nomic-embed-text-v1.5) |
| Qdrant client | `spike/src/qdrant/client.ts` | Working (upsert + cosine search) |
| PostgreSQL schema | `spike/src/db/setup.ts` | Working (channels, videos, transcripts, segments) |
| CLI query tool | `spike/src/query.ts` | Working (semantic search with formatted results + YouTube timestamp links) |
| Preflight checks | `spike/src/preflight.ts` | Working (validates LiteLLM model + dimensions before ingestion) |
| Config | `spike/src/config.ts` | Working (env-based, all vars documented in `.env`) |

### Infrastructure (All on Banner 10.0.0.33)

| Service | Container | Port | Status |
|---------|-----------|------|--------|
| PostgreSQL 16 | `knowledge-spike-postgres` | 5432 | Running |
| Qdrant 1.16.3 | Qdrant container | 6333/6334 | Running, green |
| LiteLLM | On Helicarrier (10.0.0.27) | 2764 | Running (requires API key) |

---

## Current Data State

| Channel | Videos | Ingested | Pending | Segments |
|---------|--------|----------|---------|----------|
| Fireship | 50 | 50 | 0 | 128 |
| Lex Fridman | 50 | 50 | 0 | 4,340 |
| Andrew Huberman | 50 | 50 | 0 | 1,563 |
| AI LABS | 50 | 33 | 17 | 155 |
| **Total** | **200** | **183** | **17** | **6,186** |

- PostgreSQL: ~18 MB total (channels 32KB, videos 1.1MB, transcripts 6MB, segments 11MB)
- Qdrant: 6,186 vectors x 768 dimensions, cosine distance, status green
- 17 AI LABS videos pending retry (rate-limited, background retry scheduled)

---

## What the Spike Prompt Got Wrong

These are documented in detail in the findings files below. Summary:

1. **`youtube-transcript` npm package** -- prompt specified this, but it's broken software. Production must use `youtube-transcript-api` (Python). See `spike/findings.md` lines 47-80.

2. **Embedding model and dimensions** -- prompt assumed `text-embedding-3-small` at 1536 dims. Actual: `nomic-embed-text-v1.5` at 768 dims. All three LiteLLM embedding aliases (`nomic-embed`, `embeddings`, `jarvis-text-embedding-nomic-embed-text-v1.5`) route to the same model.

3. **LiteLLM auth** -- prompt didn't mention the master key requirement. All endpoints require `Authorization: Bearer <LITELLM_MASTER_KEY>`.

4. **Huberman Lab handle** -- prompt said `@hubaborhegyi`, correct is `@hubermanlab`.

5. **Version numbers** -- prompt specified `youtube-transcript ^2.0.0` which doesn't exist (latest is 1.2.1).

---

## Key Production Decisions Discovered

### Transcript Architecture

| Priority | Method | Speed | When |
|----------|--------|-------|------|
| Primary | `youtube-transcript-api` (Python CLI via pipx) | ~0.5-1s | All videos with captions |
| Fallback | `yt-dlp` (needs deno for full functionality) | ~3-5s | Python API failures |
| Last resort | Gemini API | Slow, costs tokens | Videos with NO captions |

- No proxy/VPN needed from residential Fios network
- Webshare proxy only needed if pipeline moves to cloud datacenter

### Rate Limiting

- YouTube transcript endpoints rate-limit at ~30+ rapid requests
- Production throttle: 15 seconds between fetches (4 req/min)
- At 50 videos/day target: ~12.5 minutes of fetch time
- YouTube Data API (metadata) is NOT rate-limited at 200ms intervals
- Rate limit cooldown: 30-90 minutes after triggering

### Chunking Strategy

- Spike used **time-based 2-minute chunks** -- works adequately (scores 0.69-0.78)
- Production should use **topic-based chunking** -- confirmed by stakeholder
- Time-based chunks are noisy for long-form content (Lex Fridman 5-hour podcasts have dozens of topics per chunk)

### Embedding Model

- `nomic-embed-text-v1.5` at 768 dimensions is sufficient for this use case
- Search quality bottleneck is chunking strategy, not embedding model
- No need to add a new embedding model to Helicarrier

### Storage Projections

- 200 videos / 6,186 vectors = ~18 MB PostgreSQL + ~65 MB Qdrant
- Extrapolated to 10,000 videos: ~900 MB PostgreSQL + ~4.3 GB Qdrant
- Well within single-server capacity

---

## Detailed Findings Files

All spike learnings are documented across these files:

| File | Contents |
|------|----------|
| `_bmad-output/analysis/pre-alpha-findings.md` | **PRIMARY** -- structured findings report for production planning. Covers: results summary, challenges, deviations from prompt, lessons for production, transcript architecture decision, assumptions that were wrong, discovery questions answered, Qdrant/PostgreSQL features explored. |
| `spike/findings.md` | **RAW CHRONOLOGICAL LOG** -- append-only discovery log as things happened. Includes: root cause correction on transcript failures, transcript method comparison table, rate limiting discovery with exact error messages, production tiered strategy. |
| `_bmad-output/pre-alpha-spike-prompt.md` | Original spike prompt (for reference/comparison to actual results). |
| `_bmad-output/analysis/brainstorming-session-2026-01-29.md` | BMAD brainstorming session output (pre-spike planning). |

## Spike Source Code

| File | Purpose |
|------|---------|
| `spike/src/ingest.ts` | Main pipeline: channel resolution, video listing, transcript fetch, chunking, embedding, Qdrant upsert |
| `spike/src/query.ts` | CLI semantic search tool with formatted output + YouTube timestamp links |
| `spike/src/youtube/transcript.ts` | YouTube API (channels, videos, playlists) + transcript fetching (Python API primary, yt-dlp fallback) with throttling |
| `spike/src/embeddings/client.ts` | LiteLLM embedding client (single + batch) |
| `spike/src/qdrant/client.ts` | Qdrant collection management, upsert, cosine search |
| `spike/src/db/client.ts` | PostgreSQL connection pool |
| `spike/src/db/setup.ts` | Schema creation (channels, videos, transcripts, segments) |
| `spike/src/preflight.ts` | Pre-flight validation (LiteLLM model availability, embedding dimensions) |
| `spike/src/config.ts` | Environment variable loading with validation |

## Sample Data

| File | Contents |
|------|---------|
| `spike/samples/sample-*.json` | 25 raw transcript samples (JSON format with timestamps, from various channels) |
| `spike/reports/run-*.json` | 6 ingestion run reports (timestamps, success/fail counts, metrics) |

---

## Pending Items

1. **17 AI LABS videos** -- rate-limited during ingestion. Status reset to `pending`. Background retry scheduled (PID 417102, 15-second throttle). Will complete automatically.

2. **Topic-based chunking** -- confirmed as production direction. Not implemented in spike (spike used 2-minute time-based chunks). Requires design decisions about topic detection method.

3. **yt-dlp deno dependency** -- yt-dlp now requires deno JavaScript runtime for browser impersonation. Without it, the fallback has reduced robustness. Production should install deno alongside yt-dlp.

4. **CloudBeaver connection** -- deferred during spike. PostgreSQL is accessible via `docker exec` / psql. CloudBeaver connection can be added anytime.

---

## How to Verify

```bash
# Run a semantic search
cd spike && npx tsx src/query.ts "how does dopamine affect motivation"

# Check database state
ssh banner "docker exec knowledge-spike-postgres psql -U knowledge -d knowledge_spike -c 'SELECT name, (SELECT COUNT(*) FROM videos WHERE channel_id = c.id) AS videos FROM channels c;'"

# Check Qdrant
curl -s http://10.0.0.33:6333/collections/knowledge_segments | python3 -m json.tool

# Check retry status
tail -50 spike/reports/retry-output.log

# Run a new ingestion
cd spike && npx tsx src/ingest.ts "@SomeYouTubeChannel"
```
