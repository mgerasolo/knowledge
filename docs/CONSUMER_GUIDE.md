---
guide: knowledge
type: api
provider: knowledge
audience: [nai-dev, app]
stability: beta
version: 2.5.0
updated: 2026-08-14
verified: 2026-08-14
owner: Matt Gerasolo <matt@gerasolo.com>
---

# KnowledgeStack — YouTube Transcript & Knowledge API

> Query timestamped YouTube transcripts, entity/topic tags, and ingestion status for 50+ monitored channels, instead of re-scraping or re-transcribing content this project has already processed.

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

- You need "what has creator X said about Y" and the channel is one of the 50+ already monitored — the content is likely already transcribed and timestamped, so you avoid re-transcribing it yourself.
- You want **meaning-based search, not just literal text match** — `GET /videos/api/semantic-search` (new in 2.5.0) finds segments about an idea even when the creator phrased it differently. Ask for "handling price objections" and get the segment where the coach never says the word "objection".
- You want a timestamped segment, not just a full transcript wall of text, so you can deep-link to the moment in the video.
- You want to scope a query to a topic area — content is pre-classified into `ai-tech`, `mindset`, `political`, `business`, `general`, `health`, `faith`.
- You want to know whether "no results" means "doesn't exist" vs. "not ingested yet" — the ingestion pipeline's queue/failure state is queryable.

### Ingestion can pause on a YouTube rate limit

Transcripts are pulled from YouTube's caption endpoint, which rate-limits by IP and returns HTTP 429 with no retry hint. When that happens, ingestion stands down and waits — it does not fail videos, and nothing already in the corpus is affected. The practical consequence for a consumer is that a video published today may not appear for hours longer than usual. `GET /api/v1/status` still reports `ok` during a block (the corpus is readable); check `components.transcript_files.hours_since_newest` if freshness matters to you.

### When this doesn't help (use something else)

- You need a whole channel that isn't one of the 50+ currently monitored. Single videos CAN now be enrolled on demand (`POST /api/v1/videos/enroll`, new in 2.4.0) — but there is no on-demand "watch this whole channel" endpoint; adding a channel is a request (§4).
- You need guaranteed uptime or a support SLA. See the operational table below — there is none.
- You need entity/topic tags. The `/tags/*` endpoints return **HTTP 501** — tagging was never implemented and no tag data has ever been written. Ignore the tag graph described in older versions of this guide.

### Video descriptions carry more than the transcript

Each video record includes the full YouTube `description`, which for many creators contains material that is **not spoken in the video** — verbatim prompts, tool links, timestamps/chapters, and resource lists. If you are grounding an answer in "what this creator actually gave people," check `description` as well as the transcript segments. The large majority of videos (roughly 19 in 20) have one.

### Operational facts

| Aspect | Current reality |
|---|---|
| Maintenance / ownership | Single maintainer (Matt Gerasolo), no on-call rotation |
| Availability | Best-effort only, no uptime guarantee. Runs on a shared dev host and can go down for deploys/maintenance without notice |
| Cost / quota | Free for internal use; no server-side rate limiting. Per this project's standing courtesy rule: 2s+ delay between calls if you're batching more than 5 requests |
| Data persistence | **Resolved 2026-08-05.** SurrealDB ran on the in-memory storage backend, so it discarded every write and the `knowledge` namespace did not exist. It now runs on persistent disk storage (rocksdb), verified by restarting the container and confirming both the namespace and a canary record survived. The corpus was rebuilt from the transcript files on disk, which were never affected |
| Corpus size | Thousands of videos · hundreds of thousands of timestamped segments · 50+ channels, and growing daily. These are live figures — get current counts from `GET /api/v1/status` rather than trusting any number printed in a document |
| Data retention | Indefinite. Nothing is expired or deleted on a schedule — once a video is in the corpus it stays queryable. The transcript source files on disk are the rebuild source of record for the search index |
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

# Search transcript text (literal substring)
curl "https://knowledge.nextlevelfoundry.com/enroll/videos/api/search?q=second+brain&limit=5"

# Search by MEANING (semantic — new in 2.5.0)
curl "https://knowledge.nextlevelfoundry.com/enroll/videos/api/semantic-search?q=how+to+handle+price+objections&limit=5"
```

All calls above are confirmed working as of this guide's `verified:` date.

### Endpoint & auth

Base URL: `https://knowledge.nextlevelfoundry.com/enroll/...` (Traefik strips the `/enroll` prefix before it reaches the service).

An older host-routed domain, `https://knowledge-admin.nextlevelguild.com/...`, currently serves the same service with no prefix. It still works but is being phased out — don't build new integrations against it.

**Auth: none.** There is no API key or token check anywhere in this service. `CORS_ORIGINS` is set to allow any origin. Treat this as an internal-network-trust model, not a public API — don't expose it to end users, and don't rely on it being gated by anything but obscurity.

**Access scope: read-only, with one write.** Everything offered to you in this guide is a read, with a single exception new in 2.4.0: `POST /api/v1/videos/enroll` (below), which adds one video to the corpus. Other write/admin endpoints exist (create a channel, retry a pipeline item, and so on) but are intentionally not offered to consumers — this is a single-maintainer service with no auth layer to protect writes, so the rest of the write surface stays internal. Direct database access is also intentionally not offered: the API is the only supported read path, which lets the underlying schema change without breaking consumers. If you need something this surface doesn't give you, ask for it (§4) rather than reaching around the API.

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
GET /videos/api/search               # ?q= literal substring search across all transcript segments
GET /videos/api/semantic-search      # NEW 2.5.0 — meaning-based search; ?q=, ?domain=, ?limit=, ?min_score=
GET /videos/api/stats
GET /videos/api/domains
```

**Semantic search parameters** (`GET /videos/api/semantic-search`):

| Param | Default | Meaning |
|---|---|---|
| `q` | required | The idea to search for, in your own words — minimum 3 characters. It is matched by meaning, not by literal text |
| `domain` | none | Restrict to one topic area (values from `/videos/api/domains`). An unknown domain returns an empty result, not an error |
| `limit` | 20, cap 50 | Maximum results |
| `min_score` | 0.4 | Similarity floor, 0–1. Results under it are dropped — at the default, an off-topic query correctly returns nothing. Pass `0` to disable and see everything ranked |

Under the hood the query is embedded by the same model that embedded the corpus (via the fleet model gateway) and matched against a vector index in the datastore. The response's `model` field names the embedding model alias; if it ever changes, that is a re-embed of the whole corpus and will be announced in this guide with a version bump.

Single-video enrollment — **NEW in 2.4.0** (#46), the one consumer-facing write:

```
POST /api/v1/videos/enroll
```

Ingests ONE video through the normal pipeline without enrolling its channel — built for guest appearances: a monitored personality interviewed on a show this project doesn't (and shouldn't) watch wholesale. Synchronous — the response arrives when ingestion finishes, normally well under a minute.

```bash
curl -X POST https://knowledge.nextlevelfoundry.com/enroll/api/v1/videos/enroll \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://youtu.be/hiQW6FZkA9o",
       "tags": ["personality:myron-golden"],
       "domain": "business"}'
```

- **Payload:** `video_id` (11-char ID) or `url` (any YouTube URL shape — share links, watch pages, shorts, live, embed). Optional `tags`: lowercase slugs like `personality:myron-golden` (letters/digits/`: . _ -`, max 80 chars). Optional `domain` (default `general`).
- **Tags are corpus markers**, stored on the video record (`tags` field, visible in `/videos/api/<id>` and `/videos/api/list`) and merged, never replaced — re-enrolling with new tags adds them. Filter the video list by tag with `GET /videos/api/list?tag=personality:myron-golden`. These are distinct from the never-implemented `/tags/*` entity graph, which still returns 501.
- **Enrolling a video that is already in the corpus is safe**: it returns 200 with `already_fetched: true`, does not re-fetch anything, and still applies the tags.
- **Status codes:** `200` ingested (or already held) · `400` bad input (unparseable reference, invalid tags) · `404` yt-dlp could not read the video (bad ID, private, deleted) · `409` a stream that hasn't finished — captions don't exist yet, retry after it ends · `422` readable video with no captions · `429` YouTube is rate-limiting caption requests, retry later · `502/504` internal pipeline unreachable/timed out.
- The response carries the receipt: `segment_count`, `file_path`, `indexed` (whether the search index took the write — `false` with `index_error` means the transcript is safely on disk but not yet searchable), and `tags_applied`.

Not implemented — these return **HTTP 501**, and always have been empty:

```
GET /tags/api/list · /tags/api/<id> · /tags/api/hierarchy · /tags/api/graph · /tags/api/stats
```

Write endpoints under `/api/v1/*` (create channel, retry pipeline item, etc.) exist but are for internal/admin use — not documented here as a consumer surface.

### Health check

`GET /api/v1/status` is the health check to build against.

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
- **downloader** — the tool that fetches from YouTube is missing, cannot complete a real call, or has fallen behind YouTube's changes. Previously invisible: a dead downloader only showed up 72 hours later as a freshness warning blaming "ingestion". A downloader problem never makes `status` `down` — the corpus stays complete and queryable, it has just stopped growing.

**Not live yet.** The `downloader` component and its `problems[]` entry ship with the next rebuild of the transcript-service container, which is deliberately deferred while a long backfill runs. Until then `components.downloader` is absent from responses. Documented here now so the contract change and the code land together, not so you can rely on it today — check for the key before reading it.

### Response fields

Everything below is documented as the API returns it (not as it is stored), verified against the live service on this guide's `verified:` date. Derivation column: *passed through* = comes from YouTube unmodified · *assigned at ingest* = set from this project's channel configuration · *computed* = calculated by this service · *measured* = counted live from the datastore on every call.

**The list envelope.** List endpoints wrap their rows in a consistent envelope: a payload-specific items key, a count, and — where paging applies — echoes of `limit`/`offset`:

| Endpoint | Envelope |
|---|---|
| `GET /videos/api/list` | `{videos: [...], total, limit, offset}` — `total` is the measured count of ALL matching videos, not the page size. `limit` defaults to 50, caps at 100 |
| `GET /videos/api/search` | `{results: [...], count, query}` — `count` is only the number of rows returned (≤ `limit`), NOT the total matches, and search has no `offset`/paging. `limit` defaults to 20, caps at 50 |
| `GET /videos/api/semantic-search` | `{results: [...], count, query, model, search_type: "semantic"}` — same segment shape as `/search` plus a `score` per result (similarity 0–1, higher = closer). Results are ordered by `score` descending. No paging |
| `GET /videos/api/<id>` | `{video: {...}, segments: [...]}` — no counts; `segments` is the complete ordered list |

**Video record** — as returned by `/videos/api/list`; `/videos/api/<id>` returns the same fields plus every stored field (it selects the whole record):

| Field | Type | Meaning | Derivation |
|---|---|---|---|
| `youtube_id` | string | YouTube's video ID — the lookup key for `/videos/api/<id>` | passed through |
| `title` | string | Video title | passed through |
| `description` | string | Full YouTube description — often carries links/prompts not spoken in the video (§2) | passed through |
| `published_at` | ISO 8601 | YouTube publish date | passed through |
| `duration_seconds` | number | Video length in seconds; `0.0` where YouTube didn't supply it | passed through |
| `url` | string | Canonical `youtube.com/watch` link | computed from `youtube_id` |
| `channel_handle` / `channel_name` | string | The monitored channel this came from | assigned at ingest |
| `domain` | string | Topic area (`ai-tech`, `mindset`, …) | assigned at ingest |
| `tags` | array of strings, or absent | Corpus tags (e.g. `personality:myron-golden`) from single-video enrollment; absent on videos never tagged. Filterable via `?tag=` on `/videos/api/list` | assigned at enrollment (2.4.0) |
| `segment_count` | int or null | Number of transcript segments | computed at ingest; `null` on records the newer ingest path wrote without computing it |
| `has_timestamps` | bool or null | Whether this video's segments carry real timings (§3 Data model) | computed at ingest; `null` = never computed — check the segments' `start_time` directly before deep-linking |
| `ingested_at` | ISO 8601 | When this service indexed the video | computed by the service |
| `transcript_path`, `embedding` | — | Internal bookkeeping that leaks into `/videos/api/<id>` responses; ignore both. (`embedding` on segments powers semantic search internally — the vector itself is not part of the consumer contract) | — |

**Segment record** — `/videos/api/<id>` returns these in `segments[]`; `/videos/api/search` and `/videos/api/semantic-search` return the same shape in `results[]` plus `video_youtube_id` and `video_title` (semantic-search additionally adds `score`):

| Field | Type | Meaning | Derivation |
|---|---|---|---|
| `text` | string | The transcript text of this chunk | passed through from YouTube captions |
| `chunk_index` | int | 0-based position within the video — the sort key | computed at chunking |
| `start_time` / `end_time` / `duration` | number (seconds) | Where the chunk sits in the video. All `0.0` on plain-prose transcripts | derived from caption timings |
| `requires_visual` | bool | Heuristic: the speaker is referring to something shown on screen | computed at ingest |
| `domain` | string | Copy of the parent video's domain, so search can filter without a join | assigned at ingest |
| `video_youtube_id` | string | The parent video's YouTube ID | assigned at ingest |
| `video_title` | string | The parent video's title — enrichment the search endpoint adds per request, not stored on the segment | computed per request |

**`GET /api/v1/status`** — every field is computed at request time; nothing is cached:

| Field | Type | Meaning | Derivation |
|---|---|---|---|
| `status` | `ok` / `degraded` / `down` | The aggregate verdict — alert on anything but `ok` | computed from the component checks |
| `problems[]` | string[] | Plain-English description of each failing check; empty when `ok` | computed |
| `checked_at` | ISO 8601 | When these checks ran | computed |
| `components.postgres` | object | `ok`, `pipeline_items`, `marked_indexed`, `newest_completed_at`, `hours_since_newest` — what the pipeline *claims* to have done | measured from Postgres |
| `components.surrealdb` | object | `ok`, `videos`, `segments`, `newest_ingested_at`, `hours_since_newest`, `detail` — what the search index *actually holds*. This is where live corpus counts come from | measured from SurrealDB |
| `components.transcript_files` | object | `ok`, `files`, `newest_file_at`, `hours_since_newest` — the on-disk rebuild source of record | measured from disk |
| `thresholds` | object | `stale_ingest_hours`, `consistency_tolerance` — what the freshness and consistency checks compare against | service configuration |

**`GET /api/v1/channels/stats`**:

| Field | Type | Meaning | Derivation |
|---|---|---|---|
| `total` | int | Number of monitored channels | measured from Postgres |
| `by_domain[]` | `{domain, count, active_count}` | Channels per topic area; `active_count` counts only channels currently active for ingestion | measured |
| `by_ingestion_mode[]` | `{ingestion_mode, count}` | How each channel is ingested (currently all `auto`) | measured |
| `health` | `{healthy, warning, error, exceptions}` | Ingestion-health rollup by consecutive fetch failures: `healthy` = 0, `warning` = 1–2, `error` = 3+, `exceptions` = channels flagged as known exceptions | measured |

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
- **`embedding`** — populated as of 2.5.0 and indexed for vector search (this is what `/videos/api/semantic-search` queries). New ingests are embedded automatically; a re-runnable backfill sweeps up anything a gateway outage misses. Consumers never touch this field directly — use the semantic-search endpoint.

**`tag`** — described in guide v1.0.0 but never implemented; no such table exists and nothing writes one. Removed from this data model rather than left as an aspiration.

### Failure modes

| Symptom | Likely cause | What to do |
|---|---|---|
| Any endpoint returns **503** with `"source":"surrealdb"` | SurrealDB unreachable, or a query was rejected | Retry with backoff. If it persists, `GET /api/v1/status` names the failing component |
| `/tags/*` returns **501** | Tagging was never implemented; no tag data has ever existed | Don't retry, don't build on it. Guide v1.0.0 described a tag graph that does not exist |
| `GET /api/v1/status` reports `degraded` with a **freshness** problem | An ingestion path has stalled. Existing content is still correct and queryable — it just isn't growing | Safe to keep reading. Report it (§4) if it persists past a day |
| `GET /api/v1/status` reports `degraded` with a **consistency** problem | The pipeline is marking videos indexed that SurrealDB doesn't hold — the exact failure of July–August 2026 | Treat recent content as untrustworthy and report it immediately |
| `GET /api/v1/status` reports `degraded` with a **downloader** problem | The tool that fetches from YouTube is broken, missing, or stale. Nothing new will arrive until it is fixed | Everything already in the corpus is correct and safe to read. Report it (§4) — this one does not fix itself |
| Deep links all land at 0:00 | The video has `has_timestamps: false` — a plain-prose transcript with no timing | Check `has_timestamps` before generating a timestamped link |
| `GET /videos/api/search` finds nothing for an obviously-present idea | `/search` is **literal substring matching** | Use `/videos/api/semantic-search` for meaning-based matching, or try the creator's actual phrasing |
| `GET /videos/api/semantic-search` returns **503** with `"source":"embedding-service"` | The embedding gateway or vector store is down — the query text couldn't be embedded or matched | **Retry with backoff** — the response carries `retryable: true`. Keyword `/search` still works during such an outage |
| Semantic search returns nothing for a real idea at default settings | Everything scored under the 0.4 similarity floor — genuinely off-corpus, or phrased very differently | Retry with `min_score=0` to see the ranked long tail before concluding the content doesn't exist |
| `GET /api/v1/pipeline/stats` shows `recent_24h` all zero while content is landing | Quirk in how the 24h window is computed; not confirmed stalled ingestion | Cross-check `GET /api/v1/status` → `components.surrealdb.hours_since_newest`, which is measured directly |

**Historical note.** Between roughly 2026-07-16 and 2026-08-05 this entire surface was unusable: SurrealDB ran in memory-only mode, so the corpus was empty, while every health check reported "healthy" and the pipeline recorded 1,086 videos as successfully indexed. If you integrated during that window and concluded content didn't exist, re-check — it does. See the Changelog.

### Staying current

- **How this guide was last checked:** every call in the Quickstart was re-run against the live service on the `verified:` date in the frontmatter, and the responses matched what this guide documents.
- **What the provider owes you:** any change to an endpoint, payload, limit, or error shape updates this guide in the same unit of work as the change — a shipped change with a stale guide is a broken contract. Independently of changes, the Quickstart and the health check are re-run weekly against the live service and `verified:` is bumped when they still behave as documented.
- **What you owe yourself as a consumer:** check your delivered bundle at least weekly and compare this guide's `version` against the one you integrated with. A `major` bump means read the Changelog before your next call; `minor` means a new capability is available; `patch` means wording only. A `verified:` date weeks in the past is a yellow flag, not a red one — the guide may be fine, but nobody has confirmed it recently. Run `GET /api/v1/status` before building anything expensive on it.

<!-- internal -->
Internal-only reference (ops use, not for consumers): the Admin API container is `knowledge-admin-api`, reachable directly at `10.0.0.33:5020` on Banner. Postgres is `knowledge-postgres:5019` and SurrealDB is `knowledgestack-surrealdb:5040` on the same host, namespace `knowledge`, database `transcripts`. Source: `src/admin/api/{videos,tags,status}.py`. Bug tracking: `.claude/BUGS.md`.

SurrealDB storage backend is `rocksdb:/data/knowledge.db` — **never `memory`**, which is what caused the 2026-07/08 outage. Its data volume must be owned by uid 65532; Docker resets ownership on an *empty* named volume at container-create time, so the volume is kept non-empty via `/data/.keep`. The root credential is stored inside the datastore: changing `--pass` in the compose file does NOT rotate it (verified — the old password keeps working). Rotate with `DEFINE USER OVERWRITE root ON ROOT PASSWORD '...' ROLES OWNER;`.

Rebuild the corpus from disk with `python3 scripts/reindex_from_files.py` (idempotent, resumable, ~15 min for 3,102 files).

Deployment source of truth is this repo's `docker-compose.yml`. A stale March-2026 copy of the project at `/opt/stacks/knowledge/` on Banner previously built `admin-api` and `landing`; those now deploy from the repo. That directory is orphaned and should be removed once confirmed unused.
<!-- /internal -->

---

## 4. How to Submit Requests

All requests go through {{REQUEST_CHANNEL}}. The canonical request kinds:

- **clarification** — this guide is ambiguous or doesn't answer your question.
- **bug** — the service contradicts what this guide promises (evidence format below).
- **feature** — a capability you need that doesn't exist yet: an auth layer, a new monitored channel, whole-channel on-demand transcription.
- **feedback** — something works, but badly; or a suggestion short of a feature.
- **integration** — you are starting (or stopping) to call this API. Declare which endpoints you call and what breaks on your side if they change — it is the only way the provider knows to warn you before a breaking change ships. One message, filed once.
- **access** — you need a guide or capability delivered to you that wasn't.
- **standard-change** — a proposed change to the consumer-guide standard itself, not to this service.

**Before filing a problem report, run `GET /enroll/api/v1/status` and include its result.** If it reports `degraded` or `down`, that IS the report — the service is unwell, which is triaged differently from "my integration is broken."

**A bug report carries all six pieces of evidence.** A report without them becomes a conversation, and the conversation costs more than the fix:

1. What you were trying to do.
2. The exact command you ran (credentials removed — though this API has none).
3. The full response: status code AND body.
4. What you expected, and which line of this guide promised it.
5. When it started, and whether it ever worked.
6. Intermittent or consistent (X of Y attempts).

---

## Changelog

| Version | Date | Notes |
|---|---|---|
| 2.5.0 | 2026-08-14 | **Semantic (meaning-based) search ships: `GET /videos/api/semantic-search`** — the capability §1 has promised since v1.0.0 and every version until now disclaimed. Query with your own phrasing (`?q=`), optionally scope by `?domain=`, tune with `?limit=` (default 20, cap 50) and `?min_score=` (default 0.4). Same segment shape as keyword `/search` plus a per-result similarity `score` and a top-level `model` field naming the embedding model. Status codes: 400 bad request · 503 + `retryable: true` when the embedding gateway or vector store is down (keyword search keeps working) · 200 with an empty list when nothing relevant exists — at the default floor an off-topic query correctly returns nothing. Behind it: the corpus's segment embeddings are now real (OpenAI text-embedding-3-small via the fleet model gateway, chosen over a local model after a measured head-to-head on real corpus content), stored in a vector index in the datastore; the full pre-existing corpus was backfilled the same day, and new ingests embed automatically with failures counted and reported rather than silently swallowed — the silent-swallow path is how the corpus once ended up with zero vectors. The §2/§3/data-model claims that embeddings "are not populated" and semantic search "does not exist" are reversed. (Authored as 2.4.0 in parallel with the single-video-enrollment 2.4.0 below; renumbered at merge.) |
| 2.4.0 | 2026-08-14 | **NEW: single-video enrollment** (`POST /api/v1/videos/enroll`, #46) — ingest ONE video (a guest appearance) through the normal pipeline without enrolling its channel; accepts any YouTube URL shape or a bare video ID; looks up title/channel/date from the video itself. **NEW: video-level corpus tags** — optional `tags` (lowercase slugs, e.g. `personality:myron-golden`) are stored on the video record, merged never replaced, and returned by both video read endpoints; **NEW: `?tag=` filter on `GET /videos/api/list`** to pull a whole corpus (videos without tags simply drop out of a filtered list). Access scope in §3 amended from "read-only" to "read-only with one write". §2's "no on-demand transcription" limitation row updated — it is now channel-level only. The never-implemented `/tags/*` entity graph is unchanged and still 501; corpus tags are a different, live mechanism. |
| 2.3.1 | 2026-08-14 | Central-registry intake fixes, wording only: `audience` frontmatter now uses the registry's controlled vocabulary (`nai-dev`, `app` — was two tags the validator doesn't recognize), and the health-check documentation now sits under its own `### Health check` heading as the `api` template requires (content unchanged). Quickstart re-run against the live service on today's `verified:` date. No endpoint, payload, or behavior changes. |
| 2.3.0 | 2026-08-14 | **Standard-compliance pass — no endpoint, payload, or behavior changes.** **NEW (§3): Response fields** — the documented payload contract for the list envelope, the video record, the segment record, `GET /api/v1/status` and `GET /api/v1/channels/stats`, each field with its type, meaning and derivation, including `has_timestamps` and `segment_count` returning `null` on records the newer ingest path wrote. **NEW (§3): Staying current**, and an explicit **read-only access scope** with the rationale for not offering writes or direct database access. **NEW (§2): a data-retention row.** §4 rebuilt to the standard's request kinds and 6-part bug-evidence format, with a pre-report status check. Corpus and channel figures throughout §1–§3 generalized to approximate scope — exact counts change daily and belong to `GET /api/v1/status`, not to a document; Changelog rows keep their point-in-time numbers as historical record. Two removals: a stale §4 claim that a 200 response "doesn't always mean success" (that failure mode was fixed in 2.0.0), and a paragraph that appeared twice in §3. **If you integrated at 2.2.0, this row is your diff.** This work was authored against 2.1.0 while 2.2.0 was in flight and is recorded in detail in the 2.1.2 and 2.1.1 rows below; those sit beneath 2.2.0 by version order and are easy to miss, but their content reaches consumers for the first time here. |
| 2.2.0 | 2026-08-14 | **New `downloader` component in `GET /api/v1/status`**, plus a matching `problems[]` entry. Nothing previously checked yt-dlp — the tool that actually fetches from YouTube — so a downloader that went missing, broke, or fell behind YouTube's changes would leave every check reporting healthy, and would eventually surface 72 hours later as a freshness warning blaming "ingestion" rather than naming the cause. It reports presence, version, whether a newer release is available, whether a JavaScript runtime is present, and the result of a real (hourly-cached) call to YouTube. A downloader problem degrades but never marks the stack `down`: the corpus stays complete and queryable, it has just stopped growing. **Additive and not live yet** — it ships with the next transcript-service rebuild, deliberately deferred while a long backfill runs, so `components.downloader` is absent from responses until then. No existing field, endpoint or status code changed. |
| 2.1.2 | 2026-08-13 | Guide brought into full compliance with the consumer-guide standard — no endpoint, payload, or behavior changes. Added **Staying current** (§3), **Response fields** (§3, verified against the live API — including `has_timestamps`/`segment_count` returning `null` on newer-path records), a data-retention row (§2), and an explicit read-only access scope with the rationale for not offering writes or direct database access (§3 Endpoint & auth). §4 rebuilt to the standard's request kinds and 6-part bug-evidence format, with a pre-report status check. Removed a stale §4 claim that a 200 "doesn't always mean success" (that failure mode was fixed in 2.0.0) and a paragraph duplicated in §3. |
| 2.1.1 | 2026-08-13 | Live corpus figures (channel/video/segment counts) generalized to approximate scope — exact numbers change daily and belong to `GET /api/v1/status`, not a document. Changelog rows keep their point-in-time numbers as historical record. Frontmatter dates corrected (were timestamped a day ahead, UTC vs local). No endpoint, payload or behavior changes. |
| 2.1.0 | 2026-08-14 | **New monitored channel: Pastor Chris Durkin** (`faith`), bringing the watch list to 51 — its full archive of 609 videos is being ingested on request. Corpus figures in §2 refreshed to the measured 4,205 videos / 310,860 segments. **NEW (§2):** documents what happens when YouTube rate-limits our caption requests, which pauses ingestion without failing anything — the corpus stays readable, freshness lags. No endpoint, payload or error-shape changes. |
| 2.0.0 | 2026-08-07 | **The SurrealDB-backed read surface works.** Root cause of the 2026-07/08 outage: SurrealDB ran on the in-memory storage backend, discarding every write, so the `knowledge` namespace never existed — the "does not exist" payloads in v1.0.0 were the symptom, not the cause. Now on persistent disk storage, verified across a restart. Corpus rebuilt from the 3,102 transcript files on disk (never affected): **3,059 videos / 203,488 segments**. Four further defects fixed: (1) the indexer reported success without checking any write result, which is why 1,086 videos were recorded as indexed while the store was empty; (2) the `video` table was missing 10 fields the indexer wrote, so SCHEMAFULL rejected every video write; (3) `/videos/api/*` returned 500s and `/tags/api/*` returned 200-with-an-error-inside — datastore failures are now 503; (4) user input was interpolated unescaped into queries, including a `tag_id` that could append statements. **BREAKING:** `/tags/*` now returns **501** — tagging was never implemented and the tag data model described in v1.0.0 does not exist; it has been removed from §3 rather than left as an aspiration. **NEW:** `GET /api/v1/status` aggregate health check, including a consistency check that compares claimed-vs-actual indexed videos. `GET /videos/api/list` now returns `description`, `channel_name`, `url` and `has_timestamps`. `GET /videos/api/domains` returns real domains (it used invalid `SELECT DISTINCT` and always returned empty). |
| 1.0.0 | 2026-07-29 | First guide written to the `guides.ucontrolnetwork.com` Consumer Guide standard (`type: api`). Supersedes the prior ad hoc `v0.1.0-draft` version of this file — this is now the single Consumer Guide for this project. Scoped to the Admin API only; Embedding/Transcript services noted as non-consumer-facing in §1. Stability set to `alpha`: the SurrealDB-backed read surface (video lookup, tag browsing/hierarchy/graph, search) is non-functional. Part of that was already known (clean HTTP 500s, tracked since 2026-07-21); part was newly discovered while writing this guide (HTTP 200 responses carrying corrupted "namespace does not exist" payloads, root cause not yet confirmed). Only the Postgres-backed channel/pipeline endpoints and `/health` are confirmed reliable today. |
