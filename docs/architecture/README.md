# KnowledgeStack Architecture Documentation

**Version:** 1.0
**Date:** 2026-03-22
**Status:** Living Document (Updated as system evolves)

## Overview

KnowledgeStack is a **6-product platform** that transforms YouTube content from trusted experts into a searchable, AI-queryable knowledge repository.

## Architecture Documentation Index

| Document | Purpose | C4 Level |
|----------|---------|----------|
| [System Context](system-context.md) | External actors, system boundaries | Level 1 |
| [Container Architecture](container-architecture.md) | Services, databases, runtime components | Level 2 |
| [Platform Products](platform-products.md) | 6-product platform breakdown | Level 2+ |
| [Data Flow](data-flow.md) | Pipeline stages, data transformations | - |
| [Infrastructure](infrastructure.md) | Host deployment, networking | Deployment |
| [Security Architecture](security.md) | Auth, access control, trust boundaries | - |
| [API Contracts](api-contracts.md) | External interfaces, MCP server | - |
| [ADRs](adrs/) | Architecture Decision Records | - |

## Quick Reference

### The 6 Products

```
Tier 1: KnowledgeEnroll   (Ingestion)    n8n + yt-dlp + YouTube API
Tier 2: KnowledgeLecture  (Lecture Hall)  Speakr (open-source)
Tier 3: KnowledgeCollege  (Intelligence) SurrealDB + LiteLLM
Tier 4: KnowledgeGraduate (Refinement)   Admin UI + curation
Tier 5: KnowledgeGateway  (Access)       REST API + MCP Server
Cross:  KnowledgeOps      (Operations)   Grafana + Loki + Slack
```

### Infrastructure Hosts

```
Banner (10.0.0.33)     Development host - Speakr, PostgreSQL, SurrealDB
Helicarrier (10.0.0.27) Workflow engine - n8n, LiteLLM proxy
Jarvis (10.0.0.XX)      GPU services - WhisperX transcription
Coulson (10.0.0.XX)     Observability - Grafana, Loki, Prometheus
Fury (NAS)              Storage - audio files, transcripts
```

### Technology Stack

| Purpose | Technology |
|---------|------------|
| Transcript Repository | Speakr (AGPL-3.0) |
| Vector + Graph DB | SurrealDB |
| Workflow Engine | n8n |
| AI Routing | LiteLLM proxy |
| Transcription | WhisperX |
| Auth | Authentik (OIDC) |
| Monitoring | Grafana + Loki + Prometheus |

## Key Architecture Decisions

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](adrs/ADR-001-surrealdb-over-qdrant.md) | SurrealDB over Qdrant for vector+graph | Accepted |
| [ADR-002](adrs/ADR-002-speakr-adoption.md) | Adopt Speakr for transcript repository | Accepted |
| [ADR-003](adrs/ADR-003-six-product-platform.md) | 6-product platform architecture | Accepted |
| [ADR-004](adrs/ADR-004-n8n-pipeline-orchestration.md) | n8n for pipeline orchestration | Accepted |

## Diagram Notation

All diagrams use Mermaid notation for version control and in-repo rendering.

- **C4 diagrams** follow the [C4 Model](https://c4model.com/) conventions
- **Blue boxes** = internal systems we build/control
- **Gray boxes** = external systems/dependencies
- **Dashed lines** = async/scheduled communication
- **Solid lines** = synchronous communication
