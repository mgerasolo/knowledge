# SurrealDB RAG Spike

**Status:** Spike (throwaway code)
**Purpose:** Validate SurrealDB for vector + graph RAG queries
**Duration:** ~1 week
**Delete when:** Spike conclusions documented

## Goal

Test whether SurrealDB's unified model (vectors + graph + documents) is a better fit for KnowledgeStack than Qdrant + PostgreSQL.

## Target Channels

| Channel | Domain | Lookback |
|---------|--------|----------|
| Bible Study with Myron Golden | religion | 36 months |
| Myron Golden | business | 36 months |
| Alex Finn | ai-automation | 3 months |
| AI Labs | ai-coding | 12 months |
| MreFlow | ai-coding | 12 months |

## Quick Start

```bash
# 1. Deploy SurrealDB on Banner
ssh banner
cd /path/to/spike/surreal-rag
docker compose up -d

# 2. Initialize schema
docker exec -i knowledgestack-surrealdb \
  /surreal sql --user root --pass changeme \
  --ns knowledgespike --db transcripts < schema/init.surql

# 3. Run ingestion
python scripts/ingest_transcripts.py

# 4. Test queries
cat queries/semantic_search.surql | docker exec -i knowledgestack-surrealdb \
  /surreal sql --user root --pass changeme --ns knowledgespike --db transcripts
```

## Directory Structure

```
spike/surreal-rag/
├── docker-compose.yml      # SurrealDB + Surrealist UI
├── schema/
│   └── init.surql          # Database schema
├── scripts/
│   ├── ingest_transcripts.py   # Read from NAS, chunk, embed, store
│   └── embed_segments.py       # Generate embeddings via LiteLLM
├── queries/
│   ├── semantic_search.surql   # Basic vector search
│   ├── guest_topics.surql      # Graph traversal examples
│   └── cross_channel.surql     # Complex multi-hop
├── config/
│   └── channels.yaml           # Target channels
├── docs/
│   └── SPIKE_LOG.md            # Learnings as we go
└── README.md
```

## Endpoints

| Service | URL |
|---------|-----|
| SurrealDB | http://10.0.0.33:5040 |
| Surrealist UI | http://10.0.0.33:5041 |

## What We're Validating

1. [ ] SurrealDB vector search quality
2. [ ] SurrealMCP + LobeChat integration
3. [ ] Graph queries for entity relationships
4. [ ] Single-DB developer experience
5. [ ] Chunking strategy effectiveness
6. [ ] Embedding quality (nomic-embed-text)

## Success Criteria

- Can perform semantic search across all transcripts
- Can query "all segments where Channel X discusses Topic Y"
- Can find relationships between concepts across channels
- Performance acceptable for ~500-1000 transcripts
- Developer experience better than Qdrant + Postgres

## Spike Conclusions

*To be filled in after spike completion*

### Keep SurrealDB if:
- [ ] Query patterns are cleaner than two-DB approach
- [ ] Performance is acceptable
- [ ] MCP integration works with LobeChat

### Pivot to Qdrant if:
- [ ] Vector search quality is poor
- [ ] Graph queries are awkward
- [ ] MCP integration fails
- [ ] Performance is unacceptable

## Cleanup

When spike is complete:
```bash
# Stop and remove containers
ssh banner "cd /path/to/spike/surreal-rag && docker compose down -v"

# Remove spike directory
rm -rf spike/surreal-rag

# Commit cleanup
git add -A && git commit -m "Remove SurrealDB spike - conclusions in docs/"
```
