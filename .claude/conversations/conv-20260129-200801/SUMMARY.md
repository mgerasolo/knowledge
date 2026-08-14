# Conversation conv-20260129-200801 - TLDR

**Title:** BMAD KnowledgeStack: Brainstorm → Brief → Research → PRD (Step 9 SAVED)
**Status:** Active
**Started:** 2026-01-29 20:08
**Last Save:** 2026-03-18 (Speakr Deployment Spike COMPLETE — public URL live)

## Context in 3 Lines
- Purpose: BMAD workflow for KnowledgeStack — YouTube transcript ingestion/RAG platform (Speakr + n8n + Qdrant + LiteLLM)
- Progress: Brainstorming (52 ideas) DONE, Product Brief DONE, Party Mode stress-test DONE, PRD Prep Decisions captured, Technical Research DONE (7 topics, 200+ sources). PRD Steps 1-9 SAVED (158 FRs).
- Goal: PRD (next with PM John) → Architecture → Epics

## BMAD Workflow Checklist
- [x] BMAD workflow-init (greenfield, BMad Method track)
- [x] Brainstorming (52 ideas, 5 techniques, constraint map, morphological box)
- [x] Product Brief (5 steps, all complete)
- [x] Party Mode stress-test of Product Brief (PRD prep decisions captured)
- [x] **BMAD Research phase (COMPLETED — 7 topics, 200+ sources, formal document written)**
- [x] **BMAD PRD Steps 1-9 SAVED (158 FRs, 2 Party Mode sessions: naming + gap analysis)**
- [x] **Speakr Deployment Spike (COMPLETED 2026-03-18) — Banner:5000, public URL live**
- [ ] BMAD PRD Steps 10-11 (NFRs + Final) — NEXT
- [ ] Rename pass across Steps 1-8 (KnowledgeFeed→Enroll, Vault→Library, Link→Graduate)
- [ ] BMAD Architecture
- [ ] BMAD Epics and Stories

## PRD Step 9 Key Decisions (2026-01-31)
- **Product Renamed (Party Mode):** KnowledgeFeed→KnowledgeEnroll, KnowledgeVault→KnowledgeLibrary, KnowledgeLink→KnowledgeGraduate (education metaphor: Enroll→Library→College→Graduate)
- **Channel Scoring (Party Mode):** Authority (1-10) × Relevance (1-10) replaces named tiers. Cadence observed, not rated. Keywords optional MVP curator input.
- **Sunflower UI:** NLF custom UI kit for all custom web interfaces (Growth+). Speakr keeps its own UI.
- **158 FRs:** 78 MVP-1, 22 MVP-2, 32 Growth, 16 Vision, 10 Vision+
- **Key FR areas added in gap analysis:** Backup/recovery (FR90-93), bulk export/portability (FR94-96), pipeline stage monitoring (FR68-73), audio integrity validation (FR155), dependency version tracking (FR156), pre-ingestion AI analysis (FR102-103), thumbnails + embed preview (FR97-99), storage lifecycle (FR79-82), usage analytics (FR83-89), personal knowledge dashboards (FR143-144), API rate limiting (FR105), user attribution (FR147)
- **NAS mount on Banner:** BLOCKED — NFS export not enabled on Fury/Synology for nlf_knowledgestack share. Matt to add NFS permissions in DSM.
- **Graduate name is provisional** — may upgrade Tier 4 name later
- **"Expert" RESERVED** for future authority profiles
- **Forge/Foundry OFF LIMITS** — used elsewhere in NLF

## Matt's Research Checklist (ALL COMPLETE)
- [x] R1: n8n workflows — 4-workflow architecture, 20+ templates analyzed, sidecar yt-dlp pattern
- [x] R2: KnowledgeFeed portal fields — 100+ fields specified, MVP/post-MVP breakdown, sensible defaults
- [x] R3: Deduplication strategy — 6-layer architecture, deterministic UUIDv5, 11-state machine
- [x] R4: Qdrant plugins/tools — No plugins (API-only), multi-tenancy, hybrid search, Grafana dashboards
- [x] R5: Speakr API — 30+ endpoints mapped from source code, audio-only, no webhooks, LLM configurable
- [x] R6: Local LLM models — Qwen3 8B shared model, nomic-embed-text-v1.5, ~10GB peak VRAM
- [x] R7: Additional gaps — RSS reliability, Docker Compose, chunking, monitoring, backup, security

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

## Speakr Deployment Spike (2026-03-18) — COMPLETE

**Deployment:**
- Container: `learnedmachine/speakr:latest` on Banner:5000
- Public URL: https://transcripts.nextlevelguild.com (LIVE)
- Admin: matt@gerasolo.com
- LiteLLM: Project key sk-aWVNtN3uee9ToqVRrPJ1Lg

**Validated:**
- Audio upload, transcription, diarization (gpt-4o-transcribe-diarize)
- Summary generation via LiteLLM
- Public URL via Cloudflare Tunnel

**Fabric Research:**
- Analyzed 200+ prompt patterns from danielmiessler/fabric
- Key patterns: extract_wisdom, summarize, create_video_chapters, label_and_rate
- Integration: CLI, REST API, or copy patterns to n8n workflows

**Files:**
- `deploy/docker-compose.yml` — Container config
- `deploy/.env` — Environment (gitignored)
- `docs/spike-speakr-deployment-findings.md` — Full findings document

**Note:** n8n ingestion pipeline work is in a separate conversation.

## Key Files Created/Modified (Recent)
- `_bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md` — Product Brief (all 5 steps + party mode revisions)
- `_bmad-output/analysis/prd-prep-decisions-2026-01-30.md` — Party Mode decisions (11 sections)
- `_bmad-output/planning-artifacts/bmm-workflow-status.yaml` — Workflow tracking
- `docs/spike-speakr-deployment-findings.md` — Speakr deployment spike findings (2026-03-18)

## Next Actions
1. **Run PRD workflow** with PM John (`/bmad:bmm:workflows:prd`)
2. Continue BMAD: Architecture → Epics

## State Snapshot
**Current Persona:** Ready for PM John (PRD phase)
**Research output:** `_bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md`
**Spike output:** `docs/spike-speakr-deployment-findings.md`
**Current task:** Speakr deployment spike COMPLETE. n8n ingestion in separate conversation.
**Blockers:** None
**Ready to:** Start PRD Steps 10-11 with PM John

## Research Output Files
- `_bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md` — Formal BMAD research synthesis (all 7 topics)
- `docs/research/speakr-comprehensive-research.md` — Detailed Speakr API analysis (40+ source files)
- `docs/research/deduplication-strategy-report.md` — Detailed dedup architecture (50+ sources)

## Open Questions for Matt (from Research)
1. Does Banner (10.0.0.33) have an NVIDIA GPU? (WhisperX deployment strategy)
2. Internal-only vs external access? (AGPL compliance)
3. Speakr SQLite vs shared PostgreSQL?
4. Start with Qwen3 8B or go directly to 30B-A3B MoE?
5. WebSub callback server location for push notifications?

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


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 01:48:30
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 02:11:05
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md
  - ./_bmad-output/analysis/brainstorming-session-2026-01-29.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 02:41:12
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/bmm-workflow-status.yaml
  - ./_bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 03:08:20
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md
  - ./_bmad-output/analysis/prd-prep-decisions-2026-01-30.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 03:31:06
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./docs/research/speakr-comprehensive-research.md
  - ./docs/research/deduplication-strategy-report.md
  - ./_bmad-output/analysis/prd-prep-decisions-2026-01-30.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 13:16:16
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/prd.md
  - ./_bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 14:16:48
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/prd.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 22:09:10
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-30 23:13:13
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-31 01:50:27
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/prd.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-31 02:28:22
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/planning-artifacts/prd.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-31 03:40:18
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/project-context.md
  - ./CLAUDE.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-31 14:07:32
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:
  - ./_bmad-output/herding-protocol-input-2026-01-31.md

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-01-31 15:56:07
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/knowledge
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-03-17 01:22:10
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/KnowledgeStack
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-03-19 02:01:01
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/KnowledgeStack
- Last modified files:
  - ./spike/surreal-rag/docker-compose.yml
  - ./spike/surreal-rag/docs/SPIKE_LOG.md
  - ./spike/surreal-rag/config/channels.yaml
  - ./spike/surreal-rag/schema/init.surql
  - ./spike/surreal-rag/scripts/fetch_spike_channels.sh
  - ./spike/surreal-rag/scripts/ingest_existing.sh
  - ./spike/surreal-rag/scripts/load_to_surrealdb.py
  - ./spike/surreal-rag/README.md
  - ./spike/surreal-rag/queries/graph_traversal.surql
  - ./spike/surreal-rag/queries/semantic_search.surql

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-03-19 21:56:11
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/KnowledgeStack
- Last modified files:
  - ./_bmad-output/planning-artifacts/PRODUCT_VISION.md
  - ./spike/surreal-rag/scripts/fetch_state.json

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-03-22 01:33:19
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/KnowledgeStack
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.


---

## Pre-Compaction Checkpoint

**Timestamp:** 2026-03-22 21:37:28
**Reason:** Approaching token limit (70% usage, 10% buffer before 80% auto-compact)
**Action:** Auto-save triggered before compaction

**State at checkpoint:**
- Working directory: /home/mgerasolo/Dev/KnowledgeStack
- Last modified files:

**Recovery instructions:**
After compaction, the post-compaction hook will automatically
restore context from this file and related context files.

