---
title: 'Professor Spike Phase 1 Retrieval and Answer API'
type: 'feature'
created: '2026-08-14'
status: 'done'
review_loop_iteration: 0
baseline_commit: '618fb245f299763aab862bbb6841b91135a44727'
context:
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Professor spike needs a runnable backend that answers questions from Myron Golden's video corpus while making direct evidence, persona-grounded inference, and general AI extension unmistakably separate.

**Approach:** Build an isolated Flask API under `spike/professor/api/` with Flask-free retrieval and composition modules, environment-configured SurrealDB and LiteLLM clients, strict citation validation, request logging, offline unit tests, and a credentialed live-test script.

## Boundaries & Constraints

**Always:** Preserve the exact `POST /api/ask` response contract and three-tier semantics in `spike/professor/BRIEF.md`; load the 298-video corpus at startup; restrict retrieval to corpus video IDs with non-NONE embeddings; apply configurable linear recency weighting; rewrite history-aware questions; report per-request embedding coverage; log every request including failures where feasible; include the standing disclaimer; validate all model citations against retrieved chunks; use environment variables without printing secret values; copy/adapt the embedding config and Surreal client conventions instead of importing across trees; commit logical increments with conventional commits on `feat/professor-spike`.

**Ask First:** Any contract change, dependency on `src/`, write outside the authorized spike/log paths, destructive database operation, or need to expose/configure credentials beyond existing environment variables.

**Never:** Modify `src/`; hardcode or print secrets; fabricate citations; cite an unretrieved chunk; require Flask for `retrieval.py`, `composition.py`, or `live_test.py`; make unit tests access the network; treat missing embeddings as fatal when partial retrieval remains possible.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|---------------|---------------------------|----------------|
| Grounded ask | Valid personality/question and retrievable embedded chunks | Tier A claims cite numbered retrieved chunks; B and C are labeled; citation metadata includes valid timestamped YouTube URLs | Reject malformed model JSON or invalid citations safely; never fabricate evidence |
| Corpus silence | No relevant/embedded chunks | State corpus silence, provide Tier C, and include nearest related Tier A only if actually retrieved | Return a valid contract with coverage and diagnostic metadata |
| Multi-turn | Non-empty valid history | Rewrite to a standalone retrieval query before embedding | If rewrite fails, fall back to the original question and record the failure |
| Partial backfill | Some corpus segments have `embedding = NONE` | Search embedded rows only and report coverage percentage | Zero coverage degrades honestly without crashing |
| Invalid request/personality | Missing question, malformed history, or unknown personality | JSON client error | HTTP 400 without model/database work where possible |
| Health | Corpus loaded and SurrealDB reachable/unreachable | HTTP 200 with healthy state / HTTP 503 with degraded state | No credentials or raw secret-bearing errors in response |

</frozen-after-approval>

## Code Map

- `spike/professor/BRIEF.md` -- authoritative endpoint, retrieval, logging, testing, and acceptance contract; read-only.
- `src/embedding/config.py` -- source conventions and environment names/defaults to copy/adapt; read-only, with brief-specific 768-dimensional Nomic settings taking precedence where the current core defaults differ.
- `src/embedding/surreal_client.py` -- source HTTP SQL client, statement-error detection, UTF-8, and reachability conventions to copy/adapt; read-only.
- `spike/professor/personalities/myron-golden.json` -- nested personality manifest whose `sources[*].videos` and `guest_appearances` must flatten to 298 unique video records including title/duration metadata; read-only.
- `spike/professor/api/config.py` and `surreal_client.py` -- isolated environment configuration and parameterized Surreal HTTP access.
- `spike/professor/api/corpus.py`, `retrieval.py`, `composition.py`, `service.py` -- manifest loading, scoring/search/coverage, model calls/parsing/integrity, and Flask-free orchestration.
- `spike/professor/api/app.py` -- thin request validation and Flask response/status shell.
- `spike/professor/api/tests/` -- offline pytest coverage using fakes/fixtures.
- `spike/professor/api/live_test.py` -- direct module-based three-question credentialed integration runner.
- `spike/professor/LEARNING-LOG.md` -- append-only Phase 1 problems and chronological findings.

## Tasks & Acceptance

**Execution:**
- [x] `spike/professor/api/config.py`, `surreal_client.py`, `corpus.py` -- establish isolated config/data foundations and safe database query/write behavior.
- [x] `spike/professor/api/retrieval.py` -- embed, calculate coverage, retrieve top candidates, and rerank by cosine plus recency.
- [x] `spike/professor/api/composition.py`, `service.py` -- rewrite multi-turn queries, enforce/parse three-tier JSON, validate citations, estimate usage/cost, optionally extend with `EXTENSION_MODEL` and fall back, and persist complete request logs.
- [x] `spike/professor/api/app.py`, dependency/readme artifacts as needed -- expose thin `POST /api/ask` and `GET /health` interfaces.
- [x] `spike/professor/api/tests/` -- test recency boundaries, manifest flattening/validation, fenced or plain tier JSON parsing, and rejection/removal of citations outside retrieved context with no network.
- [x] `spike/professor/api/live_test.py` -- run the three specified prompts directly through the Flask-free service and print tiers, citations, latency, and coverage while asserting corpus membership and timestamp bounds.
- [x] `spike/professor/LEARNING-LOG.md` -- append implementation problems and findings in sections 2 and 4.

**Acceptance Criteria:**
- Given the offline test environment, when pytest runs, then all required unit tests pass without network access.
- Given valid credentials and partial embedding coverage, when the live script runs its three questions, then each answer preserves the three-tier contract and at least one returned citation belongs to the Myron corpus with a timestamp within the video's duration.
- Given any ask attempt reaching orchestration, when it completes or fails, then a `professor_log` write records the required request, retrieval, answer/error, model, usage/cost, coverage, and latency fields without exposing secrets.
- Given the live run completes, when SurrealDB is queried for `professor_log`, then corresponding records are visible.

## Spec Change Log

## Design Notes

Keep external I/O behind injectable functions/clients so offline tests exercise deterministic logic. Use bind parameters for dynamic values rather than interpolating questions, answers, or vectors into SQL. Treat model output as untrusted: extract JSON, normalize the exact contract, and filter or fail invalid Tier-A citation references before responding. Coverage is the ratio of corpus segments with embeddings to total corpus segments, not merely the fraction of returned results.

## Verification

**Commands:**
- `python3 -m pytest spike/professor/api/tests -q` -- expected: required offline tests all pass.
- `python3 -m compileall -q spike/professor/api` -- expected: all modules compile.
- `python3 spike/professor/api/live_test.py` inside the credentialed knowledge-embedding container -- expected: three valid tiered answers, valid in-corpus timestamps, coverage/latency output, and successful log verification.
- `git status --short && git log --oneline --decorate -8` -- expected: only authorized files changed and logical conventional commits present on `feat/professor-spike`.

## Suggested Review Order

**Request orchestration**

- One Flask-free transaction coordinates rewrite, retrieval, answer, citations, and mandatory logging.
  [`service.py:118`](../../spike/professor/api/service.py#L118)

- The thin HTTP shell limits itself to transport validation and status mapping.
  [`app.py:36`](../../spike/professor/api/app.py#L36)

**Evidence boundaries**

- Corpus-scoped vector search reports coverage, filters relevance, and applies recency reranking.
  [`retrieval.py:169`](../../spike/professor/api/retrieval.py#L169)

- Untrusted model JSON is normalized into strictly separated, citation-checked tiers.
  [`composition.py:121`](../../spike/professor/api/composition.py#L121)

- JSON-RPC carries large bound vectors and audit records safely in request bodies.
  [`surreal_client.py:28`](../../spike/professor/api/surreal_client.py#L28)

**Integration and proof**

- Credentialed direct-module testing validates answers, timestamps, coverage, latency, and persisted logs.
  [`live_test.py:48`](../../spike/professor/api/live_test.py#L48)

- Offline service tests pin citation integrity, logging contents, fallback, and failure behavior.
  [`test_service.py:62`](../../spike/professor/api/tests/test_service.py#L62)

- Retrieval tests pin corpus predicates, coverage arithmetic, relevance, and recency ordering.
  [`test_retrieval.py:33`](../../spike/professor/api/tests/test_retrieval.py#L33)

**Configuration and learning**

- Environment-only settings preserve the core names while exposing spike learning knobs.
  [`config.py:19`](../../spike/professor/api/config.py#L19)

- Implementation constraints and reusable findings remain in the spike's durable deliverable.
  [`LEARNING-LOG.md:77`](../../spike/professor/LEARNING-LOG.md#L77)
