# Ingestion Freshness Dashboard — Design

**Date:** 2026-08-09
**Status:** Approved, ready for implementation
**Anchor:** Give Matt one page that answers "are we ingesting, how fresh is it, and how much came in each day by category."

---

## 1. Why this exists

Matt asked for a dashboard showing what was ingested and how many per day. Investigation
found the existing admin UI cannot answer that, because **it reads a bookkeeping table the
real pipeline abandoned.**

Evidence gathered 2026-08-09:

| Question | Postgres `pipeline_items` (what the UI reads) | Real library (SurrealDB + transcript files) |
|---|---|---|
| How many videos exist? | 1,150 | 3,493 |
| Anything ingested in the last 24h? | 0 | 52 |
| AI Labs channel | 28 queued, 0 indexed | 86 videos, 99 transcript files |
| Newest completion | 55 hours ago | 12 minutes ago |

The pipeline table is not wrong about *its own* job — it is a work queue for items in
flight. It is wrong as a **record of what the library holds**, which is what every page
currently uses it for. A user looking at the site concludes the system is dead while it is
running normally.

**Design consequence:** the queue and the library are two different questions and must be
read from two different places. Freshness and counts come from the library. Only genuinely
in-flight work comes from the queue.

---

## 2. What the page answers, in priority order

Matt's stated priority, verbatim: *"The total count doesn't really help because if we're
not getting fresh data, that's a problem. It's a matter of how fresh is our information?
Are we currently fresh?"*

So the page is ordered by that, not by size:

1. **Are we running right now?** — one plain-English verdict at the top.
2. **How many came in each day, by category?** — the main chart.
3. **Which categories/channels have gone quiet?** — freshness per slice.
4. **Drill-down** — category → channel → that channel's daily history.

**Explicitly out of scope:** total library size as a headline metric. Totals appear only
as context inside drill-downs, never as the answer to "are we healthy."

---

## 3. Category taxonomy

### The problem found

The two stores disagree on category vocabulary, and the corpus vocabulary is itself split:

| Store | Vocabulary |
|---|---|
| Postgres `channels.domain` | `ai-tech`, `mindset`, `political`, `business`, `general`, `health`, `faith` |
| SurrealDB `video.domain` | `political`, `mindset`, `business`, `ai`, `general`, `health`, `ai-automation`, `ai-coding`, `religion`, `faith`, `ai-tech` |

AI is split four ways (689 videos). Faith is split two ways (41 videos). A per-category
daily chart built on the raw values would be wrong.

### The canonical taxonomy

Matt's decision: **default to top-level categories, allow drill-down into the full
sub-categories.** Business and Finance are distinct — *"Finance is about investing in
money. Business is about running a business, like Alex Hormozi's."*

| Top-level | Sub-categories mapped into it | Videos today |
|---|---|---|
| **AI** | `ai`, `ai-coding`, `ai-automation`, `ai-tech` | 689 |
| **Politics** | `political` | 1,205 |
| **Mindset** | `mindset` | 705 |
| **Business** | `business` | 456 |
| **Health** | `health` | 178 |
| **Faith** | `faith`, `religion` | 41 |
| **Finance** | *(none yet — see below)* | 0 |
| **Other** | `general`, unmapped, missing | 221 |

**Finance is deliberately present and empty.** No channel or video is currently tagged
finance; the finance-adjacent channels (Valuetainment, Myron Golden) are tagged business.
The category is rendered at zero rather than hidden, because a hidden empty category is
indistinguishable from a category that stopped producing. Reclassifying channels into
Finance is separate follow-up work, not part of this build.

**Sub-category drill-down is display-only.** The chart defaults to the 7 top-level
categories + Other. Clicking a category expands it into its sub-categories for that view.
The underlying sub-category value is never rewritten in the database — normalization is a
read-time mapping, so re-tagging upstream later does not require a migration.

**Unmapped values fall to Other and are counted.** If a new sub-category appears upstream
that this map does not know, it lands in Other and is surfaced in a small "unmapped
values" note, so the taxonomy drifting is visible rather than silent.

---

## 4. Data sources and the honesty problems in each

Three sources, each with a known defect that the design must handle explicitly.

### 4a. SurrealDB `video.ingested_at` — accurate only from 2026-08-07

The corpus was rebuilt from disk on 2026-08-05, and the rebuild stamped `ingested_at =
time::now()` on every record it wrote. So:

| Day | Videos stamped |
|---|---|
| 2026-08-05 | 3,057 ← the rebuild, not a real day's ingestion |
| 2026-08-06 | 2 |
| 2026-08-07 | 148 |
| 2026-08-08 | 235 |
| 2026-08-09 | 52 |

**Handling:** 2026-08-05 is a known rebuild date. It is excluded from the daily chart's
bars and shown instead as a labelled marker line ("corpus rebuilt from disk — 3,057
records re-filed"). Rendering it as a bar would show a fake record-breaking day 60× the
real daily rate and permanently wreck the chart's Y-axis scale.

The rebuild date is a named constant, not a magic number, with the reason in a comment.

### 4b. Transcript file modification times — real history back to March

The `.md` files on the NAS were never touched by the rebuild, so their timestamps carry
genuine per-day history:

```
2026-03-01: 13     2026-04-27: 262    2026-07-16: 91     2026-08-07: 194
2026-03-22: 277    2026-04-28: 258    2026-07-17: 251    2026-08-08: 229
2026-04-22: 35     2026-04-29: 268    2026-07-18: 252    2026-08-09: 52
2026-04-23: 249    2026-04-30: 267    2026-07-19: 257
2026-04-24: 22     2026-05-01: 196    2026-07-20: 246
                                      2026-07-21: 157
```

**This is the source for history before 2026-08-07.** It only covers the file-writing
ingestion path; the n8n path writes straight to SurrealDB and leaves no file. Pre-08-07
history is therefore labelled on the chart as reconstructed-from-files, so a gap is not
mistaken for a confirmed zero.

**Ingestion is bursty, not a daily trickle.** Tall bars separated by empty days is the
honest shape of this data, not a rendering bug. The page says so in a one-line note rather
than letting an empty day read as an outage.

### 4c. Postgres `channels` — the domain authority, but incomplete

50 channel records exist; the corpus contains videos from **72 distinct channels**. 22
channels have content but no record, therefore no authoritative domain.

**Resolution order for a video's category:**
1. The channel record's `domain`, if the channel is known — the human-curated answer.
2. Otherwise the video's own `domain` field.
3. Otherwise `Other`.

The count of videos categorised by fallback is surfaced on the page, so "22 channels are
unadopted" is visible rather than quietly absorbed into Other.

---

## 5. Freshness model

Freshness is per-slice, not global. **A global "last ingest" number hides a dead
category**, which is precisely the failure this project already suffered — an outage that
every health check reported as healthy for two weeks.

For each of {overall, each top-level category, each channel}:

| State | Rule | Colour |
|---|---|---|
| Fresh | newest video within 48h | green |
| Slowing | 48h–7d | amber |
| Stalled | over 7d | red |
| Never | no videos at all | grey |

Thresholds are configuration, not literals, and default to the existing
`STALE_INGEST_HOURS` (72h) family already used by `/api/v1/status` so the page and the
alerting endpoint cannot disagree about what "stale" means.

**Per-channel freshness is judged against that channel's own rhythm where possible.** A
channel that posts monthly is not stalled at 8 days. Where a channel has enough history to
compute a median gap between videos, "stalled" means exceeding 3× its own median gap;
otherwise it falls back to the fixed thresholds above. This prevents a wall of false red
on low-frequency channels, which would train Matt to ignore the colour.

---

## 6. Architecture

```
                    ┌─────────────────────────────┐
   SurrealDB ──────▶│                             │
   (video records)  │      metrics.py             │
                    │  ┌───────────────────────┐  │
   Transcript ─────▶│  │ categories.py         │  │──▶ /api/v1/metrics/*
   files (mtimes)   │  │ (canonical taxonomy)  │  │        │
                    │  └───────────────────────┘  │        │
   Postgres ───────▶│  freshness + daily rollups  │        ▼
   (channel domains)└─────────────────────────────┘   control.html
                                                       (ECharts)
```

### Components

| Unit | One job | Depends on |
|---|---|---|
| `api/categories.py` | Map any raw domain value to (top-level, sub-category). Pure functions, no I/O. | nothing |
| `api/metrics.py` | Read the three sources, produce daily rollups and freshness verdicts. | categories, SurrealDB, Postgres, filesystem |
| `api/metrics_routes.py` | HTTP surface. Serialisation only, no logic. | metrics |
| `templates/control.html` | Render. Fetches JSON, draws ECharts, no calculation. | metrics endpoints |

`categories.py` being pure and I/O-free is deliberate — the taxonomy is the piece most
likely to change as channels get re-tagged, and it must be testable without a database.

### Endpoints

```
GET /api/v1/metrics/daily?days=90&group=category
    → { days: [{date, rebuild?: true, reconstructed?: true,
                counts: {AI: 12, Politics: 4, ...}}], ... }

GET /api/v1/metrics/daily?days=90&group=subcategory&category=AI
    → same shape, split into ai / ai-coding / ai-automation

GET /api/v1/metrics/daily?days=90&group=channel&category=AI
    → drill-down: which channels delivered, per day

GET /api/v1/metrics/freshness
    → { overall: {state, newest_at, hours_since},
        categories: [...], channels: [...],
        unadopted_channels: 22, unmapped_domains: [] }
```

### Caching

The transcript-file scan walks ~3,500 files. It is cached in-process with a short TTL
(60s) so that opening the page does not stat the whole NAS tree on every request, and so a
browser auto-refresh cannot hammer the mount. Cache is keyed by nothing and cleared by
TTL only — this is a single-tenant admin page, not a multi-user surface.

---

## 7. Repointing the existing pages

Every page that currently reports library contents from `pipeline_items` moves to the
metrics layer:

| Page | Change |
|---|---|
| Dashboard (`/`) | Library totals and 24h counts come from the real corpus. The pipeline-flow strip stays, but is relabelled as the **work queue** — which is what it honestly measures. |
| Channels list | Video counts per channel from the corpus, plus freshness colour. |
| Channel detail | "Indexed" count from the corpus (AI Labs: 86, not 0). Keeps queue counts, labelled as queue. |
| Videos list | Already reads SurrealDB. Unchanged. |
| Pipeline page | Unchanged — it is genuinely about in-flight work, which is the queue's real job. |

**The queue is not deleted or hidden.** It is relabelled so its numbers stop being read as
library totals. Mislabelling was the defect, not the table's existence.

---

## 8. Charting

**ECharts** (Matt's preference; Apache 2.0, free). Loaded as a single script tag from CDN
with a floating major version — no build step, matching how this site is already built
(Flask + Jinja + plain CSS, no bundler).

Chart spec:
- Stacked vertical bars, one bar per day, one colour per top-level category.
- Legend click isolates a category. Bar click drills into channels for that day.
- The 2026-08-05 rebuild renders as a marker line, never a bar.
- Days before 2026-08-07 are visually distinguished as reconstructed-from-files.
- Colours follow `matt-design-preferences.md`: `rgb()`/`rgba()` only, never `oklch`/`hsl`.
  Red and green are reserved for the freshness indicators (good/bad), so **category
  colours deliberately avoid red and green** to prevent "Politics is red" reading as
  "Politics is broken."

---

## 9. Testing

| Layer | Test |
|---|---|
| `categories.py` | Every known raw value maps to the right top-level. Unknown values land in Other and are reported. Finance exists and is empty. |
| Daily rollup | The rebuild date is excluded from bars. Bursty data with zero-days produces continuous date axes, not gaps. Timezone boundaries put a video on exactly one day. |
| Freshness | Each state boundary. A monthly channel at 8 days is not red. A channel with no videos reads "never", not "stalled". |
| Endpoints | Shape and status codes; degraded upstream returns partial data with a named problem, never a 500. |
| Browser | Playwright: page loads, chart renders, drill-down changes the data, freshness banner shows real text. Artifacts to `screenshots/` per `playwright-artifact-paths.md`. |

**Failure-first cases explicitly covered**, since this project's history is silent
failures that reported healthy:
- SurrealDB unreachable → page states "cannot read the library", does not render zeros.
- Transcript mount unreadable → history section says so, does not render an empty chart.
- Zero videos returned → "no data" state, distinct from "0 ingested today".

**A zero must never be indistinguishable from a failure to read.** That distinction is the
single most important behaviour on this page.

---

## 10. Out of scope

- Reclassifying channels into Finance, or adopting the 22 unadopted channels.
- Fixing the ~41 transcript files present on disk but absent from the search library
  (13 of them on AI Labs alone) — logged separately.
- Semantic search, tagging, or anything touching the `/tags/*` 501 endpoints.
- Alerting. The page is for looking at; `/api/v1/status` remains the machine-pollable
  endpoint, and this build must not diverge from its thresholds.
