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
| 2026-08-14 | **Codex Phase-1 build attempt produced zero code.** Background job `task-msshsw3n-1nabi2` was launched from the main KnowledgeStack checkout, so Codex's writable sandbox did not include the `~/wt/professor-spike` worktree; its skill renderer halted on `[Errno 30] Read-only file system` after 21s and it (correctly) did no work rather than claiming any. | Relaunch the Codex task with the worktree as the working directory / writable root (or build directly). Process lesson: when delegating to a sandboxed builder, the target worktree must be inside its writable root — verify with a touch-test before dispatch. |
| 2026-08-14 | **Incremental commits were blocked even though spike files were writable.** This worktree's Git administrative directory resolves into the parent checkout, which remained read-only to the managed workspace; `git commit` could not create `index.lock`. | Completed and verified the implementation in the authorized worktree without pretending commits succeeded. The supervisor must commit the finished tree from a session that can write the parent repository's `.git/worktrees/professor-spike/` metadata. |
| 2026-08-14 | **The isolated dependency install could not reach PyPI.** The requested local `spike/professor/.venv` was created, but the sandbox had no package-index network access. | Kept the venv local and reused packages from the repository's existing test environment through a local path file; no global packages were installed. The requirements file remains the reproducible container install source. |
| 2026-08-14 | **One corpus video uses `duration_seconds: 0` as an unknown-metadata sentinel.** Treating every non-positive duration as corrupt prevented the full 298-video corpus from loading. | Normalize zero to unknown while still rejecting negative/non-finite durations. The live test refuses unknown-duration citations, so acceptance is not weakened. |

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

### 2026-08-14 — Phase-1 build attempt #1 (Codex): blocked, no code
- Codex background job `task-msshsw3n-1nabi2` completed in 21s with zero output:
  launched from the main checkout, the spike worktree was outside its writable
  sandbox and its workflow renderer halted immediately (see Problems Faced).
- Independent verification of the worktree confirmed no `spike/professor/api/`
  files, clean working tree, no new commits — so no partial/untested state to
  clean up. All 4 acceptance criteria remain unmet; Phase 1 build not started.

### 2026-08-14 — Phase-1 implementation
- Built an isolated Flask shell plus Flask-free corpus, retrieval, composition,
  and orchestration modules. The Myron manifest loads as 298 unique videos.
- Partial embedding coverage is measured over all corpus segments on every ask;
  retrieval searches only embedded, in-corpus segments and applies a configurable
  cosine relevance floor before recency reranking.
- SurrealDB bind data travels in the JSON-RPC request body. Putting the
  768-dimensional vector, 298 IDs, or full audit record into HTTP headers/URLs is
  size-fragile and inconsistent with the RPC query contract.
- Model output is an untrusted boundary: JSON shape, non-empty tier content,
  retrieved citation numbers, corpus membership, and finite timestamp bounds are
  checked before returning an answer. Transcript text is explicitly marked as
  untrusted evidence in the prompt.
- Logging is required behavior: valid, failed, and validation-rejected
  orchestration attempts write `professor_log`; a successful answer is not returned
  when its log write fails. Rewrite failures fall back to the original question and
  are retained in the audit record.
- Offline verification reached 39 passing pytest tests with network sockets blocked.
  The credentialed three-question live run and database record inspection remain for
  the supervisor container, as planned in the brief.
