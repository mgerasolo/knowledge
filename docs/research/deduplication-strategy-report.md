# Deduplication Strategy Research Report for KnowledgeStack

**Date:** 2026-01-30
**Researcher:** Claude Opus 4.5
**Scope:** Content ingestion pipeline deduplication across all entry points
**Status:** Research complete, architecture recommendation included

---

## Executive Summary

### Key Findings

1. **YouTube video IDs are globally unique, immutable, and never reused** -- making the 11-character video ID (`youtube_video_id`) a reliable natural key for the entire deduplication system. The existing spike schema already uses `TEXT UNIQUE NOT NULL` on this field, which is the correct foundation.

2. **A multi-layer deduplication architecture is required** -- no single check point is sufficient. The recommended approach is: early gate at ingestion entry (cheapest), PostgreSQL as the authoritative state tracker (single source of truth), deterministic Qdrant point IDs derived from video ID + chunk index (prevents vector duplicates without lookups), and n8n's Remove Duplicates node as a first-pass filter for RSS/cron triggers.

3. **The existing spike code already implements basic idempotency** via the `isVideoIngested()` function, but it has gaps: no in-flight protection (two concurrent pipelines could both pass the check), no state machine for partial failures (a video that fails at embedding is stuck), and no cross-path awareness (light mode vs full mode).

4. **Content-level deduplication (clips, mirrors, cross-channel reposts) is a Phase 2+ concern** that should not block Phase 1. The techniques exist (SimHash, MinHash, cosine similarity thresholds on embeddings) but add significant complexity. Phase 1 should capture the metadata needed to enable these checks later.

5. **PostgreSQL should be the single source of truth** for "what have we processed." Qdrant should be treated as a derived store that can be rebuilt from PostgreSQL state. This architectural decision simplifies every deduplication question.

---

## 1. YouTube Video ID as Primary Key

### 1.1 Is the YouTube Video ID Globally Unique and Stable?

**Yes, definitively.**

YouTube video IDs are 64-bit integers encoded as 11-character base64url strings using the character set `A-Za-z0-9_-`. The encoding uses URL-safe base64 (replacing `+` with `-` and `/` with `_`) without padding. [DEV Community, 2024; Archiveteam Wiki]

The ID space is enormous: 64^11 = approximately 7.3 x 10^19 possible IDs (73 quintillion). YouTube generates IDs randomly and checks for collisions server-side. At current upload rates, collision is mathematically negligible. The birthday paradox threshold is approximately 2^36 (68 billion) IDs, far beyond current usage. [Popular Mechanics, 2016; Mental Floss, 2016]

**Critical properties for deduplication:**

| Property | Value | Source |
|----------|-------|--------|
| Length | Always 11 characters | [Archiveteam] |
| Character set | `[A-Za-z0-9_-]` | [Archiveteam] |
| Underlying type | 64-bit integer, base64url encoded | [Archiveteam] |
| Last character constraint | Limited to 16 values: `[AEIMQUYcgkosw048]` | [Archiveteam] |
| Strict regex | `[A-Za-z0-9_-]{10}[AEIMQUYcgkosw048]` | [Archiveteam] |
| Practical regex | `[A-Za-z0-9_-]{11}` (sufficient for pipeline use) | [Various] |

### 1.2 Do Video IDs Ever Change?

**No.** A video ID is assigned at upload time and never changes, even if the video is edited, re-titled, or moved to a different channel. YouTube's official documentation confirms: "You can't replace a video. Any new video you upload to YouTube will get a new URL." [YouTube Help]

Re-uploading the same content always generates a new, different video ID. Deleted video IDs are never reassigned to new videos. This is enforced by database primary key constraints on YouTube's backend. [YouTube Help; Quora/YouTube Community]

**Implication for KnowledgeStack:** The `youtube_video_id` is a perfect natural key. It is stable across time, unique across all of YouTube, and never recycled. The existing `UNIQUE NOT NULL` constraint in the spike schema is correct and sufficient.

### 1.3 Extracting Video ID from URL Formats

YouTube URLs come in many formats. A robust extraction regex must handle all of them:

| URL Format | Example |
|------------|---------|
| Standard watch | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` |
| Short URL | `https://youtu.be/dQw4w9WgXcQ` |
| Shorts | `https://www.youtube.com/shorts/dQw4w9WgXcQ` |
| Embed | `https://www.youtube.com/embed/dQw4w9WgXcQ` |
| V path | `https://www.youtube.com/v/dQw4w9WgXcQ` |
| No-cookie embed | `https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ` |
| Mobile | `https://m.youtube.com/watch?v=dQw4w9WgXcQ` |
| With extra params | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120` |
| Playlist context | `https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLxxx` |

**Recommended comprehensive regex** (captures video ID in group 1):

```
/(?:https?:\/\/)?(?:www\.|m\.)?(?:youtu\.be\/|youtube(?:-nocookie)?\.com\/(?:embed\/|v\/|shorts\/|watch\?v=|watch\?.+&v=))([\w-]{11})(?!\w)/
```

[GitHub Gist afeld/1254889; labnol.org; GeeksforGeeks]

**Recommendation:** Implement this as a dedicated `extractVideoId(input: string)` utility that:
- First checks if the input is already a bare 11-character video ID
- Then tries the regex against various URL formats
- Returns `null` for invalid inputs
- Is used at every ingestion entry point before any processing begins

---

## 2. Pipeline-Level Deduplication

### 2.1 Where Should Dedup Checks Happen?

The research strongly supports a **multi-gate approach** with the cheapest checks first. The data engineering community consensus is: "Use unique event IDs, apply deduplication logic, use UPSERTs instead of INSERTs." [Airbyte, 2024; Start Data Engineering, 2024]

**Recommended gate sequence:**

```
Entry Point (RSS/Cron/Manual/API)
    |
    v
[Gate 1] n8n Remove Duplicates node (for n8n-triggered paths)
    |     - Cross-execution history, ~10K item buffer
    |     - Cheapest: in-memory check, no DB query
    |
    v
[Gate 2] PostgreSQL existence check (all paths)
    |     - SELECT status FROM videos WHERE youtube_video_id = $1
    |     - Authoritative source of truth
    |     - Returns current processing status
    |
    v
[Gate 3] Status-aware routing
    |     - 'indexed_full' -> skip (unless forced reprocess)
    |     - 'indexed_light' -> upgrade path (if full mode requested)
    |     - 'failed' -> retry path
    |     - 'processing' -> in-flight, skip or wait
    |     - NULL/not found -> proceed to ingest
    |
    v
[Gate 4] Pre-upload checks (for full mode)
    |     - Check Speakr for existing audio (by video ID tag)
    |     - Skip download if audio already uploaded
    |
    v
[Processing Pipeline]
    |
    v
[Gate 5] Qdrant upsert with deterministic IDs
          - Automatically overwrites existing vectors
          - No separate check needed
```

### 2.2 Handling In-Flight Items

This is a critical gap in the existing spike code. The `isVideoIngested()` function only checks for `transcript_status = 'fetched'`, meaning two concurrent processes could both start processing the same video.

**Recommended pattern: Optimistic locking via status transition.**

The PostgreSQL `INSERT ... ON CONFLICT ... DO UPDATE ... WHERE` pattern acts as a state machine guard. A process can only claim a video for processing if it is in a claimable state. The `WHERE` clause in the `DO UPDATE` ensures that status transitions only happen from valid prior states. [Brandur.org Idempotency Keys; Airbyte Idempotency Guide]

The sequence:
1. Attempt `INSERT INTO videos ... ON CONFLICT (youtube_video_id) DO UPDATE SET status = 'processing', claimed_at = NOW(), claimed_by = $worker_id WHERE videos.status IN ('discovered', 'queued', 'failed')`
2. Check `RETURNING` result -- if no rows returned, another worker already claimed it
3. Process the video
4. Update status to 'indexed_full' or 'indexed_light' on success, 'failed' on error

This is the same pattern used by Stripe for idempotency keys and by AWS Step Functions for pipeline state management. [Brandur.org, 2017; AWS Developer Blog]

### 2.3 Idempotency Patterns for Pipeline Stages

Each stage of the pipeline should be independently idempotent:

| Stage | Idempotency Mechanism |
|-------|----------------------|
| Video discovery | `ON CONFLICT (youtube_video_id) DO UPDATE` (upsert metadata) |
| Audio download | Check Speakr by video ID tag before downloading |
| Transcript fetch | Check `transcript_status` before re-fetching |
| Embedding generation | Deterministic -- same text always produces same vectors |
| Qdrant insertion | Deterministic point IDs -- upsert overwrites existing |
| Status update | Guarded state transitions with `WHERE` clause |

The key insight from the research: "If rerunning your pipeline scares you, it's not idempotent." [Start Data Engineering, 2024]

---

## 3. Database-Level Deduplication (PostgreSQL)

### 3.1 Schema Enhancements for Deduplication

The existing spike schema has a solid foundation with `youtube_video_id TEXT UNIQUE NOT NULL`. The following additions are recommended for production:

**Enhanced `videos` table columns:**

| Column | Type | Purpose |
|--------|------|---------|
| `ingestion_status` | `TEXT NOT NULL DEFAULT 'discovered'` | State machine status (replaces `transcript_status`) |
| `ingestion_mode` | `TEXT` | 'full' or 'light' -- tracks which path processed this video |
| `claimed_by` | `TEXT` | Worker/process ID that claimed this video for processing |
| `claimed_at` | `TIMESTAMPTZ` | When the claim was made (for stale claim detection) |
| `completed_at` | `TIMESTAMPTZ` | When processing finished |
| `retry_count` | `INTEGER DEFAULT 0` | Number of processing attempts |
| `content_hash` | `TEXT` | SHA-256 of transcript text (for content-level dedup) |
| `speakr_asset_id` | `TEXT` | Reference to Speakr audio asset (for full mode dedup) |
| `source_entry_point` | `TEXT` | 'rss', 'cron', 'manual', 'api' -- how we discovered it |

**Recommended unique constraints and indexes:**

```sql
-- Primary dedup constraint (already exists)
UNIQUE (youtube_video_id)

-- Composite index for status-based queries
CREATE INDEX idx_videos_status_mode ON videos(ingestion_status, ingestion_mode);

-- Index for stale claim detection
CREATE INDEX idx_videos_claimed ON videos(claimed_at) WHERE ingestion_status = 'processing';

-- Content hash for near-duplicate detection (Phase 2+)
CREATE INDEX idx_videos_content_hash ON videos(content_hash) WHERE content_hash IS NOT NULL;
```

### 3.2 Upsert Patterns

The spike already uses `ON CONFLICT (youtube_video_id) DO UPDATE` for both channels and videos, which is the correct pattern. For production, enhance the upsert to be status-aware:

**Discovery upsert** (when RSS/cron finds a video):
- Insert with status `discovered` if new
- On conflict: update metadata (view counts, etc.) but do NOT overwrite status if the video is already being processed or has been indexed

**Processing claim** (when pipeline picks up a video):
- Update status to `processing` with `WHERE status IN ('discovered', 'queued', 'failed')`
- This acts as an atomic lock -- only one worker can claim

**Completion update:**
- Set status to `indexed_full` or `indexed_light`
- Record `completed_at`, clear `claimed_by`

### 3.3 Content Fingerprinting

For detecting semantically identical content (same interview on two channels), compute a normalized hash of the transcript:

1. Normalize: lowercase, strip punctuation, collapse whitespace
2. Compute SHA-256 of normalized text
3. Store in `content_hash` column

This enables exact-duplicate detection. For near-duplicates, see Section 6.

---

## 4. Qdrant-Level Deduplication

### 4.1 Can Qdrant Enforce Uniqueness on Payload Fields?

**No.** Qdrant does not natively enforce unique constraints on payload fields. Uniqueness is only enforced at the **point ID level** -- upserting a point with an existing ID replaces the previous point. [Qdrant Documentation - Points; Qdrant GitHub Discussion #3461]

This means Qdrant cannot independently prevent duplicate embeddings based on `youtube_video_id` in the payload. However, this limitation is easily overcome with deterministic point IDs.

### 4.2 Deterministic Point ID Strategy

**Recommended approach: UUID v5 from video ID + chunk index.**

UUID v5 generates deterministic UUIDs from a namespace + name string using SHA-1 hashing. The same input always produces the same UUID. [Qdrant Discussion #3461; InventiveHQ UUID v5 Guide]

**Formula:**
```
point_id = UUIDv5(KNOWLEDGESTACK_NAMESPACE, "{youtube_video_id}:{chunk_index}")
```

For example:
- Video `dQw4w9WgXcQ`, chunk 0: `UUIDv5(NS, "dQw4w9WgXcQ:0")` -> always the same UUID
- Video `dQw4w9WgXcQ`, chunk 1: `UUIDv5(NS, "dQw4w9WgXcQ:1")` -> always the same UUID

**Benefits:**
- Re-processing the same video automatically overwrites existing vectors (Qdrant upsert)
- No need to query Qdrant before insertion to check for duplicates
- No need for an external ID mapping table
- Completely stateless and idempotent
- Works across any number of pipeline workers

**The existing spike uses `randomUUID()` for point IDs** -- this must be changed for production. Random UUIDs mean re-processing creates duplicate vectors rather than overwriting.

**Custom namespace:** Define a fixed UUID namespace for KnowledgeStack (generated once, stored in config):
```
KNOWLEDGESTACK_NAMESPACE = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"  // generate once
```

### 4.3 Handling Re-Processing (Update vs Skip vs Version)

With deterministic point IDs, the decision is simple:

| Scenario | Behavior |
|----------|----------|
| Same video, same chunk boundaries | Upsert overwrites -- identical content, no harm |
| Same video, different chunking strategy | New chunk indexes generate new UUIDs; old points persist with old indexes |
| Upgraded light -> full mode | Full mode uses different namespace prefix or chunk scheme; both coexist or old points are explicitly deleted |
| Forced reprocess | Same deterministic IDs, Qdrant upserts overwrite -- works automatically |

**For version transitions** (e.g., changing embedding model or chunk size): include the version in the namespace or name string:
```
point_id = UUIDv5(NS, "v2:{youtube_video_id}:{chunk_index}")
```

This creates entirely new point IDs, allowing old and new versions to coexist during migration.

### 4.4 Pre-Insertion Existence Checks

With deterministic IDs, **no pre-insertion check is needed for deduplication.** Qdrant's upsert is inherently idempotent. However, if you want to skip the embedding computation cost entirely (embeddings are the expensive part), check PostgreSQL first, not Qdrant. PostgreSQL is the source of truth for "has this video been fully processed."

---

## 5. Cross-Path Deduplication

### 5.1 Light Mode to Full Mode Upgrade

A video processed via light mode (caption scraping -> Qdrant) may later need full mode processing (audio download -> Speakr -> transcription -> Qdrant). This is an "upgrade" path.

**Recommended approach:**

1. PostgreSQL tracks `ingestion_mode` ('light' or 'full') per video
2. When full mode is requested for a video already in 'indexed_light' status:
   - Transition status to 'upgrading'
   - Run the full pipeline (download, Speakr, transcription)
   - **Delete old Qdrant points** for this video (by filtering on `youtube_video_id` payload)
   - Insert new Qdrant points with full-mode transcript and deterministic IDs
   - Update status to 'indexed_full', mode to 'full'
3. The full mode transcript is the authoritative version; it replaces light mode entirely

**Why delete-then-insert rather than upsert:** Light mode and full mode may produce different numbers of chunks with different boundaries. Upsert would leave orphan chunks from the light mode that do not exist in full mode. A clean delete-then-insert is safer.

**Qdrant deletion by payload filter:**
Qdrant supports deleting points by payload filter, so you can delete all points where `youtube_video_id = "xxx"` before inserting the new set.

### 5.2 Full Mode Should Block Light Mode

If a video already has `ingestion_mode = 'full'`, a light mode request should be silently skipped. Full mode is strictly superior (Speakr transcription vs caption scraping).

**Decision matrix:**

| Current State | Requested Mode | Action |
|--------------|----------------|--------|
| Not found | Light | Process light |
| Not found | Full | Process full |
| indexed_light | Light | Skip (already done) |
| indexed_light | Full | Upgrade to full |
| indexed_full | Light | Skip (full is superior) |
| indexed_full | Full | Skip (already done) unless force-reprocess |
| processing | Either | Skip (in-flight) |
| failed | Either | Retry with requested mode |

### 5.3 Single Source of Truth

**PostgreSQL is the single source of truth** for what has been processed. Not Qdrant, not Speakr, not n8n.

Rationale:
- PostgreSQL supports rich queries (status, mode, date ranges, channel filters)
- PostgreSQL supports transactional state changes
- PostgreSQL supports concurrent access with locking
- Qdrant and Speakr can be rebuilt from PostgreSQL state if needed
- n8n's dedup history is volatile and limited in scope

Every ingestion entry point (RSS, cron, manual, API) must check PostgreSQL before proceeding.

---

## 6. Content-Level Deduplication

### 6.1 Detecting Clips/Excerpts

YouTube clips are separate videos with their own unique video IDs. There is no reliable automated way to detect that a clip is an excerpt of a longer video. [yt-dlp Issue #9137]

**Available signals for clip detection:**

| Signal | Reliability | Method |
|--------|-------------|--------|
| Video duration | High | Clips are typically < 60 seconds; parent videos > 10 minutes |
| Title patterns | Medium | Clips often contain "clip", "excerpt", "#shorts", or reference the parent |
| Description links | Medium | Clips often link to the full video in description |
| Channel metadata | Low | YouTube Shorts badge (`is_short` flag from API) |
| YouTube API attribution | Low | yt-dlp feature request for parent video extraction exists but is not implemented |

**Recommended Phase 1 approach:**
- Store the `is_short` flag (already in spike schema)
- Store full description text (already captured)
- Add a `parent_video_id` nullable foreign key column for manual or heuristic linking
- Defer automated clip detection to Phase 2

**Recommended Phase 2 approach:**
- Parse descriptions for YouTube URLs and extract referenced video IDs
- Use transcript similarity (see 6.3) to detect overlapping content
- Build a `video_relationships` table with relationship types: `clip_of`, `mirror_of`, `continuation_of`, `references`

### 6.2 Re-uploaded/Mirrored Content Across Channels

YouTube's Content ID system detects re-uploads using audio and video fingerprinting at an industrial scale (50 million reference files, 98% of copyright management). [YouTube Help - Content ID; Wikipedia - Content ID] However, this system is not accessible to third-party applications.

**For KnowledgeStack's purposes:**

1. **Exact duplicates** (same transcript text): Detected by comparing `content_hash` (SHA-256 of normalized transcript). O(1) lookup via indexed column.

2. **Near-duplicates** (same interview on host and guest channels, slightly different edits): Requires more sophisticated approaches.

### 6.3 Near-Duplicate Detection Approaches

The research literature offers several approaches, ordered by complexity:

**Tier 1 -- Transcript Hash (Phase 1, recommended):**
- SHA-256 of normalized transcript text
- Detects exact verbatim duplicates only
- Zero false positives, trivial to implement

**Tier 2 -- SimHash/MinHash (Phase 2, recommended):**
- SimHash: Generates a 64-bit fingerprint; near-duplicates differ by small Hamming distance. Used by Google for web-scale dedup. [Google Research, 2007; Trafilatura]
- MinHash + LSH: Estimates Jaccard similarity between document shingle sets. Used by Google News. [Wikipedia - MinHash; Milvus Blog]
- Threshold: Documents with SimHash Hamming distance <= 3 (out of 64 bits) or Jaccard similarity >= 0.8 are near-duplicates

**Tier 3 -- Embedding Similarity (Phase 2+, already available):**
- Since every transcript chunk is already embedded in Qdrant, you can search for existing similar content before inserting
- Cosine similarity threshold >= 0.95 indicates near-duplicate chunks
- This is expensive at scale but leverages existing infrastructure

**Tier 4 -- Audio Fingerprinting (Phase 3+, for full mode only):**
- Tools like Panako or Chromaprint can generate audio fingerprints
- Detects content overlap even with different audio quality or compression
- Only applicable when audio is downloaded (full mode)
- Used in production by YouTube's Content ID, Shazam, and the Maze system [ACM Multimedia, 2022]

**Recommendation:** Implement Tier 1 in Phase 1. Plan schema for Tier 2. Defer Tiers 3-4 until the content library is large enough to warrant the complexity.

---

## 7. State Machine for Video Processing

### 7.1 Recommended States

Based on analysis of AWS Step Functions, Azure Data Factory, Google SRE pipeline guidance, and the specific needs of KnowledgeStack's multi-path pipeline:

```
                      +-------------+
     RSS/Cron/API --> | discovered  |
                      +------+------+
                             |
                    +--------v--------+
                    |     queued      |  (optional, for priority scheduling)
                    +--------+--------+
                             |
           +---------+-------+--------+---------+
           |                                    |
  +--------v--------+               +----------v---------+
  | downloading     |               | scraping_captions  |
  | (full mode)     |               | (light mode)       |
  +--------+--------+               +----------+---------+
           |                                    |
  +--------v--------+                          |
  | transcribing    |                          |
  | (Speakr)        |                          |
  +--------+--------+                          |
           |                                    |
           +----------------+-------------------+
                            |
                   +--------v--------+
                   |   embedding     |
                   +--------+--------+
                            |
                   +--------v--------+
                   |   indexing      |  (Qdrant upsert)
                   +--------+--------+
                            |
              +-------------+-------------+
              |                           |
     +--------v--------+        +--------v--------+
     | indexed_light   |        | indexed_full    |
     +-----------------+        +-----------------+
              |
     +--------v--------+
     |   upgrading     |  (light -> full transition)
     +--------+--------+
              |
     +--------v--------+
     | indexed_full    |
     +-----------------+


     Any state --> failed (with retry_count, error details)
     failed --> queued (manual or automatic retry)
```

### 7.2 State Definitions

| State | Description | Entry Conditions |
|-------|-------------|-----------------|
| `discovered` | Video ID seen for the first time via any entry point | RSS feed, cron scan, manual submission |
| `queued` | Approved for processing, waiting for worker capacity | Manual approval, automatic from discovered, retry from failed |
| `downloading` | Audio being downloaded for full mode | Worker claimed, full mode path |
| `scraping_captions` | Captions being fetched for light mode | Worker claimed, light mode path |
| `transcribing` | Audio uploaded to Speakr, awaiting transcription | Download complete, full mode only |
| `embedding` | Transcript being chunked and embedded | Transcript available (either path) |
| `indexing` | Vectors being written to Qdrant | Embeddings generated |
| `indexed_light` | Fully processed via light mode | Light mode pipeline complete |
| `indexed_full` | Fully processed via full mode | Full mode pipeline complete |
| `upgrading` | Transitioning from light to full mode | Upgrade requested for indexed_light video |
| `failed` | Processing failed at some stage | Any error; `retry_count` incremented |

### 7.3 State Transition Guards

Each transition should be protected by a PostgreSQL `WHERE` clause:

| Transition | Guard (`WHERE` clause) |
|------------|----------------------|
| discovered -> queued | `status = 'discovered'` |
| queued -> downloading | `status = 'queued' AND ingestion_mode = 'full'` |
| queued -> scraping_captions | `status = 'queued' AND ingestion_mode = 'light'` |
| downloading -> transcribing | `status = 'downloading'` |
| * -> embedding | `status IN ('transcribing', 'scraping_captions') AND claimed_by = $worker` |
| embedding -> indexing | `status = 'embedding' AND claimed_by = $worker` |
| indexing -> indexed_* | `status = 'indexing' AND claimed_by = $worker` |
| indexed_light -> upgrading | `status = 'indexed_light'` |
| * -> failed | `claimed_by = $worker` (only the claiming worker can fail it) |
| failed -> queued | `status = 'failed' AND retry_count < $max_retries` |

### 7.4 Stale Claim Detection

A video stuck in `processing`/`downloading`/`transcribing` state may indicate a crashed worker. Implement a stale claim detector:

- Run periodically (every 15 minutes)
- Query: `SELECT * FROM videos WHERE ingestion_status IN ('downloading', 'scraping_captions', 'transcribing', 'embedding', 'indexing') AND claimed_at < NOW() - INTERVAL '30 minutes'`
- Reset stale claims: set status to `failed` with error "stale claim timeout"
- These will be retried via the normal failed -> queued transition

### 7.5 Industry Precedents

This state machine pattern is consistent with:
- **AWS Step Functions**: States + transitions + error handling + retry logic [AWS Developer Blog]
- **AWS Data Pipeline**: `WAITING_ON_DEPENDENCIES` -> `RUNNING` -> `FINISHED`/`FAILED`/`CASCADE_FAILED` [AWS Data Pipeline Docs]
- **Google SRE**: "If retry logic is not implemented, correctness problems can result when work is dropped upon failure." [Google SRE Book - Data Processing Pipelines]
- **yt-dlp's download archive**: A flat file tracking `extractor:video_id` pairs -- conceptually the same as our `videos` table [yt-dlp Documentation]

---

## 8. n8n-Specific Deduplication

### 8.1 RSS Feed Trigger Limitations

The n8n RSS Feed Trigger determines "newness" based on the item's published date relative to the poll schedule. This is **not reliable** for deduplication -- it is known to produce 3-4x duplicate triggers for the same RSS item. [n8n Community Forum; Front2BackDev]

**Do not rely on the RSS Feed Trigger's built-in dedup for KnowledgeStack.** It should be treated as a hint, not a guarantee.

### 8.2 Remove Duplicates Node

n8n provides a dedicated Remove Duplicates node (overhauled in n8n 1.64.0) with cross-execution deduplication. [n8n Documentation]

**Key configuration for KnowledgeStack:**

| Setting | Recommended Value | Rationale |
|---------|-------------------|-----------|
| Operation | Remove Items Processed in Previous Executions | Cross-execution dedup |
| Scope | Workflow | Share dedup state across all RSS + cron triggers |
| Keep Items Where | Value Is New | Only pass through unseen video IDs |
| Value to Dedupe On | `youtube_video_id` field | Natural key |
| History Size | 50,000 | ~1 year of content at 100-150 videos/day |

**Limitations:**
- History size is capped -- oldest entries are dropped when the limit is reached (FIFO behavior is not well documented; users report confusion) [n8n Issue #23953]
- History is stored in n8n's internal database, not KnowledgeStack's PostgreSQL
- History can be lost during n8n upgrades or restarts
- The node cannot check processing status (only whether the ID was seen before)

### 8.3 Recommended n8n Dedup Architecture

```
[RSS Feed Trigger / Cron Trigger]
        |
        v
[Remove Duplicates Node]          <-- First-pass filter (n8n-internal)
  - Scope: Workflow
  - History: 50K items
  - Dedupe on: youtube_video_id
        |
        v
[HTTP Request to KnowledgeStack API]  <-- Authoritative check
  - POST /api/ingest/check
  - Body: { videoId: "xxx" }
  - Response: { status: "new" | "exists" | "failed" }
        |
        v
[IF Node: status == "new" OR status == "failed"]
        |
        v
[HTTP Request to KnowledgeStack API]  <-- Queue for processing
  - POST /api/ingest/queue
  - Body: { videoId: "xxx", mode: "light", source: "rss" }
```

This two-layer approach means:
- The Remove Duplicates node filters out ~95% of duplicates cheaply (no DB query)
- The API check catches the remaining ~5% that slipped through (n8n history limits, node restarts, manual submissions that bypassed n8n)
- PostgreSQL remains the single source of truth

### 8.4 n8n Polling Best Practices

- Set RSS polling interval to 15-30 minutes (YouTube RSS feeds update within 15 minutes of publish)
- Use the `--break-on-existing` mental model: if the first N items from an RSS feed are all already known, stop processing (reduces API calls)
- Log all n8n-triggered ingestion requests with `source_entry_point = 'rss'` or `source_entry_point = 'cron'` for audit

---

## 9. Recommended Architecture Summary

### 9.1 Deduplication Layers

```
Layer 0: URL Normalization
  - Extract youtube_video_id from any URL format
  - Canonical form: bare 11-character ID

Layer 1: n8n Pre-Filter (for automated triggers only)
  - Remove Duplicates node with 50K history
  - Cheap, fast, catches most duplicates
  - NOT authoritative

Layer 2: PostgreSQL Existence Check (all paths)
  - Single source of truth
  - Status-aware: checks ingestion_status and ingestion_mode
  - Atomic claim via ON CONFLICT ... WHERE guard
  - Handles in-flight protection

Layer 3: External Service Checks (full mode only)
  - Speakr: check for existing audio asset before download
  - YouTube API: skip metadata fetch if recently updated

Layer 4: Qdrant Deterministic IDs (vector store)
  - UUIDv5 from video_id + chunk_index
  - Upsert is inherently idempotent
  - No separate check needed

Layer 5: Content-Level Dedup (Phase 2+)
  - Transcript content_hash for exact duplicates
  - SimHash/MinHash for near-duplicates
  - Embedding similarity for semantic duplicates
```

### 9.2 Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary dedup key | `youtube_video_id` (11-char string) | Globally unique, immutable, never reused |
| Source of truth | PostgreSQL `videos` table | Transactional, queryable, supports state machine |
| Qdrant point IDs | Deterministic UUIDv5 from `{video_id}:{chunk_index}` | Eliminates need for lookup-before-insert |
| In-flight protection | `ON CONFLICT ... WHERE status IN (...)` | Atomic claim, no race conditions |
| State tracking | Explicit state machine with 11 states | Covers both light and full mode paths |
| n8n dedup | Remove Duplicates node + API callback | Two-layer filter; n8n is fast but not authoritative |
| Content dedup | Phase 1: content_hash; Phase 2: SimHash/MinHash | Incremental complexity; don't over-engineer early |
| Clip detection | Phase 1: metadata capture only; Phase 2: heuristic + similarity | No reliable automated method exists |

### 9.3 Migration from Spike to Production

The spike code already has good foundations. The key changes needed:

1. **Replace `randomUUID()` with deterministic `UUIDv5()`** for Qdrant point IDs (currently in `ingest.ts` line 233)
2. **Replace `transcript_status` with full state machine** (`ingestion_status` with 11 states)
3. **Add `ingestion_mode` column** to distinguish light vs full processing
4. **Add `claimed_by`/`claimed_at` columns** for in-flight protection
5. **Enhance `isVideoIngested()` to return status object** instead of boolean (needs to distinguish indexed_light from indexed_full)
6. **Add `content_hash` column** for future content-level dedup
7. **Create the `extractVideoId()` utility** for URL normalization at all entry points
8. **Configure n8n Remove Duplicates node** with workflow scope and 50K history

---

## 10. Bibliography

### YouTube Video ID & URL Parsing
- [DEV Community - Discover the Magic Behind YouTube's Unique Video IDs](https://dev.to/muhammadsaim/discover-the-magic-behind-youtubes-unique-video-ids-21ll)
- [Archiveteam - YouTube Technical Details](https://wiki.archiveteam.org/index.php/YouTube/Technical_details)
- [Popular Mechanics - How YouTube Makes Sure Every Video Can Have Its Own Unique Link](https://www.popularmechanics.com/technology/apps/a20039/how-youtube-link-generation-works/)
- [Mental Floss - Here's Why YouTube Will Practically Never Run Out of Unique Video IDs](https://www.mentalfloss.com/article/77598/heres-why-youtube-will-never-run-out-unique-video-ids)
- [Justinsomnia - Eighteen Quintillion YouTube Videos](https://justinsomnia.org/2016/04/eighteen-quintillion-youtube-videos/)
- [YouTube Help - Replace or Delete Your Video](https://support.google.com/youtube/answer/55770)
- [Quora - Deleted Video ID Reuse](https://www.quora.com/When-you-upload-a-video-on-YouTube-it-gets-assigned-a-random-link-id-if-you-deleted-that-video-will-the-link-the-video-ID-ever-be-used-for-a-different-video-Since-its-not-used-by-a-video-anymore)
- [varun.ch - This YouTube Video Contains Its Own ID](https://varun.ch/posts/video-id/)
- [GitHub Gist afeld/1254889 - YouTube Video ID Regex](https://gist.github.com/afeld/1254889)
- [labnol.org - RegEx Extract Video ID from YouTube URLs](https://www.labnol.org/code/19797-regex-youtube-id)
- [GeeksforGeeks - Get YouTube Video ID from URL Using JavaScript](https://www.geeksforgeeks.org/get-the-youtube-video-id-from-a-url-using-javascript/)

### Pipeline Deduplication & Idempotency
- [Airbyte - Understanding Idempotency in Data Pipelines](https://airbyte.com/data-engineering-resources/idempotency-in-data-pipelines)
- [Start Data Engineering - How to Make Data Pipelines Idempotent](https://www.startdataengineering.com/post/why-how-idempotent-data-pipeline/)
- [Brandur.org - Implementing Stripe-like Idempotency Keys in Postgres](https://brandur.org/idempotency-keys)
- [Confluent - Idempotent Reader Pattern](https://developer.confluent.io/patterns/event-processing/idempotent-reader/)
- [Google Cloud - Exactly-Once in Dataflow](https://cloud.google.com/dataflow/docs/concepts/exactly-once)
- [DEV Community - Why Idempotency Is So Important in Data Engineering](https://dev.to/chaets/why-idempotency-is-so-important-in-data-engineering-24mj)
- [Google SRE Book - Managing Data Processing Pipelines](https://sre.google/sre-book/data-processing-pipelines/)
- [AWS Developer Blog - Handling Errors, Retries, and Alerting in Step Functions](https://aws.amazon.com/blogs/developer/handling-errors-retries-and-adding-alerting-to-step-function-state-machine-executions/)

### yt-dlp Deduplication
- [yt-dlp Issue #9132 - Skip Downloading if Same ID Exists](https://github.com/yt-dlp/yt-dlp/issues/9132)
- [yt-dlp Issue #2754 - What Can --download-archive Be Used For](https://github.com/yt-dlp/yt-dlp/issues/2754)
- [yt-dlp Issue #9137 - Extract Parent Video URL from Shorts](https://github.com/yt-dlp/yt-dlp/issues/9137)
- [ArchWiki - yt-dlp](https://wiki.archlinux.org/title/Yt-dlp)

### Qdrant Deduplication
- [Qdrant Documentation - Points](https://qdrant.tech/documentation/concepts/points/)
- [Qdrant Documentation - Payload](https://qdrant.tech/documentation/concepts/payload/)
- [Qdrant GitHub Discussion #3461 - Best Practices for ID Generation](https://github.com/orgs/qdrant/discussions/3461)
- [Qdrant GitHub Discussion #5646 - Point ID Format](https://github.com/orgs/qdrant/discussions/5646)
- [DrDroid - Qdrant Duplicate Entry](https://drdroid.io/stack-diagnosis/qdrant-duplicate-entry)
- [Medium/Razroo - How to Update Existing Vector in Qdrant](https://medium.com/razroo/how-to-update-an-existing-vector-in-qdrant-using-an-external-database-for-uuid-management-ec99cf5a50b1)

### UUID v5 / Deterministic IDs
- [InventiveHQ - When Should I Use UUID v5](https://inventivehq.com/blog/when-to-use-uuid-v5-deterministic-id-generation)
- [DEV Community - Generating Deterministic UUIDs with Symfony](https://dev.to/javiereguiluz/generating-deterministic-uuids-from-arbitrary-strings-with-symfony-4ac6)

### Content-Level Deduplication
- [Google Research - Detecting Near-Duplicates for Web Crawling (SimHash)](https://research.google.com/pubs/archive/33026.pdf)
- [Wikipedia - MinHash](https://en.wikipedia.org/wiki/MinHash)
- [Spot Intelligence - SimHash Ultimate Guide](https://spotintelligence.com/2023/01/02/simhash/)
- [Milvus Blog - MinHash LSH for Fighting Duplicates](https://milvus.io/blog/minhash-lsh-in-milvus-the-secret-weapon-for-fighting-duplicates-in-llm-training-data.md)
- [Trafilatura Documentation - Deduplication](https://trafilatura.readthedocs.io/en/latest/deduplication.html)
- [GitHub - MinishLab/semhash - Semantic Text Deduplication](https://github.com/MinishLab/semhash)
- [ACM Multimedia - Maze: Web-Scale Video Deduplication](https://dl.acm.org/doi/10.1145/3503161.3548145)

### Audio Fingerprinting
- [ResearchGate - Using Audio Fingerprinting for Duplicate Detection](https://www.researchgate.net/publication/4137084_Using_Audio_Fingerprinting_for_Duplicate_Detection_and_Thumbnail_Generation)
- [ResearchGate - Audio Fingerprinting for Media Synchronisation](https://www.researchgate.net/publication/232552339_Audio_Fingerprinting_for_Media_Synchronisation_and_Duplicate_Detection)
- [YouTube Help - How Content ID Works](https://support.google.com/youtube/answer/2797370)
- [Wikipedia - Content ID System](https://en.wikipedia.org/wiki/Content_ID_(system))

### n8n Deduplication
- [n8n Docs - RSS Feed Trigger Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.rssfeedreadtrigger/)
- [n8n Docs - Remove Duplicates Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.removeduplicates/)
- [n8n Community - RSS Feed Trigger Posts Duplicates](https://community.n8n.io/t/rss-feed-trigger-posts-duplicates-how-to-process-each-item-only-once/176582)
- [n8n Community - How Does n8n Remove Dedup History at Limit](https://community.n8n.io/t/how-does-n8n-remove-deduplication-history-when-it-reaches-limit/186204)
- [n8n Issue #23953 - Remove Duplicates History Size Error](https://github.com/n8n-io/n8n/issues/23953)
- [Front2BackDev - Fixing the n8n RSS Feed Trigger](https://www.front2backdev.com/n8n-rss-feed-trigger/)

### PostgreSQL Patterns
- [Neon - PostgreSQL UPSERT Statement](https://neon.com/postgresql/postgresql-tutorial/postgresql-upsert)
- [Prisma Data Guide - INSERT ON CONFLICT](https://www.prisma.io/dataguide/postgresql/inserting-and-modifying-data/insert-on-conflict)
- [Fiddler AI Blog - Scalable Deduplication with PostgreSQL Status Tracking](https://www.fiddler.ai/blog/scalable-deduplication-clickhouse)
- [Dennis Theurer - Idempotent Database Inserts Getting It Right](https://dnnsthnnr.com/blog/idempotent-database-inserts-getting-it-right)
