# KnowledgeEnroll n8n Workflow Specifications

**Date:** 2026-03-23
**Status:** Deployed and Running
**Target:** Helicarrier (10.0.0.27)

> [Updated 2026-03-31: spike learnings — all 3 workflows deployed with actual IDs and MCP Gateway integration]

## Overview

Three workflows deployed for KnowledgeEnroll pipeline:

| Workflow | ID | Trigger | Purpose | Status |
|----------|----|---------|---------|--------|
| RSS Channel Monitor | `jSIl3ztDpfyEqDzN` | Schedule (5 min) | Poll YouTube RSS feeds, detect new videos | **Running** |
| Video Ingest Orchestrator | `wDHhaqklto0ENwSK` | Claimed from PostgreSQL | Process video: claim → transcript (MCP Gateway) → SurrealDB + Speakr | **Running** |
| Embedding Sync | (TBD) | Schedule (5 min) | Generate embeddings for new segments | **Running** |

**Key change from spec:** Transcripts are fetched via MCP Gateway (`http://10.0.0.27:2780/mcp`) instead of the YouTube Transcript Fetcher webhook. The orchestrator claims items from PostgreSQL, calls the embedding service on Banner:5030, which fetches transcripts via MCP Gateway and stores segments in SurrealDB.

---

## Workflow 1: RSS Channel Monitor (`jSIl3ztDpfyEqDzN`)

### Purpose
Poll all active YouTube channel RSS feeds and detect new videos.

### Trigger
- **Schedule:** Every 5 minutes (was 30 min in spec; increased frequency during spike)
- **Manual:** Webhook for on-demand refresh

### Logic

```
START
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. Query PostgreSQL for active channels │
│    SELECT * FROM channels               │
│    WHERE is_active = true               │
│    AND ingestion_mode != 'paused'       │
│    ORDER BY last_checked_at ASC NULLS FIRST │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 2. For each channel (batch of 10):      │
│    - Fetch RSS feed                     │
│    - Parse <entry> items                │
│    - Extract: video_id, title, published│
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 3. For each video in RSS:               │
│    - Check if youtube_video_id exists   │
│      in pipeline_items table            │
│    - If NOT exists: INSERT as           │
│      status='discovered'                │
│    - If exists: skip (dedup)            │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 4. Update channel.last_checked_at       │
│    Reset consecutive_failures on success│
│    Increment on failure                 │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 5. If new videos found:                 │
│    - Trigger Video Ingest Orchestrator  │
│      via webhook for each new video     │
│    - OR: Just set status='queued'       │
│      and let orchestrator poll          │
└─────────────────────────────────────────┘
  │
  ▼
END
```

### Database Queries

**Get active channels:**
```sql
SELECT id, youtube_handle, youtube_channel_id, name, domain,
       check_interval_minutes, last_checked_at
FROM channels
WHERE is_active = true
  AND ingestion_mode != 'paused'
ORDER BY last_checked_at ASC NULLS FIRST
LIMIT 50;
```

**Insert new video (with dedup):**
```sql
INSERT INTO pipeline_items (
    youtube_video_id, youtube_url, title, published_at,
    channel_id, status, discovered_at
)
VALUES ($1, $2, $3, $4, $5, 'discovered', NOW())
ON CONFLICT (youtube_video_id) DO NOTHING
RETURNING id;
```

**Update channel after check:**
```sql
UPDATE channels
SET last_checked_at = NOW(),
    consecutive_failures = 0,
    last_video_at = GREATEST(last_video_at, $newest_video_date)
WHERE id = $channel_id;
```

### RSS Feed Format

YouTube RSS URL: `https://www.youtube.com/feeds/videos.xml?channel_id=UC...`

```xml
<feed>
  <entry>
    <yt:videoId>dQw4w9WgXcQ</yt:videoId>
    <title>Video Title</title>
    <published>2026-03-20T14:00:00+00:00</published>
    <link rel="alternate" href="https://www.youtube.com/watch?v=dQw4w9WgXcQ"/>
    <media:group>
      <media:thumbnail url="https://..."/>
      <media:description>Description...</media:description>
    </media:group>
  </entry>
</feed>
```

### Error Handling
- RSS fetch fails → increment `consecutive_failures`, log error
- 3+ consecutive failures → send Slack alert
- Parse error → log and continue with other channels

---

## Workflow 2: Video Ingest Orchestrator (`wDHhaqklto0ENwSK`)

### Purpose
Process a batch of videos through the full pipeline: claim → transcript (MCP Gateway) → SurrealDB + Speakr.

> [Updated 2026-03-31: spike learnings — claims from PostgreSQL, MCP Gateway for transcripts, parallel store]

### Trigger
- **Schedule:** Every 5 minutes (claims batch of 5 from `status='queued'` items)

### Payload (webhook mode)
```json
{
  "pipeline_item_id": "uuid",
  "youtube_video_id": "dQw4w9WgXcQ",
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "priority": "normal"
}
```

### Logic

```
START
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. Get item from webhook OR poll DB    │
│    for status='queued' items            │
│    (use claim_pipeline_item function)   │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 2. Update status to 'downloading'       │
│    Set claimed_by, claimed_at           │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 3. Call Embedding Service (Banner:5030) │
│    Which fetches transcript via         │  ◄── MCP GATEWAY (Helicarrier:2780)
│    MCP Gateway, chunks, and stores      │      (replaces YouTube Transcript Fetcher)
│    in SurrealDB                         │
│    Also uploads to Speakr in parallel   │
└─────────────────────────────────────────┘
  │
  ├── SUCCESS ──────────────────────────┐
  │                                      ▼
  │   ┌─────────────────────────────────────────┐
  │   │ 4a. Store transcript locally or         │
  │   │     prepare Speakr upload payload       │
  │   │     Update status to 'uploading'        │
  │   └─────────────────────────────────────────┘
  │                       │
  │                       ▼
  │   ┌─────────────────────────────────────────┐
  │   │ 5. Upload to Speakr API                 │
  │   │    POST /api/recordings                 │
  │   │    (or save transcript file to NAS      │
  │   │     for Speakr to pick up)              │
  │   └─────────────────────────────────────────┘
  │                       │
  │                       ▼
  │   ┌─────────────────────────────────────────┐
  │   │ 6. Update pipeline_items:               │
  │   │    status = 'transcribing'              │
  │   │    speakr_recording_id = response.id    │
  │   └─────────────────────────────────────────┘
  │
  └── FAILURE ──────────────────────────┐
                                         ▼
      ┌─────────────────────────────────────────┐
      │ 4b. Increment retry_count               │
      │     If retry_count >= max_retries:      │
      │       status = 'failed'                 │
      │       Send Slack alert                  │
      │     Else:                               │
      │       status = 'queued' (retry later)   │
      │     Store error message                 │
      └─────────────────────────────────────────┘
  │
  ▼
END
```

### Database Queries

**Claim item for processing:**
```sql
SELECT * FROM claim_pipeline_item('queued', 'orchestrator-1', 1);
```

**Update status:**
```sql
UPDATE pipeline_items
SET status = $status,
    started_at = COALESCE(started_at, NOW()),
    last_error = $error
WHERE id = $item_id;
```

### Error Handling
- Transcript fetch fails → retry with backoff
- Speakr upload fails → retry with backoff
- Max retries exceeded → status='failed', Slack alert

---

## Workflow 3: Embedding Sync

> [Updated 2026-03-31: spike learnings — embeddings not yet generating; segments already in SurrealDB from ingestion]

### Purpose
Generate embeddings for transcript segments already in SurrealDB. (Original spec assumed sync from Speakr; actual architecture stores segments in SurrealDB directly during ingestion.)

### Trigger
- **Schedule:** Every 5 minutes

### Logic

```
START
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. Query for items ready to embed:      │
│    status = 'transcribing' AND          │
│    speakr_recording_id IS NOT NULL      │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 2. For each item:                       │
│    - Check Speakr API if transcription  │
│      is complete                        │
│    - If complete: fetch transcript      │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 3. Update status to 'embedding'         │
│    Call Python script or internal API:  │
│    - Chunk transcript                   │
│    - Generate embeddings via LiteLLM    │
│    - Insert into SurrealDB              │
└─────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────┐
│ 4. On success:                          │
│    status = 'indexed_light'             │
│    surreal_video_id = result.id         │
│    completed_at = NOW()                 │
└─────────────────────────────────────────┘
  │
  ▼
END
```

### Integration with Spike Scripts

The embedding logic already exists in `spike/surreal-rag/scripts/load_to_surrealdb.py`. Options:

**Option A:** Call Python script from n8n via Execute Command node
```bash
python3 /path/to/load_to_surrealdb.py --video-id $VIDEO_ID
```

**Option B:** Create HTTP API wrapper around the script
```
POST http://banner:5050/api/embed
{ "video_id": "...", "transcript": "..." }
```

**Option C:** Port logic to n8n Code nodes (more complex)

**Recommendation:** Option A for MVP, Option B for Growth

---

## Shared Configuration

### Environment Variables (n8n)

> [Updated 2026-03-31: spike learnings — correct ports, MCP Gateway added]

| Variable | Value | Purpose |
|----------|-------|---------|
| `KNOWLEDGE_DB_HOST` | 10.0.0.33 | PostgreSQL host |
| `KNOWLEDGE_DB_PORT` | 5019 | PostgreSQL port (was 5010 in spec) |
| `KNOWLEDGE_DB_NAME` | knowledge | Database name |
| `KNOWLEDGE_DB_USER` | knowledge | Database user |
| `KNOWLEDGE_DB_PASS` | (secret) | Database password |
| `SPEAKR_API_URL` | http://10.0.0.33:5000/api | Speakr API |
| `SURREAL_URL` | http://10.0.0.33:5040 | SurrealDB |
| `MCP_GATEWAY_URL` | http://10.0.0.27:2780/mcp | MCP Gateway for transcript fetch |
| `LITELLM_URL` | http://10.0.0.27:2764 | LiteLLM proxy for embeddings |
| `ADMIN_API_URL` | http://10.0.0.33:5020 | Admin API |
| `EMBEDDING_SERVICE_URL` | http://10.0.0.33:5030 | Embedding service |
| `SLACK_WEBHOOK` | (secret) | Alert webhook (NOT YET CONFIGURED) |

### Slack Alerts

Use existing Universal Slack Alerting workflow:
```
POST /webhook/alert
{
  "channel": "#knowledge-alerts",
  "level": "error",
  "title": "Pipeline Failure",
  "message": "Video xyz failed after 3 retries: ..."
}
```

---

## Implementation Notes

> [Updated 2026-03-31: spike learnings — MCP Gateway replaces Transcript Fetcher, Slack not yet integrated]

1. **MCP Gateway for transcripts** - Transcripts fetched via MCP Gateway at `http://10.0.0.27:2780/mcp`. This is an undocumented dependency on Helicarrier. ~~YouTube Transcript Fetcher webhook~~ no longer used.

2. **Dedup in PostgreSQL** - The `ON CONFLICT DO NOTHING` pattern handles dedup atomically

3. **Claim pattern** - Use `claim_pipeline_item()` function to prevent duplicate processing by multiple workers. Batch size: 5 items per cycle.

4. **Stale claim release** - Run `release_stale_claims(15)` periodically to handle crashed workers

5. **Error visibility** - All errors stored in `last_error` column. Slack integration NOT YET implemented — errors visible in Admin UI only.

6. **Parallel data flow** - Orchestrator sends data to both SurrealDB (segments) and Speakr (transcript) in parallel, not sequentially.

## Post-Spike Status (2026-03-31)

### Actual Performance
- RSS Channel Monitor: 50 channels polled every 5 minutes
- Video Ingest Orchestrator: 5 items per cycle, 95% success rate
- Queue cleared: no backlog remaining
- Pipeline throughput: ~50 new videos/week across all channels
