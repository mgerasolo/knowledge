# KnowledgeOps Monitoring & Operations Layer Research Report

**Date:** 2026-01-30
**Researcher:** Claude Opus 4.5
**Context:** Research for building KnowledgeOps -- the operational management product for KnowledgeStack (self-hosted YouTube transcript ingestion pipeline)

---

## Executive Summary

### Key Findings

1. **n8n has native Prometheus metrics support** -- enabling `N8N_METRICS=true` exposes a `/metrics` endpoint with execution counters, duration histograms, queue depth, and Node.js process metrics. This plugs directly into the existing Grafana+Prometheus stack on Coulson (10.0.0.28) with zero additional tooling.

2. **n8n's REST API provides full execution history access** -- the `/api/v1/executions` endpoint supports filtering by `status=error`, `workflowId`, and includes retry capability via `POST /executions/:id/retry`. This is the foundation for building a dead-letter queue and channel status tracking without any external tools.

3. **Two production-ready Grafana dashboards already exist** -- Dashboard #24474 (System Health Overview) and #24475 (Workflow & Execution Analytics) from Grafana Labs can be imported directly, providing immediate visibility into execution rates, error hotspots, queue depth, and workflow performance.

4. **A PostgreSQL-based dead-letter queue is the right fit** -- for a 50-channel system, PostgreSQL's `FOR UPDATE SKIP LOCKED` pattern provides a lightweight, transactional DLQ without adding RabbitMQ/Redis complexity. Combined with n8n's error workflow triggers, failed ingestions can be captured, categorized, and requeued entirely within the existing stack.

5. **The MVP can be built entirely with n8n + Slack + existing Grafana** -- no new tools are required for the initial operational layer. Healthchecks.io and Uptime Kuma are valuable additions for the Growth phase but are not blockers for MVP.

---

## Table of Contents

1. [n8n Execution History APIs](#1-n8n-execution-history-apis)
2. [n8n Error Handling and Retry Patterns](#2-n8n-error-handling-and-retry-patterns)
3. [n8n Prometheus Metrics and Observability](#3-n8n-prometheus-metrics-and-observability)
4. [Pipeline Monitoring Tools](#4-pipeline-monitoring-tools)
5. [Dead-Letter Queue Patterns](#5-dead-letter-queue-patterns)
6. [Slack Integration Patterns](#6-slack-integration-patterns)
7. [Grafana Dashboards for n8n](#7-grafana-dashboards-for-n8n)
8. [Tool Evaluation Matrix](#8-tool-evaluation-matrix)
9. [Recommended Architecture by Phase](#9-recommended-architecture-by-phase)
10. [Bibliography](#10-bibliography)

---

## 1. n8n Execution History APIs

### 1.1 Public REST API Overview

n8n provides a full REST API (OpenAPI 3.0 spec) at `/api/v1/` authenticated via `X-N8N-API-KEY` header. The API covers workflow management, execution control, credential management, and user management. [n8n Docs, 2026]

### 1.2 Execution Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/executions` | GET | List executions with filters |
| `/api/v1/executions/:id` | GET | Get single execution details |
| `/api/v1/executions/:id` | DELETE | Delete an execution |
| `/api/v1/executions/:id/retry` | POST | Retry a failed execution |

### 1.3 Query Parameters for Filtering

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `canceled`, `error`, `success`, `waiting` |
| `workflowId` | string | Filter by specific workflow |
| `projectId` | string | Filter by project |
| `includeData` | boolean | Include detailed execution data (node-level) |
| `limit` | integer | Number of results per page |
| `cursor` | string | Cursor-based pagination token |

**Critical note:** Use `status=error` (not `status=failed`) when querying for failed executions via the API. The UI shows "Failed" but the API uses "error" as the status value. [n8n GitHub Issue #19664]

### 1.4 Retry Capability

Failed executions can be retried programmatically:

```bash
POST /api/v1/executions/:id/retry
Body: { "loadWorkflow": false }  # false = use original version; true = use latest version
```

This is directly applicable to the KnowledgeOps re-queue capability requirement.

### 1.5 Known Limitations

- **No "running" status filter**: The API does not reliably support filtering by `running` status despite documentation suggesting otherwise. [n8n GitHub Issue #19664]
- **`includeData` + `workflowId` bug**: Combining `includeData=true` with `workflowId` may return 400 errors in some versions. [n8n Community, 2025]
- **No currently-running execution listing**: Listing in-progress executions requires workarounds using internal REST endpoints (login + cookie + internal API). [n8n Community, 2025]

### 1.6 Relevance to KnowledgeOps

**High relevance.** The executions API is the backbone for:
- **Pipeline health monitoring**: Query `status=error` to calculate failure rates per workflow
- **Channel status tracking**: Query by workflow ID, check `stoppedAt` timestamps to detect stale channels
- **Dead-letter queue**: Query failed executions, store metadata, retry via API
- **Utilization metrics**: Query execution durations and counts

### 1.7 Built-in n8n Node

n8n also has a built-in "n8n" node that can query its own API from within workflows, enabling self-monitoring workflows that:
- List failed executions and alert on them
- Calculate success/failure ratios
- Detect stale workflows (no recent executions)

---

## 2. n8n Error Handling and Retry Patterns

### 2.1 Node-Level Retry on Fail

Every n8n node has a built-in "Retry on Fail" toggle in its settings. Recommended configuration:
- **Max retries**: 3-5 attempts
- **Wait between**: 5 seconds (or use exponential backoff)
- Best for: External API calls (YouTube API, Speakr API) [easify-ai.com, 2025]

### 2.2 Error Workflows (Error Trigger)

n8n supports dedicated error workflows that fire when any workflow execution fails:
- Configure via Workflow Settings -> Error Workflow
- Error workflow must start with the "Error Trigger" node
- One error workflow can serve multiple production workflows
- The error trigger receives: workflow name, execution ID, error message, timestamp

**For KnowledgeOps**: Create a single error handler workflow that:
1. Receives failure data from any ingestion workflow
2. Writes failure to PostgreSQL dead-letter table
3. Sends Slack alert with channel name, URL, and error type
4. Increments retry counter

### 2.3 Error Branching (Continue on Error Output)

Nodes can be configured to route to an alternative path on failure rather than stopping the workflow. This enables:
- Fallback processing paths
- Error logging without workflow termination
- Partial success handling (e.g., 45 of 50 channels succeeded)

### 2.4 Advanced Patterns

| Pattern | Description | Applicability |
|---------|-------------|---------------|
| **Exponential Backoff + Jitter** | Retries with 1s, 2s, 5s, 13s delays + random 20% jitter | YouTube API rate limits |
| **Circuit Breaker** | Stop calling failing API after threshold, redirect to fallback | External service degradation |
| **Queue-Based Isolation** | Break workflows into producer/consumer with durable queue | Scale-out phase |
| **Error Classification** | Route 5xx (retry) vs 4xx (dead-letter) vs auth (refresh) | Smart DLQ routing |
| **Idempotency Keys** | Generate unique keys to prevent duplicate processing on retry | Transcript re-ingestion safety |

### 2.5 Official n8n Templates

- [Advanced Retry and Delay Logic](https://n8n.io/workflows/5447-advanced-retry-and-delay-logic/) -- Custom loop with Set, If, and Wait nodes for granular retry control
- [Auto-Retry Engine](https://n8n.io/workflows/3144-auto-retry-engine-error-recovery-workflow/) -- Automatically retries failed executions using the n8n API in batches

### 2.6 Recommendation for KnowledgeOps

**Layered approach:**
1. **Layer 1**: Node-level retry (3 attempts, 5s delay) on all HTTP/API nodes
2. **Layer 2**: Error branching on the ingestion workflow to capture partial failures
3. **Layer 3**: Global error workflow writing to PostgreSQL DLQ + Slack alert
4. **Layer 4**: Scheduled "DLQ processor" workflow that retries eligible items via API

---

## 3. n8n Prometheus Metrics and Observability

### 3.1 Native Prometheus Support

n8n uses the `prom-client` library to expose metrics at `/metrics`. Available since n8n v0.111.0. [n8n Docs, 2026]

### 3.2 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `N8N_METRICS` | `false` | Enable `/metrics` endpoint |
| `N8N_METRICS_INCLUDE_DEFAULT_METRICS` | `true` | Node.js process metrics (CPU, memory, heap, GC) |
| `N8N_METRICS_INCLUDE_QUEUE_METRICS` | `false` | Bull queue metrics (waiting, active, completed, failed) |
| `N8N_METRICS_QUEUE_METRICS_INTERVAL` | `5000` | Queue metrics sampling interval (ms) |
| `N8N_METRICS_INCLUDE_API_ENDPOINTS` | `false` | API request metrics |
| `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL` | `false` | Add workflow ID label to metrics |
| `N8N_METRICS_INCLUDE_NODE_TYPE_LABEL` | `false` | Add node type label |
| `N8N_METRICS_INCLUDE_CREDENTIAL_TYPE_LABEL` | `false` | Add credential type label |

### 3.3 Key Metrics Exposed

**Application Metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `n8n_execution_total` | Counter | Total workflow executions |
| `n8n_execution_failed_total` | Counter | Total failed executions |
| `n8n_execution_duration_seconds_bucket` | Histogram | Execution duration distribution |
| `n8n_workflow_started_total` | Counter | Total workflows started |
| `n8n_api_requests_total` | Counter | Total API requests |

**Queue Metrics** (when enabled):

| Metric | Type | Description |
|--------|------|-------------|
| `n8n_scaling_mode_queue_jobs_waiting` | Gauge | Jobs waiting for pickup |
| `n8n_queue_bull_queue_active` | Gauge | Jobs currently processing |
| `n8n_queue_bull_queue_completed` | Counter | Total completed jobs |

**Process Metrics** (default Node.js):

| Metric | Type | Description |
|--------|------|-------------|
| `process_resident_memory_bytes` | Gauge | Memory usage |
| `process_cpu_seconds_total` | Counter | CPU time |
| `nodejs_heap_size_total_bytes` | Gauge | Heap size |
| `nodejs_eventloop_lag_seconds` | Gauge | Event loop lag |
| `nodejs_gc_duration_seconds` | Histogram | Garbage collection pauses |

### 3.4 Useful PromQL Queries for KnowledgeOps

```promql
# Execution rate (executions per 5 minutes)
rate(n8n_execution_total[5m])

# Error rate
rate(n8n_execution_failed_total[5m])

# Error percentage
rate(n8n_execution_failed_total[5m]) / rate(n8n_execution_total[5m]) * 100

# 95th percentile execution duration
histogram_quantile(0.95, rate(n8n_execution_duration_seconds_bucket[5m]))

# Queue depth (if using queue mode)
n8n_scaling_mode_queue_jobs_waiting
```

### 3.5 Integration with Existing Stack

Since Prometheus is already running on Coulson (10.0.0.28), the only action needed is:

1. Add `N8N_METRICS=true` to n8n's Docker environment on Helicarrier (10.0.0.27)
2. Add n8n as a scrape target in Prometheus config:
   ```yaml
   - job_name: 'n8n'
     static_configs:
       - targets: ['10.0.0.27:5678']  # or whatever port n8n exposes
   ```
3. Import Grafana dashboards #24474 and #24475

**Estimated effort: 30 minutes to full metrics visibility.**

### 3.6 OpenTelemetry

n8n also supports OpenTelemetry for distributed tracing (Jaeger, Grafana Tempo). This is useful if KnowledgeStack grows to multiple services but is overkill for MVP.

---

## 4. Pipeline Monitoring Tools

### 4.1 Healthchecks.io

**URL:** https://healthchecks.io | [GitHub](https://github.com/healthchecks/healthchecks)
**License:** BSD
**Self-hostable:** Yes (Docker, Python/Django)

**How it works:** Dead man's switch / heartbeat monitoring. Your pipeline sends an HTTP "ping" when it completes successfully. If Healthchecks.io does not receive a ping within the expected interval, it sends alerts.

**Key features:**
- Configurable Period (expected interval) and Grace Time (how long to wait before alerting)
- Cron expression support for complex schedules
- Integrations: Email, Slack, PagerDuty, webhooks, and more
- Status badges for dashboards
- "Shell Commands" integration for local automation on state changes

**Fit for KnowledgeOps:**
- **Channel stale detection**: Create one check per YouTube channel. Each successful ingestion pings its check. If 3 weeks pass without a ping, Healthchecks alerts.
- **Pipeline heartbeat**: Ping after each scheduled pipeline run completes.
- **Limitation**: Does not provide detailed failure data -- only "ran" or "didn't run."

**Verdict:** Excellent for Growth phase. Adds a layer of "did the pipeline run at all?" monitoring that complements n8n's own execution tracking. Not needed for MVP since n8n's error workflows can handle this.

### 4.2 Uptime Kuma

**URL:** https://uptime.kuma.pet | [GitHub](https://github.com/louislam/uptime-kuma)
**License:** MIT
**Self-hostable:** Yes (Docker, single command)

**How it works:** Self-hosted monitoring tool supporting HTTP(s), TCP, Ping, DNS, Docker, and **Push (heartbeat)** monitors. The Push monitor type works identically to Healthchecks.io's dead man's switch.

**Key features:**
- 90+ notification integrations (Slack, Telegram, Discord, etc.)
- Status pages (public-facing or internal)
- Push monitoring with configurable heartbeat intervals (min 20 seconds)
- Execution time tracking via push metadata
- Docker container monitoring
- Beautiful, modern UI

**Fit for KnowledgeOps:**
- **Service health**: Monitor Speakr (HTTP check on 10.0.0.33), n8n (HTTP check on 10.0.0.27), PostgreSQL (TCP check)
- **Pipeline heartbeat**: Push monitor for each ingestion workflow
- **Status page**: Internal status page showing all KnowledgeStack components
- **Advantage over Healthchecks.io**: Also monitors service uptime (HTTP/TCP), not just job completion

**Verdict:** Strong candidate for Growth phase. Provides both service uptime AND pipeline heartbeat monitoring in one tool. If you already have Grafana, some overlap exists, but Uptime Kuma's status page feature is unique and valuable.

### 4.3 n8n's Own Monitoring Capabilities

n8n provides three health endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/healthz` | Instance reachable (returns 200) |
| `/healthz/readiness` | Instance + DB connected and migrated |
| `/metrics` | Prometheus metrics (when enabled) |

These are disabled by default and need to be enabled in configuration.

### 4.4 Comparison for KnowledgeOps

| Capability | n8n Native | Healthchecks.io | Uptime Kuma | Grafana |
|------------|-----------|-----------------|-------------|---------|
| Pipeline "did it run?" | Via API queries | Dead man's switch | Push monitor | Alert rules |
| Failure details | Full execution data | No | No | Via Loki logs |
| Service uptime | /healthz only | No | HTTP/TCP/DNS | Via blackbox exporter |
| Status page | No | Status badges | Full status page | Dashboard (not public) |
| Alerting | Error workflows | Email, Slack, etc. | 90+ channels | Slack, email, etc. |
| Self-hosted | Already running | Docker | Docker | Already running |
| Setup effort | Already exists | ~30 min | ~15 min | Already exists |

---

## 5. Dead-Letter Queue Patterns

### 5.1 PostgreSQL-Based DLQ (Recommended for KnowledgeOps)

For a system processing 50 YouTube channels, a PostgreSQL-based DLQ is ideal. No additional infrastructure (RabbitMQ, Redis, SQS) needed since PostgreSQL is already in the stack. [aminediro.com, 2025; swenotes.com, 2025]

**Schema:**

```sql
CREATE TABLE knowledge_dlq (
    id              SERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Source identification
    channel_id      TEXT NOT NULL,
    channel_name    TEXT NOT NULL,
    video_url       TEXT NOT NULL,
    video_id        TEXT NOT NULL,

    -- Error information
    error_type      TEXT NOT NULL,          -- 'api_error', 'parse_error', 'timeout', 'rate_limit', etc.
    error_message   TEXT,
    error_code      INTEGER,                -- HTTP status code if applicable
    n8n_execution_id TEXT,                  -- Reference back to n8n execution

    -- Retry management
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 5,
    next_retry_at   TIMESTAMPTZ,
    last_retry_at   TIMESTAMPTZ,

    -- Status
    status          TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'retrying', 'resolved', 'acknowledged', 'skipped'

    -- Classification
    is_retryable    BOOLEAN NOT NULL DEFAULT true,    -- false for 4xx errors, true for 5xx/timeouts

    -- Original payload (for replay)
    original_payload JSONB,

    -- Resolution
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,                   -- 'auto_retry', 'manual', 'acknowledged'
    resolution_note TEXT
);

-- Indexes for common query patterns
CREATE INDEX idx_dlq_status ON knowledge_dlq(status);
CREATE INDEX idx_dlq_channel ON knowledge_dlq(channel_id);
CREATE INDEX idx_dlq_next_retry ON knowledge_dlq(next_retry_at) WHERE status = 'pending';
CREATE INDEX idx_dlq_created ON knowledge_dlq(created_at);
```

### 5.2 Worker Pattern with SKIP LOCKED

```sql
-- Dequeue next retryable item (safe for concurrent workers)
WITH next_item AS (
    SELECT id
    FROM knowledge_dlq
    WHERE status = 'pending'
      AND is_retryable = true
      AND retry_count < max_retries
      AND (next_retry_at IS NULL OR next_retry_at <= NOW())
    ORDER BY created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
UPDATE knowledge_dlq
SET status = 'retrying',
    retry_count = retry_count + 1,
    last_retry_at = NOW(),
    updated_at = NOW()
FROM next_item
WHERE knowledge_dlq.id = next_item.id
RETURNING knowledge_dlq.*;
```

### 5.3 n8n Integration Pattern

**Producer (Error Workflow):**
1. n8n ingestion workflow fails
2. Error Trigger fires in the error handler workflow
3. Error handler parses the failure context (channel, URL, error type)
4. PostgreSQL node writes to `knowledge_dlq` table
5. Slack node sends failure alert

**Consumer (Retry Workflow):**
1. Scheduled n8n workflow runs every 15 minutes
2. Queries `knowledge_dlq` for pending items with `next_retry_at <= NOW()`
3. For each item, attempts re-ingestion
4. On success: updates status to `resolved`
5. On failure: increments retry_count, sets next_retry_at with exponential backoff
6. If retry_count >= max_retries: sets status to `acknowledged` (requires manual review), sends Slack alert

**Management Workflow (Slack-triggered):**
1. Slack command triggers n8n webhook
2. Returns DLQ summary: counts by status, top failing channels, oldest unresolved
3. Supports actions: retry specific item, skip item, retry all for a channel

### 5.4 Exponential Backoff Schedule

| Retry # | Delay | Cumulative Time |
|---------|-------|-----------------|
| 1 | 5 minutes | 5 minutes |
| 2 | 15 minutes | 20 minutes |
| 3 | 1 hour | 1 hour 20 minutes |
| 4 | 4 hours | 5 hours 20 minutes |
| 5 | 12 hours | 17 hours 20 minutes |

### 5.5 n8n-Specific DLQ Resources

- **"n8n Dead-Letter Queues Done Right" (Jan 2026)** -- Covers idempotency keys, durable payloads, and controlled reprocessing for production n8n systems. [Medium/@kaushalsinh73, 2026]
- **n8n Scaling & Reliability Guide** -- Covers queue mode topologies, error handling at scale, and production overlays with retry and dead-letter patterns. [Medium/@orami98, 2025]

---

## 6. Slack Integration Patterns

### 6.1 n8n Slack Node Capabilities

The n8n Slack node supports (via OAuth2 authentication):
- Sending messages to channels and DMs
- Rich formatting with **Slack Block Kit** (sections, headers, dividers, buttons, images)
- Attachments with fields and colors
- Message threading (reply to existing messages)
- File uploads
- Channel management (create, archive, invite users)
- User lookups

### 6.2 Block Kit Usage in n8n

**Important caveats discovered in research:**
- Blocks JSON must be wrapped in `{ "blocks": [...] }` format, not passed as a raw array
- Validate all Block Kit JSON using the [Slack Block Kit Builder](https://app.slack.com/block-kit-builder) before use
- The notification/fallback text field can override blocks if not configured correctly
- Markdown in blocks uses Slack's `mrkdwn` format, not standard Markdown

### 6.3 KnowledgeOps Slack Alert Patterns

**Pattern 1: Immediate Failure Alert**
```json
{
  "blocks": [
    {
      "type": "header",
      "text": { "type": "plain_text", "text": "Pipeline Failure Alert" }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Channel:*\nTech With Tim" },
        { "type": "mrkdwn", "text": "*Error:*\nYouTube API rate limit (429)" },
        { "type": "mrkdwn", "text": "*Video:*\nhttps://youtube.com/watch?v=..." },
        { "type": "mrkdwn", "text": "*Retry:*\n1 of 5 (next: 15m)" }
      ]
    },
    {
      "type": "actions",
      "elements": [
        { "type": "button", "text": { "type": "plain_text", "text": "Skip" }, "action_id": "dlq_skip" },
        { "type": "button", "text": { "type": "plain_text", "text": "Retry Now" }, "action_id": "dlq_retry" }
      ]
    }
  ]
}
```

**Pattern 2: Daily Digest**
```
KnowledgeStack Daily Digest - Jan 30, 2026

Pipeline Health: GREEN
  Executions: 47 success / 3 failed (94% success rate)
  Processing Time: 2h 14m total

Channel Status:
  Active (last 7 days): 42/50
  Stale (3+ weeks): 3 channels
    - ChannelA (last: Jan 5)
    - ChannelB (last: Jan 8)
    - ChannelC (last: Jan 2)

Dead Letter Queue:
  Pending: 5 items
  Retrying: 2 items
  Resolved today: 8 items
  Oldest unresolved: 3 days

Backlog: 12 videos queued, ETA ~45 minutes
```

**Pattern 3: Stale Channel Alert**
Triggered weekly or when a channel exceeds 3 weeks without ingestion.

### 6.4 Interactive Slack Buttons

For Slack interactive buttons to work in n8n:
1. Enable "Interactivity" in your Slack app settings
2. Set the Request URL to an n8n webhook endpoint
3. Create an n8n workflow that handles the button payloads
4. Parse `action_id` to determine which button was clicked
5. Execute the appropriate action (retry, skip, acknowledge)

### 6.5 Scheduled Summaries via n8n

n8n's Schedule Trigger node can fire daily/weekly digest workflows:
1. Schedule Trigger fires at 9:00 AM daily
2. n8n queries its own API for execution stats (last 24 hours)
3. n8n queries PostgreSQL for DLQ stats and channel status
4. Formats the data into a Slack Block Kit message
5. Posts to the #knowledgeops channel

### 6.6 Grafana + Slack Alerting (Complementary)

Grafana natively supports Slack as a notification contact point:
- **Method 1**: Slack Bot Token (more flexible, recommended)
- **Method 2**: Incoming Webhook (simpler, single channel)

Grafana alert rules can fire on Prometheus metrics thresholds:
- Error rate > 10% for 5 minutes
- No executions for 2+ hours (pipeline stalled)
- Queue depth growing beyond capacity

**Limitation:** Grafana does not natively send scheduled report summaries to Slack. Grafana's reporting feature (Enterprise/Cloud only) sends PDF/email. For Slack-based scheduled reports, use n8n.

---

## 7. Grafana Dashboards for n8n

### 7.1 Official Grafana Labs Dashboards

**Dashboard #24474 -- n8n System Health Overview**
- **URL:** https://grafana.com/grafana/dashboards/24474-n8n-system-health-overview/
- **Data source:** Prometheus
- **Covers:** CPU, memory, heap usage, garbage collection, event loop performance, cluster status
- **Use case:** Low-level infrastructure health of the n8n instance

**Dashboard #24475 -- n8n Workflow & Execution Analytics**
- **URL:** https://grafana.com/grafana/dashboards/24475-n8n-workflow-execution-analytics/
- **Data source:** PostgreSQL (queries n8n's database directly)
- **Covers:** Workflow statistics, execution performance, error hotspots, queue depth, long-running executions
- **Use case:** Workflow-level observability -- exactly what KnowledgeOps needs

### 7.2 Community Dashboards and Resources

| Resource | Description | Link |
|----------|-------------|------|
| n8n + Grafana Full Node.js Metrics Dashboard | Community-built, includes JSON export | [n8n Community](https://community.n8n.io/t/n8n-grafana-full-node-js-metrics-dashboard-json-example-included/115366) |
| n8n Command Center with Grafana | Comprehensive system using n8n + Supabase + Prometheus + webhooks | [demodomain.dev](https://demodomain.dev/2025/03/10/building-a-comprehensive-n8n-command-center-with-grafana-the-detailed-journey/) |
| n8n Monitoring Setup Guide (OpenCharts) | Multi-level monitoring guide for Helm deployments | [OpenCharts Docs](https://community-charts.github.io/docs/charts/n8n/monitoring) |

### 7.3 Custom KnowledgeOps Dashboard (Recommended)

Beyond the pre-built dashboards, create a custom Grafana dashboard with:

**Panel 1: Pipeline Health Overview** (Single Stat)
- Success rate (last 24h) from Prometheus: `sum(rate(n8n_execution_total[24h]) - rate(n8n_execution_failed_total[24h])) / sum(rate(n8n_execution_total[24h])) * 100`

**Panel 2: Channel Status Table** (Table from PostgreSQL)
- Query Speakr/n8n database for last ingestion timestamp per channel
- Color code: green (< 7 days), yellow (7-21 days), red (> 21 days)

**Panel 3: DLQ Status** (Table from PostgreSQL)
- Query `knowledge_dlq` for pending/retrying/failed counts

**Panel 4: Execution Timeline** (Time Series from Prometheus)
- `rate(n8n_execution_total[5m])` overlaid with `rate(n8n_execution_failed_total[5m])`

**Panel 5: Processing Backlog** (Gauge from PostgreSQL or custom metric)
- Videos queued vs processed

### 7.4 Loki Integration

n8n logs can be shipped to Loki using Promtail or Docker's Loki logging driver. This provides:
- Full-text search across n8n logs in Grafana
- Correlation between metrics spikes and log entries
- Error message details without querying the n8n API

A community Loki plugin for n8n also exists for pushing log data directly from workflows.

---

## 8. Tool Evaluation Matrix

### 8.1 Scoring Criteria

Each tool rated 1-5 on: Fit (relevance to KnowledgeOps needs), Effort (setup difficulty, 5=easiest), Maintenance (ongoing overhead, 5=lowest), Integration (compatibility with existing stack), Maturity (community, documentation, stability).

### 8.2 Evaluation

| Tool | Fit | Effort | Maint. | Integration | Maturity | Total | Phase |
|------|-----|--------|--------|-------------|----------|-------|-------|
| **n8n Native (API + Error Workflows)** | 5 | 5 | 5 | 5 | 4 | 24 | MVP |
| **n8n Prometheus Metrics** | 5 | 5 | 5 | 5 | 4 | 24 | MVP |
| **PostgreSQL DLQ** | 5 | 4 | 5 | 5 | 5 | 24 | MVP |
| **Grafana Dashboards (#24474, #24475)** | 5 | 5 | 5 | 5 | 4 | 24 | MVP |
| **Grafana Alerting -> Slack** | 4 | 4 | 4 | 5 | 5 | 22 | MVP |
| **Slack Block Kit via n8n** | 4 | 3 | 4 | 5 | 4 | 20 | MVP |
| **Uptime Kuma** | 4 | 5 | 4 | 4 | 5 | 22 | Growth |
| **Healthchecks.io** | 3 | 4 | 4 | 3 | 5 | 19 | Growth |
| **Grafana Loki (n8n logs)** | 3 | 3 | 4 | 5 | 5 | 20 | Growth |
| **Prefect/Dagster/Windmill** | 2 | 2 | 2 | 2 | 4 | 12 | Overkill |

---

## 9. Recommended Architecture by Phase

### 9.1 MVP Phase (Week 1-2)

**No new tools needed.** Everything built with n8n + PostgreSQL + existing Grafana/Prometheus.

```
n8n (Helicarrier 10.0.0.27)
  |
  |-- Ingestion Workflows (per channel)
  |     |-- Node-level retry (3x, 5s delay)
  |     |-- Error branching for partial failures
  |
  |-- Error Handler Workflow
  |     |-- Error Trigger -> Parse failure context
  |     |-- Write to PostgreSQL knowledge_dlq table
  |     |-- Send Slack alert (Block Kit formatted)
  |
  |-- DLQ Processor Workflow (every 15 min)
  |     |-- Query PostgreSQL for retryable items
  |     |-- Retry via n8n API or direct re-processing
  |     |-- Update DLQ status
  |
  |-- Daily Digest Workflow (9 AM)
  |     |-- Query n8n API for last 24h stats
  |     |-- Query PostgreSQL for channel status + DLQ counts
  |     |-- Format and send Slack digest
  |
  |-- Stale Channel Checker (weekly)
  |     |-- Query last ingestion per channel
  |     |-- Alert on 3+ week gaps
  |
  +-- /metrics endpoint -> Prometheus (Coulson)

PostgreSQL (Banner 10.0.0.33)
  |-- knowledge_dlq table
  |-- Channel status tracking (via Speakr data or custom table)

Grafana (Coulson 10.0.0.28)
  |-- Dashboard #24474 (n8n System Health)
  |-- Dashboard #24475 (Workflow & Execution Analytics)
  |-- Alert rules -> Slack contact point

Slack
  |-- #knowledgeops channel
  |-- Immediate failure alerts
  |-- Daily digest
  |-- Stale channel weekly alerts
```

**MVP Setup Steps:**
1. Add `N8N_METRICS=true` + `N8N_METRICS_INCLUDE_WORKFLOW_ID_LABEL=true` to n8n Docker environment
2. Add n8n scrape target to Prometheus config on Coulson
3. Import Grafana dashboards #24474 and #24475
4. Create `knowledge_dlq` table in PostgreSQL
5. Build Error Handler workflow in n8n
6. Build DLQ Processor workflow in n8n
7. Build Daily Digest workflow in n8n
8. Build Stale Channel Checker workflow in n8n
9. Configure Grafana -> Slack alerting contact point
10. Set up Grafana alert rules for error rate thresholds

### 9.2 Growth Phase (Month 2-3)

Add monitoring depth and self-healing:

```
+ Uptime Kuma (new, on Banner or Helicarrier)
  |-- HTTP monitors for Speakr, n8n
  |-- Push monitors for each ingestion workflow
  |-- Internal status page at status.knowledgestack.local
  |-- Slack notifications for service downtime

+ Grafana Loki Integration
  |-- Ship n8n container logs via Promtail
  |-- Ship Speakr container logs via Promtail
  |-- Correlate logs with Prometheus metrics
  |-- Custom Grafana panels combining metrics + logs

+ Custom KnowledgeOps Grafana Dashboard
  |-- Channel status heatmap (PostgreSQL data source)
  |-- DLQ depth gauge
  |-- Pipeline throughput over time
  |-- Estimated backlog completion time

+ Interactive Slack Bot
  |-- /dlq status -- show DLQ summary
  |-- /dlq retry <id> -- retry specific item
  |-- /dlq skip <id> -- skip/acknowledge item
  |-- /pipeline status -- show pipeline health
  |-- /channel <name> -- show channel details
```

### 9.3 Scale Phase (Month 4+, if needed)

Only if throughput demands exceed n8n's capabilities:

- n8n Queue Mode with Redis + separate worker nodes
- Healthchecks.io (self-hosted) for multi-pipeline monitoring
- Consider Prefect or Windmill if workflow complexity outgrows n8n
- OpenTelemetry tracing for cross-service debugging

---

## 10. Bibliography

### Official Documentation

1. n8n Docs. "API Reference." https://docs.n8n.io/api/api-reference/
2. n8n Docs. "n8n Public REST API Documentation and Guides." https://docs.n8n.io/api/
3. n8n Docs. "Error Handling." https://docs.n8n.io/flow-logic/error-handling/
4. n8n Docs. "Enable Prometheus Metrics." https://docs.n8n.io/hosting/configuration/configuration-examples/prometheus/
5. n8n Docs. "Monitoring." https://docs.n8n.io/hosting/logging-monitoring/monitoring/
6. n8n Docs. "All Executions." https://docs.n8n.io/workflows/executions/all-executions/
7. n8n Docs. "Slack Node Documentation." https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.slack/
8. n8n Docs. "Environment Variables Overview." https://docs.n8n.io/hosting/configuration/environment-variables/
9. Grafana Docs. "Configure Slack for Alerting." https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-slack/

### Grafana Dashboards

10. Grafana Labs. "n8n System Health Overview (Dashboard #24474)." https://grafana.com/grafana/dashboards/24474-n8n-system-health-overview/
11. Grafana Labs. "n8n Workflow & Execution Analytics (Dashboard #24475)." https://grafana.com/grafana/dashboards/24475-n8n-workflow-execution-analytics/

### n8n Workflow Templates

12. n8n. "Advanced Retry and Delay Logic." https://n8n.io/workflows/5447-advanced-retry-and-delay-logic/
13. n8n. "Auto-Retry Engine: Error Recovery Workflow." https://n8n.io/workflows/3144-auto-retry-engine-error-recovery-workflow/

### Tools

14. Healthchecks.io. "Open-source cron job and background task monitoring." https://github.com/healthchecks/healthchecks
15. Uptime Kuma. "A fancy self-hosted monitoring tool." https://github.com/louislam/uptime-kuma

### Community & Third-Party Sources

16. n8n Community. "Monitoring & Reporting n8n Server Workflows." https://community.n8n.io/t/monitoring-reporting-n8n-server-workflows/117368
17. n8n Community. "N8n + Grafana Full Node.js Metrics Dashboard." https://community.n8n.io/t/n8n-grafana-full-node-js-metrics-dashboard-json-example-included/115366
18. n8n GitHub. "REST API Executions Endpoint does not accept 'running' status filter (Issue #19664)." https://github.com/n8n-io/n8n/issues/19664
19. Neurobyte. "n8n Dead-Letter Queues Done Right: Replayable, Idempotent Recovery at Scale." Medium, January 2026. https://medium.com/@kaushalsinh73/n8n-dead-letter-queues-done-right-replayable-idempotent-recovery-at-scale-70686f2d15d6
20. Orami. "The n8n Scaling & Reliability Guide: Queue Mode Topologies, Error Handling at Scale, and Production Overlays." Medium, 2025. https://medium.com/@orami98/the-n8n-scaling-reliability-guide-queue-mode-topologies-error-handling-at-scale-and-production-9f33b13d2be8
21. Wednesday Solutions. "Advanced n8n Error Handling and Recovery Strategies." https://www.wednesday.is/writing-articles/advanced-n8n-error-handling-and-recovery-strategies
22. AmineDiro. "Implementing a Postgres Job Queue in Less Than an Hour." https://aminediro.com/posts/pg_job_queue/
23. Software Engineer's Notes. "Dead Letter Queues (DLQ): The Complete, Developer-Friendly Guide." September 2025. https://swenotes.com/2025/09/25/dead-letter-queues-dlq-the-complete-developer-friendly-guide/
24. DemoDomain. "Building a Comprehensive N8n Command Center with Grafana." March 2025. https://demodomain.dev/2025/03/10/building-a-comprehensive-n8n-command-center-with-grafana-the-detailed-journey/
25. LumaDock. "Monitoring n8n on a VPS with Prometheus and Grafana." https://lumadock.com/tutorials/n8n-monitoring-prometheus-grafana-vps
26. ANDREFFS. "Observability on n8n." https://www.andreffs.com/blog/observability-on-n8n/
27. Clever Cloud. "Automating Slack Summaries with n8n, Clever Cloud, and LLMs." March 2025. https://www.clever.cloud/blog/engineering/2025/03/21/automating-slack-summaries-with-n8n-clever-cloud-and-llms/
28. MartinUke0. "A Detailed Guide to Using the n8n API with Python." December 2025. https://martinuke0.github.io/posts/2025-12-10-a-detailed-guide-to-using-the-n8n-api-with-python/
29. Easify AI. "Error Handling in n8n: How to Retry & Monitor Workflows." https://easify-ai.com/error-handling-in-n8n-monitor-workflow-failures/
30. AI Fire. "5 n8n Error Handling Techniques for a Resilient Automation Workflow." https://www.aifire.co/p/5-n8n-error-handling-techniques-for-a-resilient-automation-workflow
31. Medium (The Atomic Architect). "PostgreSQL as a Message Queue: The SKIP LOCKED Pattern." https://medium.com/@the_atomic_architect/postgresql-replaced-my-message-queue-and-taught-me-skip-locked-along-the-way-87d59e5b9525
32. OpenCharts. "n8n Monitoring Setup." https://community-charts.github.io/docs/charts/n8n/monitoring

---

*Report generated 2026-01-30. Sources verified across n8n official documentation, Grafana Labs, GitHub repositories, and community publications from 2025-2026.*
