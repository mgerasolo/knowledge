---
guide: knowledge
type: api
provider: knowledge
audience: [internal-apps, agents]
stability: beta
version: 2.1.0
updated: 2026-08-14
verified: 2026-08-14
owner: Matt Gerasolo <matt@gerasolo.com>
---

# KnowledgeStack — YouTube Transcript & Knowledge API

> Query timestamped YouTube transcripts, entity/topic tags, and ingestion status for 51 monitored channels, instead of re-scraping or re-transcribing content this project has already processed.

---

## 1. Overview

KnowledgeStack watches a set of YouTube channels, transcribes and chunks their videos, embeds the chunks for semantic retrieval, and extracts an entity/topic tag graph from the transcript text. It exists so that other NextLevelFoundry/NextLevelGuild projects don't each need to independently scrape, transcribe, or tag the same source videos — a project that wants to ground an answer in what a given creator has actually said can query this API instead of hitting YouTube or relying on an LLM's general knowledge.

**Current adopters: none yet.** No other project currently integrates with this API — this guide is being published ahead of the first real integration so that a consuming project or agent starts from one accurate reference instead of reverse-engineering the code.

**Sub-services** (this guide's `type: api` scope covers the Admin API only; the others are internal plumbing, listed here for orientation):

| Service | Role | Consumer-relevant? |
|---|---|---|
| **Admin API** ("KnowledgeEnroll") | Video/tag browsing, keyword search, channel + pipeline status. | Yes — this is what this guide documents |
| Embedding Service | Turns transcripts into chunks + vector embeddings. Ingestion-side, write path. | No — internal write path; use the Admin API for reads |
| Transcript Service | Discovers new videos per channel, fetches raw transcripts. | No — internal pipeline plumbing only |

---

## 2. Value Proposition & Planning

### When this helps

- You need "what has creator X said about Y" and the channel is one of the 51 already monitored — the content is likely already transcribed and timestamped, so you avoid re-transcribing it yourself.
- You want a timestamped segment, not just a full transcript wall of text, so you can deep-link to the moment in the video.
- You want to scope a query to a topic area — content is pre-classified into `ai-tech`, `mindset`, `political`, `business`, `general`, `health`, `faith`.
- You want to know whether "no results" means "doesn't exist" vs. "not ingested yet" — the ingestion pipeline's queue/failure state is queryable.

### Ingestion can pause on a YouTube rate limit

Transcripts are pulled from YouTube's caption endpoint, which rate-limits by IP and returns HTTP 429 with no retry hint. When that happens, ingestion stands down and waits — it does not fail videos, and nothing already in the corpus is affected. The practical consequence for a consumer is that a video published today may not appear for hours longer than usual. `GET /api/v1/status` still reports `ok` during a block (the corpus is readable); check `components.transcript_files.hours_since_newest` if freshness matters to you.

### When this doesn't help (use something else)

- You need semantic ("meaning-based") search. It still does not exist. Only substring keyword search is built — it now works (§3), but it matches literal text, not meaning. Embeddings are not generated for the corpus. Use your own embedding search if you need semantic matching.
- You need a channel that isn't one of the 51 currently monitored. There's no on-demand "transcribe this video for me" endpoint — only the standing channel watch list is ingested.
- You need guaranteed uptime or a support SLA. See the operational table below — there is none.
- You need entity/topic tags. The `/tags/*` endpoints return **HTTP 501** — tagging was never implemented and no tag data has ever been written. Ignore the tag graph described in older versions of this guide.

### Video descriptions carry more than the transcript

Each video record includes the full YouTube `description`, which for many creators contains material that is **not spoken in the video** — verbatim prompts, tool links, timestamps/chapters, and resource lists. If you are grounding an answer in "what this creator actually gave people," check `description` as well as the transcript segments. 2,881 of 3,059 videos have one.

### Operational facts

| Aspect | Current reality |
|---|---|
| Maintenance / ownership | Single maintainer (Matt Gerasolo), no on-call rotation |
| Availability | Best-effort only, no uptime guarantee. Runs on a shared dev host and can go down for deploys/maintenance without notice |
| Cost / quota | Free for internal use; no server-side rate limiting. Per this project's standing courtesy rule: 2s+ delay between calls if you're batching more than 5 requests |
| Data persistence | **Resolved 2026-08-05.** SurrealDB ran on the in-memory storage backend, so it discarded every write and the `knowledge` namespace did not exist. It now runs on persistent disk storage (rocksdb), verified by restarting the container and confirming both the namespace and a canary record survived. The corpus was rebuilt from the transcript files on disk, which were never affected |
| Corpus size | 4,205 videos · 310,860 timestamped segments · 58 channels (measured 2026-08-14 from `GET /api/v1/status`) |
| Breaking-change policy | Not yet formalized — this is a pre-1.0 API with no consumer-facing versioning contract. This guide document is itself versioned (frontmatter `version:`); re-read on any bump |

### Example integration

A project building a "what has this creator said before" feature would:

1. `GET /api/v1/status` — confirm `status` is `ok` (or at least that `components.surrealdb.ok` is true) before trusting any result.
2. `GET /api/v1/channels/stats` — confirm the creator is monitored.
3. `GET /videos/api/search?q=<phrase>` — find transcript segments containing the phrase, each with `start_time` for deep-linking.
4. `GET /videos/api/<youtube_video_id>` — pull the full video record, including `description`, plus all its ordered segments.

```bash
# "What has anyone said about second brains?"
curl "https://knowledge.nextlevelfoundry.com/enroll/videos/api/search?q=second+brain&limit=5"

# Full record for one video, including the creator's own description
curl "https://knowledge.nextlevelfoundry.com/enroll/videos/api/TaKmTrsx2Lo"
```

---

## 3. Technicals

### Quickstart

```bash
# Deep status — check this FIRST; it is the only call that verifies the
# corpus is actually readable rather than just that a process is listening.
curl https://knowledge.nextlevelfoundry.com/enroll/api/v1/status
# {"status":"ok","problems":[],"components":{...}}

# Liveness (cheap, safe to poll often)
curl https://knowledge.nextlevelfoundry.com/enroll/health

# What channels/domains exist?
curl https://knowledge.nextlevelfoundry.com/enroll/api/v1/channels/stats

# Search transcript text
curl "https://knowledge.nextlevelfoundry.com/enroll/videos/api/search?q=second+brain&limit=5"
```

All calls above are confirmed working as of this guide's `verified:` date.

### Endpoint & auth

Base URL: `https://knowledge.nextlevelfoundry.com/enroll/...` (Traefik strips the `/enroll` prefix before it reaches the service).

An older host-routed domain, `https://knowledge-admin.nextlevelguild.com/...`, currently serves the same service with no prefix. It still works but is being phased out — don't build new integrations against it.

**Auth: none.** There is no API key or token check anywhere in this service. `CORS_ORIGINS` is set to allow any origin. Treat this as an internal-network-trust model, not a public API — don't expose it to end users, and don't rely on it being gated by anything but obscurity.

### Operations

Status & metadata (Postgres-backed):

```
GET /api/v1/status                   # NEW in 2.0.0 — aggregate health; see below
GET /health                          # liveness; now reflects the aggregate verdict
GET /api/v1
GET /api/v1/channels
GET /api/v1/channels/<id>
GET /api/v1/channels/stats
GET /api/v1/pipeline/items
GET /api/v1/pipeline/stats
GET /api/v1/pipeline/failed
```

Transcript content (SurrealDB-backed) — **all working as of 2.0.0**:

```
GET /videos/api/<youtube_video_id>   # single video + description + ordered segments
GET /videos/api/list                 # ?q= title search, ?domain=, ?limit=, ?offset=
GET /videos/api/search               # ?q= full-text search across 203k segments
GET /videos/api/stats
GET /videos/api/domains
```

Not implemented — these return **HTTP 501**, and always have been empty:

```
GET /tags/api/list · /tags/api/<id> · /tags/api/hierarchy · /tags/api/graph · /tags/api/stats
```

Write endpoints under `/api/v1/*` (create channel, retry pipeline item, etc.) exist but are for internal/admin use — not documented here as a consumer surface.

#### `GET /api/v1/status` — the health check to build against

Returns the aggregate verdict plus per-component detail. **Alert on `status != "ok"`**, not on the HTTP code alone.

| `status` | HTTP | Meaning |
|---|---|---|
| `ok` | 200 | All dependencies reachable, corpus non-empty, content arriving |
| `degraded` | 200 | Usable, but something is wrong — read `problems[]` |
| `down` | 503 | A dependency is unreachable or the corpus is empty. Results are not trustworthy |

`problems[]` is a list of plain-English strings. The checks that matter:

- **consistency** — compares videos the pipeline *claims* to have indexed against what SurrealDB actually holds. This is the check that would have caught the July–August 2026 outage on day one.
- **freshness (search index)** — no new video indexed in 72h → the discovery/ingest path has stalled.
- **freshness (file archive)** — no new transcript file in 72h → the archive path has stalled. Note that videos ingested during such a window exist only in SurrealDB and cannot be rebuilt from disk.

Write endpoints under `/api/v1/*` (create channel, retry pipeline item, etc.) exist but are for internal/admin use — not documented here as a consumer surface.

### Rate limits & quotas

None enforced server-side. Follow this project's standing courtesy rule: if you're making more than 5 calls in a batch, put a minimum ~2s delay between them (3s+ for large batches).

### Errors & retries

Working endpoints return JSON. Errors are `{"error": "..."}` with a non-200 status, and list endpoints generally return `{items_key: [...], total/count: N, limit, offset}`.

**Fixed in 2.0.0 — the 200-with-an-error-inside failure mode is gone.** Endpoints previously returned HTTP 200 carrying an error string where data belonged (e.g. `{"segments":"The namespace 'knowledge' does not exist"}`), which was undetectable by consumers checking status codes. A datastore failure is now always a real error status:

| Code | Meaning |
|---|---|
| 200 | Success. The payload has the documented shape |
| 400 | Bad request (missing/invalid parameter) |
| 404 | The requested video does not exist in the corpus |
| 501 | The feature was never implemented (all `/tags/*` endpoints) |
| 503 | SurrealDB unreachable or a query was rejected — **retry with backoff** |

503 is the only status worth retrying. 501 will never succeed.

### Versioning

No formal API versioning scheme exists yet. The `/api/v1` prefix is aspirational, not an enforced contract — there is currently only one version of this API, and no policy yet for how a breaking change would be communicated. This guide's own `version:` frontmatter field is the only versioning contract available today; re-read this guide on any bump.

### Data model

Records live in SurrealDB, reached only via the Admin API's `/videos/*` endpoints (never directly):

- **`channel`** — `youtube_handle`, `name`, `domain`, `ingested_at`
- **`video`** — `youtube_id`, `title`, `description`, `published_at`, `duration_seconds`, `url`, `channel_handle`, `channel_name`, `domain`, `segment_count`, `has_timestamps`, `transcript_path`, `ingested_at`
- **`segment`** — `text`, `chunk_index`, `start_time`, `end_time`, `duration`, `requires_visual` (bool), `video_youtube_id`, `domain`, `published_at`
- Relations: `channel->has_video->video`, `video->has_segment->segment`

Two fields deserve attention:

- **`has_timestamps`** — `false` for ~200 older videos stored as plain prose. Their transcript text is complete, but every segment's `start_time`/`end_time` is `0`. **Check this before building a timestamp deep-link**, or you will link everyone to 0:00.
- **`embedding`** — defined on `segment` but **not populated**. The corpus was rebuilt without embeddings because no semantic search consumes them. Treat vector search as unavailable.

**`tag`** — described in guide v1.0.0 but never implemented; no such table exists and nothing writes one. Removed from this data model rather than left as an aspiration.

### Failure modes

| Symptom | Likely cause | What to do |
|---|---|---|
| Any endpoint returns **503** with `"source":"surrealdb"` | SurrealDB unreachable, or a query was rejected | Retry with backoff. If it persists, `GET /api/v1/status` names the failing component |
| `/tags/*` returns **501** | Tagging was never implemented; no tag data has ever existed | Don't retry, don't build on it. Guide v1.0.0 described a tag graph that does not exist |
| `GET /api/v1/status` reports `degraded` with a **freshness** problem | An ingestion path has stalled. Existing content is still correct and queryable — it just isn't growing | Safe to keep reading. Report it (§4) if it persists past a day |
| `GET /api/v1/status` reports `degraded` with a **consistency** problem | The pipeline is marking videos indexed that SurrealDB doesn't hold — the exact failure of July–August 2026 | Treat recent content as untrustworthy and report it immediately |
| Deep links all land at 0:00 | The video has `has_timestamps: false` — a plain-prose transcript with no timing | Check `has_timestamps` before generating a timestamped link |
| `GET /videos/api/search` finds nothing for an obviously-present idea | Search is **literal substring matching**, not semantic | Try the creator's actual phrasing, or search `title` via `/videos/api/list?q=` |
| `GET /api/v1/pipeline/stats` shows `recent_24h` all zero while content is landing | Quirk in how the 24h window is computed; not confirmed stalled ingestion | Cross-check `GET /api/v1/status` → `components.surrealdb.hours_since_newest`, which is measured directly |

**Historical note.** Between roughly 2026-07-16 and 2026-08-05 this entire surface was unusable: SurrealDB ran in memory-only mode, so the corpus was empty, while every health check reported "healthy" and the pipeline recorded 1,086 videos as successfully indexed. If you integrated during that window and concluded content didn't exist, re-check — it does. See the Changelog.

<!-- internal -->
Internal-only reference (ops use, not for consumers): the Admin API container is `knowledge-admin-api`, reachable directly at `10.0.0.33:5020` on Banner. Postgres is `knowledge-postgres:5019` and SurrealDB is `knowledgestack-surrealdb:5040` on the same host, namespace `knowledge`, database `transcripts`. Source: `src/admin/api/{videos,tags,status}.py`. Bug tracking: `.claude/BUGS.md`.

SurrealDB storage backend is `rocksdb:/data/knowledge.db` — **never `memory`**, which is what caused the 2026-07/08 outage. Its data volume must be owned by uid 65532; Docker resets ownership on an *empty* named volume at container-create time, so the volume is kept non-empty via `/data/.keep`. The root credential is stored inside the datastore: changing `--pass` in the compose file does NOT rotate it (verified — the old password keeps working). Rotate with `DEFINE USER OVERWRITE root ON ROOT PASSWORD '...' ROLES OWNER;`.

Rebuild the corpus from disk with `python3 scripts/reindex_from_files.py` (idempotent, resumable, ~15 min for 3,102 files).

Deployment source of truth is this repo's `docker-compose.yml`. A stale March-2026 copy of the project at `/opt/stacks/knowledge/` on Banner previously built `admin-api` and `landing`; those now deploy from the repo. That directory is orphaned and should be removed once confirmed unused.
<!-- /internal -->

---

## 4. How to Submit Requests

Report bugs, request new capabilities (for example: semantic search, an aggregate health endpoint, an authentication layer), or ask questions through {{REQUEST_CHANNEL}}.

A complete, actionable request includes: which endpoint or capability you need, why your project can't proceed without it, and — for bug reports — the exact request you made and the response you got back, since (per §3) a 200 status here doesn't always mean success.

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 2.1.0 | 2026-08-14 | **New monitored channel: Pastor Chris Durkin** (`faith`), bringing the watch list to 51 — its full archive of 609 videos is being ingested on request. Corpus figures in §2 refreshed to the measured 4,205 videos / 310,860 segments. **NEW (§2):** documents what happens when YouTube rate-limits our caption requests, which pauses ingestion without failing anything — the corpus stays readable, freshness lags. No endpoint, payload or error-shape changes. |
| 2.0.0 | 2026-08-07 | **The SurrealDB-backed read surface works.** Root cause of the 2026-07/08 outage: SurrealDB ran on the in-memory storage backend, discarding every write, so the `knowledge` namespace never existed — the "does not exist" payloads in v1.0.0 were the symptom, not the cause. Now on persistent disk storage, verified across a restart. Corpus rebuilt from the 3,102 transcript files on disk (never affected): **3,059 videos / 203,488 segments**. Four further defects fixed: (1) the indexer reported success without checking any write result, which is why 1,086 videos were recorded as indexed while the store was empty; (2) the `video` table was missing 10 fields the indexer wrote, so SCHEMAFULL rejected every video write; (3) `/videos/api/*` returned 500s and `/tags/api/*` returned 200-with-an-error-inside — datastore failures are now 503; (4) user input was interpolated unescaped into queries, including a `tag_id` that could append statements. **BREAKING:** `/tags/*` now returns **501** — tagging was never implemented and the tag data model described in v1.0.0 does not exist; it has been removed from §3 rather than left as an aspiration. **NEW:** `GET /api/v1/status` aggregate health check, including a consistency check that compares claimed-vs-actual indexed videos. `GET /videos/api/list` now returns `description`, `channel_name`, `url` and `has_timestamps`. `GET /videos/api/domains` returns real domains (it used invalid `SELECT DISTINCT` and always returned empty). |
| 1.0.0 | 2026-07-29 | First guide written to the `guides.ucontrolnetwork.com` Consumer Guide standard (`type: api`). Supersedes the prior ad hoc `v0.1.0-draft` version of this file — this is now the single Consumer Guide for this project. Scoped to the Admin API only; Embedding/Transcript services noted as non-consumer-facing in §1. Stability set to `alpha`: the SurrealDB-backed read surface (video lookup, tag browsing/hierarchy/graph, search) is non-functional. Part of that was already known (clean HTTP 500s, tracked since 2026-07-21); part was newly discovered while writing this guide (HTTP 200 responses carrying corrupted "namespace does not exist" payloads, root cause not yet confirmed). Only the Postgres-backed channel/pipeline endpoints and `/health` are confirmed reliable today. |
