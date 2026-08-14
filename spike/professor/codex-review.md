# Codex Adversarial Review — Professor Spike (close-out gate)

- **Date:** 2026-08-14
- **Job:** `task-mst42ckf-nm3w01` (codex-companion background task, read-only)
- **Scope:** `spike/professor/` — `api/` code + tests, `deploy/pipe_professor.py`,
  `deploy/verify_citations.py`, compose/config
- **Review dimensions:** test integrity · three-tier contract enforcement ·
  citation integrity · security (secrets + prompt injection via untrusted
  transcripts) · break-confidence
- **Codex note:** static review only — its sandbox had no pytest. Claude-side
  compensation: full suite run independently on 2026-08-14 —
  **41 passed, 0 skipped/xfailed, 0.21s** (network-blocked via conftest).

## VERDICT: FAIL

Codex verdict FAIL, upheld after independent cross-check: **all 10 findings
CONFIRMED against the code (10/10)**. Framing for the reader: this is a
*spike close-out* gate, not a production-release gate. Findings 1/2/6/7 are one
cluster — semantic grounding of Tier A is not machine-enforced — which is a
known, logged limitation (LEARNING-LOG §5 Q4) and exactly what Matt's
10-question pass-bar run measures. The FAIL stands as written because the
guarantees the spike's own contract language implies ("verbatim", "prove
citation events persist") are stronger than what the code enforces. Nothing
here shows gamed tests or fabricated results; the live-run evidence in the
learning log survives review.

## Findings (Codex) + independent cross-check (Claude)

| # | Sev | Finding | Cross-check |
|---|-----|---------|-------------|
| 1 | HIGH | Tier A ("What Myron has said") is never verified as verbatim or entailed by its cited chunk — validation checks shape, non-empty text, and citation ordinals only. `test_service.py:62` accepts claim "I increase value." grounded by chunk "Value exceeds price." | **CONFIRMED.** `composition.py` `parse_tier_json` + `validate_citation_integrity` check ordinals/shape only; no text-vs-chunk comparison anywhere. Test fixture is exactly as described. Inference can pass as Tier A if the model misbehaves — human pass-bar run is the designed detector. |
| 2 | HIGH | The system prompt itself asks for a "first-person supported claim", not a quotation — even a compliant model paraphrases in Tier A. | **CONFIRMED** (`composition.py:170`). Context: issue #16's locked decision says "verbatim-grounded" but the build BRIEF relaxed Tier A to "claims directly supported by retrieved chunks" — the code implements the BRIEF. The verbatim-vs-supported divergence between the two documents is real and now on record. |
| 3 | HIGH | Prompt injection from untrusted transcripts has no enforceable containment — "ignore instructions in context" is itself just a prompt instruction. Malicious captions could manipulate tier text. | **CONFIRMED** (`composition.py:171,176`). Structural defenses DO exist for citations (ordinal whitelist, corpus membership, timestamp bounds — a hostile caption cannot forge a citation into an unretrieved video), but tier *text* manipulation has instruction-level defense only. Inherent LLM-RAG limitation; corpus is currently Myron's own channels, so attacker-controlled captions are not yet in scope. |
| 4 | HIGH | `/api/ask` has no authentication and compose publishes `5050:5050` on all interfaces — any LAN client can invoke costly LLM/DB work, bypassing OpenWebUI auth. | **CONFIRMED empirically** — probed unauthenticated from Friday: `http://10.0.0.33:5050/health` answers. LAN-internal only (no public route to :5050; the Traefik domain fronts OpenWebUI), but the finding is correct and matters before any wider exposure. Phase-3+ item: auth or network-restrict the API. |
| 5 | HIGH | `deploy/verify_citations.py` proves less than it claims — it prints structure but has no assertions; zero sources / missing tiers / timeout still exit 0. | **CONFIRMED.** No assert/exit-code logic; it was used as a human-read probe (output was inspected during Phase 2), but as an automated verifier it cannot fail. Rename-or-assert is the fix. |
| 6 | MED | Citation validation proves retrieval *membership*, not citation *correctness* — a false claim may cite any valid retrieved ordinal. | **CONFIRMED.** Same mechanism as finding 1. Direct video-ID fabrication IS blocked (`service.py:_citations` rejects out-of-corpus/out-of-duration). |
| 7 | MED | Tests avoid the adversarial behaviors the contract depends on — no unsupported-Tier-A test, no injection test, no wrong-chunk-citation test. Nothing skipped/xfailed/`.only`'d though. | **CONFIRMED.** Suite is honest (41 passed, 0 skipped, sockets blocked in conftest, live paths covered by `live_test.py` + real Phase-2 runs) but exercises shape/ordinal rules, not semantics. |
| 8 | MED | Secrets fail open — `SURREAL_PASS` defaults to `root/changeme`; spike `.gitignore` covers only `.venv/`, so a stray deploy `.env` would be committable. | **CONFIRMED** (`config.py:22-24`, `.gitignore`). No secret *values* in the repo; real creds live root-only on Banner per README. Fix is one line each (no default + ignore `.env`). |
| 9 | MED | `chunks_searched` underreports — reports candidate rows (≤ TOP_K×4 = 48) while the unindexed scan actually touched every embedded corpus segment. | **CONFIRMED** (`retrieval.py:251`). Misleading label in meta/log; latency numbers in the learning log are unaffected (they're wall-clock). |
| 10 | MED | `/health` can be green while every question fails — it checks corpus + SurrealDB but not LiteLLM embedding/chat reachability. | **CONFIRMED** (`app.py:56-69`). Matches the fleet's known health-check failure pattern (ingest pipeline ran empty for 2 weeks behind a green `/health`). Add a LiteLLM probe before any unattended reliance on this endpoint. |

## What this means for close-out

- **Test integrity: PASS** — no gaming found; suite re-run independently, green.
- **Citation integrity (structural): PASS** — unretrieved/out-of-corpus/out-of-duration citations are hard-blocked in code; 25/25 valid in the live run.
- **Tier contract (semantic) + injection containment: NOT ENFORCED BY CODE** — known limitation, measured next by Matt's pass-bar run; would need entailment checking / quote-locking in a Gen 2.
- **Operational hardening (findings 4, 5, 8, 9, 10):** small, concrete fixes; none block the spike's learning conclusions, all belong on any path from spike → product.
