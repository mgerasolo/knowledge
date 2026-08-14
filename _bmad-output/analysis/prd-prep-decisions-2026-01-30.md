# PRD Prep Decisions — Party Mode Output
**Date:** 2026-01-30
**Source:** Party Mode stress-test of Product Brief

These decisions were captured during Party Mode and should inform the PRD workflow.

---

## 1. Speakr API Investigation Results

### Ingest (n8n → Speakr)
- **Endpoint:** `POST /api/v1/recordings/upload` (multipart/form-data)
- **Audio files only** — cannot push pre-existing transcript text. Pipeline must download YouTube audio and upload to Speakr.
- **No source URL field** on Recording model. Workaround: store YouTube URL in the `notes` field.
- **No bulk upload** — one file at a time (can parallelize HTTP requests).
- **Auto-queues transcription** after upload — no separate call needed.
- **Can set during upload:** `notes`, `language`, `min_speakers`, `max_speakers`, `tag_ids`
- **Cannot set during upload:** `title` (AI-generated post-transcription; can PATCH after)
- **Must poll for completion:** `GET /api/v1/recordings/{id}/status` — no webhooks.

### Outgest (Speakr → Qdrant pipeline)
- **32 endpoints total**, well-suited for our pipeline.
- `GET /api/v1/recordings` — paginated (max 100/page), filterable by status, date range, tag.
- `GET /api/v1/recordings/{id}/transcript?format=json` — structured segments with speaker, text, start/end timestamps. Ideal for chunking.
- Tags, speakers, summaries, notes all accessible.
- `q` search param searches title/participants only — not transcript content.
- No semantic search via API v1 (Inquire Mode endpoints exist but undocumented/unsupported).

### Architecture Implication — Resilient Pipeline with Fallback (MAJOR DECISION)

**Full mode is the default. Light mode serves two purposes: (1) deliberate choice for lower-priority or simpler channels to conserve API capacity, and (2) automatic fallback when rate limits are hit.**

#### Full Mode (default — all channels)
1. YouTube → download audio (yt-dlp) → upload to Speakr
2. Speakr transcribes via WhisperX with diarization
3. Pipeline polls until completion, then PATCHes metadata (title, tags, YouTube URL in notes)
4. Content available in Speakr UI (KnowledgeVault) + later synced to Qdrant (KnowledgeCollege)

**Characteristics:** Longer processing (minutes per video), audio bandwidth (~28 MB/30min video), diarization included, content lives in Speakr + Qdrant. This is the desired path for every video.

#### Light Mode (deliberate or automatic fallback)
1. YouTube → scrape captions via `youtube-transcript-api` (text only, ~60 KB)
2. Text goes **directly to Qdrant** (KnowledgeCollege) — bypasses Speakr entirely
3. No audio download, no diarization

**Light mode as triage (MVP):** Every new video goes through a triage step first. Triage doesn't always need the full caption scrape — YouTube's video description and metadata alone are often sufficient to assess content value, especially for channels where we already know the creator's interests and format.

**MVP pipeline flow — n8n triage-first workflow:**
1. New video detected → metadata triage (title, description, duration, channel context)
2. Triage decision (per-channel rules):
   - **Auto-full:** High-priority multi-speaker channels → straight to full mode
   - **Light scrape:** Caption scrape to Qdrant (sufficient for single-speaker, lower-priority, or backlog)
   - **Description-only triage:** For channels like Scott Adams (daily hour-long videos, single speaker) — use description to identify which specific videos contain target content (e.g., micro lessons) before committing even to caption scraping at scale
3. Full mode (if selected): audio download → Speakr → diarized transcript

**Scott Adams example:** 10 years of daily 1-hour videos, single speaker. Full audio download for all of them is excessive — only his voice, no diarization value. Light mode with description-based filtering to find the micro-lesson segments, caption scrape the winners, full mode only if specific high-value content is identified.

**User interest profiles enhance triage:** When we have rich channel/creator profiles (what the person covers, their recurring segments, known topics), the triage step can use that context to make smarter full-vs-light decisions without even reading captions.

**Four roles for light mode:**
- **Triage/preview (MVP):** Every video gets light-mode first to assess content before committing to full audio pipeline
- **Deliberate per-channel:** Lower-priority or single-speaker channels where full mode isn't worth the API cost
- **Age-based backlog:** Historical content beyond a recency threshold (e.g., full mode for last year, light mode for the year before). Keeps audio download volume manageable.
- **Automatic fallback:** When YouTube rate limits block audio downloads — ensures content is still captured during throttling. Flagged for full-mode retry when capacity allows.

**Post-MVP enhancement:** Per-channel configurable thresholds for full mode depth and light mode depth (not just a binary toggle).

**Characteristics:** Fast (~1 second per video), negligible bandwidth, no diarization, content lives in Qdrant only (NOT in Speakr UI).

**Webshare proxies already available.** Matt has an existing Webshare.com residential proxy subscription ($6/month, 10 concurrent connections) from another project — currently unused. For bulk operations like backlog loading, route audio downloads through Webshare proxies instead of Banner's residential IP. This protects Banner from being flagged/blocked by YouTube during high-volume operations. Banner IP stays clean for daily steady-state ingestion; Webshare handles the heavy lifting. No additional cost.

#### Escalation Ladder (in order of preference)
1. **Full mode via Banner IP (10.0.0.33)** — primary path, residential IP, smart spacing
2. **Full mode via Webshare residential proxies** — split load across IPs when Banner IP is throttled (webshare.com)
3. **Light mode fallback** — caption scraping when all audio download paths are blocked. Content captured but degraded (no diarization, not in Speakr). Queued for full-mode retry later.

#### Light Mode Content Is NOT in Speakr
Light mode bypasses KnowledgeVault (Speakr) — that content is only in Qdrant. This is acceptable because:
- Content is still captured and searchable (just not in Speakr UI)
- Users can still watch the original video on YouTube
- For **deliberate** light mode channels: this is the intended permanent state unless the channel is upgraded
- For **fallback** light mode: flagged for full-mode retry when capacity allows

#### Rate Limiting & Monitoring (REQUIRED)
- **Smart spacing:** Configurable delays between YouTube API calls (yt-dlp and caption scraping)
- **429 detection & alerting:** Pipeline must flag API throttling/blocking immediately and notify admin
- **Auto-backoff:** When throttling is detected, automatically increase delays and queue remaining work
- **Proxy failover:** Escalate to Webshare residential proxies before falling back to light mode
- **Light mode retry queue:** Track videos ingested via light mode; auto-retry full mode when capacity allows
- **Dashboard visibility:** Rate limit status, error counts, throttle events, proxy usage, and light-mode backlog visible in channel management portal
- **Spike findings:** 4 req/min is safe for caption scraping; audio downloads need wider spacing
- **Per-IP awareness:** All downloads originate from Banner (10.0.0.33) — single residential IP, must not be burned. Webshare proxies provide additional IPs.

---

## 2. Channel Management Portal UX (MVP)

Matt's simplified flow:
1. User submits YouTube channel URL
2. System returns: channel name, icon, summary, recent video list
3. User sets subscription parameters:
   - **Auto-recent:** All new videos going forward + last X days of backlog
   - **Manual queue:** Searchable queue for selective ingestion
4. Channel is now monitored

Post-MVP enhancement: Surface favorite guests from tracked topics to help discover new channels.

---

## 3. Ingestion Modes (Simplified for MVP)

**Two modes only (no AI hybrid at MVP):**
- **Auto-recent:** All new standard uploads (>90s) + configurable backlog depth (last X days)
- **Manual queue:** Searchable queue — user can find specific guests, topics, videos

**Deferred to post-MVP:**
- AI-suggested hybrid mode (requires training data)
- AI-suggested episode filtering

---

## 4. Content Type Classification

**Exclusions from ingestion:**
- **Shorts:** < 90 seconds duration (no official YouTube API flag; use duration heuristic)
- **Live broadcasts:** Detectable via `liveBroadcastContent` field in YouTube Data API v3
- **Premieres:** Upcoming livestream-style premieres (detect via `upcoming` status + fixed duration)

**Content type hierarchy (build data structures from day one):**
- `content_type` enum: `video | episode | live | clip | short`
- `is_clip`: boolean — true if this content is an excerpt from another video (clips can ALSO be shorts — a short excerpt from a longer video). Not mutually exclusive with content_type.
- `source_video_id`: nullable — if `is_clip`, references the source video
- `episode_number`: nullable integer (for recurring numbered series like JRE, Lex Fridman, Scott Adams)
- `series_name`: nullable string
- **Videos** = all standard uploads (>90s). The default type.
- **Episodes** = subset of videos with recurring numbering. All episodes are videos. YouTube's Podcasts tab/playlist provides a reliable episode flag with numbering (e.g., "338 episodes" on Startup Ideas podcast).
- **Lives** = live broadcasts — detectable via `liveBroadcastContent` field. Excluded from MVP ingestion but tracked in data model.
- **Clips** = excerpts from longer content (future). Can overlap with shorts (a short clip is both).
- **Shorts** = <90s — excluded from MVP ingestion.

**Episode detection signals:**
- YouTube Podcasts playlist membership (strong signal — YouTube numbers these)
- Title pattern matching (e.g., "#338", "Ep. 42", "Episode 7")
- Series/channel convention (channels that exclusively produce numbered episodes)

**Gate:** "Zero missed **videos** (standard uploads >90s; Shorts and live broadcasts excluded)"

**Long-term ingestion enhancement:** Playlists as ingestion points — subscribe to curated playlists, not just channels. Enables ingestion of topic-specific collections, guest compilations, and podcast series directly.

---

## 5. Zero Missed Videos Verification

- Compare against a **web scrape** of the channel page
- YouTube API alone may have delays; scraping confirms completeness
- Verification runs periodically (daily cron already planned)

---

## 6. Diarization Strategy

- Use **Speakr's built-in** WhisperX diarization
- Evaluate quality during MVP; enhance later if needed
- No custom diarization pipeline at MVP

---

## 7. Initial 50 Channels

- Source: `docs/reference-youtube-channels.md` (46 channels across 4 tiers x 5 domains)
- Supreme + Leaders tiers = fully loaded
- Select Mid-tier channels to reach 50
- Matt will finalize selection during PRD/implementation

---

## 8. Parallelizable Work (Bob's Note)

The four product MVPs have sequential dependencies but some work can overlap:
- KnowledgeVault deployment can start while KnowledgeFeed n8n pipelines are being built
- Qdrant setup can begin during KnowledgeVault stabilization
- Channel management portal development can parallel pipeline work

---

## 10. Final Party Mode Flags

### AGPL-3.0 License Compliance
- Treat Speakr as a **black-box Docker container** — never fork or modify source code
- All KnowledgeStack intelligence built as separate services layered on top
- This also simplifies upgrades: pull new Speakr releases cleanly without merge conflicts

### Audio File Storage — Synology NAS
- Speakr stores audio files after upload. At 20-50 videos/day × ~28 MB each = 0.5-1.4 GB/day accumulating
- **Store audio on Synology NAS** instead of Banner's local disk to avoid filling local storage
- Performance impact expected to be acceptable for async transcription workloads (not latency-sensitive)
- Can move files to local storage as needed for performance-critical operations
- PRD should address retention policy (keep forever? delete after transcription? configurable?)

### Zero Missed Videos — Verification Method
- Not Playwright/Puppeteer scraping — use **independent YouTube Data API `search` query** against what we actually ingested
- Purpose: find gaps between what YouTube published and what our pipeline captured
- Could also compare RSS feed results against API search results to catch RSS-specific gaps
- Playwright comparison is a heavier-weight option if API-based verification proves insufficient

### Diarization Quality — Acceptance Criteria
- Using Speakr's built-in WhisperX diarization — no control over the implementation
- Cannot easily measure or grade diarization quality programmatically
- **Success criteria:** Speakr's diarization is sufficient for our needs (subjective evaluation during KnowledgeVault MVP)
- If insufficient, evaluate alternatives post-MVP — but don't block on it

### Research Workflow — Not Skipped, Needs Formal Pass
- BMAD Research workflow (Phase 1) is still "pending" in workflow status
- Brainstorming ≠ Research — they're separate workflows
- ~90% of research content already captured through party mode (Speakr API, YouTube API, content types, rate limits)
- **Decision:** Run the formal Research workflow before PRD to catch the remaining 10% and satisfy the BMAD process
- This will also produce a proper research output document that the PRD can reference

---

## 11. Product Brief Revisions Applied

Party mode resulted in these changes to the Product Brief:
1. **Executive Summary** — Changed from "infrastructure, not application" to "engine that feeds downstream AI applications — spanning content management at front, searchable repository in middle, intelligence infrastructure at back"
2. **MVP Scope** — Restructured from Phase 1/Phase 2 to four product MVPs (KnowledgeFeed, KnowledgeVault, KnowledgeCollege, KnowledgeLink)
3. **KnowledgeCollege MVP** — Slimmed from 5 features to 3 (Qdrant pipeline + data ownership + basic tagging)
4. **Out of Scope** — Entity graph, AI synthesis, cross-video queries moved from MVP
5. **Success Criteria** — Per-product gates, terminology fix (videos not episodes)
6. **Per-channel modes** — Simplified to auto-recent + manual queue (no AI hybrid at MVP)
