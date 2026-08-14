# MISTAKES.md — Claude-caused errors, tracked so they stop repeating

**What belongs here:** any mistake, misstatement, or error that Claude caused — wrong claims,
defective code it wrote, docs that said something untrue, work reported done that wasn't.
**What does not:** service bugs not caused by Claude (→ `BUGS.md`), work that's incomplete
by plan (→ `GAPS.md`).

**How to use it productively:**
- **Write the entry the moment the mistake is identified** — not at session end.
- Every entry needs a **root cause** and a **prevention rule** — an entry without "how to
  avoid it next time" is a confession, not a lesson.
- **Before starting similar work, scan the Prevention column.** That's the payoff step.
- If the same mistake appears 3×, the prevention rule has failed — escalate it to a hook,
  a rule file, or a process change, and note that here.

| # | Date | What happened | Root cause | Prevention rule | Status |
|---|---|---|---|---|---|
| 1 | 2026-07-16→08-05 | Indexer reported 1,086 videos "successfully indexed" while the database discarded every write — 2-week silent outage, health checks said healthy the whole time | Code reported success without checking any write result; health check verified the process was alive, not that the data existed | Success claims must verify the outcome, not the attempt: after a write, read it back; a health check must probe the actual dependency and data, not just respond 200 | Fixed 2026-08-07 (status endpoint now has a claimed-vs-actual consistency check) |
| 2 | 2026-07-29 | Consumer guide v1.0.0 documented a tag graph and data model that never existed — tagging was never implemented, no tag data was ever written | Documented the design intention as if it were shipped reality; never probed the endpoints before publishing | Never document a capability without calling it live first; aspirations are labeled as roadmap, never as current behavior | Fixed in guide 2.0.0 (tags removed, endpoints return 501) |
| 3 | 2026-08-13 | Guide's `updated:`/`verified:` dates were one day in the future (2026-08-14 on 2026-08-13) | Used UTC timestamp for a human-facing date field; host/user operate in EST | Human-facing dates use local time; when a generated date is "today," sanity-check it against the wall clock | Fixed in guide 2.1.1 |
| 4 | 2026-08-13 | Guide contradicted itself: "51 channels" in three places vs "58 channels" in another; "203k segments" vs "310,860" | Hardcoded exact live counts into a static document; they drifted apart as the corpus grew and edits touched only some spots | Never print exact live-system numbers in docs — use scope language ("50+", "hundreds of thousands") and point readers at the live status endpoint for current counts | Fixed in guide 2.1.1; Matt made this a standing directive 2026-08-13 |
