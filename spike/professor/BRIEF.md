# Professor Spike — Build Brief (Phase 1: Retrieval + Answer API)

Tracking: issue #16 · Learning log: `LEARNING-LOG.md` (append findings as you go)
Status quo: spike code is throwaway-quality but MUST run. Do NOT touch `src/` (core system).

## What this is
A personality-grounded RAG service. Phase 1 is the backend only: question in →
three-tier answer + citations out. Frontend (OpenWebUI pipe + video panel) is Phase 2.

## The three-tier answer contract (core product decision — non-negotiable)
Every answer separates:
- **Tier A — "What Myron has said"**: claims directly supported by retrieved chunks,
  each with citation `[n]` → (video_id, start_time). NEVER cite a chunk that wasn't retrieved.
- **Tier B — "What Myron might say"**: inference in his style from adjacent retrieved
  teachings, labeled as inference.
- **Tier C — "AI extension"**: general-AI expansion informed by his teachings, explicitly
  labeled ("he hasn't directly addressed this"). If corpus is silent on the topic, say so
  plainly and provide Tier C only (plus nearest related Tier A material).

## Architecture (match repo conventions — see src/embedding/ and src/admin/)
- Python 3.11 / Flask, config via env vars with the SAME names/defaults as
  `src/embedding/config.py` (SURREAL_URL/USER/PASS/NS/DB, LiteLLM settings).
  NEVER print secret values.
- Location: `spike/professor/api/`
- Endpoint: `POST /api/ask` `{personality_id, question, history?: [{role, content}]}` →
  ```json
  {"tiers": {"said": [{"text": "...", "citations": [1,2]}],
              "might_say": "...", "extension": "..."},
   "citations": {"1": {"video_id": "...", "start_time": 123.4, "end_time": 150.0,
                        "title": "...", "url": "https://youtube.com/watch?v=ID&t=123s",
                        "quote": "..."}},
   "meta": {"model": "...", "chunks_searched": 0, "retrieval_ms": 0, "cost_estimate_usd": 0}}
  ```
- Plus `GET /health` (checks SurrealDB reachable + corpus loaded; 200/503).

## Retrieval
- Personality corpus: `spike/professor/personalities/myron-golden.json` → flat list of
  video_ids. Load at startup.
- Embed the question via LiteLLM using the SAME embedding model as the ingest pipeline
  (see `src/embedding/config.py` EMBEDDING_MODEL — nomic-embed-text-v1.5, 768-dim).
- SurrealDB query: `vector::similarity::cosine(embedding, $qvec)` over segments WHERE
  `video_youtube_id IN $corpus AND embedding IS NOT NONE`, top-k ≈ 12.
  NOTE: backfill is in progress — coverage grows daily; log coverage % per request.
- **Recency weighting ON**: final_score = cosine × (1 + REC_BOOST × freshness), freshness
  linear-decays from 1 (published today) to 0 (≥ REC_HORIZON_DAYS old, default 730).
  REC_BOOST default 0.15. Constants in config — they're a learning-agenda knob.
- Multi-turn: if history present, first rewrite the question into a standalone retrieval
  query with one cheap LLM call.

## Answer composition
- One call to a strong chat model via LiteLLM (default `claude-sonnet`; model name in
  config) with retrieved chunks as numbered context and a system prompt enforcing the
  three-tier structure + JSON output. Optional second call for Tier C to a different model
  (config `EXTENSION_MODEL`, try `grok-4` — verify availability at runtime, fall back to
  the main model).
- Persona style: instruct the model to speak in Myron's cadence for Tiers A/B (first
  person), with the standing disclaimer field `"disclaimer": "AI recreation from public videos"`.

## Logging (day one, non-optional)
- Every request writes a `professor_log` record to SurrealDB: timestamp, personality,
  question, history length, retrieved chunk ids + scores, coverage %, full answer JSON,
  model(s), token usage / cost estimate, latency breakdown.

## Testing (required before claiming done)
- Unit tests (pytest, no network): recency scorer, corpus loader, tier-JSON parser,
  citation-integrity check (every cited n exists in retrieved set).
- Live integration script `spike/professor/api/live_test.py`: runs 3 real questions
  end-to-end, prints the three tiers + citations + latency + coverage. For SurrealDB/LiteLLM
  credentials, run it INSIDE the knowledge-embedding container on Banner
  (`ssh banner "docker exec -i knowledge-embedding python - < live_test.py"`) — creds are
  already in its env; requests lib is available. Flask isn't needed for live_test: import
  the retrieval/composition modules directly (keep them Flask-free; app.py is a thin shell).
- Sample questions: "How do I handle price objections?" · "What does the Bible say about
  wealth according to Myron?" · "How do I make my offer irresistible?"

## Acceptance (Phase 1)
1. pytest green (run and show output)
2. live_test.py produces three-tier answers with ≥1 valid citation whose video_id belongs
   to the Myron corpus and whose start_time lands inside the video's duration
3. professor_log records visible in SurrealDB after the run
4. Findings + problems appended to `LEARNING-LOG.md` (sections 2 and 4)
