# KnowledgeStack: Product Vision & Use Cases

> **Living Document** - Updated as we learn. This is the filter through which all technical decisions flow.
>
> **Parent Document:** [product-brief-knowledge-2026-01-30.md](./product-brief-knowledge-2026-01-30.md)
>
> **Last Updated:** 2026-03-31 (post-spike update)

---

## One-Line Vision

**Turn hours of expert video content into conversational AI personas, searchable wisdom, and actionable insights.**

---

## Core Use Cases

### Tier 1: Persona Agents (Primary)

| Use Case | Description | Example |
|----------|-------------|---------|
| **1.1 Expert Persona Chat** | Chat with an AI embodying a specific expert's knowledge, style, and perspective | "Talk to Myron Golden about my pricing strategy" |
| **1.2 Group Expert Panel** | Multi-agent conversation with multiple expert personas discussing a topic | "Have Alex Finn, AILABS, and mreflow discuss the best way to deploy an AI agent" |
| **1.3 Expert Research Mode** | Ask "What does [expert] say about [topic]?" as a research source | "What does Alex Finn say about n8n webhook security?" |

**Why This Matters:** Experts spend thousands of hours teaching. A persona agent makes that wisdom accessible in conversation, not video scrubbing.

### Tier 2: Content Intelligence

| Use Case | Description | Example |
|----------|-------------|---------|
| **2.1 Quote/Moment Extraction** | Find the best quotes, memorable lines, key moments from any video | "Show me Myron Golden's most quotable lines about sales" |
| **2.2 Topic Summaries** | Summary of topics + key points for each topic | "What are the main topics in this 3-hour video?" |
| **2.3 Chapter Generation** | Auto-generate chapter markers with timestamps | "Generate chapters for this video" |
| **2.4 Highlight Reel** | From a 3-hour video, find the 8 best 5-10 minute segments | "What are the must-watch segments from this video?" |
| **2.5 Video Clip Extraction** | Identify clip-worthy segments with timestamps for cutting | "Extract the 60-second segment about handling objections" |
| **2.6 Visual Hub / Analysis Dashboard** | One view showing all generated content for a video | See WhisperTranscribe reference below |

**Why This Matters:** Long-form content is valuable but inaccessible. These tools extract the signal from hours of noise.

**Reference Product:** [WhisperTranscribe](https://www.whispertranscribe.com/) - turns one recording into 57+ content types (quotes, summaries, chapters, clips, social posts, etc.)

### Tier 3: Knowledge Integration

| Use Case | Description | Example |
|----------|-------------|---------|
| **3.1 Best Practices Discovery** | Extract best practices across domains (deployments, trading, health) | "What do my AI experts recommend for deploying n8n?" |
| **3.2 Cross-Expert Synthesis** | Compare what multiple experts say about the same topic | "Compare AILABS vs mreflow perspectives on Claude Code" |
| **3.3 Research Augmentation** | Integrate expert knowledge into Claude conversations as a data source | "Using my knowledge base, help me plan this deployment" |
| **3.4 Technical Documentarian** | Track evolving best practices for technical topics | "What's the current best practice for MCP server deployment?" |
| **3.5 Knowledge Evolution** | Show how recommendations have changed over time | "Alex Finn said X in January, but AILABS recommends Y as of March" |

**Why This Matters:** The goal isn't just to store transcripts - it's to make expert knowledge a queryable resource that enhances AI conversations.

### Technical Knowledge Base (Documentarian Role)

KnowledgeStack becomes the **source of truth for technical best practices** by ingesting videos on:
- Claude Code development
- ShadCN and UI frameworks
- AI hosting and deployment
- MCP servers and integrations
- n8n workflows and automation

**Key Capability: Temporal Awareness**

For technical domains, **recency matters**. Unlike timeless wisdom (Myron Golden on sales psychology), technical recommendations become outdated quickly.

| Query Type | How Recency Applies |
|------------|---------------------|
| "How to deploy MCP servers" | Prefer March 2026 over January 2026 |
| "Best Claude Code practices" | Show evolution: "Previously X, now Y" |
| "ShadCN component patterns" | Latest version recommendations |

**Implementation Requirements:**

| Requirement | Purpose |
|-------------|---------|
| **Publish date on every segment** | Know when advice was given |
| **Topic + date indexing** | Query "topic X, sorted by recency" |
| **Supersession detection** | Flag when newer content updates older advice |
| **Domain-based recency weighting** | Technical = high recency weight, Wisdom = low |
| **Evolution timeline** | "Here's how recommendations for X changed over time" |

**Example Query:**
> "What's the best way to structure MCP servers?"

**Response with temporal context:**
> - **Jan 2026 (Alex Finn):** "Use a single index.ts with all tools..."
> - **Mar 2026 (AILABS):** "The new pattern is modular tool files with a registry..."
> - **Recommendation:** Follow AILABS' March approach (more recent, addresses scaling issues)

### Tier 4: Daily Feeds & Digests

| Use Case | Description | Example |
|----------|-------------|---------|
| **4.1 Daily Clips Feed** | Top 10 must-watch clips from recent content | "Here are the 10 clips you need to watch today" |
| **4.2 Key Points Digest** | 5 articles or key insights distilled | "Here are 5 key points from yesterday's content" |
| **4.3 Domain-Specific Tips** | 20 stock/business/health tips aggregated | "Here are 20 stock and business tips of the day" |
| **4.4 New Content Alert** | What's new from your followed experts | "Alex Finn posted 2 new videos about MCP servers" |

**Why This Matters:** Transform passive content consumption into active, curated intelligence briefings. Users get the signal without watching hours of video.

**Requirements for Daily Feeds:**
- Recency scoring (prioritize new content)
- Impact/importance scoring (what's actually valuable)
- Domain filtering (business vs AI vs health)
- Clip identification with timestamps
- Aggregation across channels
- Delivery mechanism (email, dashboard, API)

### Tier 5: Knowledge Synthesis & Aggregation

| Use Case | Description | Example Output |
|----------|-------------|----------------|
| **5.1 Best Practices Guide** | Aggregate advice on a topic into a unified guide | "Claude MCP Best Practices: 12 tips from 5 experts" |
| **5.2 How-To Synthesis** | Combine steps from multiple sources | "How to secure OpenClaw: Complete guide from Alex Finn + community" |
| **5.3 Weekly Highlights** | Time-filtered top insights | "Most powerful AI use cases I heard this week" |
| **5.4 Topic Deep Dive** | Everything known about X | "Complete guide to n8n webhooks from your knowledge base" |
| **5.5 Consensus View** | Where do experts agree? | "All 4 experts agree: always use environment variables for secrets" |

**Why This Matters:** Transform scattered insights into **actionable, consolidated knowledge** - not just retrieval, but synthesis.

**Example Outputs:**

> **Query:** "Claude MCP best practices"
>
> **Synthesized Output:**
> ```
> # Claude MCP Best Practices
> *Aggregated from Alex Finn, AILABS, mreflow (Jan-Mar 2026)*
>
> ## 1. Project Structure
> - Use modular tool files (AILABS, Mar 2026)
> - Keep index.ts clean (Alex Finn, Jan 2026)
>
> ## 2. Security
> - Never hardcode API keys (all sources agree)
> - Use .env for local, env vars for prod (AILABS)
>
> ## 3. Performance
> - Lazy-load heavy tools (mreflow, Feb 2026)
> ...
> ```

**Requirements:**
- Multi-source retrieval on topic
- Deduplication (same advice from multiple sources)
- Consensus detection (where do they agree?)
- Conflict highlighting (where do they disagree?)
- Temporal ordering (newest practices may supersede)
- Attribution (credit each source)
- Credibility weighting (TOP-tier advice first)

### Tier 6: Cross-Project Intelligence

**Concept:** Define objectives for multiple projects. When new content is ingested, automatically analyze: "Does this relate to any of my projects?"

| Use Case | Description | Example |
|----------|-------------|---------|
| **6.1 Project Objectives Registry** | Define goals/objectives for each project | "KnowledgeStack: RAG, SurrealDB, transcript ingestion" |
| **6.2 Content Routing** | New content auto-tagged to relevant projects | "This AILABS video mentions MCP → routes to 3 projects" |
| **6.3 Daily Project Digest** | Per-project report of relevant new content | "For KnowledgeStack: 2 new videos with relevant insights" |
| **6.4 Golden Standards Update** | Flag when new content should update best practices | "New MCP pattern detected → update KnowledgeStack standards?" |
| **6.5 Cross-Project Insights** | Same insight applies to multiple projects | "This security tip applies to: KnowledgeStack, OpenClaw, n8n-automations" |

**Data Model:**

```
Project
  ├─ name: "KnowledgeStack"
  ├─ objectives: ["RAG implementation", "SurrealDB integration", "transcript processing"]
  ├─ keywords: ["RAG", "vector database", "embeddings", "SurrealDB"]
  ├─ relevant_domains: ["ai-coding", "ai-automation"]
  ├─ golden_standards → GoldenStandard[] (best practices docs)
  └─ subscribed_topics → Topic[]

GoldenStandard
  ├─ project → Project
  ├─ topic: "MCP Server Structure"
  ├─ current_best_practice: "Use modular tool files..."
  ├─ sources: [Segment, Segment, ...] (evidence)
  ├─ last_updated: date
  └─ pending_updates: [Segment] (new content to review)

ContentRouting (daily analysis output)
  ├─ date: "2026-03-19"
  ├─ new_segments: [Segment] (ingested today)
  ├─ project_matches: [
      {project: "KnowledgeStack", segments: [...], relevance_score: 0.92},
      {project: "OpenClaw", segments: [...], relevance_score: 0.78}
    ]
  └─ golden_standard_flags: [
      {standard: "MCP Structure", segment: ..., reason: "New pattern mentioned"}
    ]
```

**Daily Workflow:**

```
1. Overnight: New videos ingested
2. Morning: Content routing analysis runs
   → "3 new videos processed"
   → "KnowledgeStack: 5 relevant segments found"
   → "OpenClaw: 2 relevant segments found"
   → "Golden Standard Alert: MCP structure may need update"
3. Report delivered (email, dashboard, or Claude query)
4. User reviews flagged updates, approves/rejects
5. Golden standards updated if approved
```

**Example Daily Report:**

```markdown
# Daily Intelligence Report - March 19, 2026
*3 new videos ingested, 47 segments analyzed*

## KnowledgeStack
**Relevance: HIGH** (5 segments matched objectives)

- [AILABS] New SurrealDB vector indexing approach
  → May update: Golden Standard "Vector Index Configuration"

- [Alex Finn] MCP server modularization pattern
  → Relates to objective: "RAG implementation"

## OpenClaw
**Relevance: MEDIUM** (2 segments matched)

- [Alex Finn] Security hardening for n8n webhooks
  → Action: Review for security standards doc

## No Match
- [Myron Golden] 3 segments on sales (not project-relevant)
```

---

## Decision Filter

**When making technical choices, ask:**

| Question | Implication |
|----------|-------------|
| Does this support **persona agents**? | Need speaker-level corpus, style patterns, attribution |
| Does this enable **timestamp-based features**? | Must preserve video timestamps for chapters/highlights |
| Does this allow **quote extraction**? | Need smaller chunks, impact scoring capability |
| Does this support **cross-expert queries**? | Need topic entities, speaker relationships |
| Does this integrate with **Claude/AI workflows**? | Need clean API, structured output |

**If a choice doesn't serve at least one Tier 1-2 use case, question whether we need it.**

---

## Data Requirements (Derived from Use Cases)

### Must Have (Blocks Tier 1-2 Use Cases)

> [Updated 2026-03-31: spike learnings — several items now implemented]

| Requirement | Use Cases Served | Current Status |
|-------------|------------------|----------------|
| **Timestamps on segments** | Chapters, Highlights, Deep Links, Visual Hub | **IMPLEMENTED** (spike preserved timestamps) |
| **Publish date on segments** | Technical recency, Evolution queries | **IMPLEMENTED** (denormalized from video) |
| **Domain on segments** | Recency weighting by domain | **IMPLEMENTED** (denormalized from channel) |
| **Channel hosts config** | Speaker attribution, Persona agents | NOT configured |
| **Guest extraction (title/desc/transcript)** | Complete persona corpus | **PARTIAL** (title/desc patterns working) |
| **Smaller chunks (~500 chars)** | Quote extraction, Precise retrieval | TBD (current segment size varies) |
| **Video description capture** | Guest extraction, Links | **IMPLEMENTED** (captured at ingestion) |
| **Description link extraction** | Tool references, Resources, Citations | NOT implemented |
| **Vector embeddings** | Semantic search, persona agents, all Tier 1-3 | **NOT IMPLEMENTED** (83K segments, zero embeddings) |

### Should Have (Enhances Tier 1-2)

| Requirement | Use Cases Served | Current Status |
|-------------|------------------|----------------|
| **Topic entities with video links** | "All videos where X talks about Y" | Not implemented |
| **Quote entities** | Quotable moments as first-class objects | Not implemented |
| **Quote/moment scoring** | Quote extraction, Highlights | Not implemented |
| **Entity extraction (tools, people, tech)** | Best practices, Research mode | Not implemented |
| **Publish date on segments** | Technical recency, Evolution tracking | Have on video, not segment |
| **Domain-based recency weighting** | Technical queries prefer newer | Not implemented |
| **Supersession/evolution detection** | "New method replaces old" | Not implemented |
| **Visual reference detection** | "as you can see..." triggers lazy visual analysis | Not implemented |
| **User interaction logging** | Collaborative discovery, "users like you" | Not implemented |
| **Speaker values/positions** | Counterfactual responses | Not implemented |

### Nice to Have (Tier 3-4 / Future)

| Requirement | Use Cases Served | Current Status |
|-------------|------------------|----------------|
| **Speaker style profiles** | Persona fidelity | Not implemented |
| **Cross-reference detection** | Cross-expert synthesis | Not implemented |
| **User preference learning** | Personalized feeds | Not implemented |
| **Importance/impact scoring** | Daily feeds, Highlights | Not implemented |
| **Recency weighting** | Daily feeds | Have publish_date |
| **Clip boundary detection** | Daily clips feed | Not implemented |
| **Domain-based aggregation** | Tips of the day | Have domain tags |

---

## Current Data Sources

### Active Channels

> [Updated 2026-03-31: spike learnings — 50 channels across 7 domains. Sample shown below.]

**Total:** 50 channels across 7 domains (ai-tech, business, political, mindset, health, general, faith)

| Channel | Handle | Domain | Host(s) | Content Focus |
|---------|--------|--------|---------|---------------|
| **Myron Golden** | MyronGolden | business | Myron Golden | High-ticket sales, offers, mindset |
| **Bible Study w/ Myron** | BibleStudyWithMyronGolden | faith | Myron Golden | Biblical principles, faith |
| **Alex Finn (OpenClaw)** | AlexFinnOfficial | ai-tech | Alex Finn | n8n, AI agents, no-code |
| **AILABS** | AILABS-393 | ai-tech | Cole Medin (+ others?) | Claude Code, Cursor, AI dev |
| **mreflow** | mreflow | ai-tech | (TBD) | AI tools, dev workflows |
| *(45 more channels)* | | | | See Admin UI for full list |

### Speaker Registry (Personas)

| Speaker | Primary Channel | Domains | Aliases |
|---------|-----------------|---------|---------|
| **Myron Golden** | MyronGolden | business, religion | Dr. Myron Golden, Myron |
| **Alex Finn** | AlexFinnOfficial | ai-automation | (none known) |
| **Cole Medin** | AILABS-393 | ai-coding | Cole |
| **mreflow host** | mreflow | ai-coding | (TBD - need to identify) |

> **Action needed:** Confirm host names for AILABS and mreflow channels

### Domain Taxonomy

> [Updated 2026-03-31: spike learnings — expanded to 7 domains]

| Domain | Description | Expert Personas |
|--------|-------------|-----------------|
| `ai-tech` | AI-assisted development, no-code, n8n, AI agents | Alex Finn, Cole Medin, mreflow host |
| `business` | Sales, marketing, offers, entrepreneurship | Myron Golden |
| `political` | Political commentary, current events | (various) |
| `mindset` | Personal development, productivity | (various) |
| `health` | Health, wellness, protocols | (various) |
| `general` | General interest, entertainment | (various) |
| `faith` | Faith, biblical principles | Myron Golden |

---

## Success Metrics

### Spike Phase (Completed 2026-03-31)

> [Updated 2026-03-31: spike learnings — all spike targets exceeded]

| Metric | Target | Status |
|--------|--------|--------|
| Transcripts ingested | 100+ | **1,017 videos, 83,528 segments in SurrealDB** |
| Vector search working | <100ms | 30ms achieved (keyword); **embeddings pending for semantic** |
| Graph queries working | Yes | **Verified** (<1ms) |
| Timestamps preserved | Yes | **Yes** (preserved during spike) |
| Channels monitored | 10+ | **50 channels across 7 domains** |
| Pipeline success rate | 90%+ | **95% achieved** |
| Entity extraction | Basic | **376 tags with Wikidata-grounded hierarchies** (quality issues) |

### MVP Phase (Current Focus)

| Metric | Target | Blocker |
|--------|--------|---------|
| Embeddings generated | 80%+ segments | Zero embeddings currently; ~$2 to generate |
| Semantic search working | Relevant results for synonym/concept queries | Blocked on embeddings |
| Tag quality | Products, companies, people correctly typed | 95% classified as "concept" |
| Single persona chat working | Yes | Needs College + Gateway |
| Expert query accuracy | "What does X say about Y" returns relevant content | Needs embeddings + entity graph |

### Production Phase (Future)

| Metric | Target |
|--------|--------|
| Multi-persona group chat | Working |
| Highlight extraction accuracy | Top 8 segments match human curation 70%+ |
| Research mode integration | Accessible from Claude conversations |
| Quote retrieval accuracy | >80% relevant |
| Chapter generation quality | Usable without editing |

---

## Graph Relationships (Critical for Use Cases)

```
Speaker (persona entity)
  ├─ name: "Myron Golden"
  ├─ aliases: ["Dr. Myron Golden", "Myron"]
  ├─ hosts → Channel[] (channels where they are a regular host)
  ├─ appears_in → Video[] (as guest on OTHER channels)
  ├─ discusses → Topic[]
  ├─ said → Quote[]
  └─ credibility → SpeakerCredibility[] (per-topic trust tiers)

SpeakerCredibility (per-topic trust ranking)
  ├─ speaker → Speaker
  ├─ domain: "business" | "ai-coding" | "politics" | etc.
  ├─ tier: "top" | "high" | "mid" | "low" | "none"
  ├─ notes: "20+ years building businesses, proven track record"
  └─ updated_at: date (credibility can change over time)

Channel
  ├─ name: "AILABS"
  ├─ handle: "AILABS-393"
  ├─ domain: "ai-coding"
  ├─ hosts → Speaker[] (1-4 regular hosts)
  └─ has_video → Video[]

Video
  ├─ title, description, url
  ├─ hosts → Speaker[] (from channel.hosts, may be subset)
  ├─ guests → Speaker[] (extracted from title/description/transcript)
  ├─ all_speakers → Speaker[] (computed: hosts + guests)
  ├─ has_segment → Segment[]
  ├─ covers → Topic[]
  └─ has_link → DescriptionLink[] (URLs from description)

DescriptionLink
  ├─ video → Video
  ├─ url: "https://github.com/anthropics/claude-code"
  ├─ label: "Claude Code GitHub" (extracted from description context)
  ├─ link_type: "tool" | "docs" | "repo" | "social" | "sponsor" | "other"
  ├─ mentioned_in_transcript: boolean (does the video reference this link?)
  └─ related_segments → Segment[] (segments that discuss this link)

Segment
  ├─ text, start_time, end_time
  ├─ published_at (inherited from video - for recency queries)
  ├─ domain (inherited from channel - for recency weighting)
  ├─ spoken_by → Speaker (if determinable, else null)
  ├─ about → Topic[]
  ├─ contains → Quote[]
  ├─ requires_visual: boolean (detected from trigger phrases)
  ├─ visual_refs → VisualReference[] (lazy-loaded analysis)
  └─ embedding (vector)

Topic
  ├─ name: "sales objections"
  ├─ domain: "business"
  ├─ discussed_in → Video[]
  ├─ discussed_by → Speaker[]
  └─ related_to → Topic[]

Quote
  ├─ text: "Price is never the problem..."
  ├─ said_by → Speaker
  ├─ from_segment → Segment
  ├─ from_video → Video
  ├─ timestamp (for deep link)
  └─ impact_score: 0.92

Citation
  ├─ segment → Segment (where citation appears)
  ├─ citing_speaker → Speaker (who made the citation)
  ├─ cited_speaker → Speaker (if citing a person, nullable)
  ├─ cited_source → string (book, URL, docs, etc.)
  ├─ citation_type: "firsthand" | "secondhand" | "official_docs" | "hearsay"
  └─ quote_text: "the cited content"
```

### Guest Speaker Extraction Sources

| Source | Example | Extraction Method |
|--------|---------|-------------------|
| **Video Title** | "I interviewed Alex Finn about AI agents" | Regex + NER |
| **Video Description** | "Guest: @AlexFinnOfficial" or "Featuring Alex Finn" | Pattern matching |
| **Transcript Intro** | "Today I'm joined by Alex Finn..." | LLM extraction from first 2 minutes |
| **YouTube Metadata** | (if available via API) | Direct field |

### Channel Host Configuration

Channels should have explicit host configuration:

```yaml
# Example channel config
channel:
  handle: "AILABS-393"
  name: "AILABS"
  domain: "ai-coding"
  hosts:
    - name: "Cole Medin"
      aliases: ["Cole"]
    - name: "..."  # if multiple hosts
```

**Why explicit hosts matter:**
- Solo videos: all content attributed to host
- Guest videos: distinguish host questions from guest answers
- Multi-host channels: know who the regulars are vs guests

### Key Graph Queries This Enables

| Query | Graph Pattern |
|-------|---------------|
| "All videos where Myron discusses sales" | Speaker→discusses→Topic, Topic→discussed_in→Video |
| "When is Alex Finn a guest?" | Speaker→appears_in→Video WHERE Video.channel != Speaker.owns |
| "Best quotes about AI agents" | Topic→Quote[] ordered by impact_score |
| "What do all experts say about n8n?" | Topic(n8n)→discussed_by→Speaker[], then retrieve segments |
| "Top-tier advice on sales" | Topic(sales)→Segment WHERE speaker.credibility[sales].tier = 'top' |

### Speaker Credibility System

**Credibility is per-topic, not universal.** A speaker may be top-tier in one domain and low-tier in another.

| Speaker | Business | AI/Tech | Religion | Politics |
|---------|----------|---------|----------|----------|
| Myron Golden | TOP | low | TOP | mid |
| Alex Finn | mid | TOP | none | none |
| Cole Medin | mid | TOP | none | none |
| Mark Cuban (example) | TOP | high | none | low |

**Tier Definitions:**

| Tier | Meaning | Query Behavior |
|------|---------|----------------|
| **TOP** | Proven expert, primary source | Default include, weight highest |
| **high** | Credible, experienced | Include, weight high |
| **mid** | Some credibility, verify | Include with caveats |
| **low** | Limited credibility in this area | Exclude by default, include if requested |
| **none** | No credibility / no content | Exclude |

**How Credibility Affects Queries:**

| Scenario | Behavior |
|----------|----------|
| **Standard query** | Only show TOP + high tier sources |
| **Contradiction detection** | Weight TOP-tier position higher |
| **Best practices** | TOP-tier sources only |
| **Comprehensive view** | Include all tiers with labels |
| **Research mode** | Show tier alongside each result |

**Example with Credibility:**
> **Query:** "Best practices for high-ticket sales"
>
> **Response (credibility-weighted):**
> - **[TOP] Myron Golden:** "The key is to sell the transformation, not the product..."
> - **[high] Alex Hormozi:** "Price is a function of perceived value..."
> - *(mid/low tier sources filtered out by default)*

---

## Architecture Principles

1. **Timestamps are sacred** - Never discard timestamp data; enables transcript-to-video selection, chapters, highlights, deep links
2. **Word-level timestamps ideal** - YouTube provides per-phrase timestamps; preserve granularity for precise clip selection
3. **Speaker attribution always** - Every segment must trace back to a speaker persona
4. **Guest appearances matter** - Track when speakers appear on OTHER channels, not just their own
5. **Topics link everything** - Topics connect speakers, videos, and segments into a knowledge graph
6. **Quotes are first-class** - Memorable moments are entities, not just search results
7. **Chunks serve retrieval** - Size chunks for the retrieval use case (quotes need smaller, context needs larger)
8. **Graph over flat** - Relationships are as valuable as vectors
9. **API-first** - Everything must be accessible to Claude and downstream apps
10. **Video processing ready** - Store enough metadata to enable clip extraction with ffmpeg

---

## Backend Architecture for Optimal Retrieval

### The Challenge

We have **multiple search modalities** that need to work together:

| Modality | Example Query | Tech |
|----------|---------------|------|
| **Semantic** | "advice about handling rejection" | Vector similarity |
| **Keyword** | "MCP server" (exact term) | Full-text search |
| **Graph** | "all videos where Myron is a guest" | Graph traversal |
| **Filtered** | "AI content from last 30 days" | SQL-like filters |
| **Ranked** | "TOP-tier sources only" | Credibility weighting |
| **Temporal** | "newest advice on this topic" | Date sorting |

**Most queries combine multiple modalities:**
> "What do TOP-tier experts say about MCP servers in the last 3 months?"
> = Semantic (MCP servers) + Filter (last 3 months) + Ranked (TOP-tier) + Aggregated

### SurrealDB Advantage

SurrealDB can do all of this in **one query**:
```sql
SELECT *, vector::similarity::cosine(embedding, $query_vec) AS score
FROM segment
WHERE domain IN ['ai-coding', 'ai-automation']
  AND published_at > time::now() - 3mo
  AND ->spoken_by->speaker->credibility[WHERE domain = 'ai-coding'].tier IN ['top', 'high']
  AND embedding <|10,100|> $query_vec
ORDER BY score DESC, published_at DESC
```

### Index Strategy

| Index Type | On Field(s) | Purpose |
|------------|-------------|---------|
| **HNSW Vector** | `segment.embedding` | Semantic similarity search |
| **Full-text** | `segment.text` | Keyword search, exact phrases |
| **B-tree** | `segment.published_at` | Date range filtering |
| **B-tree** | `segment.domain` | Domain filtering |
| **Graph edges** | All relationships | Traversal queries |

```sql
-- Vector index (already have)
DEFINE INDEX segment_embedding ON segment FIELDS embedding HNSW DIMENSION 1536;

-- Full-text index
DEFINE INDEX segment_text ON segment FIELDS text SEARCH ANALYZER ascii BM25;

-- Filter indexes
DEFINE INDEX segment_date ON segment FIELDS published_at;
DEFINE INDEX segment_domain ON segment FIELDS domain;
DEFINE INDEX segment_speaker ON segment FIELDS spoken_by;
```

### Denormalization Strategy

**What to store on Segment (avoid joins at query time):**

| Field | Source | Why Denormalize |
|-------|--------|-----------------|
| `published_at` | Video | Every query filters by date |
| `domain` | Channel | Every query filters by domain |
| `speaker_name` | Speaker | Display without join |
| `speaker_tier` | SpeakerCredibility | Ranking without join |
| `channel_name` | Channel | Display without join |
| `video_title` | Video | Display without join |

**Trade-off:** Storage cost vs query speed. For read-heavy workloads, denormalize aggressively.

### Pre-Computation Strategy

**Compute at ingest time (expensive, do once):**

| Computation | When | Store As |
|-------------|------|----------|
| Embeddings | Ingest | `segment.embedding` |
| Topic extraction | Ingest or batch | `segment.topics[]` |
| Quote detection | Ingest or batch | `Quote` entities |
| Sentiment/energy | Batch job | `segment.energy_score` |
| Viral potential | Batch job | `segment.viral_score` |

**Compute at query time (cheap, context-dependent):**

| Computation | When | Why |
|-------------|------|-----|
| Similarity score | Query | Depends on query vector |
| Recency weighting | Query | Depends on domain |
| Credibility filtering | Query | User preference |
| Aggregation/synthesis | Query | Depends on results |

### Caching Strategy

| Cache | Contents | TTL | Invalidation |
|-------|----------|-----|--------------|
| **Query cache** | Recent query results | 1 hour | New content ingested |
| **Embedding cache** | Query embeddings | 24 hours | Rarely changes |
| **Aggregation cache** | "Best practices for X" | 1 day | New content on topic |
| **Daily digest cache** | Pre-computed digests | 24 hours | Daily refresh |

### Search Ranking Formula

Combine multiple signals into a final score:

```python
final_score = (
    semantic_score * 0.4 +           # Vector similarity
    recency_score * 0.2 +            # Newer = better (for tech)
    credibility_score * 0.25 +       # TOP-tier = boost
    engagement_score * 0.1 +         # If we have analytics
    exact_match_boost * 0.05         # Keyword in text
)

# Recency score (domain-dependent)
if domain in ['ai-coding', 'ai-automation']:
    recency_weight = 0.3  # High - tech changes fast
else:
    recency_weight = 0.1  # Low - wisdom is timeless
```

### Query Pipeline Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│ 1. Query Understanding  │ ← Parse intent, extract filters
│    - Topic extraction   │
│    - Date range         │
│    - Speaker filter     │
│    - Domain inference   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. Query Embedding      │ ← Cache check, then LiteLLM
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Hybrid Search        │ ← SurrealDB: vector + filter + graph
│    - Vector similarity  │
│    - Full-text match    │
│    - Graph traversal    │
│    - Filter application │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. Re-ranking           │ ← Apply credibility, recency, etc.
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Aggregation          │ ← Dedupe, synthesize, format
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 6. Response Generation  │ ← LLM synthesis if needed
└─────────────────────────┘
```

### Batch Processing Jobs

| Job | Frequency | Purpose |
|-----|-----------|---------|
| **Topic extraction** | On ingest + daily catchup | Extract topics from segments |
| **Quote extraction** | On ingest + daily catchup | Find quotable moments |
| **Energy scoring** | Daily | Score segment energy/passion |
| **Viral scoring** | Daily | Predict clip potential |
| **Cross-project routing** | Daily | Match new content to projects |
| **Golden standard check** | Daily | Flag updates needed |
| **Stale content check** | Weekly | Flag outdated advice |
| **Persona refresh** | On speaker content ingest | Update persona agents |
| **Signature story detection** | Weekly | Find repeated stories across videos |

### Persona Agent Architecture

**Concept:** Build AI personas (CrewAI, LangChain, etc.) from speaker corpus. As new content is ingested, personas must update.

```
PersonaAgent
  ├─ speaker → Speaker
  ├─ framework: "crewai" | "langchain" | "autogen"
  ├─ system_prompt: "You are Patrick Bet-David..."
  ├─ style_profile: {vocabulary, sentence_structure, metaphor_patterns}
  ├─ knowledge_cutoff: date (last content ingested)
  ├─ corpus_summary: "Key beliefs, common topics, signature phrases"
  ├─ retrieval_config: {top_k, reranking, filters}
  └─ last_updated: date
```

**Persona Update Workflow:**

```
New video ingested for Speaker X
    │
    ▼
┌─────────────────────────────┐
│ 1. Detect speaker match     │ ← Is this from a known persona?
└───────────┬─────────────────┘
            │ yes
            ▼
┌─────────────────────────────┐
│ 2. Extract new knowledge    │
│    - New topics discussed   │
│    - New quotes             │
│    - Position changes?      │
│    - Style consistency?     │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 3. Update persona artifacts │
│    - Refresh corpus_summary │
│    - Update knowledge_cutoff│
│    - Add to retrieval index │
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 4. Validate persona         │ ← Test query: "Does this still sound like them?"
└───────────┬─────────────────┘
            │
            ▼
┌─────────────────────────────┐
│ 5. Flag contradictions      │ ← "Old stance vs new stance" review
└─────────────────────────────┘
```

**Example: Patrick Bet-David Persona**

```yaml
persona:
  name: "Patrick Bet-David"
  sources:
    - books: ["Your Next Five Moves", "Choose Your Enemies Wisely"]
    - channels: ["Valuetainment", "PBD Podcast"]
  corpus_stats:
    videos: 847
    segments: 12,340
    quotes: 523
    last_content: "2026-03-18"

  style_profile:
    tone: "direct, challenging, entrepreneurial"
    patterns:
      - "Let me tell you something..."
      - "Here's what nobody talks about..."
      - Uses chess/war metaphors
      - References immigrant experience

  knowledge_areas:
    - business_strategy: TOP
    - entrepreneurship: TOP
    - leadership: high
    - politics: mid  # has opinions but not primary expertise

  signature_stories:
    - title: "The Chess Story"
      frequency: 12
      summary: "Business as chess - think 5 moves ahead"
    - title: "Iranian Refugee Story"
      frequency: 8
      summary: "Coming to America, value of opportunity"
    - title: "Insurance Sales Story"
      frequency: 6
      summary: "Early career grinding, building discipline"
```

**Multi-Agent Scenarios (CrewAI/LangChain):**

| Scenario | Agents | Interaction |
|----------|--------|-------------|
| Expert Panel | Myron + PBD + Alex Hormozi | Debate business strategy |
| Technical Review | AILABS + mreflow + Alex Finn | Discuss MCP implementation |
| Cross-Domain | Myron (business) + Alex Finn (tech) | AI monetization strategy |

**Persona Freshness:**
- Flag if persona hasn't had new content in 30+ days
- Track "knowledge evolution" - did they change their mind on something?
- Version persona snapshots for "what did they think in Jan 2026 vs now?"

### API Design

```
/search
  POST {query, filters, limit}
  → Hybrid search with ranking

/segment/{id}
  GET → Full segment with context

/speaker/{id}/corpus
  GET → All content from speaker

/topic/{id}/synthesis
  GET → Aggregated best practices

/daily-digest
  GET {date, project?}
  → Daily intelligence report

/project/{id}/relevant
  GET → Content matching project objectives
```

---

## Known Limitations

### No Speaker Diarization in YouTube Transcripts

**Problem:** YouTube auto-generated transcripts are plain text - no indication of who is speaking. For solo videos this is fine, but for interviews/guest appearances we can't automatically attribute segments to speakers.

**Impact:**
- Guest appearance tracking requires manual tagging OR audio-based diarization
- Multi-speaker videos treated as "channel owner's content" by default
- Persona agents may include words spoken BY the expert and words spoken TO the expert

**Potential Solutions:**

| Approach | Effort | Quality |
|----------|--------|---------|
| **Manual tagging** | High | Perfect |
| **LLM inference** | Medium | Good (context clues like "So Myron, what do you think...") |
| **Audio diarization** | High | Excellent (requires downloading audio, running Whisper+pyannote) |
| **Ignore for MVP** | None | Accept limitation, revisit later |

**Recommendation:** For MVP, tag guest appearances at the VIDEO level (not segment). Accept that multi-speaker content is mixed. Revisit diarization when we have more data on how often this matters.

---

## Future Use Cases (Stress-Test Ideas)

These creative uses validate our data model. If we can support these, our structure is solid.

### 1. Contradiction & Disagreement Detection
**What:** Find when experts disagree on the same topic.
**Example:** "Alex Finn says always use environment variables, but AILABS says use .env files for local dev"
**Data Needed:** Topic extraction, claim extraction, speaker attribution
**Value:** Surface debates, show multiple perspectives, help user decide

### 2. Expert Prediction Tracking
**What:** Extract predictions experts make, track if they came true.
**Example:** "In Jan 2026, Alex predicted MCP would replace APIs. Status: Partially true as of March"
**Data Needed:** Prediction extraction (future-tense claims), publish date, follow-up linking
**Value:** Build trust scores, identify accurate forecasters

### 3. Analogy & Metaphor Library
**What:** Index all analogies and metaphors used to explain concepts.
**Example:** "Myron explains compound interest as 'planting oak trees' - search for more"
**Data Needed:** Analogy detection, concept linking, speaker style
**Value:** Teaching aid, content creation, understanding complex topics

### 4. Learning Path Generation
**What:** Generate a curriculum for a topic from beginner to advanced.
**Example:** "Learn MCP servers: Watch these 5 clips in order (2hr total from 20hr corpus)"
**Data Needed:** Topic difficulty scoring, prerequisite detection, segment sequencing
**Value:** Transform chaotic content into structured learning

### 5. Viral Clip Prediction & Performance Tracking
**What:** Score segments for "shareability" - short, punchy, emotional, surprising. Then track actual performance.
**Example:** "This 47-second segment has 94% viral potential - export it"
**Data Needed:** Sentiment analysis, punchiness scoring, duration, quotability
**Value:** Content repurposing, social media automation

**Phase 2 - Publishing & Analytics:**
If publishing your own clips/content, track engagement to validate and improve predictions:

| Metric | Purpose |
|--------|---------|
| Views | Raw reach |
| Watch time / retention | Did people actually watch? |
| Engagement (likes, comments, shares) | Resonance |
| Click-through (if teaser → full video) | Conversion |

**Feedback Loop:**
```
Predict viral potential → Publish clip → Track performance →
Compare prediction vs actual → Improve prediction model
```

**Data Model Extension (Future):**
```
PublishedClip
  ├─ source_segment → Segment
  ├─ platform: "youtube" | "tiktok" | "instagram" | "linkedin"
  ├─ published_at: date
  ├─ predicted_score: 0.94
  ├─ actual_metrics: {views, watch_time, engagement}
  └─ prediction_accuracy: calculated
```

### 6. Reference & Citation Graph
**What:** Extract when experts mention books, people, tools, other creators.
**Example:** "Alex Finn cites n8n docs, references Cole Medin's approach, recommends 'Building AI Apps'"
**Data Needed:** Entity extraction (people, books, tools, URLs), relationship mapping
**Value:** Build knowledge graph of influences, find recommended resources

**Firsthand vs Secondhand Knowledge:**

| Type | Example | Credibility |
|------|---------|-------------|
| **Firsthand** | "I built 50 MCP servers and learned..." | Direct experience |
| **Secondhand** | "Cole Medin says the best approach is..." | Citing another expert |
| **Citation** | "According to Anthropic's docs..." | Referencing official source |
| **Hearsay** | "I heard somewhere that..." | Low credibility |

**Why Track This:**
- Secondhand content can surface knowledge from experts NOT in your corpus
- Citation chains help verify claims ("Where did this advice originate?")
- Firsthand experience often more valuable than repeated advice
- Can trace back to primary sources for deeper learning

**Data Model Extension:**
```
Citation
  ├─ segment → Segment (where the citation appears)
  ├─ cited_speaker → Speaker (if citing a person)
  ├─ cited_source → string (book, docs, URL, etc.)
  ├─ citation_type: "firsthand" | "secondhand" | "official_docs" | "hearsay"
  ├─ quote: "the actual cited content"
  └─ context: "how it was used"
```

**Example Query:**
> "What does Anthropic's documentation say about tool use?"
>
> Could return segments where YOUR experts cite Anthropic docs, even if you haven't ingested the docs directly.

### 7. Question Extraction & FAQ Building
**What:** Extract all questions asked (by hosts, guests, rhetorically).
**Example:** "Top 10 questions asked to Myron Golden about pricing"
**Data Needed:** Question detection, topic linking, frequency counting
**Value:** Auto-generate FAQs, understand audience concerns

### 8. Energy & Passion Timeline
**What:** Track emotional intensity throughout a video, find peak moments.
**Example:** "Myron's energy peaks at 1:23:45 when discussing faith - flag for clip"
**Data Needed:** Sentiment/energy scoring per segment, speaker baseline
**Value:** Find the "fire" moments for clips, skip low-energy sections

### 9. Expert Style Profiles for Transfer
**What:** Analyze communication patterns to enable "explain in X's style."
**Example:** "Explain Docker in Myron Golden's style" → uses metaphors, biblical references, emphatic delivery
**Data Needed:** Style markers, vocabulary analysis, sentence structure, speaking patterns
**Value:** Persona agent fidelity, content creation in expert voice

### 10. Signature Story Detection
**What:** Detect when a speaker tells the same story/anecdote across multiple videos.
**Example:** "Myron has told the 'oak tree' story 7 times across 5 years - it's a signature"
**Data Needed:** Story fingerprinting, cross-video similarity, frequency tracking
**Value:** Identify core messages, most important anecdotes, speaker's "greatest hits"

**Why Repetition Matters:**
- Told 5+ times = **signature story** (core to their message)
- Told 2-4 times = **important anecdote** (resonates with them)
- Told once = **situational reference** (less significant)

**Data Model:**
```
SignatureStory
  ├─ speaker → Speaker
  ├─ title: "The Oak Tree Story" (inferred or manual)
  ├─ summary: "Compound growth explained through planting oak trees"
  ├─ occurrences → StoryOccurrence[]
  ├─ frequency: 7
  ├─ first_told: date
  ├─ most_recent: date
  ├─ significance_score: 0.95 (based on frequency + audience response)
  └─ canonical_segment → Segment (best version of the story)

StoryOccurrence
  ├─ story → SignatureStory
  ├─ segment → Segment
  ├─ video → Video
  ├─ timestamp: start/end
  └─ variation_notes: "This version includes the follow-up about patience"
```

**Detection Method:**
1. Compute semantic similarity between segments from same speaker
2. Cluster similar segments (>0.85 similarity)
3. If cluster spans 3+ videos = likely signature story
4. Human review to confirm and name

**Use Cases:**
- "What are Myron Golden's signature stories?" → List with links to best version
- "Show me every time PBD told the chess story" → All occurrences
- Persona agents prioritize signature stories in responses
- Content creation: "Include the oak tree analogy" (knows it's a proven winner)

### 10. Content Gap Analysis
**What:** Find topics your experts HAVEN'T covered.
**Example:** "No one in your corpus has discussed Kubernetes. Suggested channels to add: [list]"
**Data Needed:** Topic inventory, coverage mapping, external source suggestions
**Value:** Identify blind spots, curate new sources

---

### Data Model Validation

| Future Use Case | Data Requirements | Current Model Supports? |
|-----------------|-------------------|------------------------|
| Contradiction Detection | Topic + claim + speaker | ⚠️ Needs claim extraction |
| Prediction Tracking | Future-tense claims + dates | ⚠️ Needs prediction extraction |
| Analogy Library | Analogy detection + concept | ⚠️ Needs analogy extraction |
| Learning Paths | Difficulty + prerequisites | ⚠️ Needs difficulty scoring |
| Viral Prediction | Sentiment + punchiness | ⚠️ Needs sentiment scoring |
| Citation Graph | Entity extraction | ⚠️ Needs entity types |
| FAQ Building | Question detection | ⚠️ Needs question extraction |
| Energy Timeline | Segment-level sentiment | ⚠️ Needs sentiment per segment |
| Style Profiles | Vocabulary + patterns | ⚠️ Needs style analysis |
| Gap Analysis | Topic inventory | ✅ Supported with topics |

**Conclusion:** Our current model supports the foundation. These advanced uses need **enrichment pipelines** (LLM post-processing) on top of the base data.

---

## Advanced Creative Use Cases

### 11. Idea Genealogy Tracking
**What:** Track where ideas originate and how they spread through your expert network.
**Example:** "The 'modular MCP' pattern started with Alex Finn (Jan 12), got adopted by AILABS (Feb 3), now mreflow is teaching a variant (Mar 15)"
**Value:** See thought leadership in action, trace innovation origins, identify who's leading vs following
**Detection:** Topic + temporal analysis, cross-speaker similarity clustering

### 12. "What Would X Say?" Debate Simulator
**What:** Given a controversial topic or decision, simulate what each expert would argue based on their known positions, style, and values.
**Example:** "Should I bootstrap or raise funding?" → Generate Myron's argument (bootstrap, control) vs PBD's argument (strategic capital, scale fast)
**Value:** Get multiple perspectives without watching hours of content, stress-test decisions
**Requires:** Position extraction, values inference, argumentation patterns

### 13. Expert Blind Spot Detection
**What:** Find topics your expert network AVOIDS or has weak coverage on.
**Example:** "Your AI experts rarely discuss security. Your business experts never mention taxes. Gap in your knowledge base?"
**Value:** Identify what you DON'T know, find channels to add
**Detection:** Topic inventory vs expected topics for domain, coverage scoring

### 14. Contrarian Alert System
**What:** When new content contradicts established consensus among your experts, flag it immediately.
**Example:** "🚨 AILABS just recommended X, but this contradicts what Alex Finn, mreflow, AND Cole Medin all advise. Review?"
**Value:** Catch emerging disagreements, paradigm shifts, or potential misinformation
**Requires:** Position tracking, consensus detection, contradiction scoring

### 15. Teaching Style Matchmaker
**What:** Match your learning preferences to experts who teach that way.
**Example:** "You learn best with metaphors → Myron Golden. Step-by-step tutorials → Cole Medin. High-energy motivation → PBD. Dry technical depth → mreflow."
**Value:** Personalized learning paths, don't waste time on styles that don't click
**Requires:** Style profiling, user preference input, matching algorithm

### 16. Confidence Calibration Tracking
**What:** Track how confident experts are when making claims. Hedge words ("I think", "maybe", "probably") vs certainty ("always", "never", "definitely").
**Example:** "Alex Finn is 92% confident on n8n advice but only 60% confident on AI predictions. Weight accordingly."
**Value:** Know when to trust advice fully vs when expert is speculating
**Detection:** Linguistic analysis, hedge word detection, claim-confidence pairing

### 17. Audience Assumption Mapping
**What:** Detect what knowledge each expert ASSUMES their audience already has.
**Example:** "AILABS assumes Python proficiency. Alex Finn assumes n8n basics. Myron assumes no business background (explains everything)."
**Value:** Know if you're ready for a channel, find entry-point content
**Detection:** Explanation depth analysis, prerequisite detection, jargon density

### 18. Emotional Arc Mapping
**What:** Map the emotional journey of a video - where tension builds, where inspiration peaks, where it gets dry.
**Example:** "Minutes 0-5: setup (low energy). 12-18: conflict/tension (building). 45-50: breakthrough moment (peak). 55-60: call to action (high)."
**Value:** Skip to the good parts, understand content structure, learn storytelling patterns
**Requires:** Sentiment analysis over time, energy scoring, narrative structure detection

### 19. Cross-Expert Fact Verification
**What:** When one expert states a "fact," automatically check if other experts in your corpus confirm, contradict, or have commented on it.
**Example:** "Alex Finn says 'MCP servers should always use TypeScript' → AILABS confirms (Feb 2026), mreflow silent, no contradictions found."
**Value:** Crowd-sourced verification within your trusted network
**Requires:** Claim extraction, cross-reference matching, stance detection

### 20. "If You Liked This" Recommendation Engine
**What:** Based on a segment you found valuable, find similar insights across your entire corpus - not just same speaker or topic, but same VIBE.
**Example:** "You highlighted this Myron quote about patience → here's Alex Finn on delayed gratification, PBD on long-term thinking, and this Bible study on faith through waiting"
**Value:** Serendipitous discovery, cross-domain insights, thematic connections
**Requires:** Semantic similarity + vibe/theme extraction, cross-domain linking

---

### Data Model Validation (Advanced Use Cases)

| Creative Use Case | New Data Needed |
|-------------------|-----------------|
| Idea Genealogy | First-mention timestamps, adoption tracking |
| Debate Simulator | Position/values extraction per speaker per topic |
| Blind Spot Detection | Expected topic coverage by domain |
| Contrarian Alert | Consensus scoring, contradiction detection |
| Teaching Style Match | Style profiles, user preferences |
| Confidence Calibration | Hedge word analysis, certainty scoring |
| Audience Assumptions | Prerequisite detection, explanation depth |
| Emotional Arc | Time-series sentiment, narrative structure |
| Cross-Expert Verification | Claim extraction, stance detection |
| "If You Liked This" | Vibe/theme embeddings (beyond topic) |

---

## Technically Challenging Use Cases (Pushing Limits)

### 21. Predictive Content Analysis
**What:** Based on trending topics and each expert's patterns, predict what they'll cover NEXT.
**Example:** "Claude 4 just released. Based on patterns: AILABS will post within 48hrs (95% confidence), Alex Finn within a week, mreflow will wait for community feedback first."
**Challenge:** Temporal pattern modeling, topic trend detection, individual release cadence learning
**Technical:** Time-series prediction, event correlation, behavioral modeling

### 22. Real-Time Live Stream Analysis
**What:** During a live premiere or stream, analyze in real-time: extract quotes, detect topics, flag contradictions to previous content, identify clip-worthy moments.
**Example:** "🔴 LIVE: Myron just contradicted his 2024 stance on X. Timestamp flagged. Quote extracted. Clip boundary detected."
**Challenge:** Stream processing, real-time transcription, instant similarity search
**Technical:** Streaming ASR (Whisper), real-time embeddings, sub-second graph queries

### 23. Influence Causation vs Correlation
**What:** Determine if Expert A actually influenced Expert B, or if they independently arrived at similar conclusions.
**Example:** "Did Alex Finn's January MCP video influence AILABS's February approach, or did they both learn from Anthropic docs?"
**Challenge:** Causal inference, temporal ordering, citation chain analysis
**Technical:** Causal ML models, intervention analysis, counterfactual reasoning

### 24. Expert Voice Cloning for Audio Summaries
**What:** Generate audio summaries in the expert's actual voice (with permission/synthetic).
**Example:** "Play me a 2-minute summary of Myron's sales philosophy - in his voice."
**Challenge:** Voice synthesis, style transfer, ethical/legal considerations
**Technical:** Voice cloning (ElevenLabs, etc.), prosody matching, consent management

### 25. Counterfactual Expert Responses
**What:** Generate what an expert would LIKELY say about a topic they've never directly addressed.
**Example:** "Myron has never discussed AI directly. Based on his values and patterns, here's what he'd likely say about using AI in sales."
**Challenge:** Value extraction, reasoning pattern inference, domain transfer
**Technical:** Fine-tuned LLM on speaker corpus, constrained generation, confidence scoring

### 26. Multi-Modal Clip Understanding (Lazy Visual Analysis)
**What:** Detect when transcript references something visual, then go back to analyze those specific frames.
**Example:** "Alex says 'as you can see on screen' at 12:34 - trigger visual analysis, extract the n8n workflow diagram, OCR the node names, index it."

**The Pattern: Transcript-Triggered Visual Analysis**

Don't analyze ALL video frames (expensive, mostly talking heads). Instead:

```
1. Transcript Analysis
   └─ Detect visual reference phrases:
      - "as you can see..."
      - "look at this..."
      - "on screen we have..."
      - "let me show you..."
      - "this diagram shows..."

2. Flag Timestamp
   └─ Mark segment as "requires_visual: true"
   └─ Store timestamp range for later processing

3. Lazy Visual Fetch (batch job or on-demand)
   └─ Download video (or use yt-dlp to extract frames)
   └─ Extract frames at flagged timestamps
   └─ Run vision analysis:
      - OCR for text/code on screen
      - Diagram detection
      - UI element extraction
      - Screen recording analysis

4. Index Visual Content
   └─ Link extracted visual to segment
   └─ Store OCR text (searchable)
   └─ Generate visual embedding
   └─ Store frame image for display
```

**Data Model:**

```
VisualReference
  ├─ segment → Segment
  ├─ timestamp: 12:34.5
  ├─ trigger_phrase: "as you can see on screen"
  ├─ analyzed: boolean
  ├─ frame_url: "storage://frames/abc123.jpg"
  ├─ ocr_text: "function handleMCP() { ... }"
  ├─ visual_type: "code" | "diagram" | "ui" | "terminal" | "slides"
  ├─ visual_embedding: [vector]
  └─ extracted_entities: ["n8n", "webhook", "HTTP node"]
```

**Use Cases:**
- "Show me every diagram Alex drew about MCP" → visual search
- "Find code examples shown on screen" → OCR search
- "What UI did he click on?" → UI element extraction
- Link transcript explanation to actual visual shown

**Challenge:** Video storage/processing costs, accurate timestamp alignment, OCR quality on screen recordings
**Technical:** yt-dlp frame extraction, GPT-4V / Claude vision, Tesseract OCR, video keyframe detection

### 27. Argument Structure Extraction
**What:** Extract the logical structure of arguments: premises, evidence, conclusions, rebuttals.
**Example:** "Myron's argument for high-ticket: Premise 1 (value > price), Premise 2 (psychology of commitment), Evidence (case studies), Conclusion (charge more)."
**Challenge:** Argumentation mining, logic extraction, structure mapping
**Technical:** Argument mining NLP, discourse parsing, logic graphs

### 28. Expert "Mood" Detection Across Time
**What:** Track expert's overall sentiment/energy across months. Detect burnout, excitement phases, topic fatigue.
**Example:** "Alex Finn's energy on MCP content has declined 30% since January. Possible topic fatigue. His OpenClaw content energy is rising."
**Challenge:** Longitudinal sentiment, baseline calibration, topic-specific energy
**Technical:** Speaker-normalized sentiment, time-series anomaly detection

### 29. Collaborative Expert Discovery
**What:** Based on YOUR interaction patterns and what others with similar patterns found valuable, surface hidden gems.
**Example:** "Users who valued Myron's sales content also discovered high value in this obscure AILABS video about client psychology."
**Challenge:** User behavior modeling, collaborative filtering, cold start
**Technical:** Recommendation systems, implicit feedback, sparse matrix factorization

### 30. Semantic Diff Between Expert Versions
**What:** Track how an expert's explanation of the SAME topic has evolved. Show semantic diff.
**Example:** "Myron's 'value ladder' explanation 2022 vs 2026: Added AI component, removed outdated funnel reference, strengthened story example."
**Challenge:** Semantic versioning, concept alignment, diff visualization
**Technical:** Semantic similarity with alignment, change extraction, version graphs

---

### Confirmed Advanced Use Cases (Engineer For These)

Based on review, these advanced use cases should be factored into system design:

| # | Use Case | Priority | Data Model Impact |
|---|----------|----------|-------------------|
| **25** | Counterfactual Responses | HIGH | Speaker values/positions extraction, reasoning patterns |
| **26** | Lazy Visual Analysis | HIGH | `VisualReference` entity, transcript trigger detection |
| **29** | Collaborative Discovery | MEDIUM | User interaction tracking, value signals |

**NOT prioritized (cool but not essential):**
- #24 Voice Cloning (creepy factor)
- #21-23 (complex ML, lower ROI for now)
- #27-28, #30 (nice-to-have, not core)

### Technical Infrastructure for Confirmed Use Cases

| Use Case | Infrastructure Need |
|----------|---------------------|
| Counterfactuals (#25) | Speaker corpus fine-tuning OR rich retrieval + prompting |
| Lazy Visual Analysis (#26) | Frame extraction (yt-dlp), vision API (GPT-4V/Claude), OCR |
| Collaborative Discovery (#29) | User behavior logging, recommendation engine |

---

## Open Questions

| Question | Impact | Status |
|----------|--------|--------|
| Optimal chunk size for quotes vs context? | Retrieval quality | Needs testing |
| LLM for topic/quote extraction? | Cost, quality | Not decided |
| How to score "impact" of a quote? | Highlight quality | Needs research |
| Multi-speaker video handling? | Persona accuracy | See limitation above |
| Do we need audio diarization? | Guest appearance accuracy | Depends on use case priority |

---

## Reference Products

### WhisperTranscribe (UI/Feature Inspiration)

**URL:** https://www.whispertranscribe.com/

WhisperTranscribe turns one recording into 57+ content types. Key features we want to replicate:

### Content Type Catalog (from WhisperTranscribe)

WhisperTranscribe organizes content types by **persona filters**:
- Podcaster, YouTuber, Student, Meetings, Researcher, Educator
- Courses & Webinars, Journalist, Coach, UX Researcher, Church, Sales Calls

**Full Content Type List:**

| Category | Content Types |
|----------|---------------|
| **Summaries** | Summary By Speaker, Summary By Topic, Show Notes (3 versions) |
| **Titles & SEO** | Titles, YouTube Description, YouTube Tags, Podcast Keywords, Episode Titles |
| **Social Media** | Tweets, Twitter Threads, Instagram Posts, Facebook Posts, LinkedIn Posts, LinkedIn Carousel |
| **Long-form** | Blog Post, Newsletter |
| **Analysis** | Sentiment Analysis, Language Analysis, Contradictions & Fact Checking, Important Moments, Analogies |
| **Action-oriented** | Actionable Tips, Action Items, Next Steps, Key Themes, Pain Points, Customer Needs |
| **Questions** | FAQ, Discussion Questions, Follow Up Questions (Journalist), Follow Up Questions (UX Research), Bible Study Questions, Questions Asked |
| **Meeting/Sales** | Meeting Minutes, Session Worksheet, Follow Up Email (Sales), Follow Up Email (Meetings) |
| **Education** | Study Materials, Course Description, Discussion Guide |
| **Faith/Church** | Relevant Bible Sections, Five Day Devotional |
| **Research** | UX Report |
| **Video** | YouTube Short Scripts |
| **Custom** | User-defined content types |

### Our Priority Mapping

| Priority | Content Types | Why |
|----------|---------------|-----|
| **HIGH** | Summary By Speaker, Summary By Topic, Key Themes, Actionable Tips, Important Moments, Analogies | Core persona/knowledge extraction |
| **MEDIUM** | Titles, Show Notes, FAQ, Discussion Questions, Action Items | Content repurposing |
| **LOW** | Social posts, Blog, Newsletter, SEO tags | Marketing automation (future) |
| **DOMAIN-SPECIFIC** | Bible sections, Devotionals, UX Report, Sales follow-ups | Per-channel customization |

### Visual Hub Concept

The "Visual Hub" pattern from WhisperTranscribe:
1. Input: Video/audio URL or file
2. Processing: Transcription + AI analysis
3. Output: Dashboard with all generated content types
4. Action: Click to copy, edit, or export any output

**Key Feature: Timestamp-Linked Transcript Selection**

From the Visual Hub screenshot:
- **Three tabs**: Content Hub | Visual Hub | Transcript
- **Aspect ratio selector**: 9:16 (TikTok/Reels), 16:9 (YouTube), 1:1 (Instagram)
- **Clip navigation**: "Video clip 2/8" with prev/next arrows
- **Export clip button**: One-click export of selected segment

**The Magic:**
1. User highlights ANY text in the transcript
2. System automatically selects that exact video segment (timestamps!)
3. Video player jumps to that moment
4. Captions overlay on video with theming/styling options
5. One click to export as clip with burned-in captions

**This is why timestamps are non-negotiable.** Without word-level or segment-level timestamps, this feature is impossible.

**For KnowledgeStack Visual Hub:**
- Transcript with timestamps (clickable to jump to video)
- Text selection → video segment selection
- Auto-generated chapters with "jump to" links
- Extracted quotes (scored by impact)
- Topic tags
- Summary at different lengths (tweet, paragraph, full)
- Clip suggestions with start/end times
- Export with caption overlay (future - requires video processing)

### Clip Extraction Feature

WhisperTranscribe: "Instantly isolates the corresponding video segment and generates a vertical video clip with animated, synchronized captions"

**For KnowledgeStack:**
- Identify "clip-worthy" segments (high engagement, complete thought, quotable)
- Provide start/end timestamps
- Integration with ffmpeg or video editing API to extract clips
- Caption overlay generation

---

## Implementation Status (2026-03-20)

### Infrastructure Ready

| Component | Status | Location |
|-----------|--------|----------|
| SurrealDB | Running | Banner:5040 |
| Surrealist UI | Running | Banner:5041 |
| LiteLLM Embeddings | Running | 10.0.0.27:2764 |
| Transcript Storage | Mounted | /mnt/foundry_resources/transcripts |

### Schema v2 Applied

| Entity | Purpose | Status |
|--------|---------|--------|
| `speaker` | Persona entity with aliases | Active |
| `speaker_credibility` | Per-topic tiers (top/high/mid/low) | Active |
| `segment` | Chunks with timestamps + denormalized fields | Active |
| `visual_reference` | Lazy visual analysis triggers | Active |
| `quote` | Notable statements for highlight reels | Active |
| `signature_story` | Stories told multiple times | Active |
| `project` | Cross-project intelligence routing | Active |
| `appears_in` / `speaks_in` | Speaker-video/segment relationships | Active |

**Vector Index:** 1536 dimensions (text-embedding-3-small)

### Scripts Ready

| Script | Purpose | Key Features |
|--------|---------|--------------|
| `batch_transcript_fetcher.py` | Fetch from YouTube | Timestamps preserved, description captured |
| `load_to_surrealdb.py` | Ingest to SurrealDB | 500-char chunks, visual triggers, guest extraction, denormalization |

### Current Data State

- **357 segments** (legacy format without timestamps)
- **57 videos** fetched with timestamp-preserving fetcher (pending re-ingest)

### Next Steps to Full Value

1. **Re-fetch transcripts** with updated fetcher to get timestamps
2. **Clear and re-ingest** with v2 loader
3. **Test Visual Hub queries** (segment selection by timestamp)
4. **Test hybrid search** (vector + domain + recency)

---

## Related Documents

- [Product Brief](./product-brief-knowledge-2026-01-30.md) - Full product context
- [RAG Database Survey](../../spike/surreal-rag/docs/RAG_DATABASE_SURVEY.md) - Database selection research
- [Spike Log](../../spike/surreal-rag/docs/SPIKE_LOG.md) - Technical spike progress

---

*This document is the filter. When in doubt, check if the decision serves the use cases above.*
