# n8n Workflow Patterns Research for KnowledgeStack

**Date:** 2026-03-03
**Researcher:** Mary (Business Analyst)
**Project:** KnowledgeStack
**Purpose:** Learn from n8n's 8,000+ community workflows for content ingestion and storage patterns

---

## Executive Summary

After analyzing n8n's extensive workflow library, I identified **15+ directly applicable patterns** and **6 candidate workflows** for KnowledgeStack's MVP-1 and MVP-2 phases. The community has battle-tested solutions for every component of our pipeline: RSS monitoring, YouTube transcript extraction, AI summarization, deduplication, Qdrant RAG integration, and batch processing.

**Key Finding:** The n8n community has evolved a "sidecar pattern" for yt-dlp integration that matches our research recommendations - wrapping yt-dlp in a FastAPI microservice rather than running it directly in n8n.

---

## 1. Content Ingestion Patterns

### 1.1 RSS Feed Monitoring (Directly Applicable)

**Pattern:** Scheduled polling with intelligent deduplication

| Workflow | Key Pattern | Relevance |
|----------|-------------|-----------|
| [Automated RSS Monitoring with Gemini AI](https://n8n.io/workflows/5778-automated-rss-monitoring-with-gemini-ai-summaries-and-deduplication-to-google-sheets/) | RSS → Dedup → AI Summary → Storage | **HIGH** - Core MVP-1 pattern |
| [Smart RSS Monitoring with AI Filtering](https://n8n.io/workflows/6389-smart-rss-feed-monitoring-with-ai-filtering-baserow-storage-and-slack-alerts/) | Multi-feed → AI filtering → Database + Slack alerts | **HIGH** - Adds intelligent filtering |
| [Automated Blog Content Tracking](https://n8n.io/workflows/9596-automated-blog-content-tracking-with-rss-feeds-and-time-based-filtering/) | Time-based filtering for RSS | **MEDIUM** - Useful for backlog |

**Best Practice Learned:**
- Use time-based filtering (last X days) to avoid reprocessing old content
- Store "last seen" timestamps per feed in database
- AI filtering BEFORE full processing saves resources

### 1.2 YouTube Content Extraction

**Pattern:** Sidecar microservice for yt-dlp

| Workflow/Project | Key Pattern | Relevance |
|------------------|-------------|-----------|
| [y2b (GitHub)](https://github.com/roccoren/y2b) | FastAPI + yt-dlp + Azure Blob | **CRITICAL** - Reference architecture |
| [n8n Chronicles: Speech-to-Text](https://n8nchronicles.blogspot.com/2025/10/automate-local-speech-to-text-with-n8n.html) | yt-dlp → faster-whisper → GPT cleanup | **HIGH** - Full transcription pipeline |
| [YouTube Transcript Extraction](https://n8n.io/workflows/3417-extract-and-clean-youtube-video-transcripts-with-rapidapi/) | RapidAPI for transcripts (fallback) | **MEDIUM** - API-based alternative |

**y2b Architecture (Reference for KnowledgeStack):**
```
┌─────────────────────────────────────────────────────────┐
│ n8n Workflow                                            │
│  ┌─────────────┐    ┌──────────────────┐               │
│  │ RSS Trigger │───►│ HTTP Request to  │               │
│  │ (YouTube)   │    │ FastAPI Sidecar  │               │
│  └─────────────┘    └────────┬─────────┘               │
│                              │                          │
│                              ▼                          │
│                    ┌──────────────────┐                │
│                    │ yt-dlp Sidecar   │                │
│                    │ (FastAPI Docker) │                │
│                    │ - Download audio │                │
│                    │ - Extract meta   │                │
│                    │ - Return path    │                │
│                    └────────┬─────────┘                │
│                              │                          │
│                              ▼                          │
│                    ┌──────────────────┐                │
│                    │ Storage (Blob/   │                │
│                    │ Local + Metadata)│                │
│                    └──────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

**Best Practice Learned:**
- Never run yt-dlp directly in n8n container - use sidecar
- Cookie injection support is essential for age-restricted/membership content
- Local staging + cloud upload pattern (delete local after success)
- Metadata logging for audit trail

---

## 2. Deduplication Patterns

### 2.1 n8n Built-in Deduplication

**[Remove Duplicates Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.removeduplicates/)**

Three modes directly applicable to KnowledgeStack:

| Mode | Use Case | KnowledgeStack Application |
|------|----------|---------------------------|
| **Within Current Input** | Remove dupes in batch | Bulk backlog import |
| **Across Previous Executions** | Cross-run deduplication | Daily RSS processing |
| **Clear History** | Reset dedup state | Channel reprocessing |

**Key Configuration:**
- "Workflow scope" shares dedup data across multiple nodes
- "Keep Items Where" supports date-based or value-based selection
- Stores history in n8n database (PostgreSQL in our case)

### 2.2 External Deduplication Patterns

| Workflow | Pattern | Relevance |
|----------|---------|-----------|
| [Google Drive Duplicate Detection](https://n8n.io/workflows/13534-detect-and-move-duplicate-google-drive-files-with-supabase-and-slack/) | MD5 hash → Supabase lookup | **HIGH** - Database dedup pattern |
| [JavaScript Array Deduplication](https://n8n.io/workflows/5730-deduplicate-data-records-using-javascript-array-methods/) | Code-based dedup | **MEDIUM** - Custom logic |

**Best Practice Learned:**
- Use UUIDv5 (deterministic) as primary dedup key - matches our 6-layer strategy
- Store processed IDs in PostgreSQL (not just n8n internal)
- Hash-based comparison for content dedup (audio files)

---

## 3. AI Processing Patterns

### 3.1 Transcript Summarization

| Workflow | Key Pattern | Relevance |
|----------|-------------|-----------|
| [YouTube Video Summarization](https://n8n.io/workflows/2736-summarize-youtube-videos-from-transcript/) | Transcript → LLM Summary | **HIGH** - Core enrichment |
| [AI-Powered YouTube Chatbot](https://n8n.io/workflows/2956-ultimate-ai-powered-chatbot-for-youtube-summarization-and-analysis/) | Interactive Q&A on video | **MEDIUM** - Future phase |
| [Whisper + GPT Audio Pipeline](https://n8n.io/workflows/6139-transcribe-and-summarize-audio-with-whisper-and-gpt-from-google-drive-to-notion/) | Full audio→text→summary | **HIGH** - When Speakr unavailable |

### 3.2 RAG + Qdrant Integration

| Workflow | Key Pattern | Relevance |
|----------|-------------|-----------|
| [RAG with Citations](https://n8n.io/workflows/5023-build-a-rag-system-with-automatic-citations-using-qdrant-gemini-and-openai/) | Qdrant + auto-citation | **CRITICAL** - Citation for sources |
| [Self-Updating RAG](https://n8n.io/workflows/7647-build-a-self-updating-rag-system-with-openai-google-gemini-qdrant-and-google-drive/) | Auto-detect new files → reindex | **HIGH** - Continuous ingestion |
| [Adaptive RAG Strategy](https://n8n.io/workflows/3459-adaptive-rag-strategy-with-query-classification-and-retrieval-gemini-and-qdrant/) | Query classification → tailored retrieval | **MEDIUM** - Advanced phase |
| [PDF RAG with Mistral OCR](https://n8n.io/workflows/4400-build-a-pdf-document-rag-system-with-mistral-ocr-qdrant-and-gemini-ai/) | Document → OCR → Qdrant | **LOW** - Not transcript-focused |

**RAG Architecture Pattern:**
```
┌─────────────────────────────────────────────────────────────┐
│ Document Processing Pipeline                                │
│                                                             │
│  Source → Split (Recursive Text) → Embed (OpenAI) → Qdrant │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Query Pipeline                                              │
│                                                             │
│  Query → Classify → Strategy Select → Retrieve → Generate  │
│           │                                                 │
│           ├─ Factual: direct retrieval                      │
│           ├─ Analytical: multi-query                        │
│           ├─ Opinion: broad search                          │
│           └─ Contextual: conversation-aware                 │
└─────────────────────────────────────────────────────────────┘
```

**Best Practice Learned:**
- Recursive text splitter for chunking (overlapping chunks)
- Query classification improves retrieval quality significantly
- Auto-citation requires storing source metadata with vectors
- Self-updating pattern: webhook trigger on new content

---

## 4. Batch Processing & Scale Patterns

### 4.1 Large Dataset Handling

**[Split in Batches Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/)**

| Pattern | Use Case | KnowledgeStack Application |
|---------|----------|---------------------------|
| **Batch Size Control** | Prevent memory exhaustion | Backlog import (10K+ videos) |
| **Wait Node Integration** | Rate limiting | YouTube API / Speakr API |
| **Worker Queue Mode** | High-volume processing | Production scale-out |

**Key Metrics from Community:**
- 10,000 items with complex JSON = gigabytes of RAM without batching
- Recommended batch size: 50-100 items for API calls
- Worker count: match CPU cores with 2GB memory headroom per worker

### 4.2 Error Handling & Retry

| Workflow | Pattern | Relevance |
|----------|---------|-----------|
| [Auto-Retry Engine](https://n8n.io/workflows/3144-auto-retry-engine-error-recovery-workflow/) | Exponential backoff | **HIGH** - API resilience |
| [Advanced Retry Logic](https://n8n.io/workflows/5447-advanced-retry-and-delay-logic/) | Beyond 5-retry limit | **MEDIUM** - Edge cases |

**Best Practices Learned:**
- Default: 3-5 retries with 5-second delay for external APIs
- Exponential backoff for rate-limited services
- Dead-Letter Queue pattern: failed items → separate queue for inspection
- Error Trigger workflow for alerting (Slack/email)

---

## 5. Level 1 (MVP-1) Recommended Workflows

These workflows can be adapted or used as references for KnowledgeStack MVP-1:

### 5.1 RSS → Speakr Ingestion Pipeline

**Based on:** [Automated RSS Monitoring with Deduplication](https://n8n.io/workflows/5778-automated-rss-monitoring-with-gemini-ai-summaries-and-deduplication-to-google-sheets/)

**Adaptation for KnowledgeStack:**
```
┌────────────────────────────────────────────────────────────────┐
│ RSS Feed Monitor → YouTube Detection → Speakr Ingestion       │
│                                                                │
│ [Schedule Trigger]                                             │
│        │                                                       │
│        ▼                                                       │
│ [RSS Feed Read] ─────► Multiple YouTube channel feeds          │
│        │                                                       │
│        ▼                                                       │
│ [Remove Duplicates] ─► Scope: Workflow (cross-execution)       │
│        │                                                       │
│        ▼                                                       │
│ [Code Node] ─────────► Extract video_id, validate URL          │
│        │                                                       │
│        ▼                                                       │
│ [HTTP Request] ──────► POST to Speakr /api/v1/upload           │
│        │                 (audio_url method)                    │
│        ▼                                                       │
│ [IF Node] ───────────► Success? Log to PostgreSQL              │
│        │                 Error? → Error workflow               │
│        ▼                                                       │
│ [Postgres Insert] ───► ingestion_log table                     │
└────────────────────────────────────────────────────────────────┘
```

**Why this pattern:**
- Time-tested RSS monitoring from community
- Built-in deduplication prevents double-processing
- Database logging for audit trail
- Error workflow integration for reliability

### 5.2 yt-dlp Sidecar Service

**Based on:** [y2b GitHub Project](https://github.com/roccoren/y2b)

**Adaptation for KnowledgeStack:**
- Deploy FastAPI + yt-dlp as Docker sidecar on Banner
- Expose `/download` endpoint for audio extraction
- Use for Speakr fallback when direct YouTube URLs fail
- Store audio on Banner's mounted NAS share

### 5.3 Backlog Bulk Import

**Based on:** [Batch Processing Patterns](https://n8n.io/workflows/3409-batch-process-prompts-with-anthropic-claude-api/)

**Adaptation for KnowledgeStack:**
```
┌────────────────────────────────────────────────────────────────┐
│ Bulk Video Import from Channel History                         │
│                                                                │
│ [Manual Trigger + CSV Input]                                   │
│        │                                                       │
│        ▼                                                       │
│ [Split in Batches] ──► Batch size: 50 videos                   │
│        │                                                       │
│        ▼                                                       │
│ [Loop: For Each Video]                                         │
│        │                                                       │
│        ├──► [Postgres Check] ─► Already processed? Skip        │
│        │                                                       │
│        └──► [HTTP to Speakr] ─► Ingest                         │
│                   │                                            │
│                   ▼                                            │
│              [Wait 10s] ───────► Rate limit protection         │
│                   │                                            │
│                   ▼                                            │
│              [Postgres Log] ──► Track progress                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 6. Level 2 (MVP-2) Recommended Workflows

### 6.1 AI Enrichment Pipeline

**Based on:** [AI-Powered YouTube Summarization](https://n8n.io/workflows/2679-ai-powered-youtube-video-summarization-and-analysis/)

**Adaptation for KnowledgeStack:**
```
┌────────────────────────────────────────────────────────────────┐
│ Transcript Enrichment (Background Processing)                  │
│                                                                │
│ [Webhook: New Speakr Transcript] ─► Or scheduled poll          │
│        │                                                       │
│        ▼                                                       │
│ [Speakr API: Get Transcript]                                   │
│        │                                                       │
│        ▼                                                       │
│ [LiteLLM: Generate Summary]                                    │
│        │                                                       │
│        ▼                                                       │
│ [LiteLLM: Extract Topics/Entities]                             │
│        │                                                       │
│        ▼                                                       │
│ [LiteLLM: Channel Authority Assessment]                        │
│        │                                                       │
│        ▼                                                       │
│ [Postgres: Update Metadata]                                    │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 Qdrant RAG Integration

**Based on:** [Self-Updating RAG System](https://n8n.io/workflows/7647-build-a-self-updating-rag-system-with-openai-google-gemini-qdrant-and-google-drive/)

**Adaptation for KnowledgeStack:**
```
┌────────────────────────────────────────────────────────────────┐
│ Vector Indexing Pipeline                                       │
│                                                                │
│ [Speakr Transcript Webhook]                                    │
│        │                                                       │
│        ▼                                                       │
│ [Recursive Text Splitter] ─► Chunk size: 500, overlap: 50      │
│        │                                                       │
│        ▼                                                       │
│ [LiteLLM: nomic-embed-text-v1.5]                               │
│        │                                                       │
│        ▼                                                       │
│ [Qdrant: Upsert Vectors]                                       │
│        │                  ┌─────────────────────────────────┐  │
│        │                  │ Metadata:                       │  │
│        │                  │ - video_id                      │  │
│        │                  │ - channel_id                    │  │
│        │                  │ - timestamp_range               │  │
│        │                  │ - speaker (if diarized)         │  │
│        │                  │ - chapter_title                 │  │
│        │                  └─────────────────────────────────┘  │
│        ▼                                                       │
│ [Postgres: Mark as Indexed]                                    │
└────────────────────────────────────────────────────────────────┘
```

### 6.3 Smart Channel Prioritization

**Based on:** [Smart RSS Monitoring with AI Filtering](https://n8n.io/workflows/6389-smart-rss-feed-monitoring-with-ai-filtering-baserow-storage-and-slack-alerts/)

**Adaptation for KnowledgeStack:**
- Pre-filter videos by channel authority score before full processing
- Use AI to classify video relevance BEFORE downloading
- Skip low-priority content during peak load

---

## 7. Best Practices Summary

### 7.1 Architecture Patterns

| Pattern | Community Evidence | KnowledgeStack Application |
|---------|-------------------|---------------------------|
| **Sidecar for CLI tools** | y2b, multiple forum posts | yt-dlp in FastAPI container |
| **Database-backed dedup** | Built-in + external workflows | UUIDv5 in PostgreSQL |
| **Webhook > Polling** | Error handling guides | Speakr webhooks when ready |
| **Batch with Wait** | Scale documentation | 50-item batches + 10s wait |
| **Dead-Letter Queue** | Error handling patterns | Failed items → retry table |

### 7.2 Reliability Patterns

| Pattern | Implementation |
|---------|---------------|
| **Retry with backoff** | 3-5 retries, exponential delay |
| **Error workflows** | Slack alerts on failure |
| **Execution logging** | PostgreSQL audit table |
| **Graceful degradation** | Skip non-critical enrichment on timeout |

### 7.3 Scale Patterns

| Pattern | When to Apply |
|---------|--------------|
| **Worker queue mode** | > 100 workflows/hour |
| **Split in batches** | > 50 items per execution |
| **Parallel execution** | Independent API calls |
| **Scheduled staggering** | Multiple channel feeds |

---

## 8. Workflows to Clone/Adapt

### MVP-1 Priority (Start Here)

1. **[Automated RSS Monitoring with Deduplication](https://n8n.io/workflows/5778-automated-rss-monitoring-with-gemini-ai-summaries-and-deduplication-to-google-sheets/)** - Core ingestion pattern
2. **[y2b (GitHub)](https://github.com/roccoren/y2b)** - yt-dlp sidecar reference
3. **[Auto-Retry Engine](https://n8n.io/workflows/3144-auto-retry-engine-error-recovery-workflow/)** - Error handling

### MVP-2 Priority (After Core Works)

4. **[Self-Updating RAG with Qdrant](https://n8n.io/workflows/7647-build-a-self-updating-rag-system-with-openai-google-gemini-qdrant-and-google-drive/)** - Vector indexing
5. **[AI-Powered Summarization](https://n8n.io/workflows/2679-ai-powered-youtube-video-summarization-and-analysis/)** - Enrichment pipeline
6. **[Adaptive RAG Strategy](https://n8n.io/workflows/3459-adaptive-rag-strategy-with-query-classification-and-retrieval-gemini-and-qdrant/)** - Smart retrieval

---

## 9. Key Insights for PRD

### What the Community Validated

1. **yt-dlp sidecar is the standard** - Running yt-dlp directly in n8n is considered anti-pattern
2. **Qdrant + n8n is well-supported** - Multiple production RAG workflows exist
3. **RSS monitoring is mature** - Dozens of battle-tested implementations
4. **Deduplication is built-in** - No need for custom logic in most cases
5. **PostgreSQL integration is first-class** - Direct node support

### Gaps to Address

1. **Speakr integration** - No existing workflows (we're pioneering)
2. **Channel authority scoring** - Must build custom logic
3. **LiteLLM proxy patterns** - Community uses direct API calls (we adapt for LiteLLM)
4. **Webhook FROM Speakr** - Speakr doesn't have webhooks (must poll or add)

---

## Sources

- [n8n YouTube Integrations](https://n8n.io/integrations/youtube/)
- [n8n RSS Monitoring Templates](https://n8n.io/workflows/5778-automated-rss-monitoring-with-gemini-ai-summaries-and-deduplication-to-google-sheets/)
- [n8n Qdrant RAG Templates](https://n8n.io/workflows/5023-build-a-rag-system-with-automatic-citations-using-qdrant-gemini-and-openai/)
- [y2b GitHub - yt-dlp + n8n](https://github.com/roccoren/y2b)
- [n8n AI Automations Collection](https://github.com/lucaswalter/n8n-ai-automations)
- [n8n Batch Processing Guide](https://logicworkflow.com/blog/n8n-batch-processing/)
- [n8n Error Handling Docs](https://docs.n8n.io/flow-logic/error-handling/)
- [n8n Remove Duplicates Node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.removeduplicates/)
- [n8n Performance Optimization](https://www.wednesday.is/writing-articles/n8n-performance-optimization-for-high-volume-workflows)
- [n8n Chronicles: Speech-to-Text](https://n8nchronicles.blogspot.com/2025/10/automate-local-speech-to-text-with-n8n.html)
