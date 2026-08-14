# Architecture Decisions

Track architectural and technical decisions, tagged with conversation ID.

## Format

**Conv:** conv-YYYYMMDD-HHMMSS
**Decision:** Description
**Rationale:** Why this decision was made
**Date:** YYYY-MM-DD

---

## Decisions

(Decisions will be tracked here)

## [4bba31b2] Full YouTube metadata capture required
**Date:** 2026-04-01
**Decision:** Pull ALL available metadata from YouTube for every video, not just title/transcript. This includes: description, chapters/timestamps, hashtags, tags, category, view count, like count, comment count, thumbnail URL, uploader name. Video descriptions and chapters are the primary source for building the term/proper-noun dictionary used for transcript correction and entity extraction.
**Rationale:** Descriptions are human-written by content creators who know the correct spelling of products, people, and tools. Mining these for proper nouns auto-generates 80-90% of the correction dictionary without manual curation. Chapters provide segment-level topic context.
**Impact:** Requires schema update to video table in SurrealDB, backfill of 1,011 existing videos, and pipeline update for new videos.

## [4bba31b2] Chapter-aware segmentation is required
**Date:** 2026-04-02
**Decision:** Video chapters should be the primary segmentation boundary. Character-size chunking should only subdivide chapters that are too long. Each chapter is a standalone topic unit — findable, taggable, retrievable independently.
**Impact:** Sprint 1 — refactor chunking logic in embedder.py.

## [4bba31b2] Cross-channel persona tracking with appearance types
**Date:** 2026-04-02
**Decision:** Track people across channels with typed relationships: appeared_on (guest appearance, primary source) vs clip_referenced_in (someone played a clip, secondary). Use transcript context to classify which type during enrichment. This is core ontology functionality.
**Impact:** Ontology schema needs person → video relationship types.

## [4bba31b2] User feedback loops — design for it now, build later
**Date:** 2026-04-02
**Decision:** Data model should support thumbs up/down on RAG answers, wrong-segment flags, wrong-tag flags from day one. Actual feedback UI is Sprint 3+ (Gateway), but schema supports it from Sprint 1.
**Impact:** Add feedback fields to ontology schema design.

## [4bba31b2] Content licensing tracking — dropped from scope
**Date:** 2026-04-02
**Decision:** Not a priority. We're using transcripts for personal knowledge, not republishing.

## [4bba31b2] Engagement data — pull what's available, note retention curve as future
**Date:** 2026-04-02
**Decision:** Pull video-level statistics (views, likes, comments) via YouTube Data API. Second-by-second retention curve is not officially available via API — note for future if unofficial methods become reliable.

## [638c0809] Priority channel ingest runs as a separate paced script, not through the backfill worker
**Date:** 2026-08-14
**Decision:** A "ingest this channel now" request is served by `scripts/priority_ingest_channel.py`, run inside the transcript-service container, rather than by queueing into the standing backfill worker. The worker deliberately sleeps 30-600s between videos (~10/hour), so a 609-video channel would take roughly a week through it. The script does the identical per-video work — transcript, description, markdown file, SurrealDB index, state update — at ~5s spacing, and additionally reads `/streams` and `/shorts` and pulls each video's real `upload_date` so files land in the normal `<channel>/<YYYY-MM>/` layout instead of one undated directory.
**Impact:** Two writers now touch `fetch_state.json`. The script re-reads state immediately before each write to narrow the window, and writes `video_list.json` once at the end rather than per video. Also means a priority run dies if the container restarts — it logs to the persistent state volume and is safe to re-run, since anything already fetched is skipped.

## [638c0809] A YouTube rate-limit block is waited out, not worked around
**Date:** 2026-08-14
**Decision:** When YouTube 429s our caption requests for the whole IP, both the standing worker and the priority script park and retry with backoff rather than failing videos, switching tools, or routing around it. No proxy service was adopted — that is new third-party spend and a new egress path, which is Matt's call, not one to make mid-task.
**Impact:** Ingestion throughput is capped by whatever YouTube allows from our single WAN address. A paid residential-proxy tier (`youtube_transcript_api` supports proxies natively) is the known lever if this becomes a recurring blocker; it stays unbought until asked for.

## [638c0809] "Ready to start" is the existing `status:ai-ready` label, not a new phase
**Date:** 2026-08-14
**Decision:** `phase:0-backlog` was carrying two different meanings at once — "nobody has looked at this yet" and "decided, unclaimed, go ahead and take it" — with no way to tell them apart from the label. Work that is ready to be picked up now carries the existing `status:ai-ready` label, which already means exactly that. Rejected adding a new `phase:` value because the taxonomy already had a label for the concept, and the standing direction on this project is to stop stacking layers on top of layers.
**Impact:** Six issues — #17, #22, #23, #24, #25, #26 — carry `status:ai-ready` and are the current dispatch queue. Anyone picking up work reads that label; `phase:0-backlog` now means only "untriaged".

## [638c0809] No `blocked-by:` label — the one real dependency is a comment
**Date:** 2026-08-14
**Decision:** Exactly one cross-issue dependency exists today — #30 cannot ship before #29 — and it is recorded as a comment on #30. Rejected adding a `blocked-by:` label for it, because a label has to be kept accurate by everyone, forever, and a single relationship does not earn that maintenance cost.
**Impact:** Dependencies are stated in the blocked issue's own comments. Reconsider the label if cross-issue dependencies stop being exceptional and become routine.

## [638c0809] Adaptive per-channel scheduling (#20) is parked, not approved work
**Date:** 2026-08-14
**Decision:** Adaptive per-channel polling cadence is a future enhancement that nobody has approved. `phase:0-backlog` is the correct label for #20 and it stays there. This is written down because an agent reading the tracker later took the issue's rewritten acceptance criteria as evidence of approval and reported the issue as mislabelled — the label alone could not tell it otherwise.
**Impact:** The general rule this proves: a decision recorded only as a label is not recoverable by whoever comes next. Put the decision in the issue body, where the next reader will actually find it, and let the label follow it.
