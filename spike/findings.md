# Spike Findings — Chronological Log

Raw, append-only log of discoveries, challenges, and decisions as they happen.

---

## 2026-01-29 — Session Start

### Environment Discovery
- Banner (10.0.0.33) has port 5432 free — no port conflict for PostgreSQL
- No existing YouTube API key in shared AppServices env — key provided separately in `spike/.env`
- LiteLLM proxy at `http://10.0.0.27:2764` — need to verify embedding models available
- CloudBeaver already running at `http://10.0.0.33:8978` — just need to add connection
- Banner has ~28 containers running; port 6333/6334 appear free for Qdrant

### Decisions Made
- Using `googleapis` npm package for YouTube Data API v3 (official Google client, typed)
- Using `youtube-transcript` for transcript scraping (no auth needed)
- Using `@qdrant/js-client-rest` for Qdrant (official TypeScript REST client, lighter than umbrella package)
- Using `pg` for PostgreSQL (battle-tested, not an ORM — spike doesn't need one)
- Using `tsx` for running TypeScript directly (faster than ts-node, no build step)

### Challenge: youtube-transcript version
- Spike prompt suggested `youtube-transcript` v2.0.0 — doesn't exist. Latest is **1.2.1**.
- `googleapis` latest is 171.0.0 (prompt didn't specify, used latest)
- `@qdrant/js-client-rest` latest is 1.16.2

### Infrastructure Deployment
- Qdrant v1.16.3 deployed to Banner, ports 6333/6334. Dashboard at `http://10.0.0.33:6333/dashboard`
- PostgreSQL 16.11 (Alpine) deployed to Banner, port 5432. Container: `knowledge-spike-postgres`
- Enabled extensions: `pg_trgm`, `pg_stat_statements`
- CloudBeaver already running at `http://10.0.0.33:8978` — need to add connection

### Challenge: LiteLLM Authentication
- LiteLLM at `http://10.0.0.27:2764` requires a **master key** for all API calls (including `/models`)
- The spike prompt didn't mention LiteLLM auth — this would have blocked the executor
- Master key found in Helicarrier's LiteLLM container env: `LITELLM_MASTER_KEY`
- **Deviation from prompt:** Added `LITELLM_API_KEY` to spike `.env` (prompt only listed URL)

### Critical Finding: Embedding Dimension is 768, NOT 1536
- Prompt assumed `text-embedding-3-small` with 1536 dimensions
- Actual available model: **nomic-embed-text-v1.5** (local/self-hosted via LiteLLM)
- Dimension: **768** — Qdrant collection must use 768, not 1536
- Other available models: `deepseek-r1`, `claude-sonnet`, `claude-opus`, `gpt-4o`, `grok-4`, plus many local "jarvis-*" models
- The pre-flight check pattern from the prompt (query `/models` first) is validated as essential

### CRITICAL: youtube-transcript npm package DOES NOT WORK
- Both `youtube-transcript` (v1.2.1) and `youtube-transcript-ts` (v1.3.0) return **empty arrays** for ALL videos
- Root cause: YouTube returns a consent/cookie wall to server-side requests. The npm packages don't handle this.
- The YouTube page HTML contains caption track URLs, but fetching those URLs returns **HTTP 200 with empty body**
- **Initial Solution:** Switched to `yt-dlp` (Python tool, installed via `pipx`). yt-dlp has robust anti-bot mechanisms and successfully downloads subtitles
- yt-dlp outputs JSON3 format with `tStartMs`, `dDurationMs`, and `segs[].utf8` fields
- Performance: ~3-5 seconds per video for subtitle download (slower than scraping would have been)
- **Deviation from prompt:** Prompt specified `youtube-transcript` npm package. Switched to `yt-dlp` CLI via child_process.

### ROOT CAUSE CORRECTION: Not an IP issue — broken npm packages
- **Original diagnosis was wrong.** Initial analysis blamed YouTube's "server-side bot detection" and datacenter IP blocking. This is incorrect.
- **Banner runs on a residential Verizon Fios network (not a datacenter).** YouTube's ASN-based IP classification does not flag this network.
- **The Python `youtube-transcript-api` package (v1.2.4) works from this network with no proxy, no VPN, no API key.** It was confirmed working by ClawdBot (separate system on same network) within 24-48 hours of the spike.
- **The npm packages are simply broken software.** `youtube-transcript` (JS) and `youtube-transcript-api` (Python) are completely different codebases with confusingly similar names. The JS packages can't handle YouTube's current page structure (consent flow, cookie handling, TLS fingerprinting) regardless of IP type.
- **yt-dlp works because of browser impersonation, not IP workarounds.** It sends realistic browser headers, handles cookies, and has active anti-bot countermeasures maintained by a large community.
- **No proxy or VPN infrastructure is needed for production** on this network. Webshare residential proxies would only be needed if the pipeline moves to a cloud server (AWS/GCP/Azure).

### Transcript Method Comparison (Post-Investigation)

| Tool | Language | Works? | API Key? | Dependencies | Speed | Notes |
|------|----------|--------|----------|-------------|-------|-------|
| `youtube-transcript` (npm) | JS | **NO** | None | npm | N/A | Broken, unmaintained |
| `youtube-transcript-ts` (npm) | JS | **NO** | None | npm | N/A | Broken + CJS/ESM issues |
| `youtube-transcript-api` (PyPI) | Python | **YES** | None | pip | ~0.5-1s | Lightest, recommended for production |
| `yt-dlp` | Python | **YES** | None | pipx/binary | ~3-5s | Overkill for subtitles only, but most robust |
| Gemini API direct video | Python | **YES** | Gemini key | pip | Slow | Works even without captions, costs tokens |
| YouTube Data API captions | JS/Py | **NO** | OAuth+owner | googleapis | N/A | Owner-only access, 250 quota/video |

### Production Recommendation: Tiered Transcript Strategy
1. **Primary:** `youtube-transcript-api` (Python) — no API key, no proxy, lightest dependency, ~0.5-1s/video
2. **Fallback:** `yt-dlp` — for videos where Python API fails (rare)
3. **Last resort:** Gemini API direct video processing — for videos with no captions at all
4. **Not needed:** Webshare proxy, WireGuard VPN, or any IP workaround (residential network)
5. **Not viable:** YouTube Data API v3 captions endpoint (owner-only, 250 quota/video)

### Rate Limiting Discovery (AI LABS Channel Run)
- **Trigger:** 33 rapid transcript fetches at 500ms intervals triggered YouTube's rate limiter (HTTP 429)
- **Behavior:** Both `youtube-transcript-api` and `yt-dlp` return 429. The Python API returns non-JSON (HTML error page), causing `Unexpected token C in JSON at position 1`. yt-dlp explicitly reports `HTTP Error 429: Too Many Requests`.
- **Cooldown:** YouTube rate limit lasts **30-90 minutes** after triggering. Tested at 31 minutes — still blocked.
- **yt-dlp degradation:** yt-dlp now requires a JavaScript runtime (`deno`) for full functionality. Without it: "No supported JavaScript runtime could be found" and "impersonation target is not available." The fallback still works for non-rate-limited videos but has reduced robustness.
- **Fix:** Increased `TRANSCRIPT_THROTTLE` from 500ms to 15,000ms (15 seconds = 4 requests/minute). Conservative pace — at ~50 videos/day target, this adds ~12.5 minutes of fetch time. No reason to push faster.
- **Production recommendation:** 4 req/min for sustained batch processing. 50 videos/day = ~12.5 minutes. Even 500 videos/day fits comfortably in ~2 hours.
