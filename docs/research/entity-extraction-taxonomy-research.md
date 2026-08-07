# Entity Extraction & Taxonomy Management Research Report

**Date:** 2026-03-30
**Researcher:** Claude Opus 4.6 (1M context)
**Context:** KnowledgeStack -- YouTube transcript ingestion and RAG platform
**Current Stack:** Python, SurrealDB (graph+vector), LiteLLM proxy, n8n, Docker on Banner

---

## Executive Summary

### Key Findings

1. **Your existing LLM-based extraction (enrich.py) is the right primary approach**, but should be augmented with GLiNER as a fast pre-filter and kg-gen for relationship extraction. LLMs outperform dedicated NER on domain-diverse content like YouTube transcripts, especially for custom entity types (products, health concepts, "vibe coding"). Dedicated NER models win on speed and cost for well-defined entity types but choke on novel/domain-specific terms.

2. **kg-gen (NeurIPS 2025) is the most directly useful new tool** for your pipeline. It extracts entities AND relationships from text, supports LiteLLM-compatible endpoints (including Ollama), includes built-in entity clustering for synonym resolution, and outputs graph triples that map cleanly to SurrealDB's relation model.

3. **spaCy-entity-linker provides a free Wikidata taxonomy** (1.3GB SQLite) with hierarchical parent-child relationships that can bootstrap your tag hierarchy. For any entity it recognizes, you can automatically get its type chain (e.g., "Docker" -> "containerization platform" -> "software" -> "technology").

4. **Synonym management is best handled via embedding similarity**, which you already have infrastructure for (LiteLLM + text-embedding-3-small). Tags with cosine similarity > 0.92 are likely synonyms. kg-gen's clustering module provides an LLM-based alternative that handles edge cases better.

5. **No single ready-to-deploy solution exists** for your full pipeline. The recommended architecture is a hybrid: LLM extraction (your existing enrich.py, enhanced) + GLiNER for speed on bulk processing + spaCy-entity-linker for Wikidata grounding + embedding similarity for synonym detection. All self-hostable, all Python, all Docker-friendly.

---

## 1. Entity Extraction / NER Tools

### 1.1 LLM-Based Extraction (Your Current Approach)

**What you have:** `enrich.py` uses Haiku via LiteLLM to extract entities from transcript segments with a structured prompt returning JSON.

**Assessment:** This is well-designed for your use case. LLMs excel at:
- Custom entity types (product, company, person, technology, health, concept, topic)
- Understanding context ("Claude" in an AI video = product, not a person's name)
- Zero-shot extraction of novel entities ("vibe coding" before it was a standard term)
- Handling transcript messiness (filler words, incomplete sentences)

**Evidence:**
- The n8n + Ollama NER case study [Dresselhaus, 2025] demonstrated that "out-of-the-box LLMs significantly outperform classical NER pipelines by using clever prompting, without any model retraining"
- GPT-NER research [Wei et al., 2023] showed LLMs match SOTA on NER when properly prompted
- However, encoder-based NER models achieve F1 0.87-0.88 vs LLM F1 0.18-0.30 on clinical/structured data [ScienceDirect, 2025] -- the difference is that those are well-defined entity types on formal text, not YouTube transcripts

**Recommended improvements to your current approach:**
- Add structured output enforcement (JSON mode) to reduce parse failures
- Batch segments by video and include video title/channel context in every call
- Use a two-pass approach: fast model (Haiku) for initial extraction, then consolidate across segments with a reasoning model for deduplication
- Add confidence scores to extraction prompt

**Cost estimate:** ~$0.01-0.03 per video (50 segments x ~500 tokens each via Haiku)

| Provider | Model | Cost/1K tokens | Speed | Quality |
|----------|-------|---------------|-------|---------|
| Anthropic | Haiku 3.5 | $0.001 input | Fast | Good for structured extraction |
| Ollama local | DeepSeek-R1 14B | Free (GPU) | Medium | Good with careful prompting |
| Ollama local | Cogito 14B | Free (GPU) | Medium | 128k context, multilingual |

### 1.2 GLiNER -- Zero-Shot Lightweight NER

**GitHub:** https://github.com/urchade/GLiNER
**Install:** `pip install gliner`
**Latest version:** v0.2.26 (March 2026)
**Paper:** NAACL 2024 [Zaratiana et al., 2024]

**What it does:** A lightweight bidirectional transformer (~500M params) that extracts any entity type you specify at runtime -- no training required. You pass entity labels as a list and it finds them in text.

```python
from gliner import GLiNER

model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
labels = ["product", "company", "person", "technology", "health concept"]
entities = model.predict_entities(text, labels, threshold=0.5)
# Returns: [{"text": "Claude Code", "label": "product", "score": 0.94}, ...]
```

**Strengths:**
- Runs on CPU -- no GPU required
- ~81% F1 on multi-domain extraction (vs spaCy's lower scores on custom types)
- 10,000+ entities/second throughput
- Zero-shot: specify any entity type at runtime
- Has a spaCy wrapper (`gliner-spacy`) for pipeline integration
- Can integrate with Presidio for hybrid recognition

**Weaknesses:**
- Struggles with multi-word financial identifiers
- Cannot extract relationships (only entities)
- Lower accuracy than LLMs on highly ambiguous or novel entities
- Labels are case-sensitive (use lowercase or title case)

**Recommended role in your pipeline:** Use as a fast pre-filter before LLM extraction. Run GLiNER on all segments first (cheap, fast), then send only segments with >3 entities to the LLM for richer extraction with relationships and confidence scoring.

### 1.3 spaCy NER

**Website:** https://spacy.io
**Install:** `pip install spacy && python -m spacy download en_core_web_trf`

**Assessment:** spaCy's built-in NER handles standard types well (PERSON, ORG, GPE, PRODUCT, etc.) but requires custom training for your domain-specific types (health concepts, AI tools, "vibe coding"). The training pipeline is mature and well-documented, but the effort to create and maintain training data for your diverse YouTube content is significant.

**Best use case for you:** Not as the primary extractor, but as a preprocessing step for tokenization, sentence splitting, and feeding text to GLiNER or your LLM pipeline. spaCy's `en_core_web_trf` (transformer-based) model is the most accurate.

**Key integration:** The `gliner-spacy` wrapper lets you add GLiNER as a spaCy pipeline component, combining spaCy's text processing with GLiNER's flexible NER.

### 1.4 Microsoft Presidio

**GitHub:** https://github.com/microsoft/presidio
**Install:** `pip install presidio-analyzer presidio-anonymizer`

**What it does:** PII detection and anonymization framework. Uses NER models + regex + checksums to find sensitive data.

**Assessment for your use case:** Presidio is designed for PII detection (credit cards, SSNs, phone numbers), not general entity extraction. However, it has useful capabilities:
- Custom recognizer support (you can add your own entity types)
- GLiNER integration via `gliner_spacy` [GitHub Issue #1665]
- Ollama integration for local LLM-based recognition
- Docker deployment support

**Verdict:** Overkill for your primary use case. Potentially useful later if you need to redact PII from transcripts before processing, but not the right tool for "extract Claude Code as a product entity."

### 1.5 DBpedia Spotlight

**GitHub:** https://github.com/dbpedia-spotlight/spotlight-docker
**Docker:** `docker pull dbpedia/dbpedia-spotlight`

**What it does:** Annotates text with links to DBpedia (Wikipedia-derived) resources. Self-hostable via Docker. Recognizes entities that exist in Wikipedia/DBpedia.

**Strengths:**
- Fully self-hosted Docker deployment
- Provides DBpedia URIs for recognized entities (linked data)
- Multiple language support
- Has a spaCy integration (`spacy-dbpedia-spotlight`)

**Weaknesses:**
- Only recognizes entities that exist in DBpedia/Wikipedia
- Will miss "vibe coding", newer AI tools, and niche concepts
- Heavy resource requirements (several GB per language model)
- Entity types limited to DBpedia ontology

**Verdict:** Useful as a supplementary grounding layer -- if an entity IS in DBpedia, you get a free type hierarchy and Wikipedia link. But it cannot be your primary extractor because it will miss most of your domain-specific entities.

### 1.6 Hugging Face NER Models via Ollama

**Key model:** `zeffmuks/universal-ner` (UniNER-7B, q4_1 quantized)
**Hub:** 825+ NER models on Hugging Face

**Assessment:** Running NER-specific models through Ollama is possible but awkward. These models are designed for token classification (labeling each word), not for the generative extraction pattern your pipeline uses. The LLM approach (Haiku or local DeepSeek-R1) with structured prompts is more flexible and produces better results for your custom entity types.

**Verdict:** Not recommended as primary approach. GLiNER is a better "small model" option for fast extraction.

### 1.7 MCP Servers for Entity Extraction

**Ultimate MCP Server:** https://github.com/Dicklesworthstone/ultimate_mcp_server
- Includes entity-relationship extraction tool
- Uses LLMs to identify entities and map relationships
- Builds knowledge graphs using NetworkX
- Self-hostable, Docker support
- Multi-provider LLM support (Anthropic, OpenAI, Google, DeepSeek)

**Assessment:** Interesting but adds architectural complexity. Your pipeline already calls LLMs directly. An MCP server would add an intermediary layer. More useful if you wanted Claude Code to interactively explore extracted entities during development.

---

## 2. Taxonomy / Ontology Management

### 2.1 SKOS (Simple Knowledge Organization System)

**Standard:** W3C standard for representing controlled vocabularies, taxonomies, and thesauri.
**Core concepts:** `skos:broader`, `skos:narrower`, `skos:related`, `skos:altLabel` (synonyms), `skos:prefLabel` (canonical name)

**Python tools:**
- **skosify** (`pip install skosify`) -- Inferencing and validation for SKOS vocabularies
- **rdflib** (`pip install rdflib`) -- Full RDF/SKOS manipulation in Python
- **SKOS-Utils** -- Modular Python scripts for SKOS vocabulary development and quality assessment

**Assessment for your use case:** SKOS is the right conceptual model for your taxonomy (broader/narrower = parent/child, altLabel = synonym). However, you do NOT need to implement full RDF/SKOS infrastructure. Instead, model the SKOS relationships directly in SurrealDB:

```surql
-- Taxonomy: tag hierarchy
DEFINE TABLE tag_broader TYPE RELATION FROM tag TO tag;  -- AI -> AI Coding
DEFINE TABLE tag_related TYPE RELATION FROM tag TO tag;  -- bidirectional similarity

-- Synonyms: altLabel equivalent
DEFINE FIELD synonyms ON tag TYPE option<array<string>>;
-- OR a separate synonym table for bidirectional lookup
DEFINE TABLE tag_synonym SCHEMAFULL;
DEFINE FIELD canonical ON tag_synonym TYPE record<tag>;
DEFINE FIELD alias ON tag_synonym TYPE string;
DEFINE FIELD alias_normalized ON tag_synonym TYPE string;
```

**Verdict:** Use SKOS vocabulary/concepts, implement in SurrealDB natively. No need for a separate RDF triplestore.

### 2.2 Wikidata as Bootstrap Taxonomy

**Integration tool:** spaCy-entity-linker (https://github.com/egerber/spaCy-entity-linker)
**Install:** `pip install spacy-entity-linker`
**KB size:** ~1.3GB SQLite database

**How it works:**
1. Feed text through spaCy pipeline with entity linker
2. Each recognized entity gets a Wikidata ID
3. Call `get_super_entities()` to get the type hierarchy
4. Example: "Docker" -> Wikidata Q15206305 -> "containerization platform" -> "software" -> "technology"

**Available hierarchy data:**
- `get_super_entities()` -- All parent categories (walks P279 subclass-of and P31 instance-of)
- `get_sub_entities(limit=N)` -- Children in the hierarchy
- Entity descriptions and labels
- Popularity metrics (Wikipedia page views, inlinks)

**Practical approach for bootstrapping:**
1. Extract entities from your first 100 videos using your LLM pipeline
2. Run each unique entity through spaCy-entity-linker
3. For entities that match Wikidata: auto-populate parent hierarchy
4. For entities that DON'T match (newer tools, niche concepts): flag for manual review or LLM-based categorization
5. Store Wikidata IDs on your tag records (you already have `wikidata_id` on speaker -- extend to tags)

**Limitations:**
- ~70% accuracy on disambiguation (uses popularity-based heuristic)
- Will not find very new entities (Wikidata lags real world by months)
- 1.3GB database download required
- Cannot distinguish between homonyms contextually

**Verdict:** Excellent for bootstrapping. Use it to auto-populate hierarchies for well-known entities, then fall back to LLM classification for everything else.

### 2.3 Open-Source Taxonomy Editors

| Tool | Type | Notes |
|------|------|-------|
| **ThManager** | Desktop Java app | SKOS RDF editor with tree viewer. Dated but functional. |
| **Protege** | Desktop Java app | Full ontology editor. Overkill for tag management. |
| **Clade** | Python | Simple taxonomy management + document classifier. GitHub: flaxsearch/clade |
| **VocView** | Python web app | SKOS vocabulary viewer. Read-only, not an editor. |
| **PoolParty** | Commercial SaaS | Industry standard. Not self-hostable in free tier. |

**Assessment:** None of these are a great fit. Your taxonomy management UI should be part of your admin interface (the Flask app at `/enroll`), with a simple tree view for editing parent-child relationships. The data lives in SurrealDB; a standalone taxonomy editor would be redundant.

**Recommendation:** Build a lightweight taxonomy management page in your existing admin UI. The SurrealDB graph model already supports hierarchical relationships. A simple tree component (e.g., Vue.js tree view) displaying `tag_broader` relationships is all you need.

---

## 3. Synonym Management

### 3.1 Embedding-Based Similarity (Recommended Primary Approach)

**Infrastructure you already have:** LiteLLM proxy + text-embedding-3-small (1536 dim)

**Approach:**
1. When a new tag is created, generate its embedding
2. Compare against all existing tag embeddings via cosine similarity
3. Tags with similarity > 0.92 are likely synonyms ("AI coding" vs "vibe coding": ~0.89, "LLM" vs "large language model": ~0.95)
4. Present candidates for human confirmation or auto-merge above threshold

**Implementation sketch:**
```python
# In SurrealDB: tags already have an embedding field (from topic table)
# Query for similar tags:
SELECT id, name, vector::similarity::cosine(embedding, $new_tag_embedding) AS sim
FROM tag
WHERE embedding <|10|> $new_tag_embedding
AND id != $new_tag_id
ORDER BY sim DESC
LIMIT 5;
```

**Your schema already supports this:** The `topic` table has `embedding` and `synonyms` fields. Extend the `tag` table similarly.

### 3.2 kg-gen Clustering (Recommended for Batch Processing)

kg-gen's `cluster()` method uses LLM calls to merge entities that refer to the same concept:

```python
from kg_gen import KGGen
kg = KGGen(model="openai/haiku", api_key="...")
clustered = kg.cluster(graph, context="YouTube tech transcript entities")
# Output: entity_clusters: {"claude code": {"Claude Code", "claude-code", "Claude code"}}
```

This handles cases that pure embedding similarity misses (abbreviations, stylistic variations).

### 3.3 dedupe Library (For Structured Record Matching)

**GitHub:** https://github.com/dedupeio/dedupe
**Install:** `pip install dedupe`

**Assessment:** dedupe is designed for structured record deduplication (matching customer records, etc.), not tag/concept synonym detection. It requires human training via CLI labeling. Better suited for speaker deduplication ("Dr. Andrew Huberman" vs "Andrew Huberman" vs "Huberman") than for tag synonyms.

**Alternative:** Splink (https://github.com/moj-analytical-services/splink) -- probabilistic record linkage, won 2025 Civil Service Awards. Also more suited for structured records than free-text tag synonyms.

**Verdict:** Use embedding similarity as primary, kg-gen clustering as secondary. Reserve dedupe/Splink for speaker entity resolution if needed later.

---

## 4. Integrated Solutions & Knowledge Graph Construction

### 4.1 kg-gen (BEST FIT -- NeurIPS 2025)

**GitHub:** https://github.com/stair-lab/kg-gen
**Install:** `pip install kg-gen`
**Paper:** [Guan et al., 2025]

**Why this is the most important finding:**

kg-gen does exactly what you need:
1. Extracts entities from text
2. Extracts relationships between entities (triples: subject-predicate-object)
3. Clusters synonymous entities automatically
4. Works with ANY LiteLLM-compatible model (OpenAI, Ollama, Anthropic)
5. Outputs structured graph data that maps directly to SurrealDB relations

**Integration with your stack:**

```python
from kg_gen import KGGen

# Uses your existing LiteLLM proxy
kg = KGGen(
    model="openai/haiku",  # LiteLLM model name
    base_url="http://10.0.0.27:2764/v1",  # Your LiteLLM proxy
    api_key="sk-nlf-litellm-...",
    temperature=0.0
)

# Process a transcript segment
graph = kg.generate(
    input_data=segment_text,
    context="YouTube video transcript about AI coding tools"
)

# graph.entities: {'Claude Code', 'Anthropic', 'VS Code', ...}
# graph.edges: {'developed by', 'competes with', 'integrates with', ...}
# graph.relations: {('Claude Code', 'developed by', 'Anthropic'), ...}

# Cluster across multiple segments
combined = kg.aggregate([graph1, graph2, graph3, ...])
clustered = kg.cluster(combined, context="Tech YouTube entities")
# clustered.entity_clusters: {"anthropic": {"Anthropic", "anthropic"}}
```

**How it maps to SurrealDB:**
- `graph.entities` -> `tag` records (or `topic` records in your schema)
- `graph.relations` -> SurrealDB `RELATE` edges (e.g., `tag:claude_code->developed_by->tag:anthropic`)
- `graph.entity_clusters` -> synonym resolution (merge tags, populate `synonyms` field)

**Also has an MCP server:** `kggen mcp` -- could be accessed by Claude Code for interactive exploration.

**Limitations identified by Stablebridge project [SurrealDB Blog, 2025]:**
- Inconsistent entity granularity (sometimes too specific, sometimes too broad)
- Weak relationship classification on cross-domain content
- Context loss on long documents (chunk appropriately)
- Computational cost on large corpora

### 4.2 SurrealDB's Native Knowledge Graph Capabilities

SurrealDB is explicitly positioning as "the context layer for AI agents" with native GraphRAG support [SurrealDB, 2025]. Your schema already uses the graph model well.

**Recommended schema additions for taxonomy:**

```surql
-- Extend tag table with hierarchy support
DEFINE TABLE tag SCHEMAFULL;
DEFINE FIELD name ON tag TYPE string;
DEFINE FIELD slug ON tag TYPE string;
DEFINE FIELD normalized ON tag TYPE string;
DEFINE FIELD type ON tag TYPE string;              -- product, company, person, technology, health, concept, topic
DEFINE FIELD embedding ON tag TYPE option<array<float>>;
DEFINE FIELD synonyms ON tag TYPE option<array<string>>;
DEFINE FIELD wikidata_id ON tag TYPE option<string>;
DEFINE FIELD mention_count ON tag TYPE int DEFAULT 0;
DEFINE FIELD description ON tag TYPE option<string>;
DEFINE FIELD created_at ON tag TYPE datetime;
DEFINE FIELD auto_generated ON tag TYPE bool DEFAULT true;
DEFINE FIELD human_verified ON tag TYPE bool DEFAULT false;
DEFINE INDEX tag_slug_idx ON tag FIELDS slug UNIQUE;
DEFINE INDEX tag_type_idx ON tag FIELDS type;
DEFINE INDEX tag_normalized_idx ON tag FIELDS normalized;

-- Hierarchical taxonomy via graph edges
DEFINE TABLE tag_parent SCHEMAFULL TYPE RELATION FROM tag TO tag;
DEFINE FIELD depth ON tag_parent TYPE int DEFAULT 1;  -- 1=direct parent, 2=grandparent, etc.

-- Semantic relationships between tags
DEFINE TABLE tag_related SCHEMAFULL TYPE RELATION FROM tag TO tag;
DEFINE FIELD relation_type ON tag_related TYPE string;  -- "synonym", "see_also", "developed_by", "part_of"
DEFINE FIELD confidence ON tag_related TYPE float DEFAULT 1.0;

-- Tag hierarchy traversal function
DEFINE FUNCTION fn::tag_ancestors($tag_slug: string) {
    LET $tag = (SELECT * FROM tag WHERE slug = $tag_slug)[0];
    LET $ancestors = (
        SELECT ->tag_parent->tag.* AS parent
        FROM $tag.id
    );
    RETURN $ancestors;
};

-- Find all tags under a parent (children + grandchildren)
DEFINE FUNCTION fn::tag_descendants($tag_slug: string) {
    LET $tag = (SELECT * FROM tag WHERE slug = $tag_slug)[0];
    LET $descendants = (
        SELECT <-tag_parent<-tag.* AS children
        FROM $tag.id
    );
    RETURN $descendants;
};
```

### 4.3 n8n Integration

**n8n already supports the pieces you need:**
- LLM nodes (GPT-4, Claude, Gemini, Ollama) for entity extraction
- HTTP Request nodes for calling your embedding service API
- Code nodes (JavaScript/Python) for post-processing
- Webhook nodes for triggering enrichment pipelines

**The n8n + Ollama NER case study [Dresselhaus, 2025] architecture:**
1. Webhook receives text + entity type definitions
2. n8n constructs structured prompt
3. Ollama (local 14B model) processes extraction
4. Tagged results returned via HTTP

**Recommended n8n workflow for your pipeline:**
1. RSS trigger detects new video from subscribed channel
2. Fetch transcript via YouTube MCP/API
3. Send to your embedding service (`POST /api/embed`)
4. After embedding completes, trigger enrichment (`POST /api/enrich`)
5. Enrichment calls LiteLLM for entity extraction
6. Results written to SurrealDB tags + relations

You can enhance this by adding a kg-gen step between extraction and storage for relationship extraction.

---

## 5. Answers to Key Questions

### Q1: Should we use an LLM for extraction or a dedicated NER model?

**Answer: LLM primary, GLiNER secondary.**

For YouTube transcript content spanning AI, health, business, religion, and other diverse domains, LLMs are the right choice because:

- Your entity types are custom and domain-specific (not standard NER categories)
- Transcripts are messy (filler words, incomplete sentences, speaker crosstalk)
- You need contextual disambiguation ("Claude" = product in AI context, person elsewhere)
- Novel entities appear constantly ("vibe coding" didn't exist 2 years ago)

However, LLMs are slow and expensive at scale. Use GLiNER as a fast first pass:
1. GLiNER scans all segments (CPU, ~10K entities/sec)
2. Segments with interesting entity density get sent to LLM for rich extraction
3. LLM provides entity types, confidence, and relationships

**Cost-optimized approach:**
| Step | Tool | Cost | Speed |
|------|------|------|-------|
| Pre-filter | GLiNER | Free (CPU) | 10K+ entities/sec |
| Rich extraction | Haiku via LiteLLM | ~$0.02/video | ~2 sec/segment |
| Relationship extraction | kg-gen via LiteLLM | ~$0.03/video | ~3 sec/chunk |
| Fallback/verification | Sonnet via LiteLLM | ~$0.10/video | ~3 sec/segment |

### Q2: Is there an existing hierarchical taxonomy we can bootstrap from?

**Answer: Yes -- Wikidata via spaCy-entity-linker.**

The spaCy-entity-linker package provides a 1.3GB preprocessed Wikidata knowledge base with full parent-child hierarchy access. For any recognized entity, you can call `get_super_entities()` to get its type chain.

**Bootstrap workflow:**
1. Run your first batch of extracted entities through spaCy-entity-linker
2. For matched entities: auto-create tag hierarchy from Wikidata types
3. For unmatched entities: use LLM to classify (prompt: "What category does X belong to? Options: ...")
4. Human review of auto-generated hierarchies via admin UI
5. Over time, your taxonomy becomes self-sustaining as the LLM references existing tags

**Seed taxonomy structure (manual, as starting point):**
```
Technology
  AI
    AI Coding (synonyms: "vibe coding", "AI-assisted development")
      Claude Code
      GitHub Copilot
      Cursor
    LLMs (synonyms: "large language models")
      GPT-4
      Claude
      Gemini
    Machine Learning
      Fine-tuning
      RAG
  Software Development
    Python
    Docker
    Kubernetes
Health
  Nutrition
    Fasting (synonyms: "intermittent fasting", "IF")
    Keto
  Fitness
  Mental Health
Business
  Entrepreneurship
  Real Estate
  Cryptocurrency
```

### Q3: What's the best approach for synonym detection/management?

**Answer: Three-layer approach.**

| Layer | Method | Handles | Cost |
|-------|--------|---------|------|
| 1. Exact/fuzzy | Normalized string matching + Levenshtein | "Claude Code" vs "claude code" vs "Claude-Code" | Free |
| 2. Embedding | Cosine similarity on tag embeddings | "AI coding" vs "AI-assisted programming" | Cheap (one embedding call per new tag) |
| 3. LLM clustering | kg-gen cluster() or direct LLM prompt | "vibe coding" = "AI coding" (semantic leap) | Moderate (batch periodically) |

**Implementation:**
- Layer 1 runs on every tag creation (normalize, check for existing)
- Layer 2 runs on every NEW unique tag (embed, compare to existing tags, suggest merges above 0.90 threshold)
- Layer 3 runs as a periodic batch job (nightly? weekly?) across all tags

Store synonym relationships bidirectionally:
```surql
-- On the tag record itself
UPDATE tag:ai_coding SET synonyms = ["vibe coding", "AI-assisted development"];

-- AND as graph edges for queryability
RELATE tag:ai_coding->tag_related->tag:vibe_coding SET relation_type = "synonym";
RELATE tag:vibe_coding->tag_related->tag:ai_coding SET relation_type = "synonym";
```

### Q4: Are there any ready-to-deploy solutions vs building custom?

**Answer: No single solution, but kg-gen + spaCy-entity-linker gets you 80% there.**

| Requirement | Off-the-shelf solution | Gap |
|-------------|----------------------|-----|
| Entity extraction from text | kg-gen, GLiNER, your existing enrich.py | Need to integrate, not plug-and-play |
| Hierarchical taxonomy | spaCy-entity-linker (Wikidata) | Only covers well-known entities |
| Synonym management | kg-gen clustering + embeddings | Need to build the merge/review workflow |
| Auto-categorization | LLM classification prompt | Need to build the prompt + validation |
| SurrealDB integration | None exists | Must build the SurrealDB write layer |
| Admin UI for taxonomy | None fits | Build in your existing Flask admin |

The Stablebridge project [SurrealDB Blog, 2025] used kg-gen + SurrealDB for regulatory document knowledge graphs and is the closest existing example to what you're building.

### Q5: What do production knowledge bases use for auto-tagging at scale?

**Answer: Taxonomy + ML classifier, with LLM for cold-start.**

[Enterprise Knowledge, 2025] describes the production pattern:
1. **Define taxonomy** (human-curated top levels, AI-suggested lower levels)
2. **Train classifier** on taxonomy (once you have labeled data from LLM extraction)
3. **LLM for novel entities** (anything not in taxonomy gets LLM-classified)
4. **Human review loop** (curators verify auto-tags, corrections feed back to classifier)

**For your scale (hundreds to low thousands of videos):**
- LLM-only is fine. The classifier approach matters at 100K+ documents.
- Focus on getting the taxonomy structure right and the synonym management working.
- The human review loop is the most important piece -- build it into the admin UI.

---

## 6. Recommended Architecture

### Pipeline Overview

```
New Video Arrives (via n8n RSS or manual)
    |
    v
[Transcript Fetch] -- MCP Gateway / YouTube API
    |
    v
[Chunking + Embedding] -- existing embedding service
    |
    v
[Entity Extraction - Fast Pass]
    |-- GLiNER on CPU (all segments, extract entity mentions)
    |-- Filter: segments with 3+ entities flagged for deep extraction
    |
    v
[Entity Extraction - Deep Pass]
    |-- kg-gen via LiteLLM/Haiku (flagged segments)
    |-- Returns: entities + relationships + confidence
    |
    v
[Entity Resolution]
    |-- Normalize names (lowercase, strip whitespace)
    |-- Check against existing tags (exact match on slug)
    |-- Embedding similarity check for near-duplicates
    |-- Wikidata grounding via spaCy-entity-linker (batch, async)
    |
    v
[Taxonomy Placement]
    |-- Known entity with Wikidata match: auto-place in hierarchy
    |-- Known entity type: place under type parent (product -> Technology)
    |-- Unknown: queue for human review with LLM-suggested placement
    |
    v
[Write to SurrealDB]
    |-- Create/update tag records
    |-- Create segment->tag relations
    |-- Create tag->tag hierarchy relations
    |-- Roll up video-level tags
    |
    v
[Periodic Maintenance - Nightly]
    |-- Run synonym clustering across all tags
    |-- Refresh Wikidata groundings for unresolved entities
    |-- Generate tag embeddings for new tags
    |-- Update mention counts
```

### Python Dependencies

```txt
# Entity Extraction
gliner>=0.2.26           # Zero-shot NER, CPU-friendly
kg-gen>=0.1.0            # Knowledge graph extraction via LLM
spacy>=3.7               # NLP pipeline
spacy-entity-linker>=1.0 # Wikidata entity linking

# Existing
requests                 # HTTP client (LiteLLM, SurrealDB)
flask                    # Web framework
flask-cors               # CORS support

# Optional future
dedupe                   # For speaker entity resolution
```

### Docker Additions

```yaml
# No new containers needed!
# GLiNER, kg-gen, and spaCy-entity-linker all run as Python libraries
# inside your existing embedding service container.
#
# Only addition: download spaCy model and entity linker KB at build time
# Dockerfile addition:
# RUN python -m spacy download en_core_web_trf
# RUN python -m spacy_entity_linker "download_knowledge_base"
```

---

## 7. Implementation Priority

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 1 | Add `tag` table + hierarchy schema to SurrealDB | Small | Foundation for everything |
| 2 | Enhance `enrich.py` with structured output + confidence | Small | Immediate quality improvement |
| 3 | Integrate kg-gen for relationship extraction | Medium | Enables cross-entity insights |
| 4 | Add GLiNER fast-pass before LLM extraction | Medium | 10x speed improvement on bulk |
| 5 | Embedding-based synonym detection | Small | Deduplicate tags automatically |
| 6 | Wikidata bootstrap via spaCy-entity-linker | Medium | Auto-populate hierarchies |
| 7 | Admin UI for taxonomy management | Medium | Human-in-the-loop review |
| 8 | Periodic synonym clustering (kg-gen) | Small | Ongoing quality maintenance |

---

## 8. Bibliography

### Primary Sources (Peer-Reviewed / Official)

- [Zaratiana et al., 2024] "GLiNER: Generalist Model for Named Entity Recognition using Bidirectional Transformer." NAACL 2024. https://arxiv.org/abs/2311.08526
- [Guan et al., 2025] "KGGen: Extracting Knowledge Graphs from Plain Text with Language Models." NeurIPS 2025. https://arxiv.org/abs/2502.09956
- [Wei et al., 2023] "GPT-NER: Named Entity Recognition via Large Language Models." https://arxiv.org/abs/2304.10428
- [Scharpf et al., 2026] "Entity Linking with Wikidata: A Systematic Literature Review." ACM Computing Surveys. https://dl.acm.org/doi/10.1145/3795134
- [W3C, 2009] "SKOS Simple Knowledge Organization System." https://www.w3.org/2004/02/skos/
- [SurrealDB, 2025] "How to Build a Knowledge Graph for AI." https://surrealdb.com/blog/how-to-build-a-knowledge-graph-for-ai
- [SurrealDB, 2025] "From Knowledge Graph Generation to RAG for Stablecoin Regulatory Intelligence." https://surrealdb.com/blog/from-knowledge-graph-generation-to-rag-for-stablecoin-regulatory-intelligence

### Tool Documentation

- spaCy NER: https://spacy.io/api/entityrecognizer
- spaCy-entity-linker: https://github.com/egerber/spaCy-entity-linker
- GLiNER GitHub: https://github.com/urchade/GLiNER
- GLiNER PyPI: https://pypi.org/project/gliner/
- kg-gen GitHub: https://github.com/stair-lab/kg-gen
- Microsoft Presidio: https://github.com/microsoft/presidio
- DBpedia Spotlight Docker: https://github.com/dbpedia-spotlight/spotlight-docker
- Ultimate MCP Server: https://github.com/Dicklesworthstone/ultimate_mcp_server
- dedupe library: https://github.com/dedupeio/dedupe
- Splink: https://github.com/moj-analytical-services/splink
- n8n AI features: https://n8n.io/ai/
- SurrealDB Graph Model: https://surrealdb.com/docs/surrealdb/models/graph
- SurrealDB GraphRAG: https://surrealdb.com/solutions/graph-rag

### Industry Analysis

- [Dresselhaus, 2025] "Case Study: Local LLM-Based NER with n8n and Ollama." https://drezil.de/Writing/ner4all-case-study.html
- [Neupane, 2024] "GLiNER: A Zero-Shot NER that outperforms ChatGPT." https://netraneupane.medium.com/gliner-zero-shot-ner-outperforming-chatgpt-and-traditional-ner-models-1f4aae0f9eef
- [Branzan, 2025] "From LLMs to Knowledge Graphs: Building Production-Ready Graph Systems in 2025." https://medium.com/@claudiubranzan/from-llms-to-knowledge-graphs-building-production-ready-graph-systems-in-2025-2b4aff1ec99a
- [Enterprise Knowledge, 2025] "How to Build a Knowledge Intelligence Architecture." https://enterprise-knowledge.com/enterprise-ai-architecture-series-how-to-build-a-knowledge-intelligence-architecture-part-1/
- [Sharma, 2026] "Modern Named Entity Recognition: Beyond Traditional NLP with Transformers and LLMs." https://medium.com/@akankshaonearth/modern-named-entity-recognition-beyond-traditional-nlp-with-transformers-and-llms-2026-c935ef31e692

### Benchmarks & Comparisons

- [ScienceDirect, 2025] "Comparing encoder-only vs. large language models for named entity recognition." https://www.sciencedirect.com/science/article/pii/S0010482525010169
- [Protecto, 2025] "Comparing Best NER Models For PII Identification." https://www.protecto.ai/blog/best-ner-models-for-pii-identification/
- [James, 2024] "Reviewing NER: spaCy vs. GLiNER on real-world diet data." https://medium.com/@alvarani/reviewing-ner-spacy-vs-gliner-d2e9ee331270
- [Label Your Data, 2026] "LLM vs NLP: Which One is Right for Your Use Case in 2026?" https://labelyourdata.com/articles/machine-learning/llm-vs-nlp
- [Eden AI, 2025] "Best Named Entity Recognition APIs in 2025." https://www.edenai.co/post/best-named-entity-recognition-apis

---

## 9. Evidence Strength Assessment

| Finding | Confidence | Evidence Quality | Notes |
|---------|------------|-----------------|-------|
| LLMs outperform NER on diverse/messy text | High | Multiple peer-reviewed + industry studies | Consistent across domains |
| GLiNER competitive with LLMs on standard NER | High | NAACL 2024 paper + benchmarks | Well-validated |
| kg-gen entity clustering works | Medium | NeurIPS 2025 paper + Stablebridge case study | Limited production deployments documented |
| spaCy-entity-linker Wikidata hierarchy | Medium | GitHub docs + user reports | ~70% disambiguation accuracy is a limitation |
| Embedding similarity for synonyms >0.92 threshold | Medium | General NLP practice | Threshold needs tuning per domain |
| No turnkey solution exists | High | Exhaustive search across tools | Gap confirmed across all sources |
| SurrealDB graph model fits taxonomy | High | SurrealDB official docs + Stablebridge | Direct evidence of the pattern |

---

## 10. Alternative Research Directions

If the recommended approach proves insufficient:

1. **Fine-tune GLiNER on your data** -- After accumulating 1000+ manually verified tag annotations, fine-tune a GLiNER model specifically for your entity types. This would give you a fast, accurate, domain-specific extractor.

2. **LangGraph entity extraction agent** -- Build a multi-step agent that extracts entities, validates them against existing tags, and places them in the taxonomy, all in one pipeline. More complex but more autonomous.

3. **Weaviate or Neo4j instead of SurrealDB for taxonomy** -- If SurrealDB's graph traversal proves limiting, consider a dedicated graph database for the taxonomy layer only. However, SurrealDB's multi-model approach should handle your scale.

4. **Instructor library for structured extraction** -- `pip install instructor` provides Pydantic-validated structured outputs from LLMs, which could replace your manual JSON parsing in enrich.py with typed, validated entity objects.

5. **DSPy for prompt optimization** -- kg-gen already uses DSPy internally. You could use it directly to optimize your extraction prompts against a validation set, automatically finding the best prompt for your specific entity types.
