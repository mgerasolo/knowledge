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
| 2026-08-14 | **Live test blocked by credential scope: the embedding container's LiteLLM key is embeddings-only** (`embeddings`, `jarvis-embed`) — every chat call for answer composition returned 403. The brief's assumption "creds are already in its env" held for SurrealDB + embeddings but not chat. | Supervisor minted a scoped 7-day virtual key on the gateway (chat + embedding models only, aliased to the spike) and injected it into the container for the run. Phase 2 needs a proper per-service chat-capable key provisioned for the Professor API. |
| 2026-08-14 | **First live run failed citation validation: cited video `UzsiGvsFtpk` had no known duration.** 4 of 298 corpus videos (livestream VODs) were ingested with zero timing metadata — `duration_seconds: 0` in the manifest AND all segment `start_time`/`end_time` = 0.0 in SurrealDB. | Corpus durations backfilled with exact values via yt-dlp (commit `30e2e6b`). The deeper gap — segments without timestamps can never deep-link (`t=0s` always) — is a core-pipeline issue (see §3). |
| 2026-08-14 | **Phase 2: SurrealDB repeatedly OOM-killed at its ~4GB container memory limit.** dmesg shows three cgroup kills (04:37Z, 06:27Z, 06:38Z): one during concurrent professor scans, but two with NO professor traffic — the embedding backfill (+ status polling) alone runs the DB at the edge, and the unindexed 1536-dim cosine scan on top tips it over. Scan memory grows as coverage grows. | Spike-side: module-level scan lock in retrieval + gunicorn dropped to 1 worker (lock effectively global); OpenWebUI background task models disabled (below). Serialization reduces but cannot eliminate the risk — the DB memory headroom question is a core-stack issue (§3); vector index (#44) removes the scan term. |
| 2026-08-14 | **Phase 2: OpenWebUI task generation would DDoS the pipe.** With the pipe as the only model, OpenWebUI's title/tags/follow-up/autocomplete generation would each call the pipe itself — every UI chat firing extra full 50s RAG round-trips (extra LLM cost + concurrent SurrealDB scans, i.e., the OOM above). | All task generation disabled via compose env (`ENABLE_TITLE_GENERATION=false` etc.). A later generation could point tasks at a cheap non-RAG model instead. |
| 2026-08-14 | **Phase 2: every multi-turn ask crashed with HTTP 502.** `Composer.rewrite()` returned LiteLLM usage raw, and the service's `int()` conversion choked on nested `*_tokens_details` dicts. Phase 1's live tests were all single-turn, so the rewrite path had never run against real LiteLLM output. | `rewrite()` now filters usage to the three integer token keys exactly like `compose()` always did; regression test added. Lesson: every code path needs at least one live exercise — offline mocks mirrored the assumed shape, not the real one. |
| 2026-08-14 | **Phase 2: intermittent TierParseError ("Extra data").** claude-sonnet sometimes appends brace-bearing commentary after the tier JSON even with `response_format: json_object`; the parser's `rfind("}")` slice then captured both. | `_extract_json` now uses `json.JSONDecoder().raw_decode` to take the first balanced object and ignore trailing text; regression test added. |
| 2026-08-14 | **Phase 2: pipe citation events vanish on bare API calls.** `__event_emitter__` events route to the chat's socket/DB context; `/api/chat/completions` without `chat_id` has none, so citations are silently dropped (UI chats are unaffected). | Verification simulates the UI flow: create a chat, bind the completion to it (`chat_id` + message `id`), poll, then read persisted `sources` (`deploy/verify_citations.py`). Chat-bound completions also return immediately as background tasks — poll, don't block. |

## 3. Core-System Changes (lessons for the main pipeline)

Changes the spike proves we need in the core KnowledgeStack system — chunking,
indexing, schema, ingestion, metadata. These graduate into real issues against
the main pipeline.

| Date | Lesson | Suggested core change | Filed as |
|------|--------|----------------------|----------|
| 2026-08-14 | Pre-build audit: **0 of 327,402 segments have embeddings** — entire library semantically unsearchable; silent failure (embedder writes NONE and continues) | Fix embedding config, backfill (Myron channels first), add embedding-coverage metric to status API, then vector index | [#44](https://github.com/mgerasolo/knowledge/issues/44) |
| 2026-08-14 | Pre-build audit: **all 4,458 videos have empty uploader** — metadata backfill never landed | Run/repair metadata backfill; add metadata-coverage metric | [#45](https://github.com/mgerasolo/knowledge/issues/45) |
| 2026-08-14 | Personality corpus needs guest appearances, but pipeline is channel-only | Single-video enrollment endpoint + per-video personality tagging | [#46](https://github.com/mgerasolo/knowledge/issues/46) |
| 2026-08-14 | **Livestream VODs ingest with zero timing data** — segments carry `start_time`/`end_time` = 0.0, so citations into them can never deep-link into the video | Ingest should capture per-segment timestamps for /streams content (or flag timing-less videos so retrieval can rank them lower for citation purposes) | not yet filed |
| 2026-08-14 | **Corpus-scoped vector search is slow without an index**: cosine scan over the Myron corpus took ~16 s per question (SurrealDB `vector::similarity::cosine` full scan) | Vector index (HNSW/MTREE) once embedding backfill completes — already in #44's domain | [#44](https://github.com/mgerasolo/knowledge/issues/44) |
| 2026-08-14 | **SurrealDB memory headroom is insufficient for backfill + query workload** — three cgroup OOM kills in one day at ~4.1GB anon-rss, two of them with no professor traffic at all (backfill/polling alone). Every kill drops all in-flight ingest writes and queries. | Raise the SurrealDB container memory limit (or bound RocksDB memtable/cache), and add an alert on container restarts; vector index (#44) removes the biggest per-query memory spike | not yet filed |

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

### 2026-08-14 — Phase-1 live verification (supervisor, credentialed container)
- **All 3 sample questions PASS end-to-end**: three-tier answers with grounded
  citations, run inside the knowledge-embedding container on Banner. Independent
  re-validation of all 25 citations across the 3 answers: every video_id ∈ Myron
  corpus, every start_time within the video's duration; every Tier-A citation
  index resolves in the citation map. 0 invalid.
- **Coverage 25.79%** of corpus segments embedded (backfill still running) —
  answers are already well-grounded at a quarter coverage.
- **Latency ≈ 35–40 s/question**: retrieval ~16 s (unindexed cosine scan — see §3),
  composition ~16–24 s (claude-sonnet). Tier-C extension model (grok-4) verified
  available on the gateway.
- **Cost estimate reads $0.00** because `INPUT/OUTPUT_COST_PER_MILLION` config
  knobs default to 0 — real per-question cost not yet measured; wire actual rates
  in Phase 2 if cost tracking matters.
- **professor_log: 6 records visible in SurrealDB** after the runs (3 from the
  first partial run, 3 from the passing run); log write is confirmed per-request
  before an answer is returned.

### 2026-08-14 — Phase-2 deployment (Banner: containerized API + OpenWebUI)
- **Live**: professor-api on Banner :5050 (container healthy, /health 200 from
  Friday), OpenWebUI on :5060 with the pipe registered as model
  `professor_myron` → "Professor: Myron Golden". Stack at
  `/opt/stacks/professor`, ports picked from the free 5000-5099 slots.
- **Embedding-model stale-doc fix confirmed in prod**: query embedding uses
  alias `embeddings` (1536-dim, no prefix) matching the live index; the
  BRIEF's nomic/768 line was corrected and config defaults now match reality.
- **End-to-end through OpenWebUI verified**: chat-bound completion returns all
  three tier sections + disclaimer + HTML artifact (YouTube embed of the first
  citation + timestamped link list), with **8 citation sources persisted** on
  the message (string-only metadata) and status events carrying latency +
  coverage. Multi-turn history passthrough works (rewrite path live-exercised
  for the first time — and immediately surfaced a latent crash, see §2).
- **Latency ≈ 42-55 s/question** at 36.79% coverage (was ~35-40s at 25.79%):
  retrieval's unindexed scan is the growing term (~30s and climbing with
  backfill), composition ~17s. The scan will get worse until #44's vector
  index lands — Phase 3 should treat that index as a prerequisite for demo-able
  latency.
- **Coverage 36.79%** of corpus segments embedded at verification time
  (25.79% → 35.17% → 36.79% across the day; backfill actively running).
- **SurrealDB stability is the biggest operational risk** (see §2/§3): three
  OOM kills today, two without any professor traffic. Professor-side
  concurrency is now serialized, but the DB runs at its memory limit under
  backfill alone — the container limit and #44's index both need attention
  before any multi-user exposure.
- **Phase 3 needs**: domain + TLS via Traefik (professor.* route), Authentik in
  front of OpenWebUI (replacing the local-auth spike setup), vector index
  (#44) for latency, and a decision on task-model wiring (cheap non-RAG model
  for titles/tags instead of disabling).

### 2026-08-14 — Durkin personality added (multi-professor manifold) + API auth
- **Second professor live**: `personalities/chris-durkin.json` (344 videos, all
  from the `pastorchrisdurkin` channel — the CNCC Sunday-service livestreams
  live INSIDE that channel, no separate slug; `crosspointcity` is a different
  church in Georgia and was excluded). `speaker_purity: mixed` — services
  include worship/announcements by other speakers.
- **Multi-personality is now structural**: the API loads every
  `personalities/*.json` at startup and routes `personality_id` per request;
  composition prompts derive the persona name from the corpus (no hardcoded
  Myron). The OpenWebUI pipe is a **manifold** (`pipes()` → one model per
  personality: `professor_myron.myron-golden`, `professor_myron.chris-durkin`);
  adding professor #3 = drop a JSON file + add one registry line in the pipe.
- **Coverage 100%** for BOTH corpora at verification (the CNCC-priority
  backfill finished; Myron was 36.79% at 06:44Z and 100% by 16:25Z).
- **Timestamps are REAL for the Durkin corpus**: sampled the 12 longest
  (livestream-length) videos — 1618/1619 segments have `start_time > 0`, so
  citations deep-link properly (the #72 all-zero-timestamp defect did not hit
  this corpus). Demo question ("most recent baptisms during the church
  service?") cited his 2025-09-01 service at 23:20 with a working embed.
- **/api/ask now requires a bearer key** (`PROFESSOR_API_KEY`, generated
  value-safely into the root-only deploy/.env; unauthenticated → 401), and
  config **fails closed**: missing SURREAL_PASS / LITELLM_API_KEY /
  PROFESSOR_API_KEY aborts container startup instead of running on defaults.
  The pipe reads the key from the OpenWebUI container env via a valve default.
- **Operational learnings**: (1) Matt changing the OpenWebUI admin password
  broke automation mid-day — a dedicated service-admin account
  (`/root/professor-openwebui-service.env`, created via in-container
  open_webui model calls, no restart) now decouples automation from his
  account. (2) SurrealDB remains the demo risk: two more memcg OOM kills
  today, and cold-cache scans after a restart exceeded the 60s DB timeout →
  502s; `PROFESSOR_REQUEST_TIMEOUT=240` now waits instead of failing, but the
  #44 vector index and #73 memory headroom are still the real fixes. Direct
  corpus-wide probe queries from outside the API's scan lock are what tipped
  the DB over — probe through the API's audit log (`professor_log`) instead.

## 5. Spike Learning Report (2026-08-14)

Close-out answers to the nine learning-agenda questions in issue #16, from the
evidence in this log. Where the spike has not yet produced evidence, that is
said plainly rather than guessed. The pass bar — Matt's ~10 real questions,
7+ rated "sounds like him, correct citation, clip opens at the right moment" —
**has not yet been run**; it is the single measurement most of the open
questions are gated on.

Live state at close-out (re-probed 2026-08-14): professor-api healthy on
Banner :5050 (298 corpus videos, SurrealDB reachable), OpenWebUI serving on
:5060, and https://professor.nextlevelguild.com routing through Traefik
(public DNS record still pending — nlf-infrastructure#1169).

**1. Retrieval quality — partially answered.** Three sample questions at
25.79–36.79% embedding coverage produced well-grounded three-tier answers
(8 persisted citation sources on the Phase-2 UI answer). Whether chunks land
on the *right moments* for real questions — the re-chunking driver — is not
yet measured; needs Matt's 10-question pass-bar run.

**2. Search speed — answered: NO, not fast enough without a vector index.**
Unindexed cosine scan: ~16 s/question at 25.79% coverage, ~30 s and climbing
at 36.79% — the scan term grows with backfill. Total 35–55 s/question. The
vector index (#44) is a prerequisite for demo-able latency. Bonus finding:
concurrent scans OOM-kill SurrealDB (#73); professor-side scans are now
serialized as a stopgap.

**3. Voice quality — not yet measured.** claude-sonnet composes Tiers A/B
first-person; grok-4 verified available for the Tier-C escalation. No model
bake-off was run and no human has rated "sounds like him" — needs Matt's
pass-bar run.

**4. Tier discipline — answered: structurally YES, with a caveat.** The tier
contract is enforced in code, not just requested in the prompt: strict
tier-JSON parsing, every Tier-A claim must carry ≥1 citation from the
retrieved set, and post-checks force inference/extension labeling. Two real
model misbehaviors were caught live and fixed (trailing commentary after the
JSON; raw nested usage dicts). Caveat: enforcement is citation-shaped, not
semantic — nothing verifies a Tier-A claim's *text* is actually entailed by
its cited chunk, so semantic leakage into "What Myron has said" remains
possible; that is exactly what the human pass-bar run measures.

**5. Citation accuracy — structurally answered: 25/25 valid, 0 invalid**
(Phase-1 live run: every video_id ∈ corpus, every start_time inside the
video's duration, every citation index resolves). Whether the clip *content*
matches the claim — semantic accuracy and the error rate the agenda asks
for — is not yet human-verified; pass-bar run. Known defect class: 4
livestream VODs carry all-zero segment timestamps, so citations into them can
never deep-link (#72).

**6. Guest contamination — not yet measured.** The corpus is 298 videos from
Myron's own two channels (channel-only). Single-video enrollment for guest
appearances landed (#46, closed) but guest sources are not yet enrolled, and
there is no diarization. The contamination rate should be counted during the
pass-bar review.

**7. OpenWebUI fit — answered: YES for Gen 1, with sharp edges.** Pipe +
citation source events + Artifacts (embedded player + timestamped link list)
verified end-to-end through the real UI, multi-turn included. Every sharp
edge had a workaround: task generation would have DDoS'd the pipe (disabled),
citation events silently drop on chat-less API calls, citation metadata must
be string-only, chat-bound completions run as background tasks. The custom
two-panel UI fallback is not needed for Gen 1.

**8. Cost per conversation — not yet measured.** The cost knobs
(`INPUT/OUTPUT_COST_PER_MILLION`) default to 0, so every answer reports
$0.00. Token usage *is* logged per request in `professor_log`, so wiring real
per-model rates makes cost computable — including retroactively over the
logged runs.

**9. Recency weighting — not yet measured (ON never compared to OFF).**
Weighting ran ON throughout (REC_BOOST 0.15, 730-day horizon) and the math is
unit-tested, but there was no A/B against unweighted retrieval, so whether it
improves or distorts answers is unknown. It is a config knob — cheap to A/B
during the pass-bar run.

**Beyond the agenda** (all registered): embedding coverage was 0% at spike
start (#44), video metadata empty (#45), single-video enrollment built (#46),
timestamp-less livestream ingest (#72), SurrealDB memory headroom (#73), and
the LiteLLM key-rotation follow-ups (nlf-infrastructure#1165) plus the public
DNS record for professor.nextlevelguild.com (nlf-infrastructure#1169).

**Bottom line:** the spike proved the architecture — three enforced tiers,
validated citations, OpenWebUI pipe + artifacts — live on Banner behind a
Traefik route. The remaining unknowns are human-judgment measurements gated
on Matt's 10-question run, plus the #44 vector index for latency.
