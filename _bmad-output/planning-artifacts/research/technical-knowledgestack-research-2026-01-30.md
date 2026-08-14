---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md
  - _bmad-output/analysis/prd-prep-decisions-2026-01-30.md
  - _bmad-output/analysis/brainstorming-session-2026-01-29.md
  - docs/reference-youtube-channels.md
  - spike/findings.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'KnowledgeStack Technical Research'
research_goals: 'Comprehensive technical research across 7 areas to inform PRD'
user_name: 'Matt'
date: '2026-01-30'
web_research_enabled: true
source_verification: true
---

# Technical Research Report: KnowledgeStack

**Date:** 2026-01-30
**Author:** Mary (Analyst) on behalf of Matt
**Research Type:** Technical
**Sources Consulted:** 200+ across official documentation, GitHub repositories, academic papers, community forums
**Research Topics:** 7 (all complete)

---

## Research Overview

This report consolidates findings from 7 parallel research streams executed autonomously while Matt slept. Each topic was researched comprehensively using web search, documentation analysis, and source code inspection where applicable. The goal is to provide actionable technical intelligence for the PRD phase.

### Research Checklist Status

- [x] **R1:** n8n workflows for content publication tracking
- [x] **R2:** KnowledgeFeed portal fields and parameters
- [x] **R3:** Deduplication strategy for content ingestion
- [x] **R4:** Qdrant plugins, add-ons, and ecosystem tools
- [x] **R5:** Speakr API comprehensive review
- [x] **R6:** Local LLM model requirements and sizing
- [x] **R7:** Additional technical research gaps

### Detailed Reports

Full research reports with complete bibliographies are available at:
- `docs/research/speakr-comprehensive-research.md` (R5 - 40+ source files analyzed)
- `docs/research/deduplication-strategy-report.md` (R3 - 50+ sources)

---

## R1: n8n Workflow Patterns for YouTube Content Ingestion

### Key Finding: 4-Workflow Architecture

The recommended n8n architecture separates concerns into 4 independent workflows:

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **RSS Monitor** | Schedule (15-30 min) | Fetch YouTube RSS feeds, dedup, write to PostgreSQL queue |
| **Audio Download Worker** | Webhook or schedule | Pull from queue, call sidecar yt-dlp API, update status |
| **Transcription Poller** | Schedule (1-5 min) | Poll Speakr for completion, download transcript, trigger embedding |
| **Error Handler** | Error Trigger | Classify errors, route notifications, log failures |

### Critical Gotchas Discovered

1. **YouTube RSS 404 errors (Dec 2025):** Intermittent outages reported. Implement dual-source strategy (RSS + YouTube API fallback).
2. **RSS Feed Trigger dedup is unreliable:** Known to produce 3-4x duplicate triggers for the same item. Use external datastore (PostgreSQL) for deduplication.
3. **yt-dlp hangs in production mode:** Community reports of Execute Command node freezing. Recommendation: use a sidecar API container (FastAPI+yt-dlp, pattern from `roccoren/y2b` on GitHub) instead of installing yt-dlp directly in n8n.
4. **2GB binary data limit in n8n:** Audio files are typically <100MB so this is not a concern, but `N8N_DEFAULT_BINARY_DATA_MODE=filesystem` must be set for production.
5. **Workflow static data does not persist** during manual/test executions and is unreliable under high-frequency execution. Use PostgreSQL for all state.

### Template References

- **#10643** - Monitor Multiple YouTube Channels with dual RSS+API source
- **#5447** - Advanced Retry and Delay Logic (overcomes 5-retry/5-sec cap)
- **#2536** - Parallel Sub-Workflow with Wait-For-All pattern
- **#5629** - Multi-Channel Error Alerts (Telegram, Gmail, Discord)

### Key Design Principles

1. Decouple workflows using PostgreSQL as queue/state store
2. Externalize yt-dlp into a sidecar container
3. Use PostgreSQL for deduplication, not n8n's built-in mechanisms
4. Implement exponential backoff per Template #5447 for all API calls
5. Consider n8n queue mode (Redis-backed) if processing volume grows

---

## R2: KnowledgeFeed Portal Fields and Parameters

### Field Count Summary

| Category | Auto-Populated | Admin-Configured | Total |
|----------|---------------|-----------------|-------|
| Channel subscription | 17 | 8 | 25 |
| Per-channel settings | - | 25 | 25 |
| Video submission | 20 | 8 | 28 |
| Monitoring (per-channel) | 14 | - | 14 |
| Monitoring (per-video) | 22 | - | 22 |
| Pipeline health | 18 | - | 18 |

### MVP Channel Add Flow

1. Admin pastes YouTube URL or `@handle`
2. System auto-resolves to channel ID via YouTube Data API (1 quota unit)
3. System displays: name, avatar, subscriber count, video count, description
4. Admin selects: priority tier, domain categories, ingestion mode
5. All other settings use sensible defaults
6. Admin clicks "Subscribe" -- channel is added, first RSS check begins

### Sensible Defaults (Priority-Tier Based)

| Setting | Supreme | Leaders | Mid-tier | Occasional |
|---------|---------|---------|----------|-----------|
| `check_interval_minutes` | 15 | 30 | 60 | 120 |
| `pipeline_mode` | auto | auto | light | light |
| `auto_recent_depth_days` | 30 | 30 | 14 | 7 |
| `auto_recent_max_count` | 100 | 50 | 30 | 20 |

### YouTube Data API Quota Budget

Daily limit: 10,000 units. Typical daily run (50 channels, 200 new videos): ~270 units (2.7% of quota). **Quota is not a concern** at projected scale. Critical rule: never use `search.list` (100 units) -- use `playlistItems.list` (1 unit) instead.

### RSS vs API Field Gaps

RSS provides: video ID, title, description, thumbnail, published date, view count (last 15 videos only). RSS does NOT provide: duration, tags, like/comment counts, category, language, caption availability, live stream info. Strategy: RSS for detection (free), Data API for enrichment (1 unit per 50 videos).

---

## R3: Deduplication Strategy

> **Full report:** `docs/research/deduplication-strategy-report.md`

### 6-Layer Architecture

```
Layer 0: URL Normalization
  Extract youtube_video_id from any URL format (11 URL patterns)

Layer 1: n8n Pre-Filter (automated triggers only)
  Remove Duplicates node, 50K history, NOT authoritative

Layer 2: PostgreSQL Existence Check (all paths)
  Single source of truth, status-aware, atomic claim via ON CONFLICT

Layer 3: External Service Checks (full mode only)
  Speakr: check before upload. YouTube: skip if recently refreshed

Layer 4: Qdrant Deterministic IDs
  UUIDv5 from video_id + chunk_index. Upsert is inherently idempotent

Layer 5: Content-Level Dedup (Phase 2+)
  content_hash for exact, SimHash/MinHash for near-duplicates
```

### Highest-Impact Finding: Deterministic UUIDv5

**Replace the spike's `randomUUID()` with deterministic `UUIDv5(video_id:chunk_index)` for Qdrant point IDs.** This is the single most impactful change from spike to production:
- Upsert becomes inherently idempotent (no lookup-before-insert needed)
- Re-processing the same video safely overwrites existing vectors
- Zero additional storage or computation overhead

### 11-State Machine

```
discovered -> queued -> downloading/scraping_captions -> transcribing ->
  embedding -> indexing -> indexed_light / indexed_full
                                              |
                                         upgrading (light -> full)

Any active state -> failed (with retry_count++)
failed -> queued (if retry_count < max)
```

Each transition is guarded by a PostgreSQL `WHERE` clause for atomicity. Stale claim detection runs every 15 minutes to catch crashed workers.

### n8n Dedup Architecture

Two-layer filter: n8n Remove Duplicates node (50K history, fast but not authoritative) + API callback to PostgreSQL (authoritative check). This catches ~95% of duplicates cheaply in n8n, with PostgreSQL handling the remaining edge cases.

---

## R4: Qdrant Ecosystem and Capabilities

### Plugin System

**Qdrant has no plugin system.** All extensibility is through the REST/gRPC API. This is by design -- Qdrant is a focused vector database, not an extensible platform.

### Key Features for KnowledgeStack

| Feature | Details |
|---------|---------|
| **Web UI** | Built-in at `/dashboard`, includes collection browser, point inspector, search console |
| **Prometheus Metrics** | Native at `/metrics` on port 6333, per-node scraping |
| **Grafana Dashboards** | #24074 (Prometheus+Loki), #24603 (Prometheus-only) |
| **Multi-Tenancy** | Payload-based with `is_tenant: true` on `channel_id` index |
| **Hybrid Search** | Sparse + dense vectors with built-in RRF fusion (v1.16) |
| **Group By** | Search at chunk level, return results grouped by `video_id` |
| **Quantization** | Scalar (75% memory reduction), binary (97% reduction) |
| **Snapshots** | Native API, can write to S3 (restore requires workaround) |

### Self-Hosted vs Cloud

Self-hosted gives up: auto-scaling, automatic resharding, cloud inference, `/sys_metrics`, managed SSL/TLS. None of these are needed for KnowledgeStack's single-node deployment. **Self-hosted is the correct choice.**

### Recommended Collection Configuration

- **One collection:** `transcripts`
- **Named vectors:** `dense` (768-dim from nomic-embed-text), optionally `sparse` (BM25) later
- **Payload indexes:** `channel_id` (keyword, `is_tenant: true`), `video_id` (keyword), `published_date` (datetime), `chunk_index` (integer)
- **Optional second collection:** `videos` (one point per video for `with_lookup` in grouped queries)

### TypeScript Client Gap

The JS client (`@qdrant/js-client-rest`) lacks Python's `upload_collection` bulk method. Custom batching logic is required (batch size 100-256, `wait: false` for throughput).

---

## R5: Speakr API Comprehensive Review

> **Full report:** `docs/research/speakr-comprehensive-research.md`

### API Surface: 30+ v1 Endpoints

**Ingress (Pipeline -> Speakr):**
- `POST /api/v1/recordings/upload` -- multipart/form-data, audio files only
- Cannot push pre-existing transcript text (audio-only architecture)
- No bulk upload -- one file at a time (can parallelize HTTP requests)
- Auto-queues transcription after upload
- Can set: `notes`, `language`, `min_speakers`, `max_speakers`, `tag_ids`
- Cannot set: `title` (AI-generated post-transcription; PATCH after)

**Egress (Speakr -> Pipeline):**
- `GET /api/v1/recordings` -- paginated (max 100/page), filterable
- `GET /api/v1/recordings/{id}/transcript?format=json` -- structured segments with speaker, text, start/end timestamps
- `GET /api/v1/recordings/{id}/summary` -- AI-generated summary
- Tags, speakers, notes all accessible

### Five Critical Findings

1. **Audio-only ingestion** -- No transcript text push. Must send audio, let Speakr transcribe.
2. **No webhooks** -- Must poll `GET /api/v1/recordings/{id}/status`. Alternative: auto-export file watching (inotify on export directory).
3. **API tokens have no scopes** -- Full user access per token. Mitigation: dedicated pipeline user.
4. **LLM endpoint fully configurable** -- `TEXT_MODEL_BASE_URL` can point to LiteLLM (10.0.0.27:2764).
5. **Built-in RAG won't scale** -- Uses all-MiniLM-L6-v2 (384-dim), SQLite-stored embeddings. Won't scale past ~100K recordings. Use Qdrant instead.

### WhisperX Integration

- Separate Docker container (not embedded in Speakr)
- HTTP POST to `{ASR_BASE_URL}/asr`
- Model: large-v3 recommended (~10GB VRAM), large-v3-turbo for speed/quality balance (~6GB)
- Diarization via pyannote 3.1 (requires HuggingFace token, model agreement acceptance)
- Per-upload speaker hint overrides available

### Status Values

`PENDING -> PROCESSING -> SUMMARIZING -> COMPLETED` (or `FAILED`)

### Docker Volumes

| Path | Purpose |
|------|---------|
| `/data/uploads` | Audio file storage (mount to NAS) |
| `/data/instance` | Database, HuggingFace cache |
| `/data/exports` | Auto-export Markdown output |
| `/data/auto-process` | Watch directory for auto-ingest |

---

## R6: Local LLM Model Requirements and Sizing

### Recommended Model Stack

| Task | Model | VRAM (Q4_K_M) | Notes |
|------|-------|---------------|-------|
| **STT** | WhisperX large-v3-turbo | ~6 GB | Best speed/quality ratio |
| **Diarization** | pyannote 3.1 | ~2-4 GB shared | Alongside Whisper |
| **Summarization** | Qwen3 8B Instruct | ~6-7 GB | Top quality/cost ratio |
| **Chapter Generation** | Qwen3 8B (same model) | (shared) | Different prompt |
| **User Preferences** | Qwen3 8B (same model) | (shared) | Different prompt |
| **Content Triage** | Qwen3 8B (same model) | (shared) | Different prompt |
| **Embeddings** | nomic-embed-text-v1.5 | ~0.3 GB | 8192 context, 768 dims |

**Total peak VRAM:** ~10 GB (text processing phase)
**Minimum GPU:** 16 GB (sequential model swap)
**Recommended GPU:** 24 GB (RTX 4090 class, parallel LLM + embeddings)

### Key Sizing Insights

- **One shared model for all text tasks:** Qwen3 8B with different system prompts for summarization, chapters, triage, preferences. LiteLLM routes virtual model names to the same Ollama backend.
- **Quality cliff:** Below Q4_K_M quantization, quality degrades significantly. Q4_K_M retains 95-99% of FP16 quality.
- **Context rot:** Research shows quality degrades for inputs beyond 16K tokens. Use chunked/iterative summarization for long transcripts.
- **Embedding context matters:** all-MiniLM-L6-v2 (Speakr's built-in, 256-token limit) is inadequate for transcript chunks. nomic-embed-text-v1.5 (8192-token context) is required.

### Upgrade Path

| Current | Upgrade | VRAM | Why |
|---------|---------|------|-----|
| Qwen3 8B | Qwen3 30B-A3B (MoE) | ~16-20 GB | 30B reasoning at 3B speed |
| nomic-embed-text-v1.5 | BGE-M3 | ~1 GB | Hybrid dense+sparse retrieval |

### LiteLLM Configuration Strategy

Route virtual model names to the same Ollama model:
- `knowledge/summarize` -> `ollama/qwen3:8b` (summarization prompt)
- `knowledge/chapters` -> `ollama/qwen3:8b` (chapter gen prompt)
- `knowledge/triage` -> `ollama/qwen3:8b` (triage prompt)
- `knowledge/embed` -> `ollama/nomic-embed-text`
- Fallback to cloud APIs when local models are overloaded

---

## R7: Additional Technical Research

### YouTube RSS Feed Reliability

Three-tier monitoring recommended:
1. **WebSub/PubSubHubbub** (push, near-instant, requires public callback URL)
2. **RSS polling** (pull, 15-30 min interval, intermittent 404s reported)
3. **YouTube Data API search** (pull, daily verification, 100 units/call -- use sparingly)

### yt-dlp Audio-Only Configuration

Recommended: `yt-dlp -f "bestaudio[ext=webm]/bestaudio" --extract-audio --audio-format opus` -- opus format is smallest (~28MB/30min) and highest quality for speech. The spike used MP3; opus is the better choice for speech-only content.

### Deployment Architecture (Multi-Host)

**Banner has NO GPU.** Revised architecture splits across hosts:

| Container | Host | Image | Port | Notes |
|-----------|------|-------|------|-------|
| Speakr | Banner | murtaza-nasir/speakr | TBD | Points ASR_BASE_URL to Jarvis |
| Qdrant | Banner | qdrant/qdrant:v1.16.3-unprivileged | TBD | REST + gRPC |
| PostgreSQL | Banner | postgres:16 | internal | Shared with Speakr |
| WhisperX ASR | **Jarvis** | whisperx-asr-service | TBD | GPU required -- Jarvis only |
| n8n | **Helicarrier** | n8nio/n8n | 2725 | **Already running** -- reuse existing |
| LiteLLM | **Helicarrier** | litellm | 2764 | **Already running** -- routes to Jarvis Ollama |

**Key change:** n8n is already deployed on Helicarrier (10.0.0.27:2725). No need to deploy a second instance. KnowledgeStack workflows run on the shared n8n instance.

### Transcript Chunking Strategy

Hybrid approach with fallback chain:
1. **Chapter-based** (when YouTube chapters available) -- highest quality boundaries
2. **Semantic chunking** (primary fallback) -- sentence-level embedding similarity, target 256-512 tokens, 10-20% overlap
3. **Speaker-aware refinement** -- never split mid-speaker-turn, include speaker labels in metadata

### Monitoring and Alerting

Prometheus scrape targets for Coulson:
- n8n: `10.0.0.33:5678/metrics` (set `N8N_METRICS=true`)
- Qdrant: `10.0.0.33:6333/metrics`
- PostgreSQL: via `postgres_exporter` on port 9187
- Grafana dashboards: n8n System Health (#24474), Qdrant (#24074), NodeJS (#11159)

### Backup and Recovery

| Component | Method | Schedule | Storage |
|-----------|--------|----------|---------|
| PostgreSQL | `pg_dump` via sidecar container | Nightly | NAS |
| Qdrant | Snapshot API (`POST /collections/{name}/snapshots`) | Nightly | NAS |
| Speakr data | Volume mount backup (instance + uploads) | Nightly | NAS |
| Audio files | Already on NAS (if architecture followed) | N/A | NAS-native |

**Critical gap:** Single point of failure if all backups are on Synology NAS only. Consider weekly off-site replication.

### Security

- **AGPL-3.0 compliance:** Speakr and n8n are AGPL. If internal-only use, copyleft is generally not triggered. If external users access Speakr, full source availability is required.
- **Authentik SSO:** Speakr natively supports OIDC. n8n can be protected via Traefik Forward Auth middleware.
- **API key management:** Use `/mnt/foundry_project/AppServices/env/` for shared secrets. Never store in Docker images.
- **Network:** Use dedicated Docker bridge network. PostgreSQL should NOT expose port 5432 to host.

---

## Cross-Cutting Decisions for PRD

### Decisions Confirmed by Research

| Decision | Research Finding | Confidence |
|----------|-----------------|------------|
| PostgreSQL as dedup source of truth | YouTube video IDs are globally unique, immutable, never reused | High |
| Deterministic UUIDv5 for Qdrant | Upsert idempotency eliminates race conditions | High |
| Sidecar container for yt-dlp | Community reports of production mode hangs in n8n | High |
| RSS + API dual-source monitoring | YouTube RSS 404 outages confirmed (Dec 2025) | High |
| Qwen3 8B as shared text model | 95-99% quality retention at Q4_K_M, 131K context | High |
| nomic-embed-text-v1.5 for embeddings | 8192 context required for transcripts; all-MiniLM inadequate | High |
| Payload-based multi-tenancy in Qdrant | `is_tenant: true` with channel_id provides co-location | High |
| Speakr as black-box Docker container | AGPL compliance + upgrade path preserved | High |

### Open Questions Resolved by Matt (2026-01-30)

1. **Banner has NO GPU.** WhisperX must run on Jarvis (10.0.0.40) which has GPU + Ollama. All AI inference routes through LiteLLM (Helicarrier:2764).
2. **External access is planned.** Traefik already configured with multi-domain certs. AGPL compliance IS required -- Speakr source must remain available.
3. **Speakr SQLite vs shared PostgreSQL?** Still open -- verify during architecture phase.
4. **Model selection:** Jarvis currently runs deepseek-r1:32b, llama-4-scout-17b, bge-large. Adding Qwen3 8B or using existing models TBD during architecture.
5. **WebSub callback:** Traefik can expose a public URL -- feasible via `*.nextlevelfoundry.com` domain.

### Infrastructure Integration (from NLF Standards)

| Component | Host | IP | Port |
|-----------|------|-----|------|
| KnowledgeStack app | Banner | 10.0.0.33 | 3350 (per CLAUDE.md) |
| LiteLLM proxy | Helicarrier | 10.0.0.27 | 2764 |
| Ollama (GPU inference) | Jarvis | 10.0.0.40 | 11434 |
| n8n (existing instance) | Helicarrier | 10.0.0.27 | 2725 |
| WhisperX ASR | Jarvis | 10.0.0.40 | TBD (needs new container) |
| Qdrant | Banner | 10.0.0.33 | TBD (within port block) |
| PostgreSQL | Banner | 10.0.0.33 | internal only |
| Speakr | Banner | 10.0.0.33 | TBD (within port block) |
| Monitoring | Coulson | 10.0.0.28 | 2825 (Grafana) |
| Auth (Authentik) | Helicarrier | 10.0.0.27 | 2726 |
| Domain | Traefik | 10.0.0.27 | knowledge.nextlevelguild.com |

**Key architectural implication:** WhisperX is GPU-bound and must run on Jarvis, not Banner. Speakr's `ASR_BASE_URL` must point to Jarvis. LiteLLM already handles model routing with local-first + cloud fallback. n8n already exists on Helicarrier -- use the existing instance rather than deploying a new one.

### All Questions Resolved (2026-01-30)

1. **Speakr = PostgreSQL.** SQLite won't scale to 10K+ audio files. Speakr supports PostgreSQL natively via `DATABASE_URL` env var.
2. **Models: Add Qwen3 8B + nomic-embed-text-v1.5 to Jarvis.** Matt approved any models <40B. Both fit easily alongside existing deepseek-r1:32b.
3. **Synology NAS mount for audio.** Matt will configure a dedicated share on Fury. Speakr's `/data/uploads` mounts to NAS.
4. **Speakr = black box.** Never modify Speakr source. Keep it updatable for upstream features, bug fixes, and security patches. All customization happens outside Speakr (n8n workflows, Qdrant enrichment, KnowledgeLink API).

### Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| YouTube RSS feed outage | High | Medium | Three-tier monitoring |
| yt-dlp rate limiting | High | Low | 15-sec throttle, Webshare proxies |
| Banner host failure | Low | High | NAS backups, documented recovery |
| Qdrant single-node data loss | Medium | High | Nightly snapshots to NAS |
| AGPL compliance violation | Medium | High | External access planned -- source availability required |
| GPU unavailable on Banner | **Confirmed** | High | WhisperX on Jarvis (10.0.0.40), all AI via LiteLLM |

---

## Research Methodology

All 7 research topics were executed in parallel using specialized research agents. Each agent was given a detailed prompt derived from Matt's explicit checklist, the product brief, party mode decisions, and spike findings. Sources include:

- Official documentation (Qdrant, n8n, YouTube Data API v3, Speakr)
- GitHub repositories and source code (40+ Speakr source files)
- Community forums (n8n Community, GitHub Discussions)
- Academic papers (Spotify PODTILE, ACL/EMNLP proceedings, NLDB 2025)
- Independent benchmarks and blog posts
- n8n workflow template library (20+ templates analyzed)

Total sources consulted: 200+
Total research agent execution time: ~10 minutes (all parallel)

---

*Research compiled by Mary (Analyst) for the BMAD KnowledgeStack project.*
*Next workflow: PRD with PM John.*
