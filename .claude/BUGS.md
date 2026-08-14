# Bugs and Issues

Track bugs discovered during conversations, tagged with conversation ID.

## Format

**Conv:** conv-YYYYMMDD-HHMMSS
**Bug:** Description
**Status:** Open/Fixed/Wont-Fix
**Date:** YYYY-MM-DD

---

## Bugs

**Conv:** 2d2bc04d-bc4d-4bfd-ba8f-746d0245f33f
**Bug:** Admin API's SurrealDB-backed browse/search endpoints throw 500s in production: `GET /videos/api/list`, `GET /videos/api/search`, `GET /videos/api/stats`, `GET /tags/api/stats` (confirmed live via curl against `knowledge-admin.nextlevelguild.com` and `docker logs knowledge-admin-api` on Banner, 2026-07-21). Traceback: `AttributeError: 'str' object has no attribute 'get'` in `src/admin/api/videos.py` (`list_videos` line ~87, `search_segments` line ~151) — code assumes `surreal_query()` returns a list of dicts, but for `count()`/`GROUP ALL` queries it's getting back a list containing a raw string instead. `GET /videos/api/domains` returns 200 but an empty list even though 1,078+ videos are indexed, consistent with the same underlying result-shape mismatch. Only `GET /videos/api/<id>` (single-record SELECT) and the Postgres-backed `/api/v1/channels*`, `/api/v1/pipeline*` endpoints are confirmed working. Root cause likely a SurrealDB response-shape change (e.g. `GROUP ALL` output format) that `surreal_query()` in `videos.py`/`tags.py` no longer parses correctly — not yet root-caused further.
**Status:** Open
**Date:** 2026-07-21
**Impact:** This is the primary consumer-facing search/browse surface documented in `docs/CONSUMER_GUIDE.md` — currently broken for anyone but single-video lookups by ID. Flagged as a known issue in that guide.

---

**Conv:** e539aefe-88fd-4029-888b-c5a4c4bf106b
**Bug:** SurrealDB-backed read surface has regressed further and now includes the single-video lookup previously confirmed working. `GET /videos/api/<youtube_video_id>` and `GET /tags/api/hierarchy`/`GET /tags/api/graph` now return **HTTP 200 with corrupted payloads** (e.g. `{"segments":"The namespace 'knowledge' does not exist","video":"T"}`), not clean errors — a naive consumer checking only status code would silently ingest garbage. `GET /tags/api/list` similarly returns 200 with `{"tags":"The namespace 'knowledge' does not exist", "count":40}`. Root cause candidate found via `docker logs knowledgestack-surrealdb` on Banner: the container logs `Storage mode: in-memory only (no persist path)` — SurrealDB has **no persistent storage configured**, running as an in-memory instance that reinitializes to default `namespace 'main'`/`database 'main'` on every restart. Yet the ingestion pipeline (`/api/v1/pipeline/items`) shows videos completing to `indexed_surreal` status as recently as 2026-07-27, so either ingestion is writing to a different SurrealDB connection/namespace than the Admin API queries, or there's a namespace-name mismatch between `src/embedding/embedder.py` and `src/admin/api/videos.py`/`tags.py`. Not root-caused further — this needs its own investigation session; not chased down here since it surfaced while writing `docs/CONSUMER_GUIDE.md`.
**Status:** Open
**Date:** 2026-07-29
**Impact:** Effectively the entire SurrealDB-backed consumer surface (single-video lookup, tag hierarchy/graph, tag list) is non-functional right now — only the Postgres-backed `/api/v1/channels*` and `/api/v1/pipeline*` endpoints are reliably working. This is more severe than the 2026-07-21 finding above (that one was clean 500s; this one returns fake-successful 200s with garbage data). Forces the new Consumer Guide's stability rating to `alpha` and its Quickstart/Operations sections to lean on Postgres-backed endpoints only. If SurrealDB really has no persistence, a container restart or crash could mean **1,083+ ingested videos' embeddings/segments are only ever in memory and would be unrecoverable** — worth confirming urgently, independent of the guide work.

---

**Conv:** 638c0809-8043-4316-b32f-2d2cb5ae85ed
**Bug:** A whole-IP YouTube rate limit was being recorded as "this video has no transcript", permanently blacklisting good videos. `fetcher.fetch_transcript()` caught every exception and returned `None`, and `fetch_and_save()` treats `None` as a permanent failure and appends the id to `fetch_state.json["failed"]` — which nothing ever retries. On 2026-08-14 YouTube's caption endpoint (`/api/timedtext`) began returning HTTP 429 ("Sorry..." interstitial, no `Retry-After`) for our whole WAN address; `youtube_transcript_api` raises `IpBlocked`, and videos with confirmed English auto-captions came back looking transcript-less. Verified the block is network-wide, not container-specific: the same signed caption URL returns 429 from Banner and from Friday. `api.list()` (caption *listing*) and yt-dlp metadata/listing calls still work — only the caption *download* is blocked. Browser TLS impersonation via curl_cffi does not get around it.
**Status:** Fixed
**Date:** 2026-08-14
**Impact:** Had the standing worker run against a non-empty queue during this block, it would have burned through the queue marking every video permanently failed at roughly one video per 5 minutes. It did not, only because the queue happened to be drained. Fix: `fetch_transcript()` now raises `TranscriptBlocked` for 429/`IpBlocked`/`RequestBlocked` instead of swallowing it, `fetch_and_save()` returns `{"blocked": True}` leaving state untouched, and the backfill worker stands down for `BLOCKED_COOLDOWN_SECONDS` (default 30m) rather than advancing the queue. Four ids wrongly marked failed during diagnosis were removed from `failed` by hand.

---

**Conv:** 638c0809-8043-4316-b32f-2d2cb5ae85ed
**Bug:** Standing discovery only reads a channel's `/videos` tab, so channels that publish as livestreams are almost entirely invisible to it. Found while adding @PastorChrisDurkin: 174 videos under `/videos`, but **432 under `/streams`** — the sermons, which are the whole point of the channel. Any monitored channel that livestreams its main content has the same gap.
**Status:** Fixed (for opted-in channels)
**Date:** 2026-08-14
**Impact:** `discover_new_videos()` now reads an optional per-channel `tabs` list (default `["videos"]`, so unaffected channels still cost one request). @PastorChrisDurkin is set to `["videos", "streams"]`. The other 50 channels have NOT been audited for the same problem — if a monitored creator has moved to livestreaming, we are silently missing their recent output.
