---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain-skipped', 'step-06-innovation-skipped', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
classification:
  projectType: 'web_app'
  projectTypeDetail: 'Web application (5-product platform: KnowledgeEnroll, KnowledgeLecture, KnowledgeCollege, KnowledgeGraduate, KnowledgeOps)'
  domain: 'knowledge_management'
  domainDetail: 'Knowledge management / content intelligence'
  complexity: 'medium-high'
  complexityNotes: 'Technically ambitious (multi-host, GPU pipeline, 11-state machine) but no regulatory burden'
  projectContext: 'greenfield'
  projectContextDetail: 'Greenfield with validated foundations (spike + adopted Speakr)'
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-knowledge-2026-01-30.md
  - _bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md
  - _bmad-output/analysis/prd-prep-decisions-2026-01-30.md
  - _bmad-output/analysis/brainstorming-session-2026-01-29.md
  - _bmad-output/analysis/pre-alpha-findings.md
  - _bmad-output/analysis/spike-handoff-report.md
  - docs/research/speakr-comprehensive-research.md
  - docs/research/deduplication-strategy-report.md
  - docs/research-user-preference-profiling-systems.md
  - docs/reference-youtube-channels.md
  - docs/METADATA_ENTITIES_RESEARCH.md
documentCounts:
  briefs: 1
  research: 4
  brainstorming: 4
  projectDocs: 2
  projectContext: 0
workflowType: 'prd'
date: '2026-01-30'
author: 'Matt'
---

# Product Requirements Document - KnowledgeStack

**Author:** Matt
**Date:** 2026-01-30

## Executive Summary

**KnowledgeStack** is not a single application — it is a platform composed of 5 distinct products that work together to transform YouTube content from trusted experts into a searchable, AI-queryable knowledge repository. Each product owns a clear stage of the pipeline: content enters through **KnowledgeEnroll**, lives in **KnowledgeLecture**, gets enriched by **KnowledgeCollege**, is exposed to external tools via **KnowledgeGraduate**, and the whole system is managed through **KnowledgeOps**.

It solves a core problem: you can't scan a 3-hour video to find the 5-10 minutes worth watching. KnowledgeStack ingests, transcribes, enriches, and structures content from ~50 curated channels across 5 domains (AI/Tech, Business, Political, Mindset/Health, General) — making expert knowledge instantly accessible at the segment level.

### The 5 Products

| Product | Tier | What It Does | Tech Foundation |
|---------|------|-------------|-----------------|
| **KnowledgeEnroll** | 1 — Ingestion | Monitors RSS feeds, downloads YouTube content, deduplicates, captures metadata, manages channel subscriptions | n8n workflows, yt-dlp, YouTube API |
| **KnowledgeLecture** | 2 — Repository | Stores transcripts, provides search, per-recording AI chat, tagging, bookmarks, multi-user access | Speakr (adopted open-source, unmodified) |
| **KnowledgeCollege** | 3 — Intelligence | Embeds transcripts into vector store, enables semantic search, enriches with entities/topics/speakers | Qdrant, LiteLLM |
| **KnowledgeGraduate** | 4 — Distribution | Exposes the knowledge repository to external apps and AI tools via REST API and MCP server | Express/Flask, MCP |
| **KnowledgeOps** | Cross-cutting | Pipeline monitoring, Slack alerting, status digests, failed item management, admin tooling, DevOps lifecycle | n8n, Slack, Grafana, Loki |

### Key Differentiator

Speakr (adopted open-source, AGPL-3.0) provides the transcript repository, search, per-recording chat, and multi-user access — eliminating ~1 year of UI/auth/search development. KnowledgeStack builds the ingestion automation, intelligence layer, operational visibility, and API access that Speakr doesn't provide.

### Target Users

- **Admin (Matt):** Solo developer + curator. Configures channels, monitors pipeline, manages the system.
- **Viewers (Inner Circle):** Small group (<10 MVP) consuming transcripts via Speakr. Search, browse, chat, tag.
- **Downstream AI Tools (Vision):** Claude Code, LobeChat, OpenClaw — querying the repository via REST API or MCP.

### Infrastructure

5-host deployment on internal network (10.0.0.x):
- **Banner** (10.0.0.33): Speakr + PostgreSQL + KnowledgeStack services
- **Helicarrier**: n8n workflow engine
- **Jarvis**: WhisperX GPU transcription + LiteLLM proxy
- **Coulson**: Grafana + Loki + Prometheus (monitoring)
- **Fury/Synology NAS**: Audio file storage

### North Star

> A living repository of the world's greatest minds -- curated from trusted sources, continuously growing, with their knowledge tagged and structured so it's instantly accessible to people and applications. The purpose: to help our users and everyone who touches the tools built on it live more fulfilling, purposeful, healthy, financially successful, and happy lives.

## Success Criteria

### User Success

**Admin (Matt) Success:**
- "I subscribe to a new channel and within hours, new videos are transcribed, tagged, and searchable" -- zero manual intervention after channel setup
- "I can find that one segment where Huberman explained X" -- search returns the right segment from a 3-hour episode
- "The system runs while I sleep" -- RSS monitoring + n8n pipeline operates autonomously
- "Backlog ingestion just works" -- bulk-load historical content from ~50 channels without babysitting
- "I open the channel monitor page and immediately see: 48 channels green, 1 flagged (3+ weeks silent), 1 known exception" -- pipeline health and content gaps are visible at a glance, not buried in logs

**Viewer Success (Downstream):**
- "I found the answer in 30 seconds instead of watching a 3-hour video" -- segment-level search with playback sync
- "I didn't know this expert existed, but the system surfaced them" -- cross-channel discovery through tags and entities
- "I can chat with a recording and get answers" -- Speakr's per-recording RAG chat delivers accurate responses

**Downstream App Success (KnowledgeGraduate -- Future):**
- "My LobeChat instance can query the knowledge repository" -- API delivers structured results to external consumers
- "I can build a custom tool on top of this data" -- REST API is well-documented and stable

### Business Success

**3-Month (MVP Validation):**
- Pipeline reliably ingests new content from ~50 channels with <5% failure rate
- Speakr instance contains 500+ transcribed recordings (new content + priority backlog loading)
- Search returns usable results for queries across all 5 domains (AI, Business, Political, Mindset/Health, General)
- Canary channel (reliable weekly poster) successfully ingested every week without manual intervention
- Operational visibility in place: pipeline failures surface via Slack, per-channel status is queryable
- Channel monitor page shows all channels with last ingestion date and flags 3+ weeks silent

**Aspirational:** At least 1 inner circle user finds value and returns on their own. Not a gate -- if the system helps Matt, the project is successful. Others will primarily access through downstream systems.

**6-Month (Growth Signal):**
- Repository exceeds 2,000 recordings with historical backlog substantially loaded
- Entity enrichment (speakers, topics, organizations) covers 80%+ of recordings
- Channel tier system actively influencing processing priority
- Grafana dashboard live on Coulson with pipeline health, per-channel coverage scores, and enrichment progress
- Per-channel coverage scoring operational (e.g., "Channel X: 94% coverage, Channel Y: 61%")

**12-Month (Platform Value):**
- Repository approaching 5,000+ recordings
- KnowledgeGraduate API serving at least 1 downstream application (e.g., LobeChat)
- Tag taxonomy mature enough to enable meaningful cross-channel navigation
- System recognized by inner circle as "the place to find what [expert] said about [topic]"

### Technical Success

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Ingestion pipeline uptime | >95% (auto-recovery) | RSS -> n8n -> Speakr must run unattended |
| Transcript accuracy | "Good enough" (Speakr + WhisperX handles this) | Dependency -- we don't re-solve transcription |
| Search relevance | Aspiration: relevant results in top 3. Speakr controls this; revisit when we add our own search layer | Core value prop long-term, but not an MVP hard gate |
| Dedup accuracy | <1% false duplicates reaching Speakr | 6-layer dedup (UUIDv5 + URL + fingerprint) |
| Pipeline failure rate | <5% per batch run | Retries + dead-letter queue handle transient failures |
| System recovery | <30 min from any single-service failure | Docker Compose restart + health checks |
| Canary ingestion | Weekly canary channel passes every week | High-signal pipeline health check |
| Speakr API response | Monitor, don't control. Flag if degradation observed | Dependency we track, not engineer |

### Operational Visibility

**MVP (Observable Foundations):**
- Channel Monitor Page: Lists all ~50 monitored channels with last ingestion date, expected cadence, and flags when any channel exceeds 3 weeks without new content. Accounts for known exceptions (channels on hiatus).
- n8n execution logs with structured pass/fail per channel per run
- "Last successful run per channel" status check (n8n cron + Speakr API query)
- Slack alerts on pipeline failure (immediate)
- Slack stale-channel alert: Automated notification when any monitored channel exceeds 3 weeks without new ingested content. Known exceptions can be muted.
- Slack gap digest (daily summary of operational status)
- Dead-letter queue visibility (what failed, why, retry status)
- Canary ingestion test: weekly re-process of a known reliable channel as health check
- Built for Grafana: All metrics structured so Prometheus export + Grafana dashboards plug in cleanly at Growth phase

**Growth (Full Dashboard):**
- Grafana dashboard on Coulson: pipeline health, per-channel coverage scores, enrichment progress, error trends
- Per-channel coverage scoring: % of expected videos ingested, % enriched
- Trend analysis: failure rates over time, processing time trends, queue depth

### Measurable Outcomes

**Per-Product MVP Gates:**

| Product | Gate | Metric |
|---------|------|--------|
| KnowledgeEnroll | Automated ingestion running | New videos from ~50 channels appearing in Speakr within 24h of publish, canary channel never missed |
| KnowledgeLecture | Searchable repository | Speakr contains 500+ recordings (new + backlog), search works, per-recording chat works |
| KnowledgeCollege | Enrichment pipeline | Deferred to Growth -- MVP focuses on raw ingestion and Speakr's built-in capabilities |
| KnowledgeGraduate | API accessible | Deferred to Vision -- downstream integration after repository is mature |
| Operations | Visibility | Pipeline health surfaced via channel monitor page + Slack alerts + n8n logs, no manual log hunting required |

## Product Scope

### MVP -- Minimum Viable Product

**Must work to be useful:**
1. **KnowledgeEnroll Pipeline**: n8n workflows monitoring RSS feeds from ~50 channels -> downloading -> sending to Speakr API
2. **KnowledgeLecture (Speakr)**: Self-hosted on Banner, PostgreSQL, transcript display + search + per-recording chat
3. **Deduplication**: 6-layer pipeline preventing duplicate ingestion (UUIDv5, URL normalization, content fingerprint)
4. **Basic Metadata**: YouTube API metadata captured at ingest (title, description, channel, publish date, duration)
5. **Channel Configuration**: Tier-based processing priorities for ~50 initial channels
6. **Operational Visibility**: Channel monitor page + n8n execution logs + Slack alerts (pipeline failures + stale-channel 3-week threshold) + per-channel status checks + canary test. All metrics structured for future Grafana integration.

**Deployment Prerequisites (not product features):**
- WhisperX on Jarvis (Speakr `ASR_BASE_URL` configuration)
- Speakr PostgreSQL on Banner
- NAS mount for Speakr audio storage (Fury/Synology)
- n8n workflows on Helicarrier

**Explicitly NOT MVP:**
- Cross-repository AI queries (Speakr only has per-recording chat)
- Advanced entity enrichment (expert profiles, authority scoring)
- LobeChat integration
- Hierarchical tag taxonomy
- User preference profiling
- Multi-user access (Speakr supports it, but not a launch gate)
- Automated channel discovery (all ~50 channels manually configured)
- Grafana dashboard (Growth feature -- MVP builds the observable foundations)

### Growth Features (Post-MVP)

7. **Entity Enrichment Pipeline**: AI-powered speaker identification, topic extraction, organization tagging
8. **Hierarchical Tag Taxonomy**: Domain > Category > Topic structure
9. **Channel Taxonomy**: Automated channel classification + tier recommendations
10. **Historical Backlog Completion**: Bulk ingestion of remaining backlog beyond MVP's 500+
11. **Advanced Search**: Cross-channel topic queries, entity-based navigation
12. **Grafana Operational Dashboard**: Full pipeline visibility on Coulson with per-channel coverage scores
13. **Multi-user Access**: Speakr OIDC/Authentik integration for inner circle

### Vision (Future)

14. **KnowledgeGraduate API**: REST endpoints exposing structured knowledge to external apps
15. **LobeChat Integration**: Cross-corpus AI chat over the full repository
16. **Expert Authority Profiles**: Trust scoring, expertise mapping, conflict detection
17. **User Preference Profiling**: Personalized recommendations based on viewing patterns
18. **Cross-Reference Verification**: Fact-checking claims across multiple experts
19. **Daily Micro-Digest**: AI-generated summaries of new content across subscribed channels

## User Journeys

### Product Architecture (5-Product Platform)

| Product | Tier | Purpose |
|---------|------|---------|
| **KnowledgeEnroll** | 1 | Ingestion pipeline (n8n, RSS, dedup, metadata, channel management) |
| **KnowledgeLecture** | 2 | Transcript repository (Speakr -- search, chat, tags, playback) |
| **KnowledgeCollege** | 3 | Intelligence layer (Qdrant, enrichment, semantic search, entity graphs) |
| **KnowledgeGraduate** | 4 | API + integrations (REST, MCP, LobeChat, downstream apps) |
| **KnowledgeOps** | Cross-cutting | System management, monitoring, alerting, admin experience, DevOps lifecycle |

### Journey Index

| # | Journey | Persona | Scope | Product |
|---|---------|---------|-------|---------|
| 1 | First Channel Setup (+ bulk import) | Matt (Admin) | MVP | KnowledgeEnroll |
| 1B | The Backlog Marathon | Matt (Admin) | MVP | KnowledgeEnroll |
| 2 | Finding the Signal (+ dead-end recovery) | Matt (Search) | MVP | KnowledgeLecture |
| 3 | Pipeline Problem (explicit failure) | Matt (Ops) | MVP | KnowledgeOps |
| 3B | Silent Failure (RSS breaks) | Matt (Ops) | MVP | KnowledgeOps |
| 4 | New Viewer Discovery | Sarah (Viewer) | MVP | KnowledgeLecture |
| 5 | Curated Export for AI | Matt (Downstream) | MVP/Growth | KnowledgeLecture/KnowledgeGraduate |
| 6 | Curator Graduation | Sarah -> Curator | Growth | KnowledgeEnroll |
| 7 | AI Tool Integration (MCP + REST) | Claude/LobeChat/OpenClaw | Vision | KnowledgeGraduate |
| 8 | Morning System Check | Matt (Ops) | MVP | KnowledgeOps |
| 9 | Responding to an Alert | Matt (Ops) | MVP | KnowledgeOps |
| 10 | Investigating a Persistent Problem | Matt (Ops) | MVP | KnowledgeOps |
| 11 | Capacity Planning | Matt (Ops) | Growth | KnowledgeOps |

### Journey 1: First Channel Setup (MVP)
**Persona:** Matt (Admin) | **Product:** KnowledgeEnroll

**Opening Scene:** Matt has just deployed KnowledgeStack. Speakr is running on Banner, n8n is on Helicarrier, WhisperX is on Jarvis. The system is empty. He opens the channel management interface with his list of ~50 channels organized by tier.

**Rising Action:** He starts with bulk import -- uploads a CSV of his ~50 channels with tier assignments and ingestion rules. Supreme tier channels (Huberman, Myron Golden, Chris Williamson) are set to "auto-ingest all" with full priority. Mid-tier platform channels like Joe Rogan are set to "manual approval." He marks Scott Adams' channel as "on hiatus" so the stale-channel alert won't fire. He configures backlog settings -- Huberman gets full historical depth, mid-tier channels get last 6 months only. Kicks off the first ingestion run.

**Climax:** An hour later, he opens Speakr. Huberman's latest episode is there -- fully transcribed, searchable, with speaker diarization. He searches "dopamine protocol" and gets segment-level results from three different episodes. The system works.

**Resolution:** Over the next few days, Matt watches the Slack status reports fill in. 48 channels green. Two still processing backlog. His Slack channel has been quiet -- no failures. The pipeline is running while he sleeps.

**Reveals requirements for:** Channel management UI, bulk channel import (CSV/multi-URL), tier configuration, per-channel ingestion rules (auto/manual/hybrid), backlog depth settings, hiatus/exception flags, RSS monitoring setup.

### Journey 1B: The Backlog Marathon (MVP)
**Persona:** Matt (Admin) | **Product:** KnowledgeEnroll

**Opening Scene:** Initial channels are configured and new content is flowing. Now Matt wants to load historical content -- roughly 2,000 videos across ~50 channels. He opens the backlog configuration.

**Rising Action:** He sets priority loading: Supreme channels first (full depth), Leaders next (1 year), Mid-tier (6 months), Occasional (3 months). The system begins processing. Matt checks the Slack status report the next morning -- "Backlog: 127/2,000 processed. Supreme channels: 60% complete. Leaders: starting. Estimated: 3 weeks at current rate."

Over the following days, edge cases emerge. Some videos are privated. A few are age-restricted. One channel renamed and old URLs don't resolve. Dead-letter queue fills with these cases. Matt reviews the dead-letter items -- acknowledges the privated videos (skipped), re-queues the renamed-URL ones with corrected URLs.

**Climax:** Two weeks in, Supreme and Leader channels are fully loaded. Mid-tier is progressing. The dead-letter queue is manageable -- 15 items, all acknowledged or explained. Matt's total intervention time: ~30 minutes across 2 weeks.

**Resolution:** The backlog reaches target depth per tier. The system transitions to steady-state: new content only, with the occasional backlog batch for newly added channels.

**Reveals requirements for:** Backlog progress tracking, priority queue by tier, estimated completion rate, per-channel depth configuration, handling inaccessible content (private, deleted, age-restricted), dead-letter queue review and re-queue capability.

### Journey 2: Finding the Signal (MVP)
**Persona:** Matt (Search/Discovery) | **Product:** KnowledgeLecture

**Opening Scene:** Tuesday morning. Matt heard on a podcast that Andrew Huberman discussed a specific cold exposure protocol that contradicts another expert. He wants the exact segment but doesn't remember which episode.

**Rising Action:** He opens Speakr and searches "cold exposure protocol duration." Three results -- one from Huberman, one from Ultimate Human Podcast, one from a Chris Williamson episode where Huberman was a guest. He clicks the Huberman result. The transcript jumps to the relevant segment -- minute 47 to minute 53. He reads the 6-minute segment in 90 seconds.

**Dead-End Recovery:** On another occasion, Matt searches "dopamine fasting benefits" and gets no results. The experts used different terminology. He tries "deliberate dopamine regulation" -- finds it. This is a known MVP limitation: Speakr's built-in search has limited semantic similarity. KnowledgeCollege (Qdrant layer) is specifically what solves synonym/semantic matching in Growth phase.

**Climax:** Huberman specifically said "11 minutes total per week, not per session." Matt has the precise claim, timestamped, from the original source. He opens Speakr's chat on that recording and asks "What studies did Huberman cite?" -- the RAG chat pulls the citations from earlier in the same episode.

**Resolution:** Matt copies the relevant segment and shares it with his brother. Total time from question to answer: 3 minutes. The 3-hour episode just paid for itself.

**Reveals requirements for:** Segment-level search (Speakr), transcript display with timestamp sync (Speakr), per-recording RAG chat (Speakr), copy/share transcript segments (Speakr -- verify). Known limitation: MVP search lacks semantic similarity; KnowledgeCollege resolves this.

### Journey 3: Pipeline Problem (MVP)
**Persona:** Matt (Ops) | **Product:** KnowledgeOps

**Opening Scene:** Thursday. Matt gets a Slack notification: "Pipeline Alert (Yellow): @AILABS-393 -- ingestion failed, retry exhausted (3/3 attempts, 30min/1hr/2hr backoff). Error: Speakr API returned 413 -- payload too large."

**Rising Action:** Matt checks the Slack status context. 49 channels green, 1 red (AI Labs). The failed video is a 5-hour livestream -- the audio file exceeds Speakr's upload limit. Dead-letter queue shows: 1 item, clear error message, metadata (URL, channel, error, 3 retry attempts, first failure 4 hours ago), no other channels affected.

**Climax:** This isn't a system problem -- it's an edge case. Matt marks it as "skipped -- oversized livestream" in the dead-letter queue. The system continues processing everything else.

**Resolution:** Matt didn't dig through logs. Slack told him what broke. The status context told him it was isolated. The dead-letter queue told him why. Total investigation: 2 minutes.

**Reveals requirements for:** Slack alerting with severity levels (red/yellow/green), auto-retry with escalating backoff (30min -> 1hr -> 2hr, 3 attempts), dead-letter queue with full metadata (URL, channel, error, retry count, first/last timestamps), acknowledge/skip workflow, impact assessment (isolated vs systemic).

### Journey 3B: Silent Failure (MVP)
**Persona:** Matt (Ops) | **Product:** KnowledgeOps

**Opening Scene:** Three weeks pass. Matt gets a Slack stale-channel alert: "@AILABS-393 -- no new content in 22 days (expected: weekly)."

**Rising Action:** Matt checks YouTube directly -- the channel is posting fine. The RSS feed URL changed when the channel rebranded. The pipeline received no errors because there was nothing to fail -- the old RSS simply returned no new items.

**Climax:** Matt updates the channel config with the new feed URL. The next pipeline run picks up the 3 missed videos and ingests them successfully. A "catch-up" ingestion runs for the missed window.

**Resolution:** The stale-channel alert caught what no error log would have found. The 3-week threshold gave enough signal without false-alarming on biweekly posters.

**Reveals requirements for:** Stale-channel alerting (already scoped), RSS URL validation/update capability, catch-up ingestion for missed content windows, channel config update through admin interface.

### Journey 4: New Viewer Discovery (MVP)
**Persona:** Sarah (Viewer -- Inner Circle) | **Product:** KnowledgeLecture

**Opening Scene:** Sarah is Matt's friend, a marketing professional interested in AI but overwhelmed by the content firehose. Matt sends her a Speakr login via Authentik SSO.

**Rising Action:** Sarah logs in and sees a library of 500+ transcripts. She searches "AI marketing automation" -- results appear from Greg Isenberg, My First Million, and an unexpected hit from Sabrina Ramonov she'd never heard of.

**Note:** Speakr's default landing page experience needs evaluation for first-time viewer usability. If overwhelming for Sarah's "first 30 seconds," flag as Growth UX improvement task.

**Climax:** She opens the Greg Isenberg transcript. Instead of watching a 90-minute episode, she reads the 4-minute segment about AI-powered content repurposing. She uses Speakr's chat to ask "What tools did he recommend?" and gets a clean answer with timestamps. She thinks: "Why have I been watching full videos this whole time?"

**Resolution:** Sarah bookmarks three transcripts and tags them "marketing-tools." She comes back the next day. A week later, she messages Matt: "Can I add my own channels?"

**Reveals requirements for:** Multi-user access (Speakr + Authentik SSO), search across full repository (Speakr), transcript browsing (Speakr), per-recording chat (Speakr), tagging/bookmarking (Speakr). First-login UX evaluation (Growth).

### Journey 5: Curated Export for AI (MVP/Growth)
**Persona:** Matt (Downstream Consumer) | **Product:** KnowledgeLecture/KnowledgeGraduate

**Opening Scene:** Matt is working with OpenClaw on developing best practices for AI-assisted software development. He knows Unsupervised Learning, BMad Code, and Replit have covered this topic extensively.

**Rising Action (MVP -- Manual):** Matt opens Speakr, searches "AI coding best practices" filtered to those channels. Finds 5 relevant recordings. Uses Speakr's export feature (verify capability -- Obsidian/Logseq export exists, does it support plain text transcript download?) or copies transcript segments manually.

**Rising Action (Growth -- API):** Matt uses the KnowledgeGraduate API to query structured transcript chunks with metadata. Pipes this directly into OpenClaw.

**Rising Action (Vision -- MCP):** Matt's AI tool calls the KnowledgeStack MCP directly. No manual export at all.

**Climax:** OpenClaw synthesizes insights from 8 expert discussions into a coherent best-practices document citing specific experts and timestamps.

**Resolution:** The repository is a knowledge substrate that feeds AI tools. The MCP server (Vision) largely eliminates the need for manual export -- AI tools query directly.

**Pre-architecture flag:** Verify Speakr's transcript export capability before architecture. This determines MVP implementation path.

**Reveals requirements for:** Search with channel filtering (Speakr -- verify), transcript export/download (Speakr -- verify), KnowledgeGraduate REST API (Growth), MCP server (Vision), metadata in export (source, timestamp, speaker).

### Journey 6: Curator Graduation (Growth)
**Persona:** Sarah -> Curator | **Product:** KnowledgeEnroll

**Opening Scene:** Sarah has used KnowledgeStack as a Viewer for 3 months. She messages Matt: "I want to add Marketing Over Coffee and a few other marketing podcasts."

**Rising Action:** Matt grants Sarah Curator access. She adds Marketing Over Coffee's YouTube channel URL, sets it to auto-ingest with 3-month backlog. The system starts pulling in episodes.

**Climax:** A week later, Sarah searches "email marketing ROI" and gets results from her marketing channels alongside Matt's business/AI channels. The shared repository combines both content pools.

**Resolution:** The repository grows from two curators. Content Sarah adds benefits Matt, and vice versa. The "ingest once, share with all" model means no duplication.

**Reveals requirements for:** Curator role management, self-service channel addition, per-curator subscription management, shared repository model, access control (Curator vs Viewer).

### Journey 7: AI Tool Integration (Vision)
**Persona:** Claude Code / LobeChat / OpenClaw (via MCP or REST API) | **Product:** KnowledgeGraduate

**Opening Scene:** Matt is in a Claude Code session. He needs best practices for n8n workflow design and knows his repository has extensive coverage.

**Rising Action (MCP):** Matt types a query. Claude Code calls the KnowledgeStack MCP tool: `knowledge_search(query="n8n workflow design best practices", channels=["mreflow", "NetworkChuck", "BMadCode"])`. The MCP server queries Speakr's API and returns structured transcript segments with metadata.

**Rising Action (LobeChat):** Alternatively, LobeChat with a KnowledgeStack plugin queries the REST API, retrieves relevant segments, and synthesizes a response citing specific experts and episodes.

**Climax:** The AI tool answers from Matt's curated repository of trusted experts, not just training data. Responses include real citations: "According to Matt Wolfe (Episode 247, timestamp 23:15)..."

**Resolution:** The repository becomes an intelligence layer any AI tool can tap into. Years of curation compound -- every new tool gets smarter.

**Reveals requirements for:** MCP server implementation (tool definitions for search, retrieve, list channels), REST API endpoints (KnowledgeGraduate), structured response format (transcript + metadata + citations), authentication for API consumers, rate limiting.

### Journey 8: Morning System Check (MVP)
**Persona:** Matt (Admin/Ops) | **Product:** KnowledgeOps

**Opening Scene:** Monday morning. Matt checks Slack for the weekly status digest posted by the n8n status report workflow.

**Information Hierarchy:**
- **Tier 1 (glance -- 5 seconds):** Traffic light indicator + one-line summary. "Green -- All systems normal. 23 new this week, 0 failures." Most Monday mornings end here.
- **Tier 2 (scan -- 15 seconds):** Channel summary (49/50 current, 1 muted), backlog progress (127 remaining, Supreme done, Leaders 80%), utilization (18 min/day processing average, peak Thursday 42 min).
- **Tier 3 (drill-down -- only if needed):** Per-channel details, error patterns, dead-letter queue.

**Climax:** Matt sees green. No action needed. Utilization at 18 min/day means plenty of headroom. He closes Slack and moves on.

**Resolution:** Total admin time this week: reading one Slack message. 30 seconds.

**MVP delivery:** n8n scheduled workflow posts formatted Slack summary (daily or weekly configurable). No custom web frontend.

**Reveals requirements for:** n8n status report workflow, Slack rich message formatting (blocks), pipeline health indicator (green/yellow/red), utilization metrics (processing time per day/week), backlog queue depth + progress + estimated completion, weekly activity summary, information hierarchy (glance -> scan -> drill-down).

### Journey 9: Responding to an Alert (MVP)
**Persona:** Matt (Admin/Ops) | **Product:** KnowledgeOps

**Opening Scene:** Matt's phone buzzes with Slack: "Pipeline Alert (Yellow): 3 consecutive failures on @NetworkChuck. Error: YouTube API rate limit (429). Auto-retry scheduled in 2 hours."

**Rising Action:** The alert includes context: only NetworkChuck affected, all other channels normal. The system has already backed off with escalating retry (30min -> 1hr -> 2hr).

**Climax:** Matt acknowledges the alert. Two hours later, follow-up Slack: "Recovery: @NetworkChuck 3 videos successfully ingested on retry." Self-healed.

**Resolution:** Matt read two Slack messages. Total admin time: 15 seconds.

**Reveals requirements for:** Alert severity levels (red/yellow/green), auto-retry with escalating backoff (3 retries: 30min/1hr/2hr), alert acknowledgment, recovery notifications, Slack deep links to relevant n8n execution logs.

### Journey 10: Investigating a Persistent Problem (MVP)
**Persona:** Matt (Admin/Ops) | **Product:** KnowledgeOps

**Opening Scene:** Intermittent failure alerts for @TheDiaryOfACEO for a week. Auto-retries resolve most, but failures keep recurring.

**Rising Action:** Matt reviews the Slack alert history. Pattern: 4 failures in 7 days, all on videos >2 hours. Error: Speakr API timeout on upload for large files. Shorter videos ingest fine. Dead-letter queue shows 2 items stuck (retry exhausted), each with full metadata.

**Climax:** Matt identifies a systematic issue: large files hitting a timeout threshold. He adjusts the n8n workflow parameter (upload timeout) via n8n's configuration. Re-queues the 2 dead-letter items. They process successfully.

**Note:** MVP configuration changes are through n8n workflow parameters or environment variables. Admin configuration UI is a Growth feature.

**Resolution:** Pattern identified, root cause diagnosed, config fixed -- all without SSH or log files. The system handles large uploads from this channel going forward.

**Reveals requirements for:** Error pattern visibility in Slack alerts (recurring vs transient), per-channel failure history, dead-letter queue re-queue capability, dead-letter metadata (URL, channel, error, retry count, first/last timestamps), n8n workflow parameter configuration.

### Journey 11: Capacity Planning (Growth)
**Persona:** Matt (Admin/Ops) | **Product:** KnowledgeOps

**Opening Scene:** Month 4. Matt considers adding 20 more channels. He checks the Grafana dashboard on Coulson.

**Rising Action:** Utilization shows: 50 channels, 35 min/day average, peak 1.2 hours. Banner disk at 25%. NAS at 10%. Processing time trending up ~5 min/month as backlog loads.

**Climax:** Clear headroom. Adding 20 channels pushes daily processing to ~50 minutes. Disk won't be a concern for 6+ months.

**Resolution:** Data-driven capacity decision. Matt adds channels with confidence.

**MVP capacity metric:** Disk usage alerts on Banner and NAS mount health (n8n health check workflow). Full resource monitoring (Prometheus + Grafana) is Growth.

**Reveals requirements for:** Utilization trending (daily/weekly/monthly), resource usage visibility (disk on Banner, NAS health), capacity projection, Grafana dashboards on Coulson (Growth), Prometheus node exporters (Growth).

### KnowledgeOps Product Definition

**KnowledgeOps** is the 5th product in the KnowledgeStack platform, owning the full operational lifecycle:

**MVP (Lightweight -- Slack + n8n native):**
- Pipeline monitoring (Slack alerts, n8n execution history)
- Channel status tracking (Slack stale-channel alerts, status digest)
- Dead-letter queue (PostgreSQL table, n8n re-queue workflow)
- Status reporting (n8n -> Slack formatted summaries)
- Retry management (3 attempts, escalating 30min/1hr/2hr backoff)
- Disk usage alerts (Banner + NAS mount health check)
- Docker healthchecks and restart policies
- Backup verification (confirm automated PostgreSQL dumps + NAS snapshots per Standards)
- Structured logging to Loki (already available on Coulson)

**Growth (Solid by MVP+3 -- Grafana + expanded coverage):**
- Grafana dashboards on Coulson (pipeline health, channel coverage scores, utilization trends)
- Per-channel coverage scoring (% ingested, % enriched)
- Capacity planning metrics (resource usage, trend projections)
- AI pipeline monitoring (Langfuse/LangSmith for LLM quality when College comes online)
- Admin configuration UI (no more n8n parameter editing)
- Correlation IDs for end-to-end pipeline tracing
- Data integrity audits (orphan detection, dedup verification)

**Vision (Full admin portal):**
- Self-service admin portal (zero-SSH operations)
- Container security scanning
- Automated deployment and update management
- Full distributed tracing across all 5 hosts

**DevOps lifecycle coverage (deferred to research results):**
- Backups & recovery -- likely covered by NLF Standards (research running)
- Deployment & updates -- Docker Compose patterns (research running)
- Security & access -- Standards + AGPL compliance (research running)
- Logging & observability -- Loki already available (research running)

**Architecture-phase items (from Winston):**

| # | Item | Type |
|---|------|------|
| 1 | KnowledgeOps data store design (separate PostgreSQL DB on Banner) | Architecture decision |
| 2 | n8n workflow separation (data workflows vs ops workflows) | Design pattern |
| 3 | Cross-host monitoring scope (MVP = n8n + Speakr only) | Scope boundary |
| 4 | Speakr capability verification (export, filtering, segments, landing page) | Pre-architecture research |
| 5 | Dead-letter queue data model (PostgreSQL table design) | Data design |
| 6 | NAS mount health check design | Infrastructure |

### Journey Requirements Summary

| Capability | Journeys | Scope | Speakr Provides? |
|-----------|----------|-------|-----------------|
| Channel management UI (add, configure, tier, hiatus) | J1, J6 | MVP | No -- KnowledgeEnroll |
| Bulk channel import (CSV/multi-URL) | J1 | MVP | No -- KnowledgeEnroll |
| Per-channel ingestion rules (auto/manual/hybrid) | J1, J6 | MVP | No -- KnowledgeEnroll |
| Backlog depth configuration | J1, J1B | MVP | No -- KnowledgeEnroll |
| Backlog progress tracking | J1B | MVP | No -- KnowledgeEnroll/Ops |
| Inaccessible content handling | J1B | MVP | No -- KnowledgeEnroll |
| Segment-level search | J2, J4, J5 | MVP | Yes |
| Per-recording RAG chat | J2, J4 | MVP | Yes |
| Transcript display with timestamp sync | J2, J4 | MVP | Yes |
| Copy/share transcript segments | J2, J4 | MVP | Yes (verify) |
| Slack pipeline alerts (severity levels) | J3, J3B, J9 | MVP | No -- KnowledgeOps/n8n |
| Auto-retry with escalating backoff | J3, J9 | MVP | No -- KnowledgeOps/n8n |
| Dead-letter queue with full metadata | J3, J10 | MVP | No -- KnowledgeOps |
| Skip/acknowledge/re-queue workflow | J3, J1B, J10 | MVP | No -- KnowledgeOps |
| Stale-channel alerting (3-week threshold) | J3B | MVP | No -- KnowledgeOps/n8n |
| RSS URL validation/update | J3B | MVP | No -- KnowledgeEnroll |
| Multi-user access (Authentik SSO) | J4, J6 | MVP | Yes |
| Tagging and bookmarking | J4 | MVP | Yes |
| First-login UX evaluation | J4 | Growth | Evaluate Speakr |
| Transcript export/download | J5 | MVP | Verify (Obsidian export exists) |
| Search with channel filtering | J5 | MVP/Growth | Verify |
| Status report workflow (Slack digest) | J8 | MVP | No -- KnowledgeOps/n8n |
| Utilization metrics (processing time) | J8 | MVP | No -- KnowledgeOps/n8n |
| Alert acknowledgment + recovery notifications | J9 | MVP | No -- KnowledgeOps/n8n |
| Error pattern visibility | J10 | MVP | No -- KnowledgeOps |
| n8n workflow parameter configuration | J10 | MVP | No -- n8n native |
| Disk usage alerts (Banner + NAS) | J11 | MVP | No -- KnowledgeOps |
| Grafana dashboards (Coulson) | J11 | Growth | No -- KnowledgeOps |
| KnowledgeGraduate REST API | J5, J7 | Growth/Vision | No -- KnowledgeGraduate |
| Curator role + self-service channel add | J6 | Growth | No -- KnowledgeEnroll |
| MCP server for AI tool integration | J7 | Vision | No -- KnowledgeGraduate |
| Capacity planning metrics | J11 | Growth | No -- KnowledgeOps |
| Guest-monitor ingestion mode | J1 | MVP-2 | No -- KnowledgeEnroll |
| Personality watchlist (CRUD) | J1 | MVP-2 | No -- KnowledgeEnroll |
| Guest-match confidence scoring | J1 | MVP-2 | No -- KnowledgeEnroll |
| Guest Monitor suggestion queue | J1 | MVP-2 | No -- KnowledgeEnroll |
| Content review queue (manual/hybrid channels) | J1, J1B | MVP-1 | No -- KnowledgeEnroll |
| Unified review feed (all selective channels) | J1 | MVP-1 | No -- KnowledgeEnroll |
| Last-reviewed timestamp tracking | J1 | MVP-1 | No -- KnowledgeEnroll |
| Bulk select/skip from review queue | J1 | MVP-1 | No -- KnowledgeEnroll |

## Web Application Specific Requirements

### Project-Type Overview

KnowledgeStack is classified as a web application but operates as a 5-product backend-heavy platform. The user-facing web interface is provided entirely by Speakr (adopted, unmodified). Custom development focuses on backend pipelines (n8n), operational tooling (Slack), and API layers. Traditional web app concerns (browser matrix, responsive design, SEO) are delegated to Speakr.

### Browser Matrix

- Primary interface: Speakr (Vue.js 3 SPA) -- browser support inherited from upstream
- Target: Modern evergreen browsers (Chrome, Firefox, Safari, Edge)
- No IE11 or legacy browser support required
- Internal tool with <10 users in MVP -- browser testing scope is minimal

### Responsive Design

- Delegated to Speakr. No custom responsive work in MVP.
- Admin/Ops interface is Slack (inherently responsive)

### Performance Targets

See **Non-Functional Requirements > Performance** (NFR-P1 through NFR-P9) for all measurable performance targets across KnowledgeEnroll, KnowledgeLecture, KnowledgeOps, and KnowledgeGraduate.

### SEO Strategy

Not applicable. Internal tool, no public-facing content.

### Accessibility

- KnowledgeLecture (Speakr): Inherit upstream accessibility — no custom modifications
- Custom web interfaces (KnowledgeEnroll, KnowledgeCollege, KnowledgeGraduate, KnowledgeOps): WCAG 2.1 AA compliance via Sunflower UI (Growth phase). See NFR-A1 through NFR-A4.

### Implementation Considerations

- No custom web frontend in MVP -- all user interaction through Speakr or Slack
- Growth phase may introduce KnowledgeEnroll admin UI (channel management web interface)
- Vision phase may introduce KnowledgeOps admin portal
- KnowledgeLecture (Tier 2) uses Speakr's native Vue.js 3 interface unmodified
- All custom web interfaces for Tiers 1, 3, 4, and KnowledgeOps use Sunflower UI (NLF custom UI kit) — NOT Speakr's Vue.js 3 stack

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP in two stages. MVP-1 proves the pipeline works and transcripts are trustworthy. MVP-2 adds the intelligence layer and API access that make the platform genuinely differentiated.

**Resource Model:** Solo developer (Matt) + AI assistants (Claude Code). Speakr adoption eliminated ~1 year of UI/auth/search work. n8n reduces custom backend code. This is the key resource mitigation.

### MVP-1: Pipeline + Repository + Ops

**Gate:** 500+ recordings ingested, pipeline autonomous, search works, ops alerting functional

| Product | What Ships | Build vs Adopt |
|---------|-----------|---------------|
| **KnowledgeEnroll** | Channel mgmt, bulk import, RSS monitoring, backlog loader, dedup, retry/DLQ | Build (n8n workflows) |
| **KnowledgeLecture** | Search, chat, tags, transcripts, multi-user, SSO | Adopt (Speakr) |
| **KnowledgeOps** | Slack alerts, status digests, stale-channel alerts, disk monitoring, DLQ mgmt, dependency update monitor | Build (n8n + Slack) |

**Core Journeys:** J1, J1B, J2, J3, J3B, J4, J5 (manual), J8, J9, J10

### MVP-2: Intelligence + Access

**Gate:** Semantic search demonstrably better than Speakr alone; at least one downstream consumer (OpenClaw or Claude Code) successfully querying via API

| Product | What Ships | Build vs Adopt |
|---------|-----------|---------------|
| **KnowledgeCollege** | Qdrant vector store, embedding pipeline, semantic search, basic enrichment | Build (Qdrant + LiteLLM) |
| **KnowledgeGraduate** (basic) | REST API exposing search + transcript retrieval for downstream tools | Build (Express/Flask) |

**Enables:** J2 dead-end recovery solved (synonym/semantic matching), J5 full (API-based export), J7 partial (REST access)

### Growth (Post-MVP-2)

Growth specifics will sharpen as MVP-1 and MVP-2 teach us what matters. Current candidates:

- Grafana dashboards on Coulson (pipeline health, utilization trends)
- Admin configuration UI (no more n8n parameter editing)
- Curator role + self-service channel addition (J6)
- Capacity planning metrics (J11)
- Channel coverage scoring (% ingested, % enriched)
- AI pipeline monitoring (Langfuse/LangSmith for LLM quality)
- Correlation IDs for end-to-end pipeline tracing
- Data integrity audits (orphan detection, dedup verification)
- First-login UX evaluation for Speakr

### Vision

- MCP server (upgrades KnowledgeGraduate from REST-only to MCP+REST -- J7 full)
- Expert Authority Profiles (trust scoring, expertise mapping, conflict detection)
- Admin portal (zero-SSH operations)
- Cross-reference verification (fact-checking across experts)
- Daily micro-digest (AI-generated summaries)
- User preference profiling (personalized recommendations)
- LobeChat integration (cross-corpus AI chat)

### Dependency Update Management (KnowledgeOps)

**Pattern:** Automated release monitoring with LLM-assisted analysis

| Dependency | Monitor Method | Analysis |
|-----------|---------------|----------|
| Speakr | GitHub releases (RSS/API) | Jarvis LLM summarizes impact on our usage (API, search, chat, SSO, export) |
| n8n | GitHub releases | Jarvis LLM flags breaking workflow changes |
| Qdrant | GitHub releases (MVP-2+) | Jarvis LLM flags API changes |

**Workflow:** Release detected -> fetch notes -> LLM summary -> Slack post -> Matt decides (update/skip/investigate)

**Scope:** MVP-1 for Speakr + n8n. Expand as products come online.

### Risk Mitigation Strategy

| Risk | Type | Impact | Mitigation |
|------|------|--------|-----------|
| Speakr API limitations (upload size, timeout) | Technical | Medium | DLQ handles edge cases; document limits during architecture |
| Speakr upstream breaking changes | Dependency | Medium | LLM-monitored releases; review before update; Docker image versioning |
| WhisperX GPU availability (Jarvis single GPU) | Technical | High | Fallback = OpenAI Whisper API for burst/backup |
| YouTube API rate limits | Technical | Medium | Backoff designed; spread ingestion across day |
| Solo developer bandwidth | Resource | High | Speakr adoption + n8n reduce build scope dramatically |
| RSS feed reliability | Technical | Medium | Stale-channel alerts catch silent failures (J3B) |
| Qdrant learning curve (MVP-2) | Technical | Low | Well-documented; research already completed |

## Functional Requirements

**Total: 177 FRs** — 85 MVP-1 | 29 MVP-2 | 32 Growth | 21 Vision | 10 Vision+

**Product Suite (Education-Themed Naming — Party Mode Decision):**

| Product | Tier | Purpose | Future Sub-Products |
|---------|------|---------|-------------------|
| **KnowledgeEnroll** | 1 | Ingestion pipeline (n8n, RSS, dedup, metadata, channel management) | VideoEnroll, TextEnroll, WebEnroll, SocialEnroll |
| **KnowledgeLecture** | 2 | Transcript repository (Speakr — search, chat, tags, playback) | — |
| **KnowledgeCollege** | 3 | Intelligence layer (Qdrant, enrichment, semantic search, entity graphs) | — |
| **KnowledgeGraduate** | 4 | API + integrations (REST, MCP, LobeChat, downstream apps) | — |
| **KnowledgeOps** | Cross-cutting | System management, monitoring, alerting, admin experience | — |

**Channel Scoring Model (Party Mode Decision):**
Multi-dimensional scoring replaces named tiers. Authority (1-10) × Relevance (1-10) drives composite priority, ingestion mode, and backlog depth. Cadence is system-observed, not curator-rated.

### Source Management (KnowledgeEnroll)

- **FR1** [MVP-1]: Admin can add individual YouTube channels by URL
- **FR2** [MVP-1]: Admin can bulk import channels via CSV upload (URL + scores + preferences)
- **FR3** [MVP-1]: Admin can create, view, update, and remove Authority scores (1-10) per channel
- **FR4** [MVP-1]: Admin can create, view, update, and remove Relevance scores (1-10) per channel
- **FR5** [MVP-1]: Admin can create, view, update, and remove per-channel ingestion mode (auto-ingest all, manual approval, hybrid, guest-monitor [MVP-2])
- **FR6** [MVP-1]: Admin can create, view, update, and remove per-channel backlog depth settings (full history, time-bounded, count-bounded)
- **FR7** [MVP-1]: Admin can set, update, and clear hiatus status per channel
- **FR8** [MVP-1]: Admin can create, view, update, and remove keyword filters per channel
- **FR9** [MVP-1]: Admin can create, view, update, and remove length preferences (min/max duration) per channel
- **FR10** [MVP-1]: Admin can create, view, update, and remove format preferences (shorts, standard, livestream) per channel
- **FR11** [MVP-1]: System derives composite priority score from Authority × Relevance ratings
- **FR12** [MVP-1]: System derives ingestion mode and backlog depth recommendations from composite priority
- **FR13** [MVP-1]: Admin can view and update channel RSS feed URLs
- **FR14** [MVP-1]: Admin can deactivate or remove channels from monitoring

### Content Ingestion Pipeline (KnowledgeEnroll)

- **FR15** [MVP-1]: System monitors RSS feeds for new content from all enrolled channels
- **FR16** [MVP-1]: System automatically downloads and submits new content to KnowledgeLecture (Speakr)
- **FR17** [MVP-1]: System prevents duplicate ingestion via YouTube video ID matching — if a video ID already exists in pipeline records, skip it
- **FR17B** [Growth]: System extends deduplication with additional layers (URL normalization, content fingerprinting, status-aware routing, pre-upload Speakr check) for edge case coverage (re-uploaded content, renamed channels, cross-posted videos). Architecture phase to evaluate existing dedup tools/libraries before building custom.
- **FR18** [MVP-1]: System captures YouTube API metadata at ingestion (title, description, channel, publish date, duration, tags)
- **FR19** [MVP-1]: System processes backlog content in priority order (highest composite score first)
- **FR20** [MVP-1]: System auto-retries ingestions that fail with transient errors (rate limits, timeouts, network) using escalating backoff (30min → 1hr → 2hr, 3 attempts max)
- **FR21** [MVP-1]: System routes non-transient failures (oversized, private, deleted, unsupported) directly to the failed items queue with no auto-retry
- **FR22** [MVP-1]: System routes exhausted-retry items (3 transient failures) to the failed items queue with full metadata

### Content Repository (KnowledgeLecture — Speakr)

- **FR23** [MVP-1]: Users can search across all transcripts with keyword queries
- **FR24** [MVP-1]: Users can view transcripts with synchronized timestamps and playback
- **FR25** [MVP-1]: Users can use per-recording RAG chat to ask questions about individual recordings
- **FR26** [MVP-1]: Users can tag and bookmark recordings
- **FR27** [MVP-1]: Users can export transcripts (Speakr Obsidian/Logseq export — verify capability)
- **FR28** [MVP-1]: Users can browse the recording library by channel, date, or tags
- **FR29** [MVP-1]: System provides speaker diarization for multi-speaker content (WhisperX)

### Content Intelligence (KnowledgeCollege)

- **FR30** [MVP-2]: System embeds transcript content into Qdrant vector store for semantic search
- **FR31** [MVP-2]: Users can perform semantic search with synonym and concept matching
- **FR32** [Growth]: System enriches recordings with entity extraction — speakers, topics, organizations
- **FR33** [Growth]: System maintains hierarchical tag taxonomy (domain > category > topic)
- **FR34** [Growth]: System performs automated channel classification and tier recommendations

### Content Distribution (KnowledgeGraduate)

- **FR35** [MVP-2]: External applications can query the knowledge repository via REST API
- **FR36** [MVP-2]: External applications can retrieve transcript segments with metadata via API
- **FR37** [Vision]: AI tools can access the repository via MCP server
- **FR38** [Vision]: LobeChat can perform cross-corpus AI chat over the full repository

### Pipeline Operations (KnowledgeOps)

- **FR39** [MVP-1]: System sends Slack alerts on pipeline failures with severity levels (red/yellow/green)
- **FR40** [MVP-1]: System sends stale-channel alerts when channels exceed 3x their observed average posting frequency (e.g., daily poster flagged after 3 days silent, weekly poster after 3 weeks, monthly poster after 3 months). Cadence is derived from FR45 observed data.
- **FR41** [MVP-1]: System posts formatted status digests to Slack (daily/weekly configurable)
- **FR42** [MVP-1]: Curators can review failed items queue via Slack notifications and n8n workflow triggers
- **FR43** [MVP-1]: Curators can acknowledge, skip, or re-trigger failed items
- **FR44** [MVP-1]: System monitors disk usage on Banner and NAS mount health
- **FR45** [MVP-1]: System observes channel publishing cadence automatically (detected from RSS feed activity)
- **FR46** [MVP-1]: System sends recovery notifications when auto-retried items succeed

### System Administration (KnowledgeOps)

- **FR47** [MVP-1]: System supports multi-user access via Authentik SSO/OIDC (Speakr provides)
- **FR48** [MVP-1]: Admin can view per-channel status (last ingestion, expected cadence, flag status)
- **FR49** [MVP-1]: Admin can configure n8n workflow parameters for pipeline tuning
- **FR50** [MVP-1]: System provides structured logging to Loki (Coulson)
- **FR51** [MVP-1]: Admin can view backlog progress (processed/total, per-tier completion, estimated rate)

### Dependency & Ecosystem Management (KnowledgeOps)

- **FR52** [MVP-1]: System monitors dependency releases (Speakr, n8n, Qdrant) via GitHub RSS/API
- **FR53** [MVP-1]: System generates LLM-assisted impact summaries for dependency updates (Jarvis)
- **FR54** [MVP-1]: System posts dependency update notifications to Slack for admin review
- **FR55** [MVP-1]: System maintains Docker image versioning for rollback capability

### UI Standards

- **FR56** [Growth+]: All custom-developed web interfaces must use Sunflower UI (NLF custom UI kit). KnowledgeLecture/Speakr retains its native interface unmodified.

### Failed Items Management (KnowledgeOps)

- **FR57** [Growth]: Curators can manage the failed items queue via Sunflower UI admin page (browse, filter by error type, bulk re-trigger, bulk dismiss)

### Access Control & User Management

- **FR58** [MVP-1]: System defines three human roles: Admin (full application-level control — channel management, pipeline config, user management, system settings), Curator (channel management + failed queue + all viewer capabilities), Viewer (search, browse, chat, tag, bookmark — read-only). Three tiers of Service Account are introduced progressively: Consumer (read-only API access for downstream tools like Claude Code, LobeChat, OpenClaw — MVP-2), Curator API (channel add/manage via API — Growth), Admin API (bulk user management, system config via API — Growth).
- **FR59** [MVP-1]: Admin can create, view, update, and remove user accounts and role assignments
- **FR60** [MVP-1]: System enforces role-based permissions on all operations (Speakr OIDC + Authentik)
- **FR61** [MVP-2]: Admin can create API keys for external service access to KnowledgeGraduate
- **FR62** [MVP-2]: Admin can revoke API keys
- **FR63** [MVP-2]: Admin can view API key usage and activity
- **FR64** [MVP-2]: API keys are scoped by service account tier — Consumer keys (read-only search and retrieval, MVP-2), Curator API keys (channel management + consumer capabilities, Growth), Admin API keys (bulk user management + system config + all capabilities, Growth)

### User Profile & Settings

- **FR65** [MVP-1]: Users can view and update their profile (display name, email, avatar — synced from Authentik SSO)
- **FR66** [MVP-1]: Users can manage personal settings (notification preferences, default display options, timezone)
- **FR67** [Vision]: System supports extended user profiles with preference modeling, topic interests, and personality-matched content routing

### Pipeline Stage Monitoring (KnowledgeOps)

- **FR68** [MVP-1]: System tracks pipeline stage for each item (RSS poll → metadata fetch → download → upload → Speakr processing → complete)
- **FR69** [MVP-1]: System performs post-upload verification by polling Speakr API to confirm successful transcription after handoff
- **FR70** [MVP-1]: System alerts when items are stuck in "uploaded but not processed" state beyond a configurable threshold
- **FR71** [MVP-1]: System performs periodic Speakr health checks (API responsiveness, WhisperX/Jarvis availability)
- **FR72** [MVP-1]: System logs and categorizes failures by pipeline stage, enabling pattern detection (e.g., "all Stage 4 failures = Speakr is down" vs "one Stage 2 failure = video is private")
- **FR73** [MVP-1]: System queues items that fail at the Speakr handoff (Stage 4) separately from items that fail at earlier stages, enabling targeted re-trigger when Speakr recovers

### API Documentation

- **FR74** [MVP-2]: KnowledgeGraduate REST API provides interactive Swagger/OpenAPI documentation page with all endpoints, parameters, and response schemas
- **FR75** [Growth]: System provides user-facing documentation and guide covering Curator and Viewer workflows

### Storage Management

- **FR76** [MVP-1]: System downloads audio in optimized format/bitrate (audio-only, compressed — specific format determined during architecture based on Speakr requirements)
- **FR77** [MVP-1]: System provides storage utilization monitoring with configurable alert thresholds on NAS and Banner (e.g., 70%, 85%, 95%)
- **FR78** [Growth]: System provides storage trending and capacity projection (estimated months remaining at current ingestion rate)
- **FR79** [Growth]: System tracks last-accessed date for each audio file
- **FR80** [Growth]: System automatically archives (compress + move to cold storage) audio files not accessed within a configurable threshold (e.g., 6 months)
- **FR81** [Growth]: System automatically deletes archived audio files after a second configurable threshold (e.g., 12 months since last access) unless flagged for retention
- **FR82** [Growth]: System re-downloads audio on demand when a user requests playback of a deleted recording (transparent re-pull from YouTube with progress indicator)

### Usage Analytics

- **FR83** [MVP-1]: System logs user activity events (searches, recording opens, chat queries, exports) as structured events with user ID and timestamp
- **FR84** [MVP-1]: System logs audio playback events (recording ID, start/stop timestamps, segments played)
- **FR85** [Growth]: Admin can view per-user and aggregate usage analytics (most-searched topics, most-accessed recordings, most-active channels)
- **FR86** [Growth]: System provides usage dashboards via Grafana (Coulson) showing content engagement patterns
- **FR87** [Vision]: Recommendation engine consumes usage history to generate personalized content suggestions
- **FR88** [Growth]: System tracks client-side user behavior (time-on-page, scroll depth, segment engagement) via self-hosted analytics or lightweight event tracking integrated into KnowledgeLecture
- **FR89** [Vision]: System builds per-user interest profiles from combined backend activity logs and client-side behavior data to power content recommendations

### Backup & Recovery

- **FR90** [MVP-1]: System performs automated scheduled backups of all KnowledgeStack data stores (PostgreSQL, channel configurations, n8n workflow exports) coordinated with NLF Standards backup infrastructure
- **FR91** [MVP-1]: Admin can perform on-demand backup of any individual data store
- **FR92** [MVP-1]: Admin can restore KnowledgeStack to a known good state from backups (documented recovery procedure)
- **FR93** [MVP-2]: System includes Qdrant vector store in backup/restore procedures

### Bulk Export & Portability

- **FR94** [MVP-1]: Admin can bulk export all channel configurations, scoring data, and enrollment settings in a portable format (JSON/CSV)
- **FR95** [Growth]: Admin can bulk export the full recording catalog with transcripts and metadata in a portable, Speakr-independent format
- **FR96** [Growth]: Admin can import previously exported data into a fresh KnowledgeStack instance (migration path)

### Visual Identification & Preview

- **FR97** [MVP-1]: System captures and stores video thumbnail URL at ingestion alongside other YouTube API metadata
- **FR98** [MVP-1]: System displays video thumbnails in recording listings and search results (KnowledgeLecture — verify Speakr capability, supplement if needed)
- **FR99** [MVP-1]: System provides YouTube embed player preview (modal) allowing users to scan/preview the original video from within the interface

### Content Metadata Freshness

- **FR100** [Growth]: System performs periodic metadata refresh for ingested recordings (title, description, thumbnail) to detect upstream changes on YouTube

### Channel Discovery

- **FR101** [Vision]: System suggests related channels based on enrolled channel metadata and user preference profiles (MVP+10)

### Pre-Ingestion Intelligence

- **FR102** [MVP-1]: System performs AI-assisted pre-ingestion analysis of video descriptions to extract candidate guest speakers and key topics using local LLM (Jarvis)
- **FR103** [MVP-1]: System displays AI-extracted guest names and topic hints alongside thumbnails and titles in channel video listings and backlog review screens
- **FR104** [Growth]: Post-ingestion entity enrichment (FR32) validates and refines pre-ingestion guest/topic hints with authoritative data from actual transcripts

### Guest Monitor Channels (KnowledgeEnroll)

- **FR164** [MVP-2]: Admin can designate channels with "guest-monitor" ingestion mode — system monitors RSS feed but does not auto-ingest; instead applies AI pre-screening to identify content featuring tracked personalities or matching configured domain topics
- **FR165** [MVP-2]: Admin can create and manage a personality watchlist — a list of named individuals to track for guest appearances across guest-monitor channels (separate from enrolled channel hosts)
- **FR166** [MVP-2]: System cross-references Guest Monitor channel video descriptions against both the personality watchlist and configured domain/topic keywords using pre-ingestion AI analysis (FR102)
- **FR167** [MVP-2]: System scores guest-match confidence per video: name in title = high, name in description = medium, topic-keyword match only = low
- **FR168** [MVP-2]: System surfaces matched Guest Monitor videos in a suggestion queue for admin review — not auto-ingested regardless of confidence score
- **FR169** [MVP-2]: Admin can configure minimum confidence threshold per Guest Monitor channel to control suggestion volume

### Content Review Queue (KnowledgeEnroll)

- **FR170** [MVP-1]: System maintains a review queue for all channels with non-auto ingestion modes (manual, hybrid), showing all published videos not yet ingested or explicitly skipped
- **FR171** [MVP-1]: System tracks "last reviewed" timestamp per channel, updated when admin completes a review session (selects or skips items)
- **FR172** [MVP-1]: Review queue shows content since last review or 30 days, whichever window is longer
- **FR173** [MVP-1]: Admin can view review queue per-channel (focused review of one channel's pending content)
- **FR174** [MVP-1]: Admin can view unified review feed across all selective channels, sorted by publish date
- **FR175** [MVP-1]: Admin can bulk-select videos from review queue for ingestion or mark as "skipped" (skipped items leave the active queue but remain accessible via "show skipped" filter)
- **FR176** [MVP-1]: Review queue displays video thumbnails (FR97), YouTube descriptions (FR117), and AI-extracted guest/topic hints (FR103) to support informed decisions
- **FR177** [MVP-2]: Review queue for Guest Monitor channels additionally displays AI confidence scores and matched personality/topic names

### KnowledgeGraduate API Rate Limiting & Monitoring

- **FR105** [MVP-2]: KnowledgeGraduate API enforces rate limiting per API key (configurable thresholds)
- **FR106** [MVP-2]: System monitors and logs all API calls to KnowledgeGraduate (caller, endpoint, response time, status code)
- **FR107** [MVP-2]: Admin can view API usage dashboards showing call volume, top consumers, error rates, and latency

### User Activity

- **FR108** [MVP-1]: Users can view their own search history and recent activity (recordings opened, searches performed)

### Database & Configuration Management

- **FR109** [MVP-1]: System uses a database migration framework for all schema changes (versioned, reversible migrations)
- **FR110** [MVP-1]: System includes integration tests that validate compatibility with Speakr API and n8n workflow interfaces after dependency updates
- **FR111** [MVP-1]: Dependency update procedure includes running integration test suite before promoting to production
- **FR112** [MVP-1]: Pipeline is safe to re-process any previously ingested item without creating duplicates or side effects — running the same video through twice produces the same result or simply skips (safe-to-run-twice by design, verifiable by test)
- **FR113** [MVP-1]: System maintains centralized configuration registry documenting all cross-service settings (API URLs, ports, credentials, feature flags) across all hosts
- **FR114** [MVP-1]: System validates cross-service configuration on startup and alerts on mismatches

### Bulk Curator Operations

- **FR115** [Growth]: Curators can perform bulk operations on channels (pause/resume all, update scores by domain, set backlog depth in batch)

### Onboarding

- **FR116** [Growth]: System provides a guided first-login experience for new Viewers (MVP+3+)

### Search Results Enhancement

- **FR117** [MVP-1]: Search results display the YouTube video description as context preview alongside title and thumbnail

### Relevance Scoring

- **FR118** [Vision]: System generates per-user relevance scores for recordings based on AI-extracted topics matched against the user's interest profile
- **FR119** [Vision]: System displays relevance scores to users in search results, browse listings, and content recommendations to aid discovery and prioritization

### Library → College Sync Pipeline

- **FR120** [MVP-2]: System automatically embeds new recordings into Qdrant when ingested into KnowledgeLecture (event-driven or scheduled sync)
- **FR121** [MVP-2]: System chunks transcripts using hybrid strategy (chapters → semantic → sub-chunk) before embedding
- **FR122** [MVP-2]: Admin can view College indexing status (total embedded vs total in Library, pending queue, sync health)

### KnowledgeGraduate API Completeness

- **FR123** [MVP-2]: KnowledgeGraduate API supports filtered queries (by channel, date range, domain, entity, topic)
- **FR124** [MVP-2]: KnowledgeGraduate API supports paginated responses with configurable page size
- **FR125** [MVP-2]: KnowledgeGraduate API returns standardized error responses with error codes and descriptive messages
- **FR126** [MVP-2]: KnowledgeGraduate API supports versioning to maintain backward compatibility across releases

### Cross-Product Navigation

- **FR127** [MVP-2]: College search results link directly to the corresponding recording in Library for transcript view and playback

### Search Quality

- **FR128** [Growth]: System provides a mechanism to evaluate semantic search quality against baseline keyword search results (test query set with expected results) — aspirational, not a hard gate

### Long-Term Operations

- **FR129** [Growth]: System enforces configurable data retention policies for logs, usage analytics, and pipeline history (TTL-based archival and purge)
- **FR130** [Growth]: System maintains an audit trail for all state-changing operations (actor, timestamp, action, before/after values)
- **FR131** [Growth]: System performs periodic disaster recovery validation by restoring backups to a test environment
- **FR132** [Growth]: System tracks and reports operational resource consumption (LLM API calls, GPU hours, storage growth, compute utilization)
- **FR133** [Growth]: System automates database maintenance tasks (VACUUM, ANALYZE, index optimization) on schedule
- **FR134** [Growth]: System supports secret rotation for all credentials and API keys without service downtime
- **FR135** [Growth]: System maintains operational runbooks for common failure scenarios and recovery procedures
- **FR136** [Growth]: System performs periodic data quality audits (orphaned records, missing metadata, cross-store consistency)
- **FR137** [Growth]: System supports feature flags for incremental capability rollout and per-user feature gating
- **FR138** [Growth]: Admin can offboard users with configurable data handling (retain channels, revoke API keys, reassign ownership)
- **FR139** [Vision]: System tracks content provenance and licensing metadata for compliance reporting
- **FR140** [Vision]: System provides longitudinal channel health analytics (quality trends, frequency trends, relevance drift)
- **FR141** [Vision]: System runs continuous canary tests validating search quality, transcription accuracy, and enrichment quality against baseline metrics

### User Engagement & Recommendations

- **FR142** [Vision]: System detects declining user engagement with enrolled channels and prompts users to confirm continued interest
- **FR143** [Growth]: Users can view a personal knowledge dashboard showing their top domains, most-consulted experts, topic distribution, and engagement trends over time
- **FR144** [Growth]: System generates periodic personal knowledge summaries (monthly/quarterly/annual "Knowledge Wrapped" style reports) highlighting learning patterns, new discoveries, and interest shifts
- **FR145** [Vision]: KnowledgeGraduate API exposes topic coverage analysis endpoints enabling downstream tools to identify knowledge blind spots and recommend underexplored domains
- **FR146** [Vision]: System tracks interest drift over time and visualizes how user focus areas evolve across quarters

### API User Attribution

- **FR147** [MVP-2]: KnowledgeGraduate API requires end-user identification parameter for analytics-eligible endpoints and supports it as optional for basic query endpoints
- **FR148** [Growth]: Usage analytics dashboards include API-sourced activity alongside direct platform usage, giving users a unified view of their knowledge consumption across all access methods

### Personalized Digests

- **FR149** [Vision]: System generates personalized periodic email digests per user (configurable: weekly/biweekly) summarizing most-accessed content, trending topics, and recommended content they haven't engaged with

### Cross-Channel Intelligence

- **FR150** [Growth]: System tracks entity appearances across channels (same guest on multiple enrolled channels) and surfaces cross-channel connections in browse and search results

### Content Availability Tracking

- **FR151** [MVP-1]: System categorizes content access failures by type (bad URL, private, deleted, unlisted, age-restricted, geo-blocked) and stores the specific failure reason with the DLQ entry
- **FR152** [MVP-1]: System flags previously accessible content that becomes unavailable after successful ingestion (status change detection on periodic metadata checks)

### Smart Content Recommendations

- **FR153** [Vision]: When multiple recordings cover the same topic across channels, system recommends the shortest/most-concentrated version first with a "deep dive available" link to longer alternatives

### Failure Pattern Learning

- **FR154** [Growth]: System accumulates structured failure data (error type, stage, time, channel, resolution) to enable pattern analysis and pipeline optimization over time

### Audio Integrity

- **FR155** [MVP-1]: System validates audio file integrity after download (file size check, format validation, duration match against YouTube API metadata) before submitting to KnowledgeLecture

### Dependency Version Tracking

- **FR156** [MVP-1]: System tracks installed versions of all dependencies (Speakr, WhisperX, n8n, Qdrant, LiteLLM, yt-dlp) and displays current versions on an ops dashboard
- **FR157** [Growth]: System performs automated cross-system integration tests after any dependency update and reports pass/fail before promoting to production

### Self-Healing Configuration

- **FR158** [Growth]: System attempts auto-discovery of new RSS feed URLs when channels appear rebranded or relocated, proposing fixes for admin approval rather than just alerting

### Personality-Driven Discovery (KnowledgeEnroll)

- **FR159** [Vision]: Building on the personality watchlist (FR165), system extends tracking beyond enrolled channels — users can flag additional personalities for broad YouTube discovery (not limited to guest-monitor channels)
- **FR160** [Vision]: System periodically searches YouTube Data API for recent videos featuring watchlisted personalities (FR165) on un-enrolled channels, using title and description matching
- **FR161** [Vision]: System scores each discovery result by guest-appearance confidence (e.g., "[Name] interview" in title = high; name mentioned in description only = low)
- **FR162** [Vision]: System filters out results from already-enrolled channels to surface only new discovery opportunities
- **FR163** [Vision]: System presents a discovery feed where users can one-off ingest a specific video or enroll the source channel

### Post-MVP Enhancement Trajectory (Scoring Model & Filtering)

| Phase | Enhancement |
|-------|-------------|
| **MVP-1** | Authority × Relevance (curator-rated), optional positive keyword filters, length/format preferences, content review queue for manual/hybrid channels |
| **MVP-2** | Guest Monitor channel type: AI-screened ingestion suggestions based on personality watchlist + domain topic matching, confidence scoring |
| **Growth** | Negative keyword filters for short-form content at source level (topic exclusion works cleanly on clips with clear topic boundaries) |
| **MVP+3** | Inferred relationship metrics: host/guest ratio, format distribution, per-channel topic strengths |
| **MVP+8** | Keyword filters evolve to semantic tag/concept matching with synonym support (ties into KnowledgeCollege tag taxonomy) |
| **MVP+10-15** | Cross-referencing shorts with marathon episodes for quality signal (creator-curated highlights as value indicators) |
| **Vision** | Per-segment topic filtering within long-form episodes (include relevant segments, skip irrelevant — requires segment-level topic classification) |
| **Vision** | Per-entity topic authority scores (e.g., "this person is strong on finance, weak on politics") |
| **Future** | SocialEnroll sub-product (Twitter/X, Facebook, Instagram content ingestion) |

### Architecture Notes (Carry Forward)

- Deploy Speakr on Banner with 2-3 manually uploaded test files as FIRST implementation task (Epic 0/Sprint 0)
- ARCHITECTURE GATE: Resolve all "verify" annotations in FRs (FR27, FR98, and others) — determine definitively whether Speakr provides the capability or we build it
- ARCHITECTURE GATE: Evaluate existing dedup tools/libraries before building custom multi-layer dedup (FR17B)
- Verify Speakr capabilities during architecture: transcript export, search filtering, segment copy/share, landing page UX, thumbnail display
- Web App Requirements section guidance change: custom web components use Sunflower UI (NLF custom UI kit), NOT Speakr's Vue.js 3 stack
- "Expert" is a RESERVED term for future authority profiles feature — not a product name
- "Forge" and "Foundry" are OFF LIMITS — used elsewhere in NLF business

### Moonshot Ideas (Captured for Future Reference)

**Core Platform (Growth/Vision):**
- ~~Personality Watchlist Discovery~~: **PROMOTED** — Core concept split into Guest Monitor Channels (FR164-169, MVP-2) for enrolled channel monitoring and Personality-Driven Discovery (FR159-163, Vision) for broad YouTube search. Content Review Queue (FR170-177) provides the operational backfill review workflow.
- Smart Backlog Prioritizer: system analyzes descriptions to fill topic gaps in repository
- Channel Cross-Pollination Score: detect same guest across channels, surface connections
- Dead Content Early Warning: detect declining video availability before content disappears
- Cost-Per-Recording Tracker: instrument pipeline for per-recording resource cost
- Canary Content Validation: periodic re-transcription of known recording to detect quality drift
- Self-Healing Channel Config: auto-discover new RSS URLs when channels rebrand
- Smart Retry Learning: learn from failure patterns to optimize retry scheduling
- Seasonal Ingestion Optimizer: pre-allocate capacity based on historical posting patterns

**Multi-Tenancy / Collaboration (Future):**
- Group Content Scoping: Support user groups where certain enrolled content is visible only to group members. Group admins can manage membership and content visibility. Enables team-specific knowledge libraries within the shared platform.

**AIKBase / NextLevel Apps Layer (Future):**
- Expert Debate Simulator: generate synthetic debates between experts using their actual positions
- Prediction Tracker: parse, tag, and score expert predictions over time
- Knowledge Time Machine: show how expert consensus shifted over time on any topic
- Auto-Generated Course Builder: sequence best segments across experts into structured courses
- Contradiction Detector: flag when experts directly contradict each other
- Consensus/Contrarian Scoring: rate personalities on alignment with broader expert community

## Non-Functional Requirements

**Total: 58 NFRs** across 9 categories. Only categories relevant to KnowledgeStack are included.

### Performance

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-P1 | End-to-end ingestion latency (RSS detect → searchable in Speakr) | <2 hours | MVP-1 | Core pipeline SLA |
| NFR-P2 | Backlog processing throughput | ~100 videos/day sustained | MVP-1 | Historical loading rate |
| NFR-P3 | WhisperX transcription speed (Jarvis) | <0.5x real-time (1-hour video < 30 min) | MVP-1 | GPU utilization efficiency |
| NFR-P4 | Slack alert delivery from error detection | <5 minutes | MVP-1 | Operational responsiveness |
| NFR-P5 | Status digest generation | <30 seconds for full system report | MVP-1 | Admin experience |
| NFR-P6 | Speakr search response time | <2s (monitor, don't control) | MVP-1 | Dependency we track |
| NFR-P7 | Speakr RAG chat response time | <5s (monitor, don't control) | MVP-1 | Dependency we track |
| NFR-P8 | KnowledgeGraduate API response time (p95) | <500ms for search, <200ms for retrieval | MVP-2 | API consumer experience |
| NFR-P9 | n8n workflow execution (single video pipeline, excluding transcription) | <15 minutes | MVP-1 | Pipeline efficiency |

### Security

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-S1 | Authentication | All user access via Authentik SSO/OIDC — no local passwords | MVP-1 | Single auth source |
| NFR-S2 | Network exposure | All services internal network only (10.0.0.x) — no public internet exposure except via Traefik reverse proxy with TLS | MVP-1 | Internal tool |
| NFR-S3 | API authentication | All KnowledgeGraduate API calls require valid API key | MVP-2 | Prevent unauthorized access |
| NFR-S4 | Secrets management | No credentials in source code, Docker images, or logs. All secrets via env files or Infisical | MVP-1 | Standard practice |
| NFR-S5 | AGPL compliance | Speakr used unmodified; if modified, source must be made available per AGPL-3.0 | MVP-1 | Legal requirement |
| NFR-S6 | Transport encryption | TLS for all external-facing endpoints (Traefik). Internal service-to-service: plaintext acceptable on trusted LAN | MVP-1 | Pragmatic for internal |
| NFR-S7 | Data at rest | PostgreSQL and NAS follow NLF Standards encryption policies | MVP-1 | Defer to existing standards |

### Scalability

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-SC1 | Repository capacity | Support 10,000+ recordings without performance degradation | Growth | 5K at 12-month, headroom beyond |
| NFR-SC2 | Channel capacity | Support 100+ monitored channels | Growth | ~50 MVP, room to double |
| NFR-SC3 | Concurrent users | Support 10 simultaneous users (Speakr + API) | MVP-2 | Inner circle + API consumers |
| NFR-SC4 | Storage growth | NAS supports 2TB+ audio storage | Growth | ~200MB/video avg × 10K recordings |
| NFR-SC5 | Pipeline parallelism | Process multiple channels concurrently without resource contention on Jarvis GPU — engineer conservatively at <50% estimated capacity | MVP-1 | Single GPU bottleneck management |
| NFR-SC6 | GPU utilization monitoring | Grafana dashboard on Coulson tracking Jarvis GPU utilization, processing queue depth, and throughput rates — enabling data-driven decisions on ingestion frequency, especially during backlog loading | MVP-2 | Tune pipeline speed with real data |

### Reliability

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-R1 | Pipeline uptime | >95% (auto-recovery) | MVP-1 | "Runs while I sleep" |
| NFR-R2 | Single-service recovery | <30 minutes from any single-service failure | MVP-1 | Docker restart + healthchecks |
| NFR-R3 | Data durability | Zero data loss for ingested recordings (PostgreSQL backups + NAS) | MVP-1 | Transcripts are expensive to recreate |
| NFR-R4 | Dedup accuracy | <1% false duplicates reaching Speakr | MVP-1 | Video ID dedup (MVP-1), multi-layer (Growth) |
| NFR-R5 | Pipeline failure rate | <5% per batch run | MVP-1 | Retries + DLQ handle the rest |
| NFR-R6 | Canary validation | Weekly canary channel ingests successfully every week | MVP-1 | High-signal health check |
| NFR-R7 | Graceful degradation | If WhisperX/Jarvis is down, pipeline queues items and resumes when available — no data loss | MVP-1 | GPU is single point of failure |

### Integration

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-I1 | Speakr API compatibility | Maintain compatibility with Speakr REST API; integration tests run before any Speakr upgrade | MVP-1 | Core dependency |
| NFR-I2 | n8n workflow portability | All workflows exportable/importable; no hardcoded secrets in workflow definitions | MVP-1 | Disaster recovery |
| NFR-I3 | YouTube API compliance | Respect rate limits and Terms of Service; no scraping | MVP-1 | Sustainability |
| NFR-I4 | Cross-host communication | System monitors cross-host latency and alerts if communication between the 5 hosts degrades beyond acceptable thresholds. Network infrastructure is a deployment prerequisite, not controlled by KnowledgeStack | MVP-1 | Monitor, don't control |
| NFR-I5 | Dependency isolation | Each service runs in isolated Docker container with explicit resource limits | MVP-1 | Prevent cascade failures |

### Accessibility

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-A1 | Speakr interface | Inherit upstream accessibility — no custom modifications | MVP-1 | Adopted as-is |
| NFR-A2 | Sunflower UI custom interfaces | WCAG 2.1 AA compliance for all custom-built web interfaces | Growth | Build right from the start |
| NFR-A3 | Keyboard navigation | All custom UI actions achievable via keyboard | Growth | Basic usability |
| NFR-A4 | Screen reader compatibility | Sunflower UI components include ARIA attributes and semantic HTML | Growth | Accessibility foundation |

### Maintainability

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-M1 | Deployment method | Docker Compose for all services; single-command deploy/update per host | MVP-1 | Solo dev operability |
| NFR-M2 | Configuration documentation | All cross-service settings documented in centralized registry (FR113) | MVP-1 | No tribal knowledge |
| NFR-M3 | Dependency update cycle | Review dependency updates within 1 week of release notification | MVP-1 | Stay current |
| NFR-M4 | Recovery documentation | Documented recovery procedure for every service — tested annually | MVP-1 | Bus factor = 1 |
| NFR-M5 | Code documentation | n8n workflows include inline comments explaining business logic | MVP-1 | Future-self readability |
| NFR-M6 | Log retention | Structured logs retained 90 days in Loki (Coulson) | MVP-1 | Troubleshooting window |

### Data Integrity

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-D1 | Safe-to-run-twice pipeline | Re-processing any item produces identical results with no side effects — running the same video twice either skips or produces the same outcome | MVP-1 | FR112 as NFR |
| NFR-D2 | Backup frequency | Daily automated backups of PostgreSQL; NAS snapshots per NLF Standards | MVP-1 | Recovery point objective |
| NFR-D3 | Backup verification | Monthly restore test to validate backup integrity | Growth | Trust but verify |
| NFR-D4 | Audio file validation | Every downloaded file passes integrity check before Speakr submission (FR155) | MVP-1 | Garbage in = garbage out |
| NFR-D5 | Cross-store consistency | Periodic audit verifying Speakr recording count matches pipeline records | Growth | Detect drift |

### Testing & Verification

| ID | Requirement | Target | Phase | Rationale |
|----|-------------|--------|-------|-----------|
| NFR-T1 | Deploy verification gate | Every deployable service exposes `GET /health` (200 OK) and `GET /version` (returns `{ commit, version, built }`). Post-deploy script compares commit SHA to expected before advancing to human review. | MVP-1 | Eliminates "not deployed" false-positive review cycles |
| NFR-T2 | 6-layer verification architecture | Verification layers: (1) container health, (2) service availability, (3) API contract integrity, (4) pipeline data integrity, (5) production smoke, (6) UI workflows. Playwright is layer 6 — never the first line of defense. | MVP-1 | Catches issues at the cheapest layer |
| NFR-T3 | Contract-first development | API boundaries between products define zod schemas before tests or implementation. Schemas shared between test and production code in `src/contracts/`. | MVP-1 | Prevents spec drift and test fragility |
| NFR-T4 | Red-green-fail verification | Phase 3 (tests writing) must verify tests actually fail before advancing to implementation. CI or local test run confirms red state. | MVP-1 | TDD discipline — prevents vacuously passing tests |
| NFR-T5 | Variant testing matrix | Custom web interfaces (KnowledgeEnroll, KnowledgeOps) tested across 3 viewports (mobile 375px, tablet 768px, desktop 1280px) × 2 color schemes (light, dark). Full matrix on critical user journeys only. | MVP-1 | Catch responsive/theme regressions without combinatorial explosion |
| NFR-T6 | Mutation testing | Stryker mutation testing run periodically on critical modules (dedup, pipeline state machine, contract validation) to verify test quality. Not every commit — scheduled or milestone gate. | Growth | Tests that pass mutations are not testing anything |
| NFR-T7 | Auto-reject on deploy failure | If deploy verification gate (NFR-T1) fails, issue is automatically returned to development phase with diagnostic details. No human review triggered. | MVP-1 | Matt's time is the greatest constraint — don't waste it on undeployed code |

---

## Spike Findings Addendum (2026-03-20)

> **Status:** Spike in progress. Findings inform Architecture phase decisions.

### Database Architecture Investigation

**Finding:** SurrealDB spike (in progress) shows promise for hybrid vector+graph model as alternative to Qdrant + separate graph store.

| Aspect | Original PRD (Qdrant) | Under Investigation (SurrealDB) |
|--------|----------------------|--------------------------------|
| Vector search | Qdrant HNSW | SurrealDB HNSW (1536 dim) |
| Graph queries | Separate PostgreSQL | Native graph traversal |
| Hybrid queries | Two databases, app-level join | Single query combining vector + graph + filters |
| Operational complexity | 2 databases | 1 database |

**Spike Status:**
- Vector search: Working (~30ms, 357 segments)
- Graph traversal: Working (<1ms)
- Hybrid queries: Working
- **Not yet tested:** Scale beyond 500 segments, production stability, backup/restore

**Impact on FRs:**
- FR30, FR93, FR120: Currently specify "Qdrant" — Architecture phase will evaluate SurrealDB as alternative
- No PRD changes yet — decision made during Architecture

### New Schema Concepts (Inform Architecture)

| Concept | Description | Source |
|---------|-------------|--------|
| **Speaker credibility per domain** | Speakers have different authority levels per topic. Myron Golden: TOP on business, LOW on tech. | Brainstorm FP #1 |
| **Visual trigger detection** | Segments containing "as you can see" flagged for lazy visual analysis | PRODUCT_VISION Use Case #26 |
| **Signature stories** | Stories told 5+ times across videos indicate core messages | PRODUCT_VISION Use Case #27 |
| **Denormalized segment fields** | `domain` and `published_at` stored on segments for hybrid query performance | Spike implementation |

### Schema Entities Validated

```
speaker              - Persona entity with aliases
speaker_credibility  - Per-domain tier (top/high/mid/low/none)
segment             - Now includes start_time, end_time, requires_visual, denormalized fields
visual_reference     - Lazy analysis queue for visual content
signature_story      - Repeated stories across videos
project              - Cross-project intelligence routing
```

### Timestamp Criticality (Strengthened)

**Original PRD:** Timestamps mentioned in journey maps (J2, J4).

**Spike Finding:** Timestamps were being discarded by YouTube transcript fetcher. Now preserved.

**Why Non-Negotiable:**
1. Visual Hub requires word/segment-level timestamps for text-to-video sync
2. Clip extraction needs precise start/end times
3. Citation references need exact source timestamps
4. Without timestamps, Use Cases 2.3-2.6 (chapters, highlights, clips) are impossible

**Action Taken:** `batch_transcript_fetcher.py` updated to preserve `start_time` and `duration` per segment.

### Guest Extraction (FR102-103 Validated)

Implementation working:
- Title patterns: "X with Y", "X ft. Y", "X | Y"
- Description patterns: "Guest: X", social handles
- Stored as Speaker → appears_in → Video relationships

### References

- [PRODUCT_VISION.md](./PRODUCT_VISION.md) - Full use case tiers with implementation status
- [RAG_DATABASE_SURVEY.md](../../spike/surreal-rag/docs/RAG_DATABASE_SURVEY.md) - Database evaluation
- [init.surql](../../spike/surreal-rag/schema/init.surql) - Enhanced schema v2
