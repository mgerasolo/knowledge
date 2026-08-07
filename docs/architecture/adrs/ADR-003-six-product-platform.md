# ADR-003: 6-Product Platform Architecture

**Status:** Accepted
**Date:** 2026-03-22
**Deciders:** Matt
**Context:** Architectural evolution from 5-product to 6-product structure

## Context

The original KnowledgeStack architecture defined 5 products:
1. KnowledgeEnroll (Ingestion)
2. KnowledgeLecture (Lecture Hall)
3. KnowledgeCollege (Intelligence)
4. KnowledgeGraduate (Distribution/API)
5. KnowledgeOps (Operations)

During PRD refinement, we identified that:
1. **"Graduate" was overloaded** -- both refinement AND distribution
2. **Curation workflows** (golden standards, human review) are distinct from API access
3. **External API access** deserves its own product boundary

## Decision

**Split into 6 products**, separating refinement from external access:

| Tier | Product | Purpose |
|------|---------|---------|
| 1 | KnowledgeEnroll | Ingestion |
| 2 | KnowledgeLecture | Lecture Hall (Speakr) |
| 3 | KnowledgeCollege | Intelligence (SurrealDB) |
| 4 | **KnowledgeGraduate** | **Refinement** (curation, golden standards) |
| 5 | **KnowledgeGateway** | **External Access** (REST API, MCP) |
| Cross | KnowledgeOps | Operations |

## Rationale

### Why Separate Graduate and Gateway

| Concern | Graduate (Refinement) | Gateway (Access) |
|---------|----------------------|------------------|
| Users | Admin curators | External AI tools |
| Data flow | Internal enrichment | External queries |
| Interface | Admin UI | REST API, MCP |
| Phase | Growth | Vision |
| Focus | Quality | Availability |

### Product Boundaries

**KnowledgeGraduate (Tier 4 - Refinement)**
- Curate "golden standard" excerpts
- Flag signature stories (recurring themes)
- Manage quote library with viral scoring
- Human review workflows
- Citation/attribution tracking

**KnowledgeGateway (Tier 5 - Access)**
- REST API for structured queries
- MCP server for AI tools
- API key authentication
- Rate limiting
- Usage analytics

### Benefits

1. **Clearer ownership:** Each product has a single responsibility
2. **Independent evolution:** Gateway can scale for API traffic while Graduate focuses on quality
3. **Phased delivery:** Graduate (Growth) and Gateway (Vision) can ship independently
4. **Better naming:** "Gateway" clearly indicates external access

## Consequences

### Positive

- Cleaner product boundaries
- Easier to reason about data flow
- Independent team/phase ownership
- Better maps to use cases

### Negative

- More products to track (6 vs 5)
- PRD references needed updating (completed)
- Documentation complexity

### Migration

Updated the following documents:
- `_bmad-output/planning-artifacts/prd.md` - All references
- Created `docs/architecture/platform-products.md` - Full documentation

## Alternatives Considered

### Alternative 1: Keep 5 Products (Graduate = API)

- **Pro:** Simpler, fewer products
- **Con:** Overloaded "Graduate" concept
- **Why rejected:** Refinement and API access are distinct concerns

### Alternative 2: Keep 5 Products (Graduate = Refinement, API in College)

- **Pro:** Intelligence + API in one
- **Con:** College scope creep, API concerns mixed with enrichment
- **Why rejected:** College should focus on intelligence, not serving

## References

- Original PRD: `_bmad-output/planning-artifacts/PRD_Original.md`
- Updated PRD: `_bmad-output/planning-artifacts/prd.md`
- Platform Products: `docs/architecture/platform-products.md`
