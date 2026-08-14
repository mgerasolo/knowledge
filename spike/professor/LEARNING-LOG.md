# Professor Spike — Learning Log

Append-only. Every entry dated. Tracking issue: [#16](https://github.com/mgerasolo/knowledge/issues/16)

The spike is a **learning instrument** (Matt, 2026-08-13): success is measured in
answered questions, not shipped code. This log is the deliverable that outlives the
throwaway code. Three registers + a chronological findings section.

---

## 1. Future Enhancements

Ideas surfaced during the spike that belong to later generations, not the spike.

| Date | Enhancement | Source |
|------|-------------|--------|
| 2026-08-13 | **Voice learning** — extract the personality's speaking style (signature phrases, recurring expressions, cadence) into a style profile injected into the persona prompt; later possibly fine-tuning. Myron has a distinct style with regularly repeated phrases. | Matt |
| 2026-08-13 | **Gen 2: Councils** — multiple professors in one conversation | Matt (issue #16) |
| 2026-08-13 | **Response ratings** + expert-in-the-loop review (Chris Durkin reviewing answer quality) | Matt (issue #16) |
| 2026-08-13 | **Wispr-style content actions** — key points, quotes, summaries on any answer (OpenWebUI Actions) | Matt (issue #16) |
| 2026-08-13 | **Speaker diarization** — true person-level corpus purity (separate the personality's speech from hosts/guests) | issue #16 |

## 2. Problems Faced

Every problem hit during the spike — what happened, what it cost, how it was
resolved or worked around.

| Date | Problem | Resolution / workaround |
|------|---------|------------------------|
| _(none yet — build not started)_ | | |

## 3. Core-System Changes (lessons for the main pipeline)

Changes the spike proves we need in the core KnowledgeStack system — chunking,
indexing, schema, ingestion, metadata. These graduate into real issues against
the main pipeline.

| Date | Lesson | Suggested core change | Filed as |
|------|--------|----------------------|----------|
| 2026-08-14 | Pre-build audit: **0 of 327,402 segments have embeddings** — entire library semantically unsearchable; silent failure (embedder writes NONE and continues) | Fix embedding config, backfill (Myron channels first), add embedding-coverage metric to status API, then vector index | [#44](https://github.com/mgerasolo/knowledge/issues/44) |
| 2026-08-14 | Pre-build audit: **all 4,458 videos have empty uploader** — metadata backfill never landed | Run/repair metadata backfill; add metadata-coverage metric | [#45](https://github.com/mgerasolo/knowledge/issues/45) |
| 2026-08-14 | Personality corpus needs guest appearances, but pipeline is channel-only | Single-video enrollment endpoint + per-video personality tagging | [#46](https://github.com/mgerasolo/knowledge/issues/46) |

## 4. Chronological Findings

Raw discoveries as they happen, newest last.

### 2026-08-13 — Pre-build
- Feasibility confirmed: 4,285 videos / ~314k embedded segments in SurrealDB, all
  with start/end timestamps + video IDs. Myron Golden (2 channels), Pastor Chris
  Durkin, Scott Adams all ingested.
- Frontend decision: OpenWebUI (RAG backend as a Pipe, citations via source
  events, video side panel via Artifacts). Thin custom two-panel UI is the
  fallback on the same API.
- grok-4 confirmed on the LiteLLM gateway during the January spike — re-verify at
  build time for the Tier-C ("AI extension") escalation model.

### 2026-08-14 — Pre-build audit (before any spike code)
- Probed the live store to verify spike prerequisites. Found the two silent gaps
  above (#44, #45) — the spike would have returned zero search results on day one.
  Lesson for the core system: quality coverage (embeddings %, metadata %) must be
  first-class health metrics; "ingested" is not "usable".
- Handed to the parallel semantic-search/embeddings workstream via #44 (embedding
  backfill + vector index are its domain; spike blocks on Myron-channel backfill only).
