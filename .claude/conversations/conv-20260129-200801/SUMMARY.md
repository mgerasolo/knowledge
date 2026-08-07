# Conversation conv-20260129-200801 - TLDR

**Title:** BMAD Brainstorming: Knowledge Ingestion Platform
**Status:** Active
**Started:** 2026-01-29 20:08
**Last Save:** 2026-01-30 (updated after brainstorming completion)

## Context in 3 Lines
- Purpose: BMAD workflow brainstorming for knowledge ingestion/RAG platform (YouTube transcripts, expert profiles, vector+relational DB)
- Progress: ALL 5 brainstorming techniques completed (52 ideas, 4 constraint insights, 12-dimension morphological box). Pre-alpha spike also completed in parallel sessions. Cross-Pollination resumed in new conversation after context overflow.
- Goal: Next is Step 4 (idea consolidation), then continue through BMAD planning (Research, Product Brief, PRD, Architecture, Epics)

## Task Checklist
- [x] BMAD workflow-init (greenfield, BMad Method track)
- [x] Brainstorm Step 1: Session setup (topic, goals, context)
- [x] Brainstorm Step 2: Technique selection (hybrid: 3 AI-recommended + 2 wildcards + 1 added)
- [x] Phase 0 Research: n8n workflows, diarization tools, vector DB comparison, ai-hedge-fund
- [x] Brainstorm Technique 1: First Principles Thinking (10 principles, FP #1-#10)
- [x] Pre-alpha spike prompt created (`_bmad-output/pre-alpha-spike-prompt.md`)
- [x] Ideas #11-#14 captured during spike planning
- [x] Brainstorm Technique 2: Dream Fusion Laboratory (Ideas #15-#28)
- [x] Brainstorm Technique 3: Cross-Pollination (Ideas #29-#48, 6 deferred items)
- [x] Brainstorm Technique 4: Constraint Mapping (4 key insights CM-1 through CM-4, Ideas #49-#50)
- [x] Brainstorm Technique 5: Morphological Analysis (12 dimensions, Ideas #51-#52)
- [x] Pirate Code Brainstorm (wildcard used throughout all techniques)
- [ ] Brainstorm Step 4: Idea organization and consolidation (52 ideas → themes)
- [ ] BMAD Research phase
- [ ] BMAD Product Brief
- [ ] BMAD PRD
- [ ] BMAD Architecture
- [ ] BMAD Epics and Stories

## Decisions Made (Architecture)
- **MAJOR PIVOT — Speakr Adoption:** Adopt [Speakr](https://github.com/murtaza-nasir/speakr) (Python/Flask + Vue.js 3, AGPL-3.0) as foundation layer for catalog/playback/search/tags/chat/multi-user
- **Two-Tier Architecture:** Speakr = transcript repository; NextLevel AI Kbase = intelligence overlay (expert profiles, advanced tags, entity relationships, channel taxonomy)
- **Ingestion Pipeline:** YouTube → n8n (RSS monitoring) → Speakr REST API (`/api/v1/upload`)
- Frontend: ~~React + Vite~~ → Speakr Vue.js 3 (as-is)
- Backend: n8n for ingestion orchestration + Speakr Flask for catalog/UI
- Vector DB: Qdrant (self-hosted Docker) — may serve as enrichment layer on top of Speakr's built-in search
- Relational DB: PostgreSQL (existing, shared with Speakr)
- AI Routing: LiteLLM proxy (existing, 10.0.0.27:2764)
- Automation: n8n first, native code when n8n limits
- Diarization: Speakr's WhisperX + OpenAI diarize (replaces our custom pipeline)
- Chunking: Hybrid chapters → semantic → sub-chunk (3-layer)
- Planning Track: BMad Method (full: PRD + UX + Architecture)
- Spike: Pre-alpha prototype completed in separate session (spike/ directory)

## Decisions Made (Morphological Analysis — 12 Dimensions)
- Transcript: Hybrid YouTube API + Whisper fallback
- Discovery: RSS + n8n + manual URL + daily cron confirmation + bulk backlog loader
- Chunking: Chapters → semantic → sub-chunk (3-layer)
- Embedding: LiteLLM proxy (local models for bulk, OpenAI for quality)
- Pipeline: RSS feeds + historical bulk loader + n8n supplemental
- Metadata: YouTube API at ingest + AI enrichment in background
- Entity Resolution: Phased hybrid (exact match → AI → Wikidata)
- API: REST/Express for Phase 1
- Priority: Recency × Tier for recent 6 months; tier-based for backlog; per-channel overrides
- Enrichment: Recent = immediate local AI; historical = casual background

## Key Constraint Mapping Insights
- CM-1: The ONE real constraint is developer bandwidth (Matt + AI across multiple projects)
- CM-2: Core value prop = "You can't scan a 3-hour video to find the 5-10 minutes worth watching"
- CM-3: Downtime-based enrichment architecture — natural lulls between ingestion bursts
- CM-4: "Good Enough" engineering philosophy — 80% accuracy across 10K hours > 99% across 100

## Ideas Summary (52 total)
- FP #1-#10: First Principles (metadata envelope, authority profiles, curator vs creator, statement classification, host-as-platform, channel types, capture-first, meta-knowledge, coverage levels, capture-now-utilize-later)
- #11-#14: Spike planning (metadata refresh, live content, cross-reference verification, playlist auto-ingest)
- #15-#28: Dream Fusion (source trust, sentiment signals, daily micro-podcast, episode distillation, source scoring, guest navigation, YouTube heatmap, user interest profile, personality-matched routing, tag taxonomy, conversational onboarding, channel-inferred profiling, expert conflict detection, recommendation engines)
- #29-#48: Cross-Pollination (entity tracking, topic graph, feedback signals, three-entity architecture, source hierarchy, nullable people, URL field, organizations, format field, automation triggers, topic synonyms, mute filters, citation tracking, disambiguation, block references, watch history, skill trees, expert taxonomy, highlighting, read/unread queue)
- #49-#50: Constraint Mapping (scope separation ingest vs display, channel processing profiles)
- #51-#52: Morphological Analysis (backlog ingestion strategy, guest discovery pipeline)

## Key Files Created/Modified
- `_bmad-output/planning-artifacts/bmm-workflow-status.yaml` — BMAD workflow tracking
- `_bmad-output/analysis/brainstorming-session-2026-01-29.md` — Main brainstorming document (52 ideas, 5 techniques, constraint map, morphological box)
- `_bmad-output/pre-alpha-spike-prompt.md` — Spike prompt (completed)
- `_bmad-output/analysis/pre-alpha-findings.md` — Spike findings
- `docs/reference-youtube-channels.md` — Matt's channel list (46 channels, 4 tiers × 5 domains)
- `docs/research-user-preference-profiling-systems.md` — Recommendation engine research

## Failed Attempts (Don't Retry)
- Context overflow during Cross-Pollination in original conversation — restarted in new conversation and recovered via context files

## Speakr Adoption Pivot (MAJOR)
- **Discovery:** github.com/murtaza-nasir/speakr (2.7K stars, AGPL-3.0, Docker, PostgreSQL, OIDC)
- **Provides FREE:** Transcript display + audio sync, speaker diarization, semantic search, RAG chat, tag system, REST API (Swagger), self-hosted Docker, PostgreSQL, SSO/OIDC, export to Obsidian/Logseq, voice profiles, multi-user + permissions
- **We still build:** YouTube → n8n → Speakr pipeline, channel subscription/monitoring, entity model extensions, hierarchical tag taxonomy, expert authority profiles (later phase), enrichment pipeline, backlog ingestion strategy, guest discovery pipeline
- **Architecture:** Two-tier — Speakr = transcript repository; NextLevel AI Kbase = intelligence overlay app with expert profiles, advanced tags, entity relationships, channel taxonomy
- **Revised phases:** Phase 4 (UI) = FREE, Phase 7 (multi-user) = FREE
- **Matt's framing:** "A whole team's worth of work while shaving off probably a year's worth of work"

## Next Actions
1. Product Brief workflow (Step 1 complete, Step 2 Vision Discovery next)
2. Party Mode after Product Brief to stress-test it
3. Continue BMAD: PRD → Architecture → Epics

## State Snapshot
**Current Persona:** PM (Product Manager — John)
**Current file:** `_bmad-output/analysis/brainstorming-session-2026-01-29.md`
**Current task:** Product Brief workflow — Step 1 input discovery done, output file not yet created, Step 2 pending
**Blockers:** None
**Ready to:** Create Product Brief output file and begin Step 2 (Vision Discovery)

---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 (post-brainstorm-completion)
**Reason:** Manual save — all 5 brainstorming techniques completed
**Action:** Full documentation update

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/analysis/brainstorming-session-2026-01-29.md (52 ideas, all techniques)
  - ./docs/reference-youtube-channels.md (Matt's channel taxonomy)

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.
The brainstorming doc is self-contained — read it to restore full session context.
All 52 ideas are documented inline with Matt's exact framing quotes.

---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 00:58:58
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/analysis/brainstorming-session-2026-01-29.md
  - ./spike/reports/retry-output.log
  - ./spike/reports/run-2026-01-30T05-33-45.json

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.

