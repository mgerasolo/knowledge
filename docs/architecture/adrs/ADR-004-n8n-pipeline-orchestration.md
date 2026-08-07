# ADR-004: n8n for Pipeline Orchestration

**Status:** Accepted
**Date:** 2026-01-30
**Deciders:** Matt
**Context:** Technology selection for ingestion pipeline orchestration

## Context

KnowledgeStack's ingestion pipeline needs to:
- Monitor ~50 YouTube channel RSS feeds
- Download audio files
- Trigger transcription
- Handle failures with retries
- Send Slack alerts
- Run on a schedule (15-30 minute intervals)

This requires a workflow orchestration tool that a solo developer can maintain.

## Decision

**Use n8n** (self-hosted on Helicarrier) for pipeline orchestration.

## Rationale

### Why n8n

| Requirement | n8n Capability |
|-------------|----------------|
| RSS monitoring | RSS Feed Trigger node |
| HTTP calls | HTTP Request node |
| Scheduling | Cron/Interval triggers |
| Error handling | Error Trigger node |
| Slack integration | Slack node (native) |
| Visual debugging | Execution history UI |
| Self-hosted | Docker deployment |

### Architecture Fit

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n WORKFLOW ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Workflow 1: RSS Monitor                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐ │
│  │ RSS Trigger │──►│ Dedup Check  │──►│ Queue to PostgreSQL   │ │
│  └─────────────┘   └──────────────┘   └───────────────────────┘ │
│                                                                  │
│  Workflow 2: Download Worker                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐ │
│  │ Queue Poll  │──►│ yt-dlp Call  │──►│ Upload to Speakr      │ │
│  └─────────────┘   └──────────────┘   └───────────────────────┘ │
│                                                                  │
│  Workflow 3: Error Handler                                       │
│  ┌─────────────┐   ┌──────────────┐   ┌───────────────────────┐ │
│  │Error Trigger│──►│ Classify     │──►│ Slack Alert           │ │
│  └─────────────┘   └──────────────┘   └───────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Known Gotchas (from research)

| Issue | Mitigation |
|-------|------------|
| RSS Trigger dedup unreliable | Use PostgreSQL for authoritative dedup |
| Workflow static data doesn't persist | Store all state in PostgreSQL |
| yt-dlp hangs in Execute Command | Use sidecar API container |
| 2GB binary data limit | Set `N8N_DEFAULT_BINARY_DATA_MODE=filesystem` |

### Existing Deployment

n8n is already running on Helicarrier (10.0.0.27) for other NLF workflows. KnowledgeStack adds workflows to the existing instance.

## Consequences

### Positive

- **Low-code visual development** - Faster iteration
- **Built-in integrations** - Slack, HTTP, RSS native
- **Self-hosted** - Full control, no vendor lock-in
- **Execution history** - Debug failed runs easily
- **Already deployed** - No new infrastructure

### Negative

- **State management** - Must use PostgreSQL, not workflow variables
- **Complex logic** - JavaScript in Code nodes can be hard to maintain
- **No unit testing** - Manual testing of workflows
- **Rate limiting** - Need custom backoff logic

### Technical Debt

- Deduplication logic duplicated in n8n + PostgreSQL
- yt-dlp sidecar adds operational complexity
- Error classification requires maintenance

## Alternatives Considered

### Alternative 1: Apache Airflow

- **Pro:** DAG-based, Python-native, mature
- **Con:** Heavy (requires Celery/Redis), overkill for ~50 channels
- **Why rejected:** Too complex for solo developer

### Alternative 2: Prefect

- **Pro:** Python-native, modern, good local dev
- **Con:** Another service to deploy, less visual
- **Why rejected:** n8n already deployed

### Alternative 3: Custom Python Scripts + Cron

- **Pro:** Full control, simple
- **Con:** No visual debugging, manual error handling
- **Why rejected:** n8n provides better observability

### Alternative 4: Temporal

- **Pro:** Durable execution, excellent for workflows
- **Con:** Heavy infrastructure (multiple services)
- **Why rejected:** Overkill for this scale

## References

- n8n Documentation: https://docs.n8n.io/
- Technical Research: `_bmad-output/planning-artifacts/research/n8n-workflow-patterns-research-2026-03-03.md`
- Helicarrier n8n: https://n8n.nextlevelguild.com
