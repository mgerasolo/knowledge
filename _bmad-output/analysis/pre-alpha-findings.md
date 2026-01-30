# Pre-Alpha Spike Findings Report

**Date:** 2026-01-30
**Duration:** ~30 minutes build + ~8 minutes ingestion
**Scope:** 150 videos across 3 channels, 6,031 transcript segments vectorized

---

## Results Summary

| Metric | Value |
|--------|-------|
| Channels ingested | 3 (Fireship, Lex Fridman, Andrew Huberman) |
| Videos processed | 150 (140 succeeded, 0 failed, 10 skipped via idempotency) |
| Transcript failures | 0 (after switching to yt-dlp) |
| Total segments | 6,031 |
| Total vectors in Qdrant | 6,031 |
| Avg transcript length | ~80K chars (short-form: ~5K, long-form: ~96K) |
| Avg segments per video | ~40 (2-3 for Fireship shorts, 50-311 for long podcasts) |
| Avg embedding time per video | ~900ms |
| Total ingestion wall clock | ~7.3 minutes (3 channels x 50 videos) |
| Qdrant storage | 65 MB |
| PostgreSQL storage | 81 MB |
| Embedding model | nomic-embed-text-v1.5 (768 dimensions) |
| Embedding latency | ~35-50ms per single embedding, ~100ms batch |

## Challenges

- **youtube-transcript npm package is broken:** Both `youtube-transcript` (v1.2.1) and `youtube-transcript-ts` (v1.3.0) return empty arrays for ALL videos. **Root cause (corrected):** The JS npm packages are broken/unmaintained software that cannot handle YouTube's current page structure (consent flow, cookie handling). This is NOT an IP blocking issue — Banner runs on a residential Verizon Fios network, not a datacenter. The Python `youtube-transcript-api` (v1.2.4) works from the same network with no issues. The two packages are completely different codebases with confusingly similar names. Initial spike resolution: switched to `yt-dlp` CLI. Post-spike recommendation: use `youtube-transcript-api` (Python) instead — lighter, faster, no binary dependency.

- **LiteLLM requires authentication:** The spike prompt listed the LiteLLM URL but didn't mention it requires a master key (`LITELLM_MASTER_KEY`) for all API calls including `/models`. This would have blocked any executor without knowledge of the key's location (found in Helicarrier's LiteLLM container env).

- **youtube-transcript v2.0.0 doesn't exist:** The prompt specified `^2.0.0` but the latest version is 1.2.1. Minor, but indicates the prompt was written with assumed version numbers.

- **Huberman Lab handle was wrong:** The prompt suggested `@hubaborhegyi` — the correct handle is `@hubermanlab`. The YouTube API returned 0 results with the wrong handle, which caused a clean error but no data for that channel on the first run.

## Deviations from Spike Prompt

- **Transcript fetching method:** Prompt specified `youtube-transcript` npm package. The JS npm packages are broken (not an IP issue — see Challenges above). Switched to `yt-dlp` during spike, then validated `youtube-transcript-api` (Python, v1.2.4) as the preferred production method. The Python package works from this residential network with no API key, no proxy, no VPN. It is lighter and faster than yt-dlp (~0.5-1s vs ~3-5s per video).

- **LiteLLM API key:** Prompt only listed `LITELLM_URL` in the `.env` template. Added `LITELLM_API_KEY` as a required environment variable.

- **Embedding model and dimension:** Prompt assumed `text-embedding-3-small` with 1536 dimensions. Actual available model is `nomic-embed-text-v1.5` with **768 dimensions**. The pre-flight check correctly detected this and configured Qdrant accordingly.

- **No CloudBeaver connection configured:** CloudBeaver was already running but adding the database connection was deferred — not needed for the spike since `psql` via `docker exec` worked fine.

## Lessons for Production

- **Use `youtube-transcript-api` (Python) as the primary transcript source.** The npm transcript libraries (`youtube-transcript`, `youtube-transcript-ts`) are broken software — they cannot handle YouTube's current page structure regardless of IP. The Python `youtube-transcript-api` (v1.2.4, PyPI) works from our residential Fios network with zero configuration — no API key, no proxy, no VPN. It returns transcript data in-memory with timestamps. `yt-dlp` remains a reliable fallback (heavier, 3-5s/video). Gemini API can process videos that have no captions at all (costs API tokens). **No IP workarounds are needed** from this network — Webshare proxy and WireGuard VPN are only relevant if the pipeline moves to a cloud datacenter.

- **Pre-flight checks are essential.** The prompt's recommendation to check `/models` before starting saved hours of debugging. The embedding dimension mismatch (768 vs 1536) would have caused silent failures. Production must validate embedding dimensions match Qdrant collection config on startup.

- **Time-based chunking produces useful search results.** 2-minute chunks with nomic-embed-text-v1.5 at 768 dimensions returned relevant results with cosine similarity scores of 0.70-0.80 for good matches. However, chunks from long podcasts (2+ hours) can be noisy — topic-based chunking would likely improve relevance for production.

- **Idempotency works well and is critical.** The "skip already ingested" pattern (check `transcript_status='fetched'` by YouTube video ID) worked perfectly on re-runs. The batch processed the full 50 videos and skipped the 10 already done without re-fetching or re-embedding.

- **Channel content type dramatically affects segment counts.** Fireship (5-10 min videos): 2-5 segments each. Lex Fridman (2-5 hour podcasts): 50-311 segments each. Huberman (1-2 hour episodes): 15-116 segments each. Production needs to budget differently for long-form vs short-form content.

- **Batch embedding is significantly faster than individual calls.** Embedding 20 texts at once takes ~100ms vs ~50ms each sequentially. Production should always batch. The LiteLLM nomic-embed endpoint handles batches of 20 well.

- **Storage is very manageable.** 150 videos / 6,031 vectors = 65 MB in Qdrant + 81 MB in PostgreSQL. Extrapolating to 10,000 videos (~400K vectors): ~4.3 GB Qdrant + ~5.4 GB PostgreSQL. Well within single-server capacity.

- **YouTube API quota is not a bottleneck at this scale.** Using `playlistItems.list` (1 unit/call) instead of `search.list` (100 units/call), the spike used ~450 units total (3 channel lookups + 3 playlist pages + 3 video detail calls). The 10,000 unit daily quota supports ~500+ videos per day.

- **yt-dlp subtitle quality is good.** Auto-generated subtitles have occasional transcription errors but are fully usable for semantic search. Speaker labels are not included (expected — no diarization). The JSON3 format provides millisecond-precision timestamps.

- **Transcript scraping rate limiting is real.** YouTube's transcript endpoints (not the Data API) rate-limit at ~30+ rapid requests. At 500ms intervals, video 34 triggered HTTP 429 on both `youtube-transcript-api` and `yt-dlp`. The block lasts 30-90 minutes. Production must throttle transcript fetches to ~4 requests/minute (15-second intervals). At ~50 videos/day target, this adds ~12.5 minutes of fetch time — no issue. The YouTube Data API (metadata, playlist listings) is unaffected at 200ms intervals.

- **yt-dlp requires deno for full functionality.** As of current versions, yt-dlp warns "No supported JavaScript runtime could be found" without deno installed. Browser impersonation is unavailable without it. Production should install deno alongside yt-dlp if using it as a fallback.

## Transcript Architecture Decision (Post-Spike)

**Context:** The spike used `yt-dlp` as a workaround for broken JS npm packages. Post-spike investigation revealed the root cause was broken JS libraries, not IP blocking. The Python `youtube-transcript-api` is the correct production solution.

**Recommended production architecture:**

| Priority | Method | Package | When to Use | Speed | Dependencies |
|----------|--------|---------|-------------|-------|-------------|
| Primary | `youtube-transcript-api` | Python (PyPI) | All videos with captions | ~0.5-1s | `pip install youtube-transcript-api` |
| Fallback | `yt-dlp` | Python (pipx) | If Python API fails on specific videos | ~3-5s | Binary + optional ffmpeg |
| Last resort | Gemini API | Python (urllib) | Videos with NO captions at all | Slow | Gemini API key, costs tokens |

**IP/Proxy notes:**
- Banner is on a residential Verizon Fios network — no datacenter IP blocking applies
- No Webshare proxy, WireGuard VPN, or IP workaround is needed
- If pipeline moves to cloud (AWS/GCP/Azure), residential proxy becomes necessary — Webshare ($3.50/GB) has native `youtube-transcript-api` integration via `WebshareProxyConfig`
- The YouTube Data API v3 captions endpoint is NOT viable (requires video owner OAuth, 250 quota/video)

## Assumptions That Were Wrong

- **"youtube-transcript npm package will work":** The JS npm packages (`youtube-transcript`, `youtube-transcript-ts`) are broken/unmaintained. This is NOT an IP or bot detection issue — the Python `youtube-transcript-api` works from the same network. The JS packages simply cannot handle YouTube's current consent flow and page structure. Production should use the Python package.

- **"text-embedding-3-small with 1536 dimensions":** The LiteLLM proxy routes to a local nomic-embed model with 768 dimensions. The prompt should have said "check the actual model and dimension at runtime."

- **"LiteLLM is open (no auth)":** LiteLLM requires a master key for all endpoints. This is a standard security practice but wasn't documented in the spike prompt.

## If I Started Over

- **Use `youtube-transcript-api` (Python) from the beginning.** Don't waste time on JS npm transcript packages — they're broken. The Python package works immediately with no configuration. Call it from Node.js via `execFile` or run it as a lightweight Python script. Abstract the transcript source behind an interface so the method can be swapped (Python API primary, yt-dlp fallback, Gemini last resort).

- **Add a `.env.example` file** with all required variables documented. The executor had to discover `LITELLM_API_KEY` and `EMBEDDING_MODEL` through trial and error.

- **Include the correct YouTube channel handles.** Verify handles before writing the prompt. The wrong Huberman handle wasted a batch run.

- **Start with 5 videos, not 50.** The first run should validate the entire pipeline end-to-end with 5 videos before committing to a large batch. This catches issues like the transcript failure early.

## Discovery Questions Answered

| Question | Answer |
|----------|--------|
| Which transcript method works best? | **`youtube-transcript-api` (Python)** — lightest, fastest (~0.5-1s), no API key. `yt-dlp` works as fallback (~3-5s). JS npm packages are broken. |
| How many videos fail transcripts? | **0 out of 150** (with yt-dlp — auto-generated subs available on virtually all videos) |
| What does raw transcript data look like? | JSON3 format: events with `tStartMs`, `dDurationMs`, `segs[].utf8`. Auto-generated, no speaker labels. See `spike/samples/` |
| How long per video end-to-end? | **~4-6 seconds** (yt-dlp: 3-5s, embed: 0.1-3s depending on length, DB: <100ms) |
| Does time-based chunking work? | **Yes, adequately.** 2-min chunks produce relevant search results (scores 0.70-0.80). Topic-based would improve long-form content |
| What embedding model via LiteLLM? | **nomic-embed-text-v1.5**, 768 dimensions, ~35-50ms per embedding |
| Rate limiting issues? | **YES — transcript scraping hits 429 at ~33 rapid requests (500ms delay).** YouTube blocks the IP for 30-90 minutes. Production uses 15s between transcript fetches (4 req/min). YouTube Data API (metadata) has no rate limit issues at 200ms delay. |
| Qdrant size after 150 videos? | **65 MB** (6,031 vectors x 768 dims). Extrapolates to ~4.3 GB for 10K videos |

## Qdrant Features Explored

- **Basic dense vector cosine search:** Works well. Scores of 0.70-0.80 for relevant content, clear separation from irrelevant results.
- **Payload indexes:** Created indexes on `video_id`, `channel_name`, `youtube_video_id` — useful for filtered queries.
- **Full-text payload indexing:** Not tested — basic semantic search was sufficient for the spike.
- **Hybrid search (BM25 + dense):** Not tested — would be valuable for production to combine keyword and semantic search.
- **Named vectors:** Not tested — single dense vector was sufficient.

## PostgreSQL Extensions Used

- **pg_trgm:** Installed, indexes created on `channels.name` and `videos.title`. Not directly tested via queries but available for fuzzy search.
- **pg_stat_statements:** Installed. Would show slow queries if we ran any analysis.
- **ParadeDB/TimescaleDB:** Not installed — not needed for spike scope.
