# Pre-Start Concerns: Spike Prompt Review

**Reviewed by:** Claude (executor perspective — the AI that will run this spike)
**Date:** 2026-01-29
**Prompt reviewed:** `_bmad-output/pre-alpha-spike-prompt.md`

This document captures issues, gaps, and ambiguities found during review of the spike prompt **before execution begins**. The intent is to resolve these before starting so the spike runs smoothly and doesn't waste time on preventable blockers.

---

## Blocking Issues (Will stop execution)

### 1. ~~YouTube API Authentication Not Addressed~~ RESOLVED

~~The prompt references YouTube Data API v3 for fetching channel metadata, video details, tags, stats, and thumbnails — but never mentions how to authenticate.~~

**Resolution:** YouTube API key is now available in the `.env` file. The prompt should reference `YOUTUBE_API_KEY` in its `.env` template so the executor knows to expect it.

### 2. Transcript Fetching vs. Metadata Fetching Are Conflated

The prompt says:
> "Fetches the transcript using YouTube's transcript API (try `youtube-transcript` npm package or YouTube Data API v3)"

These are not interchangeable:

| Need | Method | Auth Required |
|------|--------|---------------|
| **Transcripts** | `youtube-transcript` npm package (scrapes from page) | None |
| **Transcripts** | YouTube Data API v3 captions endpoint | OAuth 2.0 (not just API key) |
| **Video/channel metadata** | YouTube Data API v3 (`videos.list`, `channels.list`) | API key |

The captions endpoint requires **OAuth 2.0** (user consent flow), not just an API key. This is significantly more complex than a simple key. The npm scraping package is the practical choice for transcripts.

**Impact:** If the executor tries the Data API for transcripts, they'll hit an OAuth wall and waste time. If they use only the npm package, they won't have metadata (tags, stats, etc.).

**Suggested fix:** Make explicit that the spike should use:
- `youtube-transcript` npm package for transcript text
- YouTube Data API v3 (API key auth) for video/channel metadata
- These are **two separate data sources** feeding into the pipeline

### 3. PostgreSQL Setup Has No Docker Command

The prompt provides a full Docker command for Qdrant and CloudBeaver but says only "check if shared AppServices PG exists, or spin up a new one" for PostgreSQL. If no shared PG exists, the executor needs:

- Docker image and version
- Port to expose
- Volume mount path
- Credentials to set
- Database name to create

**Suggested fix:** Add a Docker command block parallel to the Qdrant one:
```bash
ssh banner
docker run -d \
  --name knowledge-postgres \
  --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=knowledge \
  -e POSTGRES_PASSWORD=<from-env-or-generate> \
  -e POSTGRES_DB=knowledge_spike \
  -v /opt/knowledge/postgres/data:/var/lib/postgresql/data \
  postgres:16-alpine
```

Or specify which shared PG to use and how to check for it.

---

## High-Risk Issues (Will cause wasted time)

### 4. YouTube API Quota Not Mentioned

YouTube Data API v3 has a default quota of **10,000 units/day**.

| API Call | Cost per call |
|----------|--------------|
| `search.list` | **100 units** |
| `videos.list` | 1 unit |
| `channels.list` | 1 unit |
| `playlistItems.list` | 1 unit |

If the executor uses `search.list` to find videos from a channel, fetching 50 videos costs **5,000+ units** (multiple paginated calls at 100 units each). Across 3-5 channels, the daily quota is exhausted before finishing one batch.

**Suggested fix:** Recommend using `playlistItems.list` on the channel's "uploads" playlist (1 unit per call) instead of `search.list` (100 units per call). This is a **100x cost difference** for the same result. Add a note about the 10K daily quota so the executor plans batches accordingly.

### 5. No `.env` Template

The prompt mentions `spike/.env` but provides no template. The executor has to guess which variables are expected and what format to use.

**Suggested fix:** Add an example:
```env
# Infrastructure
QDRANT_URL=http://10.0.0.33:6333
POSTGRES_URL=postgresql://knowledge:password@10.0.0.33:5432/knowledge_spike
LITELLM_URL=http://10.0.0.27:2764

# YouTube
YOUTUBE_API_KEY=your-key-here

# Behavior
BATCH_SIZE=50
```

### 6. No Throttling or Rate-Limit Strategy

The prompt asks "any rate limiting issues with YouTube APIs?" as a discovery question but provides no initial strategy. Without deliberate throttling:
- YouTube may rate-limit or block the API key
- LiteLLM may queue or reject rapid embedding requests
- Qdrant bulk inserts may timeout

**Suggested fix:** Recommend a starting delay between API calls (e.g., 100-200ms) and mention the YouTube quota. Let the executor adjust based on what they observe, but don't start at full speed.

---

## Clarity Issues (Will cause confusion)

### 7. Two Findings Files — Unclear Relationship

The prompt requires updating two documentation files after each task:
- `spike/findings.md` — described as real-time discovery notes
- `_bmad-output/analysis/pre-alpha-findings.md` — described as cumulative summary

Both are updated "after completing each major task." The prompt doesn't clarify:
- Is one a draft and the other polished?
- Is one chronological and the other categorical?
- Should they contain the same information in different formats?

**Suggested fix:** Define the relationship explicitly. Example:
- `spike/findings.md` = **chronological raw log** (append-only, stream of consciousness, timestamped entries as things happen)
- `pre-alpha-findings.md` = **structured deliverable** (organized by the template categories — Challenges, Deviations, Lessons — updated periodically with polished insights)

### 8. `speaker_label` Column vs. "No Diarization" Rule

The `segments` table schema includes a `speaker_label` column, but the "What NOT to Build" section says "No diarization or speaker identification." This sends mixed signals.

**Suggested fix:** Add a note to the schema: `speaker_label (nullable — reserved for future use, leave NULL in spike)`.

### 9. Qdrant Payload Structure Not Specified

The PostgreSQL schema is detailed (every column defined), but the Qdrant payload structure is undefined. The executor needs to decide what metadata to store alongside vectors in Qdrant. This matters because it determines whether query results require a database round-trip or can be returned directly.

**Suggested fix:** Add a payload specification:
```
Qdrant payload per point:
- segment_id (int) — FK to PostgreSQL segments table
- video_id (int) — FK to PostgreSQL videos table
- channel_name (string) — for display in query results
- video_title (string) — for display
- text (string) — the segment text
- start_time (float) — segment start in seconds
- end_time (float) — segment end in seconds
- youtube_video_id (string) — for building YouTube URLs
```

### 10. npm Scripts Not Defined

The prompt mentions `npm run ingest` as the entry point but doesn't define other scripts. The `package.json` needs a `scripts` section.

**Suggested fix:** Suggest minimum scripts:
```json
{
  "scripts": {
    "ingest": "tsx src/ingest.ts",
    "query": "tsx src/query.ts",
    "setup-db": "tsx src/db/setup.ts"
  }
}
```

---

## Scope Creep Concerns (Will distract from core spike goals)

### 11. Qdrant "Features to Explore" Section

Six advanced Qdrant features listed (hybrid search, BM25, named vectors, payload indexes, collection aliases, TypeScript client). Even with "don't try to use all of these," the section invites exploration that doesn't serve the spike's core purpose of validating the ingestion pipeline.

**Recommendation:** Move to an appendix or "Future Exploration Notes" section. For the spike, basic dense vector cosine search is the only thing needed. The discovery question "does simple search produce useful results?" is more valuable than testing advanced retrieval.

### 12. PostgreSQL Extensions (ParadeDB, TimescaleDB)

`pg_trgm` and `pg_stat_statements` are reasonable (trivial to enable, genuinely useful). But ParadeDB and TimescaleDB are complex additions that require specific Docker images and configuration. They don't serve the spike's core validation goals.

**Recommendation:** Keep `pg_trgm` + `pg_stat_statements` as requirements. Move ParadeDB and TimescaleDB to a "consider for production" finding. Don't install them during the spike.

### 13. ~~CloudBeaver Deployment~~ RESOLVED (Partially)

~~Deploying CloudBeaver is a convenience tool that adds setup overhead.~~

**Resolution:** CloudBeaver is already running on Banner. The prompt should be updated to:
- Remove the `docker run` deployment command for CloudBeaver (it's already up)
- Replace it with: "After PostgreSQL is running, add the spike database as a new connection in the existing CloudBeaver instance at `http://10.0.0.33:8978`"
- The executor just needs to configure a database connection, not deploy the tool

---

## Minor Items

| # | Item | Note |
|---|------|------|
| 14 | **Commit strategy undefined** | Branch name specified (`spike/pre-alpha-ingest`) but no guidance on when to commit. Suggest: commit after each major task. |
| 15 | **`aspect_ratio` from thumbnails is unreliable** | Many channels use custom thumbnails that don't match video aspect ratio. Document as a known limitation. |
| 16 | **"Check if shared AppServices PG exists"** | The executor can't easily verify this. Provide a specific command or file path to check. |
| 17 | **No guidance on channel URL format** | YouTube channel URLs come in multiple formats (`/channel/UC...`, `/@handle`, `/c/name`). The executor needs to handle this or pick one format. |

---

## Summary

| Category | Count | Resolved |
|----------|-------|----------|
| Blocking issues | 3 | 1 (#1 — API key in .env) |
| High-risk issues | 3 | 0 |
| Clarity issues | 4 | 0 |
| Scope creep concerns | 3 | 1 (#13 — CloudBeaver already running) |
| Minor items | 4 | 0 |

The prompt's structure, scope control, and documentation requirements are strong. The main remaining gaps are around **YouTube API specifics** (quotas, transcript vs. metadata distinction) and **infrastructure setup completeness** (PostgreSQL Docker command). Resolving the 2 remaining blocking issues and 3 high-risk issues before starting would prevent significant wasted time during execution.
