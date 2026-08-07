# System Context (C4 Level 1)

**Last Updated:** 2026-03-22

## System Context Diagram

```mermaid
C4Context
    title KnowledgeStack System Context

    Person(admin, "Admin (Matt)", "Solo developer + curator")
    Person(viewer, "Viewer", "Inner circle members (<10)")

    System(knowledge, "KnowledgeStack", "6-product platform for YouTube transcript intelligence")

    System_Ext(youtube, "YouTube", "Video hosting, transcripts, RSS feeds")
    System_Ext(authentik, "Authentik", "OIDC identity provider")
    System_Ext(slack, "Slack", "Pipeline alerts and notifications")

    System_Ext(claude, "Claude Code", "AI assistant querying knowledge")
    System_Ext(lobechat, "LobeChat", "Cross-corpus AI chat")
    System_Ext(openclaw, "OpenClaw", "Research AI tool")

    Rel(admin, knowledge, "Configures channels, monitors pipeline")
    Rel(viewer, knowledge, "Searches, browses, chats with transcripts")

    Rel(knowledge, youtube, "Fetches RSS, downloads audio, gets transcripts")
    Rel(knowledge, authentik, "Authenticates users via OIDC")
    Rel(knowledge, slack, "Sends pipeline alerts")

    Rel(claude, knowledge, "Queries via MCP/REST API")
    Rel(lobechat, knowledge, "Queries via REST API")
    Rel(openclaw, knowledge, "Queries via REST API")
```

## Actors

### Human Users

| Actor | Role | Interactions |
|-------|------|--------------|
| **Admin (Matt)** | Solo developer + curator | Configure channels, monitor pipeline, manage system, troubleshoot failures |
| **Viewers** | Inner circle members | Search transcripts, browse recordings, chat with content, tag/bookmark |

### External Systems

| System | Integration | Purpose |
|--------|-------------|---------|
| **YouTube** | RSS feeds, Data API v3, transcript API | Content source - video metadata, transcripts |
| **Authentik** | OIDC | User authentication, SSO |
| **Slack** | Webhook | Pipeline alerts, daily digests, failure notifications |

### Downstream AI Tools (Vision Phase)

| System | Protocol | Purpose |
|--------|----------|---------|
| **Claude Code** | MCP Server | AI assistant querying the knowledge repository |
| **LobeChat** | REST API | Cross-corpus AI chat over transcripts |
| **OpenClaw** | REST API | Research tool accessing structured knowledge |

## System Boundaries

### What KnowledgeStack Does

- Monitors YouTube channels for new content (RSS + API)
- Downloads and transcribes audio (WhisperX via Speakr)
- Stores transcripts with search and per-recording chat (Speakr)
- Enriches content with embeddings and entity extraction (SurrealDB)
- Provides operational visibility (n8n + Slack + Grafana)
- Exposes knowledge to external tools (REST API + MCP)

### What KnowledgeStack Does NOT Do

- Host video files (YouTube is the source)
- Provide public access (internal network only)
- Create transcripts for videos without captions (Gemini fallback deferred)
- Moderate content (curated sources only)

## Data Flows Summary

| Flow | Direction | Data |
|------|-----------|------|
| Ingestion | YouTube → KnowledgeStack | RSS items, metadata, transcripts |
| Search | Viewer ↔ KnowledgeStack | Queries, results, segments |
| Alerts | KnowledgeStack → Slack | Pipeline failures, digests |
| Auth | User ↔ Authentik ↔ KnowledgeStack | OIDC tokens |
| API Access | AI Tools ↔ KnowledgeStack | Structured queries, results |

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│ INTERNAL NETWORK (10.0.0.x)                                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ KnowledgeStack Platform                               │ │
│  │  - All 6 products run here                            │ │
│  │  - All data stays internal                            │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Authentik    │  │ n8n          │  │ Grafana      │     │
│  │ (SSO)        │  │ (Workflows)  │  │ (Monitoring) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
          │                    │
          │                    │ HTTPS
          ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│ EXTERNAL SERVICES                                           │
│  YouTube, Slack, (future: LiteLLM cloud fallback)           │
└─────────────────────────────────────────────────────────────┘
```

## Context Scope Notes

- **MVP Scope**: Admin + Viewers interacting with Speakr, pipeline monitoring via Slack
- **Growth Scope**: Add Grafana dashboards, multi-user access
- **Vision Scope**: AI tool integration via KnowledgeGateway API/MCP
