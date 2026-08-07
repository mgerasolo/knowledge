# Speakr Comprehensive Research Report

**Date:** 2026-01-30
**Version Analyzed:** v0.8.5.1
**Repository:** github.com/murtaza-nasir/speakr
**License:** AGPL-3.0 (dual-licensed with commercial option)
**Docker Image:** learnedmachine/speakr:latest
**Documentation Site:** murtaza-nasir.github.io/speakr

---

## Executive Summary

1. **Full REST API v1 exists** at `/api/v1/` with Swagger docs at `/api/v1/docs`. Authentication via Bearer tokens (API keys created per-user). The API supports upload, list, retrieve, transcript export (JSON/text/SRT/VTT), batch operations, and chat. Rate limits are documented: 60/min for stats, 100/min for reads, 30/min for writes, 10/min for processing.

2. **Audio-only ingestion** -- Speakr accepts audio file uploads exclusively. There is no endpoint to push pre-existing transcript text. The auto-process watch directory provides an alternative ingestion path for files dropped on disk.

3. **No webhooks exist.** Speakr has no outbound webhook system for transcription completion. The only notification mechanism is browser push notifications (Web Push/VAPID). Automated pipelines must poll `GET /api/v1/recordings/{id}/status` for completion.

4. **Embedding/RAG is built-in but basic** -- uses all-MiniLM-L6-v2 (384-dim) with cosine similarity over SQLite/PostgreSQL-stored vectors. No external vector database. Adequate for small-to-medium deployments but will not scale to hundreds of thousands of recordings.

5. **LLM endpoint is fully configurable** -- TEXT_MODEL_BASE_URL can point to any OpenAI-compatible endpoint (OpenRouter, LiteLLM, Ollama, etc.). Separate chat model endpoint supported. This is critical for KnowledgeStack integration.

---

## 1. Complete API Surface (Ingress)

### 1.1 Upload Endpoint

**`POST /api/v1/recordings/upload`**

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `file` | binary (multipart) | Yes | Audio file |
| `notes` | string | No | User notes (markdown) |
| `file_last_modified` | integer | No | Client timestamp (ms epoch) |
| `language` | string | No | ISO 639-1 code for ASR |
| `min_speakers` | integer | No | Diarization hint |
| `max_speakers` | integer | No | Diarization hint |
| `tag_ids[0]`, `tag_ids[1]`... | integer | No | Tag assignment (array-style) |
| `tag_id` | integer | No | Legacy single tag |

**Response:** 202 Accepted with recording object (status='PENDING'), queues transcription automatically.

**Supported Audio Formats:**
- Direct: PCM (s16le, s24le, f32le), MP3, FLAC, AAC, Opus, Vorbis
- With auto-conversion: Any format FFmpeg can decode (WebM, WAV, AIFF, AMR, 3GP, OGG, WMA, M4A, and 20+ others)
- Video files: Audio track extracted automatically via FFmpeg

**File Size Limits:**
- Default: 250 MB (configurable via admin settings in database)
- With chunking enabled: Effectively unlimited (files split at CHUNK_LIMIT, default 20MB chunks with 3s overlap)

**Critical Limitation:** Audio-only. There is NO endpoint to submit pre-existing transcript text. You cannot push a transcript JSON or text directly -- you must push an audio file and let Speakr transcribe it.

### 1.2 Internal (non-v1) Upload

**`POST /upload`** -- The internal UI upload endpoint. The v1 API endpoint delegates to this same handler. Identical parameters.

### 1.3 Metadata Updates After Upload

**`PATCH /api/v1/recordings/{id}`**

Updatable fields:
- `title` (string)
- `participants` (string)
- `notes` (string)
- `summary` (string)
- `meeting_date` (ISO 8601)
- `is_inbox` (boolean)
- `is_highlighted` (boolean)

**`PUT /api/v1/recordings/{id}/summary`** -- Replace summary text
**`PUT /api/v1/recordings/{id}/notes`** -- Replace notes text

### 1.4 Batch Operations

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/recordings/batch` | PATCH | Batch update inbox/highlight/tags |
| `/api/v1/recordings/batch` | DELETE | Batch delete recordings |
| `/api/v1/recordings/batch/transcribe` | POST | Batch queue transcription |

All accept `recording_ids` array. Return per-recording results with success/error counts.

### 1.5 Processing Triggers

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/recordings/{id}/transcribe` | POST | Queue/re-queue transcription |
| `/api/v1/recordings/{id}/summarize` | POST | Queue summary generation |
| `/api/v1/recordings/{id}/chat` | POST | Interactive chat about recording |

### 1.6 Auto-Process Watch Directory

Alternative ingestion: drop audio files into a watched directory. Requires:
```
ENABLE_AUTO_PROCESSING=true
AUTO_PROCESS_WATCH_DIR=/data/auto-process  # mount in docker
AUTO_PROCESS_MODE=admin_only|user_directories|single_user
```

Files are detected, converted, and queued for transcription automatically. Polling interval: 30 seconds (configurable).

### 1.7 Rate Limits

| Category | Limit |
|----------|-------|
| Stats endpoints | 60/minute |
| GET operations | 100/minute |
| Modification operations | 30/minute |
| Processing/batch | 10/minute |
| Token creation | 10/hour |
| Token management | 20/hour |

### 1.8 Authentication Methods

All API v1 endpoints accept (in priority order):
1. `Authorization: Bearer <token>` (recommended)
2. `X-API-Token: <token>` header
3. `API-Token: <token>` header
4. `?token=<token>` query parameter

Tokens are created via UI (Account Settings > API Tokens) or `POST /api/tokens`. Tokens are hashed (SHA-256) before storage; plaintext shown only once at creation. Expiration options: none, 30 days, 90 days, 1 year.

**Important:** Tokens grant full access to the user's resources. There is no scope/permission system on tokens -- a token can do everything the user can do.

---

## 2. Complete API Surface (Egress)

### 2.1 Recording Listing

**`GET /api/v1/recordings`**

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `page` | int | 1 | Pagination |
| `per_page` | int | 25 | Max 100 |
| `status` | string | all | all/pending/processing/completed/failed |
| `sort_by` | string | created_at | created_at/meeting_date/title/file_size/status |
| `sort_order` | string | desc | asc/desc |
| `date_from` | ISO date | - | Filter |
| `date_to` | ISO date | - | Filter |
| `tag_id` | int | - | Filter by tag |
| `q` | string | - | Full-text search |
| `inbox` | bool | - | Inbox filter |
| `starred` | bool | - | Starred filter |

**Search syntax:** Supports `date:today|yesterday|thisweek|YYYY-MM-DD`, `tag:name`, `speaker:name` within the `q` parameter. Text search covers title, participants, transcription text, and notes.

**Response:**
```json
{
  "recordings": [...],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 150,
    "total_pages": 6,
    "has_next": true,
    "has_prev": false
  }
}
```

### 2.2 Recording Detail

**`GET /api/v1/recordings/{id}`**

Query params: `format` (full|minimal), `include` (transcription,summary,notes)

Returns: id, title, status, participants, created_at, meeting_date, completed_at, file_size, original_filename, mime_type, is_inbox, is_highlighted, audio_available, processing_time_seconds, error_message, tags.

### 2.3 Transcript Retrieval

**`GET /api/v1/recordings/{id}/transcript`**

| Format | Description |
|--------|-------------|
| `json` (default) | Segments array with speaker, text, start, end timestamps |
| `text` | Plain text with speaker labels |
| `srt` | SubRip subtitle format |
| `vtt` | WebVTT subtitle format |

### 2.4 Summary and Notes

- `GET /api/v1/recordings/{id}/summary` -- Markdown summary + boolean flag
- `GET /api/v1/recordings/{id}/notes` -- Markdown notes + boolean flag

### 2.5 Audio Download

- `GET /api/v1/recordings/{id}/audio` -- Stream or download (add `?download=true`)

### 2.6 Status Polling

- `GET /api/v1/recordings/{id}/status` -- Returns status, queue_position, error_message, completed_at

### 2.7 Tags

- `GET /api/v1/tags` -- All user's personal and accessible group tags
- Fields: id, name, color, is_group_tag, group_id, custom_prompt, default_language, default_min_speakers, default_max_speakers, protect_from_deletion, can_edit

### 2.8 Speakers

- `GET /api/v1/speakers` -- All speakers ordered by use_count
- Fields: id, name, use_count, last_used, confidence_score, has_voice_profile
- `GET /api/v1/recordings/{id}/speakers` -- Speakers in specific recording with similarity suggestions

### 2.9 Calendar Events

- `GET /api/v1/recordings/{id}/events` -- Extracted events array
- `GET /api/v1/recordings/{id}/events/ics` -- ICS calendar file

### 2.10 Statistics

**`GET /api/v1/stats`** (scope=user|all)

Returns: recording counts (total/completed/processing/pending/failed), storage usage, queue status, token usage (monthly, budget, percentage), transcription usage (seconds/minutes, budget, cost estimate), activity metrics.

### 2.11 Export Capabilities

**Auto-Export (Obsidian/Logseq compatible):**
- Exports Markdown files to `AUTO_EXPORT_DIR`
- Per-user subdirectories: `{export_dir}/{username}/recording_{id}.md`
- Includes metadata, notes, summary, formatted transcription
- Triggered automatically after processing completes

**Template-based transcript export:**
- `GET /recording/{id}/download/transcript?template_id=X` -- Formatted transcript download
- 7 default templates: Simple Conversation, Timestamped, Interview Q&A, Meeting Minutes, Court Transcript, SRT Subtitle, Screenplay
- Custom templates with variables: `{{speaker}}`, `{{text}}`, `{{start_time}}`, `{{end_time}}`, `{{index}}`
- Filters: `|upper`, `|srt`

**Document exports (via internal endpoints, not v1 API):**
- `GET /recording/{id}/download/summary` -- Word (.docx) document
- `GET /recording/{id}/download/notes` -- Word (.docx) document
- `POST /recording/{id}/download/chat` -- Chat export as Word (.docx)

### 2.12 OpenAPI Spec

- `GET /api/v1/openapi.json` -- OpenAPI 3.0.3 specification
- `GET /api/v1/docs` -- Swagger UI interactive documentation

---

## 3. User Management

### 3.1 Roles

| Role | Capabilities |
|------|-------------|
| **Admin** | Full system access: user CRUD, system settings, default prompts, vector store management, group management, statistics dashboard, auto-deletion control |
| **Group Admin** | Manage members and tags within assigned groups only; no system-wide access |
| **Standard User** | Upload, transcribe, view own recordings, manage personal tags/speakers, share if permitted |

There are only two database-level roles: `is_admin=true` (full admin) and `is_admin=false` (standard user). Group admin is a membership role within a group, not a system-level role.

### 3.2 User Model Fields

- Core: id, username, email, password (bcrypt), name, job_title, company
- SSO: sso_provider, sso_subject
- Preferences: transcription_language, output_language, ui_language, diarize, extract_events, summary_prompt
- Budgets: monthly_token_budget (tokens), monthly_transcription_budget (seconds)
- Permissions: is_admin, can_share_publicly
- Email: email_verified, email_verification_token

### 3.3 Content Isolation

Recordings are owned by `user_id`. All API queries filter by current_user.id unless admin scope is requested. Users see only their own recordings unless content is explicitly shared (internal sharing or public links).

### 3.4 Service Accounts for Automation

There is no dedicated "service account" concept. **Workaround:** Create a standard user (e.g., "pipeline-bot") via admin UI or `POST /admin/users`, then create an API token for that user. The token grants full access to that user's recordings. This is the recommended approach for pipeline automation.

Admin API for user creation:
- `POST /admin/users` -- Create user with username, email, password, is_admin, budgets
- Requires admin authentication

### 3.5 SSO/OIDC Integration

Supports any OIDC-compliant provider (Keycloak, Azure AD/Entra ID, Google, Auth0).

**Environment Variables:**
```
ENABLE_SSO=true
SSO_PROVIDER_NAME=Keycloak
SSO_CLIENT_ID=speakr
SSO_CLIENT_SECRET=change-me
SSO_DISCOVERY_URL=https://keycloak.example.com/realms/master/.well-known/openid-configuration
SSO_REDIRECT_URI=https://speakr.example.com/auth/sso/callback
SSO_AUTO_REGISTER=true
SSO_ALLOWED_DOMAINS=                     # comma-separated, empty = all
SSO_DEFAULT_USERNAME_CLAIM=preferred_username
SSO_DEFAULT_NAME_CLAIM=name
SSO_DISABLE_PASSWORD_LOGIN=false         # admins always retain password access
```

**Important limitation:** No role/group mapping from OIDC claims. SSO users are created as standard users; admin must be set manually.

### 3.6 Budget Management

**Token Budgets (LLM usage):**
- Set per-user in 10,000-token increments (minimum 100,000)
- 80% warning, 100% block threshold
- Monthly auto-reset
- Covers: summaries, chat, titles, event extraction

**Transcription Budgets (ASR usage):**
- Set per-user in minutes (minimum 10)
- Same 80%/100% threshold model
- Monthly auto-reset
- Cost estimation available for OpenAI providers

---

## 4. Plugins and Extensions

### 4.1 Plugin System

**There is no plugin system.** Speakr does not have a plugin architecture, extension API, or marketplace.

### 4.2 Extensibility Points

1. **Custom Transcription Connectors** -- The connector-based architecture in `src/services/transcription/connectors/` is designed for extensibility. New connectors extend `BaseTranscriptionConnector`, declare capabilities, and register in the registry. This requires code changes to the container image (fork or custom Dockerfile).

2. **Transcript Templates** -- Users can create custom transcript formatting templates with variable substitution and regex-based filename extraction. This is the primary user-facing customization.

3. **Naming Templates** -- Custom auto-naming patterns for recordings with variables (`{{ai_title}}`, `{{filename}}`, `{{date}}`, `{{datetime}}`) and regex extraction from filenames.

4. **Custom LLM Prompts** -- Per-user, per-tag, and admin-level default prompts for summary generation. Tag prompts stack when multiple tags apply.

### 4.3 Community Forks

No significant community forks with added features were found as of this analysis date. The project has 215 forks on GitHub but none appear to add substantial new capabilities.

### 4.4 Model Swapping

**Whisper models (via WhisperX):** Configurable via `WHISPER_MODEL` environment variable on the WhisperX container. Options: tiny, base, small, medium, large-v2, large-v3. This is configured on the ASR container, not on Speakr.

**LLM models:** Fully swappable via `TEXT_MODEL_NAME` and `CHAT_MODEL_NAME` environment variables. Any OpenAI-compatible API works.

### 4.5 Theme/UI Customization

No theme system. The frontend is Vue.js 3 with Tailwind CSS, supporting dark/light mode toggle. Six UI languages: English, Spanish, French, German, Chinese, Russian. Customization requires modifying the source.

---

## 5. Configuration (Docker)

### 5.1 Complete Environment Variables Reference

#### Required
```
TRANSCRIPTION_API_KEY=         # OpenAI key OR leave empty for ASR endpoint
TEXT_MODEL_API_KEY=            # LLM provider key (OpenRouter, OpenAI, etc.)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme
```

#### Transcription Provider
```
TRANSCRIPTION_CONNECTOR=      # openai_whisper | openai_transcribe | asr_endpoint (auto-detect if empty)
TRANSCRIPTION_BASE_URL=       # Default: https://api.openai.com/v1
TRANSCRIPTION_MODEL=          # whisper-1 | gpt-4o-transcribe | gpt-4o-mini-transcribe | gpt-4o-transcribe-diarize
USE_NEW_TRANSCRIPTION_ARCHITECTURE=true
```

#### Self-Hosted ASR (WhisperX)
```
ASR_BASE_URL=http://whisperx:9000    # URL of WhisperX container
ASR_TIMEOUT=1800                      # 30 minutes default
ASR_DIARIZE=true
ASR_MIN_SPEAKERS=                     # optional hint
ASR_MAX_SPEAKERS=                     # optional hint
ASR_RETURN_SPEAKER_EMBEDDINGS=false   # WhisperX only, enables voice profiles
```

#### LLM Configuration
```
TEXT_MODEL_BASE_URL=https://openrouter.ai/api/v1
TEXT_MODEL_NAME=openai/gpt-4o-mini
CHAT_MODEL_API_KEY=                   # Optional separate chat model
CHAT_MODEL_BASE_URL=                  # Optional separate chat endpoint
CHAT_MODEL_NAME=                      # Optional separate chat model
SUMMARY_MAX_TOKENS=8000
CHAT_MAX_TOKENS=5000
ENABLE_STREAM_OPTIONS=true            # Set false for LLM servers without stream_options
```

#### Audio Processing
```
ENABLE_CHUNKING=true
CHUNK_LIMIT=20MB                      # Size or duration (e.g., 600s, 10m)
CHUNK_OVERLAP_SECONDS=3
AUDIO_COMPRESS_UPLOADS=true           # Compress lossless to lossy
AUDIO_CODEC=mp3                       # mp3 | flac | opus
AUDIO_BITRATE=128k
AUDIO_UNSUPPORTED_CODECS=             # Comma-separated exclusion list
```

#### User Management
```
ALLOW_REGISTRATION=false
REGISTRATION_ALLOWED_DOMAINS=         # Comma-separated email domains
```

#### Feature Flags
```
ENABLE_INQUIRE_MODE=false             # Semantic search / RAG
ENABLE_INTERNAL_SHARING=false         # User-to-user sharing
ENABLE_PUBLIC_SHARING=true            # Public share links
ENABLE_AUTO_PROCESSING=false          # Watch directory
ENABLE_AUTO_EXPORT=false              # Auto Markdown export
ENABLE_AUTO_DELETION=false            # Retention-based deletion
INCOGNITO_MODE_DEFAULT=false          # Privacy mode default
SHOW_USERNAMES_IN_UI=false
USERS_CAN_DELETE=true
```

#### Auto-Processing
```
AUTO_PROCESS_MODE=admin_only          # admin_only | user_directories | single_user
AUTO_PROCESS_WATCH_DIR=/data/auto-process
AUTO_PROCESS_CHECK_INTERVAL=30        # seconds
AUTO_PROCESS_DEFAULT_USERNAME=        # for single_user mode
```

#### Auto-Export
```
AUTO_EXPORT_DIR=/data/exports
AUTO_EXPORT_TRANSCRIPTION=true
AUTO_EXPORT_SUMMARY=true
```

#### Retention / Deletion
```
GLOBAL_RETENTION_DAYS=                # days before deletion
DELETION_MODE=                        # audio_only = delete audio, keep transcript
```

#### Background Processing
```
JOB_QUEUE_WORKERS=2                   # Transcription worker threads
SUMMARY_QUEUE_WORKERS=2               # Summary worker threads
JOB_MAX_RETRIES=3
```

#### Database
```
SQLALCHEMY_DATABASE_URI=sqlite:////data/instance/transcriptions.db
# For PostgreSQL:
# SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host:5432/speakr
```

#### Logging
```
LOG_LEVEL=INFO                        # ERROR | INFO | DEBUG
TIMEZONE=UTC
```

### 5.2 Docker Volumes

| Volume | Purpose | Required |
|--------|---------|----------|
| `/data/uploads` | Audio file storage | Yes |
| `/data/instance` | Database (SQLite), HuggingFace cache | Yes |
| `/data/exports` | Auto-export Markdown output | If auto-export enabled |
| `/data/auto-process` | Watch directory for auto-ingest | If auto-process enabled |

**NAS mounting:** Yes, any volume can be a bind mount to NAS storage. Audio files are stored in `/data/uploads` organized by recording ID. The instance directory contains the SQLite database and HuggingFace model cache.

### 5.3 Port

Single port: **8899** (Gunicorn with 3 workers, 600s timeout)

---

## 6. WhisperX Integration

### 6.1 Architecture

Speakr connects to WhisperX via HTTP POST to `{ASR_BASE_URL}/asr`. WhisperX runs as a separate Docker container (not embedded in Speakr). The connection is one-way: Speakr sends audio, receives JSON response.

### 6.2 WhisperX Container Setup

```yaml
# Separate docker-compose for WhisperX
services:
  whisperx:
    image: onerahmet/openai-whisper-asr-webservice:latest-gpu
    environment:
      - HF_TOKEN=hf_xxx            # Required: accept model agreements first
      - DEVICE=cuda
      - COMPUTE_TYPE=float16
      - BATCH_SIZE=16              # 32 for high-end, 8 for entry-level GPU
      - WHISPER_MODEL=large-v3     # tiny|base|small|medium|large-v2|large-v3
    ports:
      - "9000:9000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Prerequisite:** Must accept Hugging Face model agreements for pyannote/speaker-diarization-3.1, pyannote/segmentation-3.0, and the diarization pipeline before deployment.

### 6.3 Model/VRAM Requirements

| Model | VRAM | Quality |
|-------|------|---------|
| tiny | ~1 GB | Low |
| base | ~1 GB | Low-Medium |
| small | ~2 GB | Medium |
| medium | ~5 GB | Good |
| large-v2 | ~10 GB | High |
| large-v3 | ~10 GB | Highest (recommended) |

**Minimum hardware:** NVIDIA GPU with 8GB+ VRAM, 16GB RAM, 50GB disk
**Recommended:** 16GB+ VRAM, 32GB RAM, 100GB SSD

### 6.4 Diarization Configuration

| Parameter | Where Set | Default | Notes |
|-----------|-----------|---------|-------|
| `ASR_DIARIZE` | Speakr env | true | Enable/disable per-instance |
| `ASR_MIN_SPEAKERS` | Speakr env | None | Hint, not hard limit |
| `ASR_MAX_SPEAKERS` | Speakr env | None | Hint, not hard limit |
| `ASR_RETURN_SPEAKER_EMBEDDINGS` | Speakr env | false | WhisperX only; 256-dim vectors |
| Per-upload overrides | Upload params | - | language, min_speakers, max_speakers |
| Per-tag defaults | Tag config | - | Default ASR settings per tag |

### 6.5 Speed/Quality Tradeoff

Controlled primarily by model selection (tiny=fast/low vs large-v3=slow/high) and BATCH_SIZE on the WhisperX container. COMPUTE_TYPE (float16 vs int8) also affects speed. These are configured on the WhisperX container, not Speakr.

---

## 7. AI Chat / RAG Features

### 7.1 LLM Configuration

Speakr uses any OpenAI-compatible API endpoint. Critical for KnowledgeStack: **TEXT_MODEL_BASE_URL can point to LiteLLM**.

```
TEXT_MODEL_BASE_URL=http://litellm:4000/v1   # Point to LiteLLM
TEXT_MODEL_API_KEY=sk-xxx
TEXT_MODEL_NAME=gpt-4o-mini
```

Separate chat model endpoint is supported:
```
CHAT_MODEL_BASE_URL=http://litellm:4000/v1
CHAT_MODEL_API_KEY=sk-xxx
CHAT_MODEL_NAME=claude-3-5-sonnet
```

### 7.2 LLM Usage

| Feature | Uses LLM | Notes |
|---------|----------|-------|
| Title generation | Yes | Auto-generates from transcript |
| Summary generation | Yes | Customizable via prompts |
| Chat with transcript | Yes | Full conversation with context |
| Event extraction | Yes | Calendar events from transcript |
| Speaker identification | Yes | LLM-based speaker name inference |
| Inquire mode | Yes | RAG across all recordings |

### 7.3 RAG Implementation (Inquire Mode)

**Requires:** `ENABLE_INQUIRE_MODE=true`

**Embedding Model:** all-MiniLM-L6-v2 (SentenceTransformers)
- 384-dimensional vectors
- CPU-based (no GPU needed for embeddings)
- ~500MB RAM when loaded
- Best with English; variable for other languages

**Chunking Strategy:**
- Max chunk size: 500 characters
- Overlap: 50 characters
- Intelligent sentence-boundary breaking
- Typical: 50-60 chunks per hour of audio

**Storage:** Embeddings stored as binary blobs in the relational database (SQLite or PostgreSQL). No external vector database.

**Search Flow (POST /api/inquire/search):**
1. Query encoded to 384-dim vector
2. All accessible recording chunks retrieved from DB
3. Cosine similarity computed (scikit-learn)
4. Top-k results returned (default: 5)
5. Fallback to text matching if embeddings unavailable

**Chat RAG Flow (POST /api/inquire/chat):**
1. Query routing (determines if RAG lookup needed)
2. Query enrichment (LLM generates 3-5 alternative search terms)
3. Multi-query semantic search (8 chunks per query, deduplicated)
4. Auto-speaker detection and filter adjustment
5. Context assembly (hierarchical by recording source)
6. LLM response generation with source citations

**Scaling Considerations:**
- Each chunk: ~2KB storage
- 10,000 hours of recordings: ~100MB of embeddings
- SQLite adequate for small-to-medium deployments
- Very large instances may need dedicated vector database (not currently supported)

---

## 8. Webhooks and Events

### 8.1 Webhooks

**Speakr does NOT support outbound webhooks.** There is no webhook configuration, no callback URL registration, and no event emission system.

The word "webhook" appears only in the API reference documentation as a use-case example, not as an implemented feature.

### 8.2 Push Notifications

Browser push notifications (Web Push / VAPID) are available but only for browser clients:
- Triggered on transcription completion
- Requires VAPID key generation and configuration
- Only delivers to subscribed browser sessions
- Not suitable for server-to-server notification

### 8.3 Polling Strategy for Automation

For pipeline automation, the recommended approach:

```
1. POST /api/v1/recordings/upload  --> returns recording ID
2. Poll GET /api/v1/recordings/{id}/status every N seconds
3. When status == "COMPLETED":
   GET /api/v1/recordings/{id}/transcript?format=json
   GET /api/v1/recordings/{id}/summary
```

**Status values:** PENDING -> PROCESSING -> SUMMARIZING -> COMPLETED (or FAILED)

**Alternative:** Use auto-export. Configure `ENABLE_AUTO_EXPORT=true` and mount the export directory. Monitor the export directory for new `.md` files. This avoids polling the API but only provides Markdown format.

### 8.4 Auto-Export as Event Proxy

When auto-export is enabled, Speakr writes a Markdown file after processing completes:
```
{AUTO_EXPORT_DIR}/{username}/recording_{id}.md
```

An external file watcher (inotify, fswatch) on this directory can serve as a poor-man's webhook. The exported file contains title, metadata, notes, summary, and formatted transcription.

---

## 9. Additional Findings

### 9.1 Internal API (Non-v1 Endpoints)

Beyond the documented v1 API, Speakr has internal endpoints used by the frontend. These are not versioned and may change without notice:

| Endpoint | Notes |
|----------|-------|
| `POST /recording/{id}/reprocess_transcription` | Re-queue with new ASR params |
| `POST /recording/{id}/update_transcript` | Edit transcript text + speaker map |
| `POST /recording/{id}/update_speakers` | Rename speakers in transcript |
| `POST /recording/{id}/auto_identify_speakers` | LLM-based speaker naming |
| `GET /recording/{id}/download/transcript` | Formatted export with template |
| `GET /recording/{id}/download/summary` | Word doc export |
| `POST /recording/{id}/download/chat` | Chat export as Word doc |
| `POST /recording/{id}/toggle_inbox` | Toggle inbox status |
| `POST /recording/{id}/toggle_highlight` | Toggle starred status |
| `POST /recording/{id}/reset_status` | Reset stuck processing |

### 9.2 Admin API

Admin endpoints at `/admin/` (require is_admin=true):

| Category | Endpoints |
|----------|-----------|
| Users | GET/POST/PUT/DELETE `/admin/users`, toggle-admin |
| Stats | `/admin/stats`, `/admin/token-stats/*`, `/admin/transcription-stats/*` |
| Settings | GET/POST `/admin/settings` |
| Auto-deletion | run, stats, preview |
| Inquire | process-recordings, status |
| Auto-process | status, start, stop, config |
| Groups | Full CRUD + member management |

### 9.3 Sharing Model

**Internal Sharing** (ENABLE_INTERNAL_SHARING=true):
- User-to-user sharing with permission levels: view, edit, reshare
- Permission cascading validation (prevents circular shares)
- Audit logging of all share operations
- User search endpoint for recipient discovery

**Public Sharing** (ENABLE_PUBLIC_SHARING=true):
- Public link generation with unique public_id
- Configurable: show/hide summary and notes on public view
- Per-user permission to create public shares (admin controlled)

**Group Sharing:**
- Tag-based automatic sharing within groups
- Two modes: share with all members, or group leads only
- Group admins get edit permissions, members get view-only
- Retroactive sync available for existing recordings

### 9.4 Database Schema Key Tables

Based on model analysis:
- `user` - User accounts with budgets and preferences
- `recording` - Core recording data with transcript, summary, status
- `api_token` - Hashed API tokens with expiration
- `tag` / `recording_tag` - Tagging system
- `speaker` - Speaker profiles with voice embeddings
- `speaker_snippet` - Audio samples for speaker identification
- `transcript_chunk` - Chunked text with embeddings for Inquire mode
- `internal_share` - User-to-user sharing with permissions
- `share` - Public sharing links
- `share_audit_log` - Audit trail for sharing operations
- `event` - Calendar events extracted from transcripts
- `processing_job` - Job queue state
- `token_usage` - LLM token consumption tracking
- `transcription_usage` - ASR usage tracking
- `naming_template` - Auto-naming patterns
- `transcript_template` - Export formatting templates
- `push_subscription` - Web Push subscriptions
- `organization` / group tables - Group management
- `system_setting` - Admin-configurable system settings

### 9.5 Open Issues / Feature Requests (as of 2026-01-30)

Notable open items:
- #200: "Sharing links are not Claude friendly" -- public share rendering issues
- #199: "Enable Voice Embeddings within Organisation" -- org-wide voice profiles
- #194: "Doesn't support Azure Foundry OpenAI" -- Azure-specific API compatibility
- #188: "More granular privacy/data controls" -- enhanced privacy features
- #174: "Arbitrary file attachments" -- request to attach non-audio files

Community discussions requesting: folder organization, AI translation, to-do list generation, CPU-based ASR alternatives (Parakeet), multiple file upload improvements.

---

## 10. KnowledgeStack Integration Assessment

### 10.1 Recommended Integration Pattern

```
YouTube Audio --> KnowledgeStack Pipeline --> POST /api/v1/recordings/upload
                                                     |
                                          Poll GET /api/v1/recordings/{id}/status
                                                     |
                                          GET /api/v1/recordings/{id}/transcript?format=json
                                          GET /api/v1/recordings/{id}/summary
                                                     |
                                          Store in KnowledgeStack DB / Vector Store
```

### 10.2 Key Integration Considerations

1. **No transcript push** -- Must send audio files, cannot bypass transcription. For YouTube content where transcripts already exist, this means re-transcribing audio (potentially higher quality than YouTube auto-captions).

2. **No webhooks** -- Must implement polling or use auto-export file watching. Polling interval recommendation: 10-30 seconds for active jobs.

3. **Service account pattern** -- Create a dedicated user ("knowledge-pipeline") with API token. All pipeline-ingested recordings will be owned by this user.

4. **Tag-based organization** -- Create tags for content categories (e.g., "youtube", "podcast", channel-specific tags). Tags can carry custom summary prompts optimized for content type.

5. **LLM endpoint sharing** -- Point TEXT_MODEL_BASE_URL to KnowledgeStack's LiteLLM instance for unified LLM management and cost tracking.

6. **Embedding independence** -- Speakr's built-in Inquire mode uses its own embeddings (all-MiniLM-L6-v2, 384-dim). KnowledgeStack likely wants its own embedding pipeline with a different model. These are independent systems.

7. **PostgreSQL recommended** -- For multi-user and production use, configure `SQLALCHEMY_DATABASE_URI` to use the shared AppServices PostgreSQL instance rather than SQLite.

8. **Auto-export as secondary signal** -- Enable auto-export to a mounted directory. Even if polling is primary, the exported Markdown serves as a backup data source and can trigger downstream processing via inotify.

### 10.3 Gaps for KnowledgeStack

| Gap | Impact | Workaround |
|-----|--------|------------|
| No transcript push API | Must re-transcribe audio from YouTube | Accept higher-quality transcription as a benefit |
| No webhooks | Cannot get push notifications | Poll status endpoint; or use auto-export file watching |
| No folder/hierarchy | Flat list organization only | Use tags for categorization |
| No bulk metadata import | Cannot set rich metadata during batch upload | PATCH after upload |
| Token scopes | API tokens have full user access | Isolate pipeline user; minimize permissions via separate user account |
| SQLite embedding limits | Inquire mode won't scale past ~100K recordings | Use KnowledgeStack's own vector store (Qdrant) instead |

---

## Bibliography

| Source | Type | Access Date |
|--------|------|-------------|
| [Speakr GitHub Repository](https://github.com/murtaza-nasir/speakr) | Primary source, codebase analysis | 2026-01-30 |
| `src/api/api_v1.py` | API v1 route definitions | 2026-01-30 |
| `src/api/recordings.py` | Recording management routes | 2026-01-30 |
| `src/api/auth.py` | Authentication implementation | 2026-01-30 |
| `src/api/tokens.py` | API token management | 2026-01-30 |
| `src/api/admin.py` | Admin routes | 2026-01-30 |
| `src/api/inquire.py` | Inquire/RAG routes | 2026-01-30 |
| `src/api/shares.py` | Sharing system | 2026-01-30 |
| `src/api/speakers.py` | Speaker management | 2026-01-30 |
| `src/api/groups.py` | Group management | 2026-01-30 |
| `src/api/system.py` | System routes | 2026-01-30 |
| `src/api/events.py` | Calendar events | 2026-01-30 |
| `src/api/templates.py` | Transcript templates | 2026-01-30 |
| `src/api/naming_templates.py` | Naming templates | 2026-01-30 |
| `src/api/push_notifications.py` | Push notifications | 2026-01-30 |
| `src/models/user.py` | User model | 2026-01-30 |
| `src/models/recording.py` | Recording model | 2026-01-30 |
| `src/models/api_token.py` | API token model | 2026-01-30 |
| `src/config/app_config.py` | Application configuration | 2026-01-30 |
| `src/config/startup.py` | Startup configuration | 2026-01-30 |
| `src/auth/sso.py` | SSO/OIDC implementation | 2026-01-30 |
| `src/services/embeddings.py` | Embedding/vector service | 2026-01-30 |
| `src/services/llm.py` | LLM service | 2026-01-30 |
| `src/services/job_queue.py` | Job queue system | 2026-01-30 |
| `src/services/transcription/base.py` | Transcription connector base | 2026-01-30 |
| `src/services/transcription/connectors/asr_endpoint.py` | WhisperX connector | 2026-01-30 |
| `src/file_exporter.py` | Export implementation | 2026-01-30 |
| `src/file_monitor.py` | Auto-process file watcher | 2026-01-30 |
| `src/utils/token_auth.py` | Token auth middleware | 2026-01-30 |
| `src/utils/audio_conversion.py` | Audio format handling | 2026-01-30 |
| `src/tasks/processing.py` | Processing pipeline | 2026-01-30 |
| `config/env.transcription.example` | Environment variable reference | 2026-01-30 |
| `config/env.sso.example` | SSO configuration reference | 2026-01-30 |
| `config/docker-compose.example.yml` | Docker deployment reference | 2026-01-30 |
| `Dockerfile` | Container build spec | 2026-01-30 |
| `requirements.txt` | Python dependencies | 2026-01-30 |
| `docs/user-guide/api-reference.md` | Official API documentation | 2026-01-30 |
| `docs/user-guide/api-tokens.md` | Token documentation | 2026-01-30 |
| `docs/admin-guide/whisperx-setup.md` | WhisperX setup guide | 2026-01-30 |
| `docs/admin-guide/vector-store.md` | Vector store documentation | 2026-01-30 |
| `docs/admin-guide/sso-setup.md` | SSO setup guide | 2026-01-30 |
| `docs/admin-guide/user-management.md` | User management guide | 2026-01-30 |
| `docs/admin-guide/model-configuration.md` | Model configuration guide | 2026-01-30 |
| `docs/admin-guide/group-management.md` | Group management guide | 2026-01-30 |
| `docs/advanced/custom-connectors.md` | Connector extensibility | 2026-01-30 |
| `docs/PUSH_NOTIFICATIONS_SETUP.md` | Push notifications guide | 2026-01-30 |
| GitHub Issues (open) | Community feedback | 2026-01-30 |
| GitHub Discussions | Community requests | 2026-01-30 |
