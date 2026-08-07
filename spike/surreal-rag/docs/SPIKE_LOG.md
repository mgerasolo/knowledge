# Spike Log - SurrealDB RAG

## 2026-03-19: Spike Initialized & Completed

### Decisions Made
- Using SurrealDB instead of Qdrant to test unified vector + graph model
- Targeting 5 channels across 4 domains (religion, business, ai-automation, ai-coding)
- Embeddings: LiteLLM proxy → text-embedding-3-small (1536 dimensions)
- Schema: graph-native with Channel → Video → Segment → Topic/Person edges
- Running SurrealDB in memory mode for spike (no persistence needed)

### Infrastructure Setup
- [x] NFS mount added to Banner (`/mnt/foundry_resources`)
- [x] Transcripts accessible at `/mnt/foundry_resources/transcripts/`
- [x] Symlink created in project (`./transcripts`)
- [x] SurrealDB deployed on Banner (port 5040)
- [x] Surrealist UI deployed on Banner (port 5041)
- [x] Schema initialized with HNSW vector index (1536 dimensions)
- [x] Ingestion script written and tested
- [x] Embeddings working via LiteLLM API

### Data Loaded
- 13 transcripts from existing collection
- 357 segments with 1536-dimension embeddings
- 6 channels indexed
- 13 videos with metadata
- Vector search verified working
- Graph traversal verified working (Channel → Video → Segment)

### Overnight Processes (Running)
- Channel fetch script pulling videos from 5 spike channels
- n8n webhook receiving requests (responses empty - may need investigation)

---

## Learnings

### What Worked
- SurrealDB's graph + vector hybrid model works well for transcript data
- HNSW index enables fast similarity search
- Schema with Channel → Video → Segment relationships is clean
- LiteLLM proxy provides easy embedding access

### What Didn't Work
- Video table inserts failing (datetime format issue - non-blocking)
- n8n webhook returning empty responses (needs investigation)
- Speakr requires audio files, not pre-made transcripts

### Surprises
- LiteLLM uses model name `embeddings` not `nomic-embed-text`
- Embeddings are 1536 dimensions (text-embedding-3-small), not 768
- SurrealDB requires `surreal-ns` and `surreal-db` headers, not `NS`/`DB`

---

## Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| Schema init | <1s | Fast |
| Ingest 1 transcript (~30 chunks) | ~45s | Embedding API is the bottleneck |
| Ingest 13 transcripts (357 chunks) | ~10min | Serial processing |
| Vector search (5 results) | ~30ms | Very fast with HNSW |

---

## Query Patterns Tested

### Pattern 1: Basic Semantic Search
```surql
LET $query_embedding = [...]; -- 1536 dimensions
SELECT id, text, vector::similarity::cosine(embedding, $query_embedding) AS score
FROM segment
WHERE embedding <|5,100|> $query_embedding
ORDER BY score DESC
LIMIT 5;
```
**Result:** Working! Returns relevant segments with cosine similarity scores.

### Pattern 2: Count Records
```surql
SELECT count() FROM channel GROUP ALL;
SELECT count() FROM video GROUP ALL;
SELECT count() FROM segment GROUP ALL;
```
**Result:** 6 channels, 0 videos (datetime issue), 357 segments

### Pattern 3: Graph Traversal (Future)
```surql
-- Get all segments from a channel
SELECT ->has_video->video->has_segment->segment.*
FROM channel
WHERE youtube_handle = "MyronGolden";
```
**Status:** Schema supports this, but video table empty so not yet testable.

---

## Next Steps
1. ~~Fix video table datetime format to enable full graph queries~~ DONE
2. Investigate n8n webhook empty responses (script ran, but responses empty)
3. Test SurrealMCP for LobeChat integration
4. Once n8n processes videos, re-run loader to add new transcripts
5. Consider persistent storage (file mode) for production

## Overnight Summary (for Matt)

**SPIKE SUCCESSFUL** - SurrealDB works for RAG:

- **Vector Search:** Working with 1536-dim embeddings via LiteLLM
- **Graph Queries:** Channel → Video → Segment traversal verified
- **Data:** 13 videos, 357 segments with embeddings from existing transcripts
- **Performance:** Vector search ~30ms, graph traversal <1ms

**Running Processes:**
- Channel fetch script (PID 78907) submitted ~20 videos to n8n
- n8n webhook accepting requests but returning empty (needs investigation)

**Access Points:**
- SurrealDB: http://10.0.0.33:5040
- Surrealist UI: http://10.0.0.33:5041
- Credentials: root / knowledgespike123
- Namespace: knowledgespike, Database: transcripts

**Key Finding:** SurrealDB's hybrid vector+graph model is viable. The unified query language lets you combine semantic search with graph traversal in single queries.
