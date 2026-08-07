# ADR-001: SurrealDB Over Qdrant for Vector+Graph Storage

**Status:** Accepted
**Date:** 2026-03-22
**Deciders:** Matt
**Context:** Pre-Alpha Spike Evaluation

## Context

KnowledgeStack requires both:
1. **Vector storage** for semantic search over transcript embeddings
2. **Graph relationships** for entity connections (speaker→video, segment→topic)

The original PRD specified Qdrant for vector storage with PostgreSQL handling relationships. During the pre-alpha spike, we validated Qdrant worked (6,186 vectors, cosine similarity 0.69-0.78). However, analysis revealed we'd need a separate graph database or complex SQL for relationship queries.

## Decision

**Use SurrealDB as a unified vector+graph database**, replacing the Qdrant+PostgreSQL split for the intelligence layer.

## Rationale

### Why SurrealDB

| Capability | SurrealDB | Qdrant+PostgreSQL |
|------------|-----------|-------------------|
| Vector search | HNSW index, cosine similarity | Native HNSW |
| Graph relationships | Native graph edges, traversal | SQL joins or separate Neo4j |
| Query language | SurrealQL (SQL-like + graph) | REST API + SQL |
| Hybrid queries | Single query: vector + filters + graph | Multiple queries, app-level join |
| Schema flexibility | SCHEMAFULL or schemaless | Schema required |
| Deployment | Single container | 2+ containers |

### Key Advantages

1. **Unified queries**: `SELECT segment WHERE <-speaks_in<-speaker.name = 'Myron Golden' AND vector::similarity::cosine(embedding, $query) > 0.7`

2. **Graph traversal**: Find all topics a speaker discusses across all videos with a single query

3. **Simpler stack**: One database instead of two (Qdrant + PostgreSQL for relationships)

4. **Native functions**: Built-in `fn::hybrid_search`, `fn::speaker_content` for common patterns

### Validated in Spike

The SurrealDB spike (March 2026) validated:
- 1536-dimension HNSW index working
- Graph relationships (channel→video→segment→topic)
- Hybrid search combining vector + graph + filters
- Import of existing transcripts with embeddings

## Consequences

### Positive

- Simpler architecture (one DB for intelligence layer)
- More powerful queries (graph + vector in one)
- Easier entity relationship modeling
- SurrealQL is intuitive for SQL users

### Negative

- Less mature than Qdrant (smaller community)
- Fewer client libraries
- Learning curve for graph query patterns
- Need to monitor performance at scale

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| SurrealDB stability | Monitor closely, keep PostgreSQL as fallback for critical data |
| Performance at 100K+ vectors | Benchmark early, consider sharding |
| Missing features | PRD_Original.md preserved if we need to switch back |

## Alternatives Considered

### Alternative 1: Qdrant + PostgreSQL (Original Plan)

- **Pro:** Proven vector DB, large community
- **Con:** No native graph, complex joins for relationships
- **Why rejected:** Graph queries are central to KnowledgeStack use cases

### Alternative 2: Qdrant + Neo4j

- **Pro:** Best-in-class for each concern
- **Con:** Three databases total, complex ops
- **Why rejected:** Operational overhead too high for solo developer

### Alternative 3: PostgreSQL + pgvector + Apache AGE

- **Pro:** Single DB, familiar SQL
- **Con:** pgvector HNSW is newer, AGE less mature
- **Why rejected:** SurrealDB more purpose-built

## References

- SurrealDB Documentation: https://surrealdb.com/docs
- KnowledgeStack Spike: `spike/surreal-rag/`
- Original PRD (Qdrant): `_bmad-output/planning-artifacts/PRD_Original.md`
- Updated PRD (SurrealDB): `_bmad-output/planning-artifacts/prd.md`
