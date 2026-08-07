# RAG Database Survey - March 2026

## Executive Summary

Survey of 15 open source RAG systems on GitHub to inform KnowledgeStack's database selection.

**Key Finding:** SurrealDB's hybrid vector+graph model is viable and aligns well with KnowledgeStack's domain (interconnected transcript data). Most RAG projects use Qdrant or ChromaDB for vectors, with Neo4j for optional graph features.

**Recommendation:** Continue with SurrealDB for spike/MVP phase. The unified model reduces operational complexity and maps naturally to the YouTube transcript domain.

---

## Survey Results

### RAG Systems Analyzed

| # | Project | Primary Vector DB | Graph Support | Stars |
|---|---------|-------------------|---------------|-------|
| 1 | LangChain | Pluggable (Qdrant, ChromaDB, etc.) | Neo4j | 100k+ |
| 2 | LlamaIndex | Pluggable | Neo4j, KuzuDB | 40k+ |
| 3 | RAGFlow | Elasticsearch + Infinity | No | 35k+ |
| 4 | Haystack | Pluggable | Neo4j | 18k+ |
| 5 | Dify | Weaviate (default) | No | 60k+ |
| 6 | PrivateGPT | Qdrant (default) | No | 55k+ |
| 7 | Quivr | Supabase/pgvector | No | 35k+ |
| 8 | AnythingLLM | LanceDB (default) | No | 30k+ |
| 9 | Canopy | Pinecone (required) | No | 3k+ |
| 10 | Mem0 | Qdrant (default) | Neo4j, Memgraph | 25k+ |
| 11 | Verba | Weaviate (required) | No | 6k+ |
| 12 | Kotaemon | ChromaDB (default) | No | 20k+ |
| 13 | Microsoft GraphRAG | LLM extraction + Neo4j | Core feature | 20k+ |
| 14 | OpenAI Assistants | Proprietary | No | N/A |
| 15 | SurrealDB (kaig) | Native multi-model | Native | 30k+ |

### Vector Database Popularity

| Database | Projects Supporting | Key Strength |
|----------|---------------------|--------------|
| Qdrant | 12/15 | Filtering, Rust performance |
| ChromaDB | 10/15 | Simplest local setup |
| Weaviate | 9/15 | Built-in vectorization |
| Milvus | 8/15 | Billion-scale |
| pgvector | 7/15 | PostgreSQL integration |
| Pinecone | 6/15 | Managed service |
| LanceDB | 3/15 | Embedded, zero-config |
| Elasticsearch | 2/15 | Hybrid search |
| SurrealDB | 1/15 | Multi-model (unique) |

### Graph Database Support

| Database | Projects Using |
|----------|----------------|
| Neo4j | LangChain, LlamaIndex, Haystack, Mem0, GraphRAG |
| Memgraph | Mem0 |
| KuzuDB | LlamaIndex, Mem0 |
| SurrealDB | Native (no separate graph DB) |

---

## Analysis

### Pattern 1: Pluggable Architecture Dominates

Most mature RAG frameworks (LangChain, LlamaIndex, Haystack) support multiple vector databases through adapters. This allows:
- User choice based on infrastructure
- Easy switching between development and production databases
- Vendor independence

### Pattern 2: Qdrant is the De Facto Standard

Qdrant appears as default or recommended in the most projects due to:
- Excellent performance (Rust-based)
- Strong filtering capabilities (ACORN algorithm)
- Open source with managed cloud option
- Active community and documentation

### Pattern 3: GraphRAG is Emerging

Microsoft's GraphRAG paper (2024) sparked interest in combining knowledge graphs with vector search:
- Knowledge graphs capture relationships vectors miss
- Graph traversal provides explainable context
- Most implementations require TWO databases (vector + graph)
- SurrealDB is unique in offering both in one system

### Pattern 4: Local-First Options Growing

Projects like PrivateGPT, AnythingLLM, and Kotaemon prioritize local deployment:
- LanceDB and ChromaDB dominate this space
- Zero-config embedded options are highly valued
- Privacy-conscious users avoid cloud vector DBs

---

## KnowledgeStack Context

### Our Domain Requirements

1. **YouTube Transcripts**: Documents with rich metadata (channel, date, domain)
2. **Semantic Search**: Find relevant segments across speakers/topics
3. **Graph Relationships**: Channel → Video → Segment → Topic/Person
4. **Hybrid Queries**: "Find business advice from Myron Golden about sales in the last year"

### Spike Results (SurrealDB)

| Metric | Result |
|--------|--------|
| Segments loaded | 357 |
| Embedding dimensions | 1536 (text-embedding-3-small) |
| Vector search latency | ~30ms |
| Graph traversal | Working |
| Index type | HNSW |

---

## Recommendation

### Decision: Continue with SurrealDB

**Rationale:**

1. **Domain Fit**: YouTube transcripts ARE a knowledge graph - speakers reference each other, topics connect across videos, channels relate to domains.

2. **Operational Simplicity**: One database instead of two (no Qdrant + Neo4j coordination).

3. **Spike Validation**: 30ms vector search and graph traversal already working.

4. **Innovation Upside**: Hybrid queries (vector + graph + filters in one statement) not possible with traditional stack.

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Limited framework support | Use HTTP API, build thin wrapper |
| Performance at scale | Benchmark at 10k, 50k, 100k segments |
| Community size | Growing rapidly (30k+ stars) |
| Production readiness | Monitor their releases, have Qdrant fallback plan |

### Migration Insurance

Keep these abstractions to enable future migration if needed:
- LiteLLM for embeddings (model-agnostic)
- Standard 1536-dim embeddings (OpenAI-compatible)
- Clean data model (easy to re-chunk and re-embed)

---

## Sources

### RAG Framework Documentation
- [RAGFlow GitHub](https://github.com/infiniflow/ragflow)
- [Dify Documentation](https://github.com/langgenius/dify/discussions/4308)
- [PrivateGPT Vector Stores](https://docs.privategpt.dev/manual/storage/vector-stores)
- [Haystack Integrations](https://haystack.deepset.ai/integrations)
- [AnythingLLM Docs](https://docs.useanything.com/features/vector-databases)
- [Kotaemon GitHub](https://github.com/Cinnamon/kotaemon)
- [Canopy GitHub](https://github.com/pinecone-io/canopy)
- [Mem0 Documentation](https://docs.mem0.ai/components/vectordbs/dbs/qdrant)
- [Verba GitHub](https://github.com/weaviate/Verba)

### Vector Database Comparisons
- [ZenML Vector Database Comparison](https://www.zenml.io/blog/vector-databases-for-rag)
- [Firecrawl Best Vector Databases 2026](https://www.firecrawl.dev/blog/best-vector-databases)
- [TiDB Best Vector Database for RAG](https://www.pingcap.com/compare/best-vector-database/)

### GraphRAG Resources
- [Neo4j GraphRAG Integration](https://neo4j.com/blog/developer/microsoft-graphrag-neo4j/)
- [Weaviate GraphRAG Blog](https://weaviate.io/blog/graph-rag)
- [Qdrant GraphRAG with Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/)

### SurrealDB
- [SurrealDB Vector Documentation](https://surrealdb.com/docs/surrealdb/models/vector)
- [SurrealDB GraphRAG Solutions](https://surrealdb.com/solutions/graph-rag)
- [Multi-cycle Reasoning on SurrealDB](https://surrealdb.com/blog/beyond-basic-rag-building-a-multi-cycle-reasoning-engine-on-surrealdb)

---

*Survey conducted: March 2026*
*Analysts: Mary (📊), Winston (🏗️), Oscar (🚦)*
