---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/analysis/brainstorming-session-2026-01-29.md
  - _bmad-output/analysis/pre-alpha-findings.md
  - _bmad-output/pre-alpha-spike-prompt.md
  - _bmad-output/analysis/spike-handoff-report.md
  - docs/reference-youtube-channels.md
  - docs/research-user-preference-profiling-systems.md
  - _bmad-output/planning-artifacts/bmm-workflow-status.yaml
externalReferences:
  - name: Speakr
    url: https://github.com/murtaza-nasir/speakr
    role: Tier 2 transcript repository (adopted as foundation layer)
architecturePivot: Six-product platform with parallel data flow to Speakr (Lecture) and SurrealDB (College)
date: 2026-01-30
author: Matt
---

# Product Brief: KnowledgeStack

> [Updated 2026-03-31: spike learnings — renamed products, updated architecture, added spike outcomes]

## Executive Summary

KnowledgeStack is a self-hosted YouTube transcript ingestion and repository platform that automatically monitors, captures, and catalogs expert content from curated YouTube channels. KnowledgeStack is the engine that feeds downstream AI applications — spanning content management at the front, a searchable repository in the middle, and intelligence infrastructure at the back. Each tier serves a different audience: admins and curators manage ingestion, users explore transcripts, and downstream applications consume structured knowledge programmatically.

The system employs a six-product architecture: (1) **KnowledgeEnroll** — an n8n-based ingestion layer handling channel management, RSS monitoring, and selective content capture; (2) **KnowledgeLecture** — Speakr as the UI/listening layer providing transcript playback, search, tagging, and per-recording chat; (3) **KnowledgeCollege** — SurrealDB as the intelligence layer providing vector search, graph queries, and entity enrichment; (4) **KnowledgeGraduate** — curation and refinement of golden standard content; (5) **KnowledgeGateway** — REST API and MCP server for downstream tool access; and (6) **KnowledgeOps** — pipeline monitoring, admin UI, and operational visibility.

**Spike outcome (2026-03-31):** The core pipeline is validated and running. 50 channels monitored, 1,017 videos indexed in SurrealDB with 83,528 segments. Key architectural pivots: SurrealDB replaced Qdrant, MCP Gateway replaced youtube-transcript-api/yt-dlp for transcript fetching, and data flows in parallel to Lecture (Speakr) and College (SurrealDB) rather than sequentially.

KnowledgeStack solves a fundamental infrastructure problem: the world's leading experts produce thousands of hours of high-value content across YouTube, but that content is trapped in linear video format — unsearchable, uncorrelated, and inaccessible to AI systems. By extracting, structuring, and storing this content in a queryable repository, KnowledgeStack transforms passive video consumption into an active, AI-ready knowledge asset.

---

## Core Vision

### Problem Statement

Hundreds of hours of expert content are published daily across YouTube — spanning health, finance, investing, business, marketing, and technology. This content represents a vast, continuously updated body of knowledge from the world's leading practitioners and thinkers. However, it exists in the least accessible format possible: linear video that must be watched sequentially to extract value.

The consequences are severe for serious knowledge consumers:
- **Information overload:** 100+ hours of potentially relevant content per day, but only 1-2 hours available for consumption
- **Redundancy blindness:** When a major topic breaks (e.g., a new AI tool release), 50-100 hours of coverage appear from reliable sources alone — much of it overlapping, but you can't know which parts are redundant without watching all of it
- **Context-dependent waste:** A viewer installing on macOS must sit through VPS installation content (and vice versa) because there's no way to skip to the relevant segments
- **Ephemeral gems in noise:** Channels like Real Coffee with Scott Adams produce 3,000+ episodes where 90%+ is time-sensitive commentary, but the remaining timeless insights are buried without transcription-level access
- **Knowledge siloed by source:** The same expert appears across multiple channels as host, guest, or clip — but there's no way to aggregate their knowledge into a unified view

### Problem Impact

For the target user — a knowledge-driven professional who actively curates expert sources across multiple domains — the current state means:
- Hours spent watching content that turns out to be redundant or irrelevant
- Valuable expert insights lost because they're buried in 3-hour conversations
- No ability to cross-reference what multiple experts say about the same topic
- AI assistants that can't leverage curated expert knowledge because the content isn't in a structured, queryable format
- Downstream applications (expert panels, personalized feeds, best-practice extraction) are impossible to build without the structured data layer

### Why Existing Solutions Fall Short

| Solution | What It Does | Where It Falls Short |
|---|---|---|
| **YouTube native** | Algorithmic recommendations, playlists | No transcript search, no cross-referencing, algorithm serves YouTube's interests not yours |
| **Snipd** | Audio podcast aggregation with AI snippets | Audio-only (no video), interface quality issues, timing lag on content availability |
| **Fabric** | AI-powered content processing | Early-stage tooling, limited integration with custom infrastructure |
| **Recall.ai** | Meeting/content transcription and search | Consumer SaaS — data lives in their cloud, not your infrastructure; can't feed downstream custom AI apps |
| **Generic RAG tools** | Document ingestion into vector stores | Not purpose-built for video/podcast content; no channel management, no selective ingestion, no entity tracking |

**The common gap:** Every existing solution is a *consumer endpoint* — a finished app that solves one problem in one way. None provides the **infrastructure layer** that enables building multiple custom applications on top of structured expert knowledge. When you need expert panels, personalized feeds, best-practice extraction, and trust-weighted AI consultation — all from the same data — you need your own repository.

### Proposed Solution

KnowledgeStack is a three-tier infrastructure platform:

**Tier 1 — KnowledgeEnroll: Ingestion & Channel Management (What We Build):**

> [Updated 2026-03-31: spike learnings — MCP Gateway replaces yt-dlp, 50 channels operational]

- n8n-based automation monitoring RSS feeds from 50+ curated YouTube channels
- Per-channel configuration: auto-ingest all, manual selection queue, or hybrid with AI-suggested filtering
- Per-channel backlog depth settings (all-time, last 2 years, last 6 months)
- Admin UI for channel management, pipeline monitoring, and ingestion settings
- MCP Gateway transcript extraction pipeline (Helicarrier:2780) feeding content into both Lecture and College

**Tier 2 — KnowledgeLecture: Lecture Hall (Speakr, adopted as-is):**
- Self-hosted transcript playback with full-text search
- Tagging, bookmarks, and AI-powered chat per recording
- REST API enabling programmatic access from any downstream application
- Multi-user support, SSO/OIDC authentication, export capabilities

**Tier 3 — KnowledgeCollege: Intelligence & Enrichment (MVP-2):**

> [Updated 2026-03-31: spike learnings — SurrealDB replaces Qdrant, promoted to MVP-2]

- SurrealDB vector+graph+document store for unified semantic search and graph queries
- Embedding generation via LiteLLM proxy (text-embedding-3-small, 1536 dims)
- Entity extraction and tagging (kg-gen + spaCy-entity-linker, Wikidata-grounded)
- Cross-channel knowledge correlation and redundancy detection
- Background AI enrichment pipeline (entity resolution, topic segmentation, cross-references)

**Tier 4 — KnowledgeGraduate: Refinement (Growth):**
- Golden standard curation and premium excerpt management
- Human review workflows for content quality
- Expert authority profiles with trust/credibility rankings

**Tier 5 — KnowledgeGateway: API & Connectivity (MVP-2/Growth):**
- REST API exposing search + transcript retrieval
- MCP server for AI tool integration (Vision)
- API key authentication and rate limiting
- Integration layer enabling downstream apps to consume enriched knowledge

### Key Differentiators

1. **Infrastructure, not application:** KnowledgeStack is a data platform that feeds unlimited downstream use cases — not a single-purpose consumer app. The same repository powers expert panels, daily feeds, best-practice extraction, and AI consultation.

2. **Curated source authority:** Unlike generic AI that treats all sources equally, KnowledgeStack is built on user-curated channel taxonomies with explicit trust tiers. The user decides which experts matter, not an algorithm.

3. **Selective ingestion with per-channel intelligence:** Not a firehose. Each channel has its own ingestion profile — auto-ingest everything from Lex Fridman, manually approve Rogan episodes, mine timeless gems from Scott Adams' 3,000-episode archive.

4. **Six-product separation of concerns:** KnowledgeEnroll (ingestion), KnowledgeLecture (UI/listening), KnowledgeCollege (intelligence), KnowledgeGraduate (curation), KnowledgeGateway (API), and KnowledgeOps (operations) are independent products. Data flows in parallel to Lecture and College, not sequentially. Each product evolves independently.

5. **AI-assisted solo development:** Built by a domain expert (not a traditional developer) using AI-assisted development tools, proving that deep domain knowledge + AI tooling can produce infrastructure-grade systems without a traditional engineering team.

### System Components

> [Updated 2026-03-31: spike learnings — renamed to 6-product model, SurrealDB replaces Qdrant, parallel data flow]

| Component | Tier | Scope | Description |
|---|---|---|---|
| **KnowledgeEnroll** | 1 | Ingestion | n8n-based ingestion + admin UI. RSS monitoring, channel subscriptions, MCP Gateway transcript fetch, dedup pipeline. |
| **KnowledgeLecture** | 2 | Lecture Hall | Speakr (adopted as-is). UI/listening layer with transcript playback, search, tags, chat, multi-user. |
| **KnowledgeCollege** | 3 | Intelligence | SurrealDB vector+graph+document store. Embeddings, semantic search, entity enrichment, graph queries. |
| **KnowledgeGraduate** | 4 | Refinement | Golden standard curation, human review workflows, premium excerpts. |
| **KnowledgeGateway** | 5 | Access | REST API + MCP server exposing repository to external apps and AI tools. |
| **KnowledgeOps** | Cross-cutting | Operations | Pipeline monitoring, admin UI, Slack alerting, operational visibility. |

**Data Flow:** KnowledgeEnroll → (KnowledgeLecture + KnowledgeCollege) in parallel → KnowledgeGraduate → KnowledgeGateway

---

## Target Users

### Access Hierarchy

| Role | Access Level | Capabilities |
|---|---|---|
| **Admin** | Full system control | All curator abilities + infrastructure config, user management, system settings, n8n workflow management |
| **Curator** | Content contribution | Add channels, manage subscriptions, approve episodes, set per-channel ingestion rules, contribute to shared repository |
| **Viewer** | Read-only consumption | Browse and search shared repository, use Speakr chat/tags, discover content — cannot add channels or content |

### Primary Users

#### 1. Admin — "Matt" (Founder Persona)

**Context:** A knowledge-driven professional and self-taught technologist who actively consumes expert YouTube content across 5+ domains (AI/tech, business, finance, health, political commentary). Manages a curated taxonomy of 46+ YouTube channels organized into trust tiers (Supreme, Leaders, Mid-tier, Occasional). Not a traditional developer — builds with AI-assisted tools (Claude Code) and automation platforms (n8n).

**Problem Experience:** Spends hours watching content that turns out to be redundant or irrelevant. When a topic breaks (new AI tool release), 50-100 hours of coverage flood in and there's no way to extract the signal without watching linearly. Has tried Snipd (audio-only, poor UX), Fabric (too early), and considered Recall (but needs data in own infrastructure for downstream apps).

**How They Use KnowledgeStack:**
- Full system administration: infrastructure, user management, n8n workflow configuration
- Manages channel subscriptions, ingestion rules, and backlog loading through the Tier 1 Channel Management UI
- Sets per-channel policies: auto-ingest all (Lex Fridman), manual approval (Joe Rogan), gem-mining (Scott Adams 3,000-episode archive)
- Reviews daily episode suggestion queues for hybrid channels
- Browses and searches transcripts directly in Speakr (Tier 2)
- Uses Speakr's chat/tag features for immediate exploration
- Eventually consumes enriched intelligence through Tier 3 AI Kbase apps

**Success Vision:** 100 YouTube channels monitored daily. New content auto-ingested or queued for quick approval. Backlog from key channels loaded per configured depth. All content searchable, taggable, and accessible to downstream AI applications. "A massive repository of absolute geniusness that can be used in so many different ways."

#### 2. Curator — "The Power User"

**Context:** A trusted member of the inner circle (friend, family, fellow tech enthusiast) who shares domain interests and has their own expert sources to contribute. Understands the system well enough to manage their own channel subscriptions and content curation.

**How They Use KnowledgeStack:**
- Subscribes to their own channels through the Tier 1 Channel Management UI
- Sets ingestion preferences for their subscriptions (auto, manual, hybrid)
- Approves episodes from their subscription queues
- All content they contribute becomes available to the shared repository (ingest once, share with all)
- Full access to Speakr for browsing, searching, chatting, tagging
- May evolve from Viewer to Curator as they engage more deeply

#### 3. Viewer — "The Inner Circle"

**Context:** Close friends, brother, tech-curious people invited to explore the repository. They consume and benefit from the curated knowledge without contributing to ingestion. May eventually request curator access.

**How They Use KnowledgeStack:**
- Receive Speakr access (multi-user, SSO/OIDC via Authentik)
- Browse and search the shared transcript repository
- Use Speakr's chat feature to ask questions about content
- Tag and organize content for personal reference
- Discover experts and topics they wouldn't have found on their own

**Success Vision:** Log in and immediately access a curated library of expert transcripts. Search for what they need without watching hours of video. Get the key insights from a 3-hour podcast in 5 minutes.

### Secondary Users

#### 4. API Consumer — Tier 3 Applications

**Context:** The NextLevel AI Knowledge Base and future downstream applications that programmatically access the KnowledgeLecture repository. System-to-system integrations, not human users.

**How They Use KnowledgeStack:**
- Query Speakr's REST API for transcript data, metadata, tags
- Pull structured content into SurrealDB for advanced vector search and RAG
- Build entity graphs, expert profiles, and cross-references on top of repository data
- Serve end users through their own interfaces (expert panels, daily feeds, best-practice generators)

**Success Vision:** Clean, well-documented API surface providing reliable access to all ingested content with rich metadata. The repository is the single source of truth that multiple intelligence apps build upon without duplicating ingestion work.

### User Journey

**New User Onboarding (Viewer → potential Curator):**
1. **Invitation:** Admin adds user to Speakr (SSO/OIDC via Authentik)
2. **Exploration:** User logs in and browses the shared repository — transcripts from 100+ channels already available
3. **Discovery:** Searches for a topic, finds expert discussions they didn't know existed
4. **Engagement:** Uses Speakr chat to ask questions about recordings, tags content for personal reference
5. **"Aha!" Moment:** Realizes they can get key insights from a 3-hour podcast in 5 minutes by reading the transcript and using search
6. **Expansion (optional):** Requests Curator access to subscribe to their own channels and contribute to the shared repository
7. **Routine:** Checks the repository regularly as part of their knowledge workflow

### Content Sharing Model

- **Channel subscriptions:** Per-user (each Curator manages their own channel list)
- **Ingested content:** Shared across all users (ingest once, available to everyone — no duplication for shared channel subscriptions)
- **Access tiers:** Viewer (browse shared content), Curator (add channels + content), Admin (full system control)

### Data Architecture Note

> [Updated 2026-03-31: spike learnings — SurrealDB replaces Qdrant, parallel data flow]

Speakr maintains its own PostgreSQL database with transcript storage and sentence-transformers for in-memory similarity search. SurrealDB serves as the unified intelligence store providing vector search (HNSW, 1536 dims), graph traversal, and document storage in a single database. Data flows from KnowledgeEnroll to both Lecture (Speakr) and College (SurrealDB) in parallel, resulting in intentional data duplication. This is an accepted trade-off: storage is cheap, Speakr provides transcript playback and per-recording chat, while SurrealDB provides semantic search and entity graphs. The spike validated this architecture with 1,017 videos and 83,528 segments.

---

## Success Metrics

KnowledgeStack's overarching goal is to make knowledge management, learning, and having data ready for ingestion into downstream systems like LLMs **nearly frictionless**. Every metric below serves that principle — if a routine task requires SSH, raw SQL, or manual intervention that could be automated, that's a failure.

### Pipeline Health (Is KnowledgeEnroll Working?)

| Metric | Target | How Measured |
|---|---|---|
| Channel monitoring coverage | 100% of configured channels actively monitored | RSS check logs + cron job fallback confirmation |
| Transcript extraction accuracy | 90-95% success rate with duration and metadata captured | Extraction success/failure ratio per ingestion attempt |
| Ingestion throughput | 100+ videos per day sustained capacity | Daily ingestion count |
| Content freshness | Videos ingested within 6 hours of YouTube publish (long-term) | Time delta: YouTube publish timestamp → Speakr availability |
| RSS + cron reliability | Zero missed episodes — RSS as primary, cron jobs as safety net | Comparison: known YouTube publishes vs. ingested episodes |

### Content Coverage (Is It Capturing What Matters?)

| Metric | Target | How Measured |
|---|---|---|
| Channels monitored | 100+ curated channels across 5 domains | Channel count in KnowledgeEnroll |
| Total episodes ingested | 5,000+ videos (cumulative milestone) | Speakr recording count |
| Backlog completion | Per-channel configured depth fully loaded | % of backlog episodes ingested per channel |
| Metadata quality | All episodes tagged and documented with complete YouTube metadata | % episodes with title, description, channel, publish date, duration |

### User Value (Are People Getting What They Need?)

| Metric | Target | How Measured |
|---|---|---|
| Self-service channel management | Users can add channels, one-off videos, and manage subscriptions through the portal | Portal feature completeness and task completion without admin help |
| AI-powered knowledge extraction | Users can query across multiple videos to extract best practices, compare expert opinions, and synthesize actionable insights | Successful cross-video AI queries (e.g., "best practices from 6 videos about CloudBot") |
| Speakr adoption | Active users browsing, searching, chatting, and tagging in Speakr | Speakr interaction logs |
| Inner circle engagement | Demo-ready system with active Viewer/Curator users | User count and return visits |

### Operational Simplicity (Is It Nearly Frictionless?)

| Metric | Target | How Measured |
|---|---|---|
| Admin portal usability | Channel management, subscriptions, episode approval, and ingestion settings all achievable through the KnowledgeEnroll web portal — no n8n console or CLI required | Admin can add a channel, set ingestion mode, and approve an episode entirely through the UI |
| Curator self-service | New Curator can subscribe to their first channel and trigger ingestion without admin intervention | End-to-end self-service flow completion |
| Enhancement portal usability | Tag management, entity editing, and enrichment controls accessible through KnowledgeCollege management UI — not raw database queries | Admin can review/edit tags, entity associations, and trigger enrichment runs through the portal |
| LLM-ready data | Content structured and accessible so downstream AI systems can consume it without custom ETL or data wrangling | API query returns complete, well-structured transcript + metadata in a single call |
| Zero-SSH operations | All routine tasks (channel management, content review, enrichment, user management) achievable without terminal access | Audit: can every weekly admin task be done through a portal? |

### Tier 3 Readiness (Is the Foundation Solid for KnowledgeCollege & KnowledgeGateway?)

| Metric | Target | How Measured |
|---|---|---|
| API availability | REST API accessible and reliable for downstream applications | Speakr API uptime and response completeness |
| Knowledge graph foundation | Cross-video entity relationships enabling "find me everything Expert X said about Topic Y" | Entity graph coverage and query accuracy |
| Advanced tagging & enrichment | Ability to upgrade, enhance, and re-tag existing content programmatically | Enrichment pipeline operational status |
| Speakr uptime | Repository available continuously as the single source of truth | Service availability monitoring |

### North Star

> We have a repository of amazing knowledge from hundreds of trusted experts — a massive collection of their cumulative publicly spoken wisdom. We can access and utilize that knowledge in unlimited ways: feeding it into Claude Code to determine best practices, developing expert personalities for an AI hedge fund app, generating a daily feed of what content to focus on, or any downstream application we haven't imagined yet.
>
> **The test:** Is the repository rich enough, structured enough, and accessible enough that any new use case is a matter of *querying the data* — not rebuilding the pipeline?

---

## MVP Scope

### Core Features

KnowledgeStack comprises four products, each with its own MVP. They are sequential — each depends on the previous tier — but each delivers standalone value and has its own "done" definition.

#### KnowledgeEnroll MVP — Ingestion & Channel Management

The content intake layer: YouTube content flows into the system through automated and on-demand pipelines.

| Feature | Description |
|---|---|
| **n8n RSS ingestion pipeline** | n8n workflows monitoring YouTube RSS feeds for new content from subscribed channels, triggering automatic transcript extraction and upload to KnowledgeLecture |
| **Top 50 channels loaded** | Initial channel list covering the highest-priority sources across all domains — Supreme and Leaders tiers fully loaded, select Mid-tier channels |
| **On-demand video entry** | Ability to manually submit individual YouTube URLs for immediate ingestion — one-off videos, guest appearances on non-subscribed channels, or ad-hoc content |
| **Cron fallback safety net** | Daily cron job confirming RSS didn't miss any published videos from monitored channels |
| **Basic channel management portal** | Web interface for adding/removing channels, viewing subscription status, and managing ingestion settings — no raw n8n console required for routine channel operations |
| **Per-channel ingestion modes** | Each channel configurable as auto-recent (all new videos + last X days backlog) or manual queue (searchable queue for selective ingestion) — AI-suggested hybrid deferred to post-MVP |

**KnowledgeEnroll MVP "Done" means:** 50 channels are being monitored with per-channel ingestion modes. New videos are automatically ingested. One-off videos can be added on demand. Channel management is handled through a basic web portal.

#### KnowledgeLecture MVP — Transcript Repository (Speakr)

The repository layer: Speakr deployed, configured, and stable — receiving content from KnowledgeEnroll and serving it to users and downstream systems.

| Feature | Description |
|---|---|
| **Speakr deployed and configured** | KnowledgeLecture (Speakr) running as a self-hosted Docker service with PostgreSQL, configured for the KnowledgeStack environment |
| **Diarization working** | Speaker diarization enabled and producing quality output for ingested transcripts |
| **Content searchable and browsable** | Full-text search, semantic search, tagging, and AI chat operational for all ingested content |
| **REST API accessible** | Speakr's built-in REST API verified and available for KnowledgeCollege and any downstream applications — providing interim programmatic access from day one |

**KnowledgeLecture MVP "Done" means:** Speakr is running and stable. All KnowledgeEnroll content flows in with diarization. Content is searchable and browsable. REST API is accessible for KnowledgeCollege and other applications. This is a light MVP — primarily deployment and configuration — but a distinct product with its own acceptance criteria.

#### KnowledgeCollege MVP — Intelligence Layer

> [Updated 2026-03-31: spike learnings — SurrealDB replaces Qdrant, data already in SurrealDB, embeddings needed]

The intelligence layer: transcript segments already stored in SurrealDB (83,528 segments from spike). Needs embedding generation and semantic search activation.

| Feature | Description |
|---|---|
| **Embedding generation** | Generate 1536-dim embeddings for all transcript segments via LiteLLM proxy (text-embedding-3-small). Full corpus cost ~$2. |
| **Semantic search** | SurrealDB HNSW index enabling vector similarity + keyword + graph filter queries in a single operation |
| **Entity extraction** | kg-gen + spaCy-entity-linker producing Wikidata-grounded tag hierarchies (376 tags exist, quality needs improvement) |

**KnowledgeCollege MVP "Done" means:** 80%+ segments have embeddings. Semantic search returns relevant results for synonym/concept queries. Basic entity tagging classifies products, companies, and people correctly (not 95% "concept"). The foundation is laid for entity graphs, AI synthesis, and advanced enrichment.

#### KnowledgeGateway MVP — Downstream Connectivity

> [Updated 2026-03-31: spike learnings — renamed from KnowledgeGateway, may ship alongside College in MVP-2]

The API layer: downstream applications can consume knowledge from KnowledgeCollege programmatically.

| Feature | Description |
|---|---|
| **REST API** | Structured API surface enabling other applications (Claude Code, LobeChat, OpenClaw, custom apps) to query KnowledgeCollege data programmatically |
| **API key authentication** | Basic API key management for downstream consumers |
| **At least one downstream integration** | Validated end-to-end: at least one external application successfully consuming data from KnowledgeStack |

**KnowledgeGateway MVP "Done" means:** Downstream applications can programmatically query and consume structured knowledge data from KnowledgeCollege. At least one integration proves the pattern works.

**Note:** Speakr's REST API provides interim programmatic access from KnowledgeLecture MVP onward. Downstream apps don't have to wait for KnowledgeCollege/KnowledgeGateway to start consuming data — KnowledgeCollege upgrades the query quality, and KnowledgeGateway formalizes the connectivity layer.

### Out of Scope for MVP

| Deferred Feature | Rationale | Target Product (post-MVP) |
|---|---|---|
| **Historical backlog bulk loading** | MVP focuses on the top 50 channels going forward; deep historical backlog is a scale feature | KnowledgeEnroll |
| **AI-suggested episode filtering** | Requires training data and pattern recognition that doesn't exist yet | KnowledgeCollege |
| **Expert authority profiles** | Enrichment feature requiring trust/credibility ranking — research problem, not pipeline problem | KnowledgeCollege |
| **Hierarchical tag taxonomy** | Advanced tagging beyond Speakr's built-in tags and basic KnowledgeCollege tagging | KnowledgeCollege |
| **Entity graph** | People, topics, and source relationships require entity resolution (exact match → AI → Wikidata) — a program of work beyond MVP | KnowledgeCollege |
| **Cross-video AI synthesis** | AI-powered multi-video summaries require SurrealDB embeddings + entity structure to be meaningful | KnowledgeCollege |
| **Topic-based cross-video query** | Advanced cross-corpus queries depend on entity graph and enrichment pipeline | KnowledgeCollege |
| **Virtual expert panels** | Downstream application feature requiring entity graph and authority profiles | KnowledgeGateway |
| **Personalized daily content feeds** | Downstream application feature requiring user profiling | KnowledgeGateway |
| **Multi-user/Curator onboarding** | MVP is admin-only; Viewer access through Speakr is available but Curator self-service deferred | KnowledgeEnroll |
| **100+ channel target** | MVP proves the pipeline with 50; scaling to 100+ is a post-MVP expansion | KnowledgeEnroll |
| **Cross-channel redundancy detection** | Requires significant corpus analysis and topic overlap algorithms | KnowledgeCollege |

### MVP Success Criteria

**KnowledgeEnroll MVP Success Gates:**
- 50 channels actively monitored via RSS with cron fallback — zero missed videos (standard uploads > 90s; Shorts and live broadcasts excluded)
- Per-channel ingestion modes (auto-recent/manual queue) configurable through the portal
- 90%+ transcript extraction success rate
- On-demand video submission working end-to-end
- Basic channel management portal operational — add channel, set mode, view status without n8n console
- Content available in KnowledgeLecture within 6 hours of YouTube publish (for monitored channels)

**KnowledgeLecture MVP Success Gates:**
- Speakr deployed, configured, and stable
- Diarization producing quality speaker-attributed transcripts
- Full-text and semantic search operational
- AI chat and tagging functional
- REST API responding and accessible for KnowledgeCollege

**KnowledgeCollege MVP Success Gates:**

> [Updated 2026-03-31: spike learnings — SurrealDB replaces Qdrant, data exists, embeddings needed]

- 80%+ segments have vector embeddings in SurrealDB
- Semantic search returns relevant results for concept/synonym queries
- Entity tagging correctly classifies products, companies, and people (not just "concept")
- New content automatically embedded on ingestion

**KnowledgeGateway MVP Success Gates:**
- At least one downstream application successfully consuming data via REST API
- API key authentication operational
- End-to-end validated: external app queries KnowledgeStack and gets structured, usable results

**Go/No-Go for Scaling Beyond MVP:**
- Pipeline proves reliable over 2+ weeks of continuous operation
- At least one meaningful query demonstrates cross-corpus value
- System handles 50 channels without performance degradation — green light for 100+

### Future Vision

Each product MVP establishes its foundation. Post-MVP enhancements build on top of each product independently:

**KnowledgeEnroll (post-MVP):**
- Scale to 100+ channels with historical backlog bulk loading
- Curator self-service onboarding and multi-user content contribution
- Enhanced admin UI with approval queues and analytics
- AI-suggested episode filtering based on learned patterns

**KnowledgeLecture (post-MVP):**
- Speakr upstream improvements adopted as they ship (free upgrades)
- Extended export capabilities for downstream consumption

**KnowledgeCollege (post-MVP):**
- Entity graph: people, topics, and source relationships across the corpus
- Expert authority profiles with trust/credibility rankings
- Background AI enrichment pipeline (entity resolution, topic segmentation)
- Hierarchical tag taxonomy beyond basic tagging
- Cross-video AI synthesis with source attribution
- Cross-channel redundancy detection
- Topic-based cross-video queries ("find me everything Expert X said about Topic Y")

**KnowledgeGateway (post-MVP):**
- MCP server for AI tool integration (Claude Code, LobeChat)
- Virtual expert panels for AI-mediated multi-source consultation
- Personalized daily content feeds based on user interest profiles
- API marketplace for downstream applications
- Integration with Claude Code best-practice extraction and applications not yet imagined
