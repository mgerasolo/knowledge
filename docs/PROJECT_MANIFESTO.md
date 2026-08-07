# KnowledgeStack — Project Manifesto

> **Audience:** Project Manager / Product Management Office. Non-technical. This is the "what and why" document — the plain-language north star that every technical decision is measured against.
>
> **Status:** Pre-alpha (spike validated, intelligence layer not yet activated)
> **Last updated:** 2026-07-12
> **Owner:** Matt
> **Grounded in:** `PRODUCT_VISION.md`, `product-brief-knowledge-2026-01-30.md`, and the Jan 2026 brainstorming session

---

## 1. What KnowledgeStack Is

**In one line:**
> Turn thousands of hours of expert video content into searchable wisdom, conversational AI experts, and actionable insights — a private knowledge engine that other apps and AI assistants can plug into.

**In a paragraph:**
KnowledgeStack automatically watches a curated set of YouTube channels, captures the transcripts of everything they publish, and organizes that content into a searchable, structured knowledge repository. It is **not a single app you open** — it is an **engine / backend** that turns messy long-form video into clean, queryable knowledge. Its "customers" are primarily **other software**: Matt's own applications and his Claude Code / AI coding sessions, which query it for things like "what are the current best practices for X," Bible-study notes for content creation, or expert opinions on a topic.

**The mental model — a school:** the product names follow an academic metaphor, and it's the easiest way to explain the whole system:

| Stage | What happens (plain language) |
|-------|-------------------------------|
| **Enroll** | Students (videos) get admitted — channels are monitored, new content is pulled in |
| **Lecture** | The lecture hall — you can listen to / read / search any transcript |
| **College** | Where raw material becomes *intelligence* — search by meaning, connect ideas, tag people & topics |
| **Graduate** | The best of the best — curated top quotes, highlight reels, "golden standard" answers |
| **Gateway** | The doors out — how other apps and AI tools request and receive knowledge |
| **Ops** | The administration office — monitoring, alerts, health, keeping the lights on |

---

## 2. The Problem It Solves

Experts publish **hundreds of hours of high-value content every day** across YouTube — on business, health, faith, AI, politics, and more. That knowledge is trapped in the **least accessible format possible: linear video** you have to watch start-to-finish.

- **Information overload** — 100+ hours of relevant content a day, 1–2 hours to actually consume it.
- **Redundancy blindness** — when a big topic breaks, 50–100 hours of overlapping coverage appears; you can't tell what's redundant without watching it all.
- **Buried gems** — a single timeless insight sits inside a 3-hour conversation with no way to jump to it.
- **Siloed by source** — the same expert shows up across many channels; there's no unified view of what they actually think.
- **Invisible to AI** — none of this content is in a form an AI assistant can search or reason over.

**The core insight:** every existing tool (Snipd, Fabric, Recall, generic RAG) is a *finished consumer app* solving one problem one way. KnowledgeStack is the **infrastructure layer underneath** — build it once, and unlimited downstream uses become "just a query."

---

## 3. Who It's For

**Primary purpose: a personal tool.** Built by and for Matt, using AI-assisted development. It may serve as a *spike* toward a formal product someday, but that is **not** the goal.

**The real "users" are mostly machines:**

| Consumer | How they use it |
|----------|-----------------|
| **Matt's other apps** | Query the repository as a knowledge backend (e.g., an AI hedge-fund app pulling expert personas) |
| **Claude Code / AI coding sessions** | Ask "what are the current best practices for X?" and get answers grounded in trusted experts |
| **Content-creation workflows** | Pull Bible-study notes, quotes, and source material for creating content |
| **Matt (human)** | Directly search transcripts, find the signal in hours of video, get 5-minute answers from 3-hour podcasts |

**Left open, not planned:** sharing with an inner circle (friends/family as viewers) exists in the original vision but is explicitly a "maybe later," not a current objective.

---

## 4. Objectives (the strategic "why")

1. **Make expert knowledge frictionless to access** — if getting an answer requires SSH, raw SQL, or manual work, that's a failure.
2. **Be infrastructure, not an app** — the repository must be rich, structured, and accessible enough that any *new* use case is a matter of querying data, not rebuilding the pipeline.
3. **Feed downstream AI** — the primary output is clean, LLM-ready knowledge that Matt's apps and AI sessions consume without custom data wrangling.
4. **Respect source authority** — the user decides which experts matter (trust tiers), not an algorithm.
5. **Capture continuously and stay current** — new content flows in automatically; for fast-moving topics (AI/tech), recency matters and old advice gets superseded.

---

## 5. Goals

**Near-term (get the engine actually working end-to-end):**
- Ingestion running reliably and unattended (no silent stalls).
- Every ingested transcript flows all the way through to *searchable-by-meaning* — not just stored as raw text.
- One real downstream consumer (a Claude Code session or app) successfully querying the repository.

**Mid-term (make it intelligent):**
- Search by meaning across the whole corpus, not just keywords.
- People, topics, and quotes recognized as first-class things you can query.
- Automatic post-processing: best quotes, topic summaries, and "what's new" digests.

**Long-term (make it a platform):**
- Conversational **expert personas** ("talk to Myron Golden about pricing").
- Cross-expert synthesis ("what do all my AI experts say about MCP servers?").
- A stable public doorway (API + MCP) any of Matt's tools can rely on.

---

## 6. Product Structure (what a non-technical stakeholder needs to know)

KnowledgeStack is **six products that work as one pipeline**. Each owns one clear job and can advance independently.

| # | Product | One-line role | Think of it as… |
|---|---------|---------------|-----------------|
| 1 | **KnowledgeEnroll** | Bring content in — monitor channels, pull transcripts, avoid duplicates | Admissions office |
| 2 | **KnowledgeLecture** | Store & serve transcripts you can read, search, and chat with | The lecture hall (Speakr) |
| 3 | **KnowledgeCollege** | Turn transcripts into *intelligence* — meaning-search, entities, connections | The classroom where learning happens |
| 4 | **KnowledgeGraduate** | Curate the best — top quotes, highlight reels, golden-standard answers | Honors program |
| 5 | **KnowledgeGateway** | Let other apps & AI tools request knowledge | The front door / API |
| 6 | **KnowledgeCapture** | Capture Matt's *own* raw thoughts (voice) to refine into content | Your own notebook / thesis work |
| — | **KnowledgeOps** | Keep it all healthy — monitoring, alerts, admin | Facilities & administration |

**Flow:** content comes in through **Enroll**, lands in **Lecture** and **College** at the same time, gets refined in **Graduate**, and is served out through **Gateway** — with **Ops** watching over everything. **Capture** runs alongside as a second, *personal* input: Matt's recorded ideas flow into the same intelligence layer (as their own namespace) to be cross-referenced against the experts.

### 6b. KnowledgeCapture (personal content) — new, in design

Where the experts are *lectures*, this is where **Matt records his own thinking** — the raw material for building courses (e.g., entrepreneurial/mindset principles for young audiences), inspired by and cross-linked to the expert corpus. Personal content moves through a **maturity pipeline** — `raw → research → rehearsal → produced` — and is kept separate from the trusted expert corpus so half-formed ideas never carry expert authority.

**Current status:** in design (see `docs/superpowers/specs/2026-07-12-knowledge-capture-design.md`). Near-term scope is *capture only* — reliably record voice rambles (iOS, via Speakr) with timestamps, stored as the `raw` stage. Extraction, cross-referencing, and a YouVersion-style highlight-to-promote browse layer are deferred to later specs.

---

## 7. Content Lines (the "subjects" the school teaches)

The repository is organized around **7 major content lines**, each a lens for curating channels and filtering answers:

| Content line | What it covers |
|--------------|----------------|
| **Mindset** | Growth & positivity mindset — becoming mentally stronger and more driven |
| **Health** | How to be physically & mentally the best you |
| **Theology** | Religious thought and biblical principles |
| **Business** | How to set up and grow a business |
| **AI & Programming** | Best techniques and lessons for being better at AI-assisted programming |
| **AI Content Generation** | How to best use and create content, courses, videos, and lessons using AI and other tools |
| **Politics** | Political commentary and current events |

*(These are the initial lines; the taxonomy can expand as channels are added.)*

---

## 8. Features (by capability, plain language)

**Getting content in (Enroll)**
- Monitor a curated list of channels and auto-detect new videos.
- Pull the transcript for each new video, with title, description, publish date, and duration.
- Add one-off videos on demand (a guest appearance, an ad-hoc link).
- Avoid duplicates automatically.
- Per-channel rules: auto-ingest everything, or queue for manual approval.

**Reading & listening (Lecture)**
- Full-text search across every transcript.
- Read/playback synced to the video, with tags and bookmarks.
- Chat with any single recording ("summarize this," "what did they say about X?").

**Intelligence (College)**
- **Search by meaning**, not just keywords ("advice about handling rejection").
- Recognize **people, topics, and quotes** as things you can query and connect.
- Connect ideas across videos and experts (knowledge graph).
- **Post-processing:** best-quote extraction, topic summaries, auto-chapters, highlight reels.

**Curation (Graduate)**
- A quote library scored for impact / "shareability."
- "Golden standard" answers — the current best take on a topic, with sources.
- Signature-story detection (the anecdotes an expert repeats most).

**Access out (Gateway)**
- A clean API and an MCP server so Claude Code and other apps can query the repository.
- Filtered queries (by expert, topic, date, content line) with citations.

**Signature "wow" capabilities (vision)**
- **Expert persona chat** — converse with an AI embodying a specific expert.
- **Expert panels** — multiple personas debating a topic.
- **Daily digests** — "here are the 10 clips / 5 insights you need today."
- **Cross-project routing** — new content auto-matched to Matt's active projects.

---

## 9. Version Releases (high-level roadmap)

| Release | Theme | Products active | What "done" looks like |
|---------|-------|-----------------|------------------------|
| **Spike** ✅ | Prove it works | Enroll, Lecture, Ops | *Done* — 50 channels, ~1,000 videos & ~83K segments loaded, pipeline ~95% reliable |
| **MVP-1** | Reliable intake | Enroll, Lecture, Ops | Ingestion runs unattended; new videos searchable in the lecture hall within hours; managed from a portal, not a terminal |
| **MVP-2** | Make it smart | + College, + Gateway (basic) | Search-by-meaning works across the corpus; people/topics tagged correctly; at least one app/AI session querying it |
| **Growth** | Refine & enrich | + Graduate | Best-quote & summary pipelines running; golden standards; richer entity graph |
| **Vision** | Full platform | Gateway (full) | Expert personas, cross-expert synthesis, daily feeds, MCP integration across Matt's tools |

---

## 10. Current Status (honest snapshot — 2026-07-12)

**What's real and working:**
- Enroll pulled **~1,707 raw transcripts** (plus ~83,528 segments loaded in the spike). Content skews business/wealth/mindset (Napoleon Hill, Myron Golden, etc.).
- Lecture (Speakr) is running; content is browsable/searchable by keyword.
- An admin UI exists for channels/pipeline/videos.

**What's NOT done yet (the honest gaps):**
- **Ingestion is dormant** — it silently stopped on **May 1, 2026** (a cold-start bug; being fixed).
- **Raw transcripts don't flow into the intelligence layer** — the fetcher writes files and stops; nothing pushes them into College/embeddings.
- **Zero search-by-meaning** — embeddings were never generated, so the whole intelligence layer is blocked.
- **No post-processing** — no best-quote extraction, no summaries, no cleanup pipeline in production.
- **Graduate & Gateway** — not built.

**Plain-language summary:** the *front half* of the school works (get students in, hold lectures). The *back half* — where content actually becomes intelligence — has been built on paper and partially prototyped, but **has not run**. Turning that on is the central near-term job.

---

## 11. North Star

> We have a repository of amazing knowledge from hundreds of trusted experts — a massive collection of their cumulative publicly-spoken wisdom. We can access and use that knowledge in unlimited ways: feeding it into Claude Code to find best practices, building expert personas, generating a daily feed of what to focus on, or any downstream use we haven't imagined yet.
>
> **The test:** Is the repository rich enough, structured enough, and accessible enough that any new use case is a matter of *querying the data* — not rebuilding the pipeline?
