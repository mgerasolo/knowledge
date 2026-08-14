# GAPS.md — "We thought this was done, but it isn't" register

**What belongs here:** work believed or reported complete that turned out partial, stubbed,
or drifted from the plan — things we need to go back and refine, change, or enhance.
**What does not:** Claude-caused errors (→ `MISTAKES.md`), ordinary service bugs (→ `BUGS.md`),
brand-new feature ideas (→ GitHub issues).

**How to use it:**
- **Add an entry the moment a "wait, that's not actually done" is discovered** — the
  discovery is the valuable event; unrecorded, it gets re-discovered from scratch later.
- Each entry names **what was believed**, **what's actually true**, and **what closing it
  takes** — so any future session can pick it up without re-investigating.
- Review this file when planning any sprint or picking next work; close entries only when
  the gap is verifiably closed (state the check), never because time passed.

| # | Found | Believed / planned | Actually true | What closing it takes | Status |
|---|---|---|---|---|---|
<<<<<<< HEAD
| 1 | 2026-08-13 | Semantic (meaning-based) search was built — an embedding service exists with a search endpoint | The endpoint is an empty stub returning "not implemented"; embeddings were never generated for the corpus; consumers get literal keyword matching only | Pick vector store (decision open with Matt: SurrealDB vs Qdrant) → backfill embeddings for ~300k segments → build consumer search endpoint → auto-embed new ingests → guide bump | CLOSED 2026-08-14 — Matt picked SurrealDB + OpenAI embeddings (after a measured local-vs-cloud head-to-head on real corpus content); `GET /videos/api/semantic-search` shipped with tests for the 400/503/empty failure paths; ingest embeds by default with failures counted; full-corpus backfill run same day. Verification: live public-URL query returned correctly-ranked timestamped segments; coverage check = zero non-empty segments left unembedded (see conv f8229/4e5f logs + guide 2.4.0) |
| 2 | 2026-07-29 | Entity/topic tagging was part of the shipped platform (per early guide + landing copy) | Never implemented; no tag data has ever existed; `/tags/*` returns 501 | Decide whether tagging is still wanted at all; if yes, it's a full feature build; if no, remove from roadmap and landing copy | OPEN — not scheduled |
| 3 | 2026-08-13 | Tech stack plan (CLAUDE.md) says Qdrant is the vector DB | No Qdrant is deployed anywhere; the embedding code targets SurrealDB | Resolve via gap #1's decision, then correct CLAUDE.md's tech-stack table to match reality | CLOSED 2026-08-14 — Matt locked SurrealDB (HNSW index in the same store); CLAUDE.md tech table now names SurrealDB vector search + the OpenAI embedding model and notes Qdrant was never deployed |
=======
| 1 | 2026-08-13 | Semantic (meaning-based) search was built — an embedding service exists with a search endpoint | The endpoint is an empty stub returning "not implemented"; embeddings were never generated for the corpus; consumers get literal keyword matching only | Pick vector store (decision open with Matt: SurrealDB vs Qdrant) → backfill embeddings for ~300k segments → build consumer search endpoint → auto-embed new ingests → guide bump | OPEN — decision pending |
| 2 | 2026-07-29 | Entity/topic tagging was part of the shipped platform (per early guide + landing copy) | Never implemented; no tag data has ever existed; `/tags/*` returns 501 | Decide whether tagging is still wanted at all; if yes, it's a full feature build; if no, remove from roadmap and landing copy | OPEN — not scheduled |
| 3 | 2026-08-13 | Tech stack plan (CLAUDE.md) says Qdrant is the vector DB | No Qdrant is deployed anywhere; the embedding code targets SurrealDB | Resolve via gap #1's decision, then correct CLAUDE.md's tech-stack table to match reality | OPEN — tied to #1 |
>>>>>>> origin/main
| 4 | 2026-08-13 | Publishing the consumer guide made the capability discoverable by other projects | Worse than believed: a 1.0.0 submission had sat in the central inbox REJECTED (6 validation errors) since 2026-07-29 with nobody notified — the failure report sat next to the file unnoticed for two weeks | Fixed the two remaining blockers (audience vocabulary, health-check heading), resubmitted as 2.3.1 | CLOSED 2026-08-14 — validator 0 errors; accepted, merged (nlf-infrastructure #1151), published; verified present in this host's bundle manifest at version 2.3.1 |
| 5 | 2026-08-13 | Breaking-change policy exists implicitly via the guide | No consumer-facing versioning contract exists; the API's `/v1` prefix is aspirational | Formalize before (or with) the first real consumer integration | OPEN |
| 6 | 2026-08-07 | Deployment fully migrated to this repo's docker-compose | A stale March-2026 copy of the project sits at an orphaned directory on the dev host, previously building two services | Confirm nothing references it, then remove (deletion protocol applies) | OPEN |
| 7 | 2026-08-13 | Every ingested video record carries complete metadata (`segment_count`, `has_timestamps`, `duration_seconds`) | The newer ingest path writes records with these left `null`/`0` — found live during guide verification; consumers checking `has_timestamps === false` mis-handle these records | Backfill the null fields on existing records; fix the ingest path to compute them at write time; then tighten the guide's Data model wording | OPEN |
