# KnowledgeOps Research Report: AI-Native Ops Tools & Full DevOps Lifecycle

**Date:** 2026-01-30
**Author:** Claude Opus 4.5 research agent on behalf of Matt
**Research Type:** Operational / DevOps / AI-Native Tooling
**Sources Consulted:** 60+ across official documentation, GitHub repositories, vendor comparisons, community guides, CNCF publications
**Supplements:** `_bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md` (the earlier technical research)

---

## Executive Summary

**Key Finding 1:** Langfuse is the clear winner for LLM/AI pipeline observability in a self-hosted context. It is MIT-licensed, deploys via Docker Compose, integrates with LiteLLM (which KnowledgeStack already uses), and provides tracing, prompt management, and evaluation -- all self-hosted with no restrictions. However, for KnowledgeStack MVP where the "AI" is primarily Speakr transcription + LiteLLM enrichment (not a RAG chatbot), Langfuse is a Growth-phase addition, not MVP.

**Key Finding 2:** The existing Grafana/Prometheus/Loki stack covers 70-80% of KnowledgeOps needs at MVP. Adding cAdvisor for container metrics, the Grafana LLM plugin for AI-assisted log analysis, and Grafana Tempo for distributed tracing completes the observability picture without introducing new platforms.

**Key Finding 3:** pgBackRest with WAL archiving is the industry-standard PostgreSQL backup solution and works well in Docker. Combined with n8n workflow Git backups and NAS-based volume backups, this provides a complete backup strategy. The most critical gap is having a tested recovery playbook -- backups without tested restores are worthless.

**Key Finding 4:** AGPL-3.0 compliance for Speakr requires immediate attention since external access is planned. If Speakr is modified or tightly integrated and exposed over a network, source code disclosure obligations may be triggered. Architectural isolation (Speakr as a standalone service with clean API boundaries) is the recommended mitigation.

**Key Finding 5:** For KnowledgeOps MVP, resist the temptation to build everything. The research identifies a clear MVP/Growth/Overkill classification for each area. The MVP focuses on extending the existing Grafana stack, implementing pgBackRest, adding Docker healthchecks with autoheal, and establishing correlation IDs for pipeline tracking.

---

## Table of Contents

1. [Research Area 1: AI-Native Ops Tools](#1-ai-native-ops-tools)
   - 1.1 LLM Observability Platforms
   - 1.2 AI-Powered Incident Detection
   - 1.3 RAG Pipeline Monitoring
   - 1.4 LLM-Powered Log Analysis
   - 1.5 n8n + AI Monitoring
2. [Research Area 2: Full DevOps Lifecycle](#2-full-devops-lifecycle)
   - 2.1 Backup & Recovery
   - 2.2 Deployment & Updates
   - 2.3 Security & Access
   - 2.4 Performance & Capacity
   - 2.5 Logging & Observability
   - 2.6 Health Checks & Self-Healing
   - 2.7 Data Integrity
3. [Consolidated Recommendations](#3-consolidated-recommendations)
4. [Bibliography](#4-bibliography)

---

## 1. AI-Native Ops Tools

### 1.1 LLM Observability Platforms

The LLM observability space has matured significantly in 2024-2026, with several platforms competing to be the "Datadog for AI." Here is a comparison of the leading options relevant to KnowledgeStack:

#### Langfuse (Recommended for Growth Phase)

- **License:** MIT (fully open source, no restrictions) [Langfuse GitHub, 2025]
- **Self-hosting:** Docker Compose deployment in ~5 minutes; production via Kubernetes/Helm
- **Architecture:** Langfuse Web + Worker + PostgreSQL + ClickHouse + Redis + S3/Blob Store
- **Key Features:** End-to-end tracing for LLM calls, prompt versioning with playground, LLM-as-judge evaluation, cost tracking per token/model, OpenTelemetry native support, session tracking for multi-step workflows
- **KnowledgeStack Relevance:** Integrates natively with LiteLLM (which KnowledgeStack uses). Could trace every enrichment call -- the exact prompt sent, model response, token usage, latency. Sessions could track a video through the full enrichment pipeline.
- **Recent News:** ClickHouse acquired Langfuse in 2025, signaling long-term viability and investment in the open-source platform [ClickHouse Blog, 2025]
- **Self-hosting Requirements:** PostgreSQL (already have), ClickHouse (new dependency), Redis (lightweight), S3-compatible storage (MinIO or NAS path)

**Assessment for KnowledgeStack:** Langfuse is powerful but introduces significant new infrastructure (ClickHouse, Redis, S3). At MVP scale (processing a few hundred videos), the overhead is not justified. The existing Grafana/Loki stack can capture LLM call metrics through structured logging. **Recommendation: Growth phase.**

#### Arize Phoenix (Alternative)

- **License:** Open source (BSD-3)
- **Self-hosting:** Runs locally or in containers; built entirely on OpenTelemetry
- **Key Features:** Trace visualization, RAG evaluation metrics, embedding clustering, OpenTelemetry-native
- **KnowledgeStack Relevance:** Lighter weight than Langfuse; good for local debugging of AI pipelines
- **Limitation:** Primarily an observability/debugging tool -- less comprehensive for production monitoring than Langfuse

**Assessment:** Useful for ad-hoc debugging during development. Not needed for ops. [Arize Phoenix, 2025]

#### LangSmith (Not Recommended)

- **License:** Closed source (Enterprise license required for self-hosting)
- **Limitation:** LangChain-centric; KnowledgeStack does not use LangChain
- **Assessment:** Skip entirely. Framework lock-in, closed source, and the wrong ecosystem. [orq.ai, 2025]

#### Comparison Matrix

| Criteria | Langfuse | Arize Phoenix | LangSmith |
|----------|----------|---------------|-----------|
| Self-hosted (free) | Yes (MIT) | Yes (BSD-3) | No (Enterprise only) |
| Docker Compose deploy | Yes | Yes | No |
| LiteLLM integration | Native | Via OpenTelemetry | No |
| OpenTelemetry support | Yes | Yes (native) | Limited |
| Infrastructure overhead | High (ClickHouse, Redis, S3) | Low (standalone) | N/A |
| Production monitoring | Excellent | Good | Excellent |
| **KnowledgeStack Phase** | **Growth** | **Optional** | **Skip** |

### 1.2 AI-Powered Incident Detection & Root Cause Analysis

The AIOps space in 2025-2026 is dominated by enterprise SaaS platforms (Datadog Bits AI, Dynatrace Davis AI, BigPanda) that are priced far beyond KnowledgeStack's scale. However, relevant self-hosted options exist:

#### Grafana AI Capabilities (Recommended)

- **Grafana LLM Plugin:** Open source plugin that connects Grafana OSS to OpenAI/Azure OpenAI, enabling natural language queries, dashboard exploration, and "explain this" features across all data sources [Grafana Labs, 2025]
- **Grafana MCP Server:** Allows AI agents (Claude, etc.) to interact with Grafana data directly
- **Grafana SRE Agent (Cloud only):** Automated root cause analysis -- not available for OSS, but the LLM plugin provides a subset of capabilities
- **KnowledgeStack Relevance:** Since Grafana is already running on Coulson, adding the LLM plugin is a zero-cost enhancement. Configure it to use LiteLLM as the LLM provider for cost-effective AI-assisted analysis.

**Assessment:** The Grafana LLM plugin is the only AI-native ops tool that fits MVP -- it leverages existing infrastructure and adds AI capabilities incrementally. [Grafana Labs, 2025]

#### Custom LLM Log Analysis (Growth Phase)

The CNCF community has documented approaches for using local/self-hosted LLMs to analyze and streamline logs [CNCF Blog, 2024]. Key patterns:

- Use quantized open-source models (Llama 3, DeepSeek) running on Ollama to analyze log patterns
- Build n8n workflows that feed Loki log queries to a local LLM for anomaly detection
- Keep all data on-premise -- no external LLM API calls for sensitive log data
- 8-bit quantized models can run on standard server CPUs

**Assessment:** Interesting for Growth phase. An n8n workflow could periodically query Loki, send log summaries to Ollama for analysis, and alert on detected anomalies. Low cost, self-hosted, and leverages existing infrastructure. [CNCF, 2024]

#### Community Project: AI-Powered Observability System

A GitHub project combines Prometheus + Grafana + Loki + LLM engine for real-time anomaly detection and root cause insights [KeerthiKeswaran/AI-Powered-Observability-and-Log-Analysis-System, GitHub]. Worth monitoring as a reference architecture but not production-ready.

**MVP/Growth/Overkill Classification:**
- **MVP:** Grafana LLM plugin (add to existing Grafana instance)
- **Growth:** Custom n8n + Ollama log analysis workflow
- **Overkill:** Enterprise AIOps platforms (Datadog, Dynatrace, BigPanda)

### 1.3 RAG Pipeline Monitoring

KnowledgeStack's pipeline is not a traditional RAG system -- it is an ingestion + transcription + enrichment pipeline. However, some RAG monitoring concepts apply:

#### Relevant RAG Monitoring Concepts

- **Retrieval quality metrics:** When KnowledgeStack later adds a retrieval/search layer (e.g., Qdrant similarity search), tools like Ragas (open source, Apache 2.0) can evaluate retrieval precision, recall, faithfulness, and answer relevancy [Braintrust, 2025]
- **Pipeline stage monitoring:** Each stage (RSS fetch -> download -> dedup -> upload -> transcribe -> enrich) should have latency, error rate, and throughput metrics -- this is standard pipeline observability, not RAG-specific
- **Content quality evaluation:** LLM-as-judge patterns (supported by Langfuse and Ragas) can evaluate enrichment output quality

**Assessment:** RAG-specific tools are premature for KnowledgeStack MVP. Standard pipeline observability via Prometheus metrics + Loki logs covers current needs. Ragas and Langfuse become relevant when a retrieval/search layer is added. [Langfuse Blog, 2025; Ragas, 2025]

### 1.4 LLM-Powered Log Analysis

Beyond the Grafana LLM plugin discussed in 1.2, additional approaches exist:

#### OpenLLMetry (Traceloop)

- Open-source GenAI observability based on OpenTelemetry [Traceloop/openllmetry, GitHub]
- Auto-instruments LLM calls and exports traces to any OpenTelemetry-compatible backend
- Could pipe LiteLLM call traces directly into Grafana Tempo
- **Assessment:** Lightweight alternative to Langfuse for Growth phase. Requires less infrastructure.

#### Local LLM for Log Streamlining (CNCF Pattern)

- Use open-source LLMs to reduce log verbosity while maintaining context [CNCF, 2024]
- Achieves cost savings on log storage (Loki) by reducing log volume
- Can run on standard CPUs with 8-bit quantized models
- **Assessment:** Nice-to-have for Growth phase if log volume becomes a cost concern.

### 1.5 n8n + AI Monitoring Integrations

n8n serves as the workflow orchestration layer for KnowledgeStack. Monitoring n8n itself and the AI pipelines it orchestrates requires specific patterns:

#### n8n Observability Best Practices [n8n Docs, 2025; Wednesday.is, 2025]

1. **Metrics Export:** n8n can export execution metrics to Prometheus -- track workflow execution count, duration, error rate, and queue depth
2. **Error Triggers:** Use n8n's error trigger node to catch workflow failures and route alerts to Slack
3. **Structured Logging:** n8n supports custom log streaming to any aggregator; configure structured JSON logging with correlation IDs
4. **Git-Based Version Control:** Critical for auditing and rollback (see Section 2.2)
5. **Webhook Monitoring:** Track webhook response times and error rates for inbound triggers (RSS feed checks)

#### n8n + AI Monitoring Pattern

An effective pattern combines n8n + Ollama for AI-powered DevOps:
- n8n workflow fetches execution history from its own API
- Sends execution data to a local LLM (Ollama) for anomaly detection
- LLM identifies patterns: increasing failure rates, abnormal execution times, stuck workflows
- Alerts via Slack with LLM-generated summaries

**Assessment for KnowledgeStack:**
- **MVP:** Prometheus metrics export from n8n + error trigger to Slack
- **Growth:** n8n self-monitoring workflow with Ollama analysis
- **Overkill:** Enterprise workflow orchestration monitoring

---

## 2. Full DevOps Lifecycle

### 2.1 Backup & Recovery

#### PostgreSQL Backup Strategy

**pgBackRest (Recommended)** [Data Egret, 2025; pgBackRest Docs, 2025; Severalnines, 2025]

pgBackRest is the industry-standard PostgreSQL backup tool, supporting full, differential, and incremental backups with WAL archiving for point-in-time recovery (PITR).

Key configuration for Docker:
- Layer pgBackRest on top of the official PostgreSQL Docker image
- Enable asynchronous WAL archiving (`archive-async=y`) for better performance
- Configure a dedicated spool path (same filesystem as `pg_wal` but not inside it)
- Use `start-fast=y` for immediate backup start
- Set `process-max` per command (e.g., backup=4, restore=8)
- Match `compress-type` between archive-push and backup commands (lz4 recommended)

Common pitfall: WAL archive retention trap. If `repo-retention-archive` is not explicitly configured, old WAL files may accumulate indefinitely. Set this explicitly based on your retention policy. [Data Egret, 2025]

PITR in Docker: Not as hard as feared once you have an end-to-end playbook. Key steps: ensure WALs are archived (backups alone are not enough), stop Postgres, restore from a throwaway container, then start again. [Data Egret, 2025]

**pg_dump (Simpler Alternative for MVP)**

For MVP scale (small database), a daily `pg_dump` cron job may be sufficient:
- `docker exec postgres pg_dump -Fc -f /backups/knowledge_$(date +%Y%m%d).dump`
- Store dumps on NAS via bind mount
- Retention: keep 30 daily, 12 monthly
- Test restore monthly

**Recommendation:**
- **MVP:** Daily `pg_dump` to NAS, monthly restore test
- **Growth:** pgBackRest with WAL archiving and PITR capability
- **Overkill:** Streaming replication to a standby (premature at this scale)

#### Docker Volume Backup

**Bind Mount Strategy (Recommended)** [Marius Hosting, 2025; WunderTech, 2025]

- Use bind mounts to visible shared folders (e.g., `/data/docker/knowledge/`) rather than Docker-managed volumes
- This makes data visible to standard backup tools (rsync, NAS backup agents)
- Docker Compose YAML files stored in Git provide the "infrastructure" backup
- Combine with Offen (docker-volume-backup) or Backrest for container-aware, database-safe backups

**Btrfs Caution:** If the NAS uses ext4 (not Btrfs), file locks during backup can cause corruption, especially for SQLite databases. PostgreSQL is safe due to WAL, but be aware for other stateful services. [SynoForum, 2025]

**Recommendation:**
- **MVP:** Bind mounts + rsync to NAS + Git for Compose files
- **Growth:** Offen/Backrest for automated, container-aware backups with notifications
- **Overkill:** Kubernetes-style persistent volume snapshots

#### NAS-Based Backup for Audio Files

Audio files on the Synology NAS require their own backup strategy:

- **Hyper Backup:** Synology's built-in backup tool can schedule automated backups to cloud (Backblaze B2, AWS S3) or a second NAS [Synology, 2025]
- **Snapshot Replication:** Available only for Btrfs-formatted shared folders. Provides instant point-in-time recovery. Cannot be used for `@docker` directories, but works for regular shared folders. [SynoForum, 2025]
- **3-2-1 Rule:** 3 copies, 2 different media types, 1 offsite
- **Immutable Backups:** Growing trend -- set immutability flags on backup files to prevent ransomware modification

**Recommendation:**
- **MVP:** Hyper Backup of audio shared folder to a second volume or USB drive
- **Growth:** Offsite replication to Backblaze B2 ($6/TB/month) + Btrfs snapshots
- **Overkill:** Multi-site NAS replication

#### Speakr Data Backup (Black Box Considerations)

Speakr runs as a containerized service with its own internal state. Key data to protect:

- **Speakr's database:** If Speakr uses an internal database (likely SQLite or PostgreSQL), its data volume must be bind-mounted and backed up
- **Model files:** Whisper models downloaded by Speakr; these can be re-downloaded but backup saves time
- **Configuration:** Speakr's configuration files/environment variables
- **Transcription outputs:** If stored within Speakr before retrieval, these need protection

**Recommendation:** Ensure all Speakr data directories are bind-mounted to visible paths. Include them in the standard Docker volume backup process. Document the Speakr container's volume mounts and environment variables so the service can be rebuilt from backups.

#### Disaster Recovery Playbook

A tested disaster recovery playbook is more important than sophisticated backup tools. Document and test:

1. **Full rebuild from scratch:** New VM, install Docker, restore Compose files from Git, restore data from backups
2. **Single service recovery:** Rebuild one container from backup
3. **Database restore:** Restore PostgreSQL from pg_dump or pgBackRest
4. **NAS failure:** Restore audio files from offsite backup
5. **Test frequency:** Quarterly restore test to a throwback VM

### 2.2 Deployment & Updates

#### Docker Compose Update Strategies

**Simple Rolling Update (MVP)** [Docker Docs, 2025; Dokploy, 2025]

For Docker Compose on a single VM:
```bash
# Pull new images
docker compose pull

# Recreate only changed services (no-deps avoids restarting dependencies)
docker compose up -d --no-deps <service-name>
```

This is sufficient for MVP. The brief downtime during container restart is acceptable for a non-user-facing ingestion pipeline.

**Blue-Green Deployment (Growth)** [TechnicallyShane, 2025; Primfeed, 2025; Ritesh Rana, 2025]

For zero-downtime updates:
- Maintain two Compose project environments (blue and green)
- Deploy new version to inactive environment
- Run health checks and smoke tests
- Switch Traefik routing to the new environment
- Keep old environment on standby for instant rollback

Key requirements: Traefik label-based routing (already in the infrastructure), health checks on all services, and a deployment script that automates the switchover.

**Recommendation:**
- **MVP:** Simple `docker compose pull && docker compose up -d` with brief downtime
- **Growth:** Blue-green with Traefik routing and automated health check verification
- **Overkill:** Kubernetes with rolling update controllers

#### Speakr Upstream Update Process

Speakr is a third-party Docker image (AGPL-3.0 licensed). Update process:

1. Monitor Speakr's GitHub/Docker Hub for new releases (n8n workflow or Renovate bot)
2. Pull new image to a test environment: `docker compose -f docker-compose.test.yml pull speakr`
3. Run smoke test: submit a known audio file, verify transcription output matches expected baseline
4. If tests pass, update production Compose file and deploy
5. If tests fail, keep current version and create a tracking issue

**Recommendation:** Build an n8n workflow that checks for Speakr updates weekly, pulls to a staging environment, runs a smoke test, and notifies via Slack.

#### n8n Workflow Version Control

Multiple proven approaches exist [n8n.io, 2025; Wednesday.is, 2025; n8n-version-control GitHub, 2025]:

**Option 1: n8n Workflow Template (Simplest)**
- Use the official "Git Backup of Workflows and Credentials" template (n8n.io/workflows/1053)
- Exports all workflows as JSON, commits only when changes detected
- Runs on a schedule (daily) or on workflow save events
- Credentials exported encrypted by default (save the encryption key separately)

**Option 2: Bash Script + Cron**
- `docker exec n8n n8n export:workflow --all --output=/data/exports`
- Git commit and push from the host
- More control, less elegance

**Option 3: Bidirectional Sync (Growth)**
- Template n8n.io/workflows/5081 provides two-way sync between n8n and GitHub
- If n8n version is newer, it updates GitHub; if GitHub is newer, it updates n8n
- Useful for multi-environment (dev/staging/prod) workflows

**Recommendation:**
- **MVP:** Option 1 (n8n workflow template for daily Git backup)
- **Growth:** Option 3 (bidirectional sync with environment promotion)
- **Overkill:** Full CI/CD pipeline with linting, testing, and staged deployment

#### Database Migration Patterns

For PostgreSQL schema changes:

- **Liquibase or Flyway:** Industry-standard database migration tools. Liquibase supports drift detection and policy checks. [Liquibase, 2025]
- **Simple approach for MVP:** Numbered SQL migration files in Git, applied manually or via a startup script
- **n8n internal migrations:** n8n handles its own database migrations on startup -- just ensure backups before n8n version upgrades

**Recommendation:**
- **MVP:** Manual SQL migration files in Git, applied before deployment
- **Growth:** Flyway or Liquibase integrated into deployment pipeline
- **Overkill:** Automated schema diffing and migration generation

### 2.3 Security & Access

#### Container Security Scanning

**Trivy (Recommended)** [Aqua Security, 2025; Stakater, 2025; OpsDigest, 2025]

Trivy is the leading open-source container security scanner:
- Scans for vulnerabilities, misconfigurations, and embedded secrets
- Single Docker command: `docker run aquasec/trivy image <image-name>`
- Integrates with CI/CD pipelines (GitHub Actions, GitLab CI)
- VS Code extension available for development-time scanning
- Fast scans suitable for both ad-hoc and automated use

**Grype (Complementary)** [Anchore, 2025]

- Focused specifically on vulnerability detection with high accuracy
- Generates SBOMs (Software Bill of Materials) via Syft
- Smaller database updates than Trivy (better for bandwidth-constrained environments)

**Recommendation:**
- **MVP:** Weekly Trivy scan of all production images via cron or n8n workflow, results to Slack
- **Growth:** Trivy in CI/CD pipeline (fail build on critical/high CVEs) + Grype for SBOM generation
- **Overkill:** Continuous scanning with admission controllers

#### Secrets Management

**Infisical (Recommended for Growth)** [Infisical, 2025; GitHub, 2025]

- MIT-licensed, self-hosted via Docker Compose
- Requires PostgreSQL (already have) + Redis
- UI for managing secrets across environments
- Integrations with Docker, GitHub Actions, Kubernetes
- Secret rotation, versioning, and audit logging

**Current Approach (Acceptable for MVP)**

The project uses shared `.env` files at `/mnt/foundry_project/AppServices/env/` and the Infrastructure team's `secrets.sh` scripts. This is acceptable for MVP if:
- `.env` files are not committed to Git (verify `.gitignore`)
- File permissions restrict access (600, owned by deploy user)
- Secrets are rotated periodically (at minimum, after any team change)

**HashiCorp Vault / OpenBao (Overkill)**

Vault's BSL license change has led to the OpenBao fork (MPL 2.0). Both are operationally complex and overkill for this scale.

**Recommendation:**
- **MVP:** Current shared `.env` file approach with strict file permissions
- **Growth:** Infisical self-hosted for centralized secrets management with audit trail
- **Overkill:** HashiCorp Vault / OpenBao

#### AGPL-3.0 Compliance (Speakr)

**This requires immediate attention.** [Vaultinum, 2025; FOSSA, 2025; PowerPatent, 2025]

Speakr is licensed under AGPL-3.0. Key implications:

1. **AGPL vs GPL:** AGPL adds Section 13, which treats network access ("Remote Network Interaction") as equivalent to distribution. If users interact with AGPL-licensed software over a network, the source code must be made available -- even if the software is never "distributed" in the traditional sense.

2. **Two triggers for compliance obligation:** (a) You have modified the program, AND (b) you make the modified program available to people remotely through a computer network. Both must occur.

3. **KnowledgeStack risk analysis:**
   - If Speakr is used internally only (no external network access) --> lower risk
   - If Speakr's API is exposed externally, even indirectly through KnowledgeStack --> compliance obligation may be triggered
   - If Speakr is modified in any way (configuration changes via environment variables likely do not count as "modification," but code changes do) --> heightened risk

4. **Mitigation strategy -- Architectural isolation:**
   - Keep Speakr as a standalone service with clean API boundaries
   - Do not modify Speakr's source code
   - Use containerization to enforce isolation (Speakr in its own container, communication only via documented API)
   - Document that KnowledgeStack interacts with Speakr only through its public API
   - If external access is planned, consult legal counsel

5. **SBOM compliance:** Generate and maintain a Software Bill of Materials listing all components and their licenses. Trivy can assist with this.

6. **Source code availability:** If compliance is triggered, you must make the corresponding source code (Speakr with any modifications) available from a network server at no charge.

**Recommendation:**
- **MVP (Immediate):** Document architectural isolation of Speakr. Verify no source code modifications. Generate SBOM. If external access is planned, consult legal counsel before launch.
- **Growth:** Automated license compliance scanning (FOSSA, Trivy license scanning)
- **Overkill:** Full open-source program office

#### Network Security Between Hosts

KnowledgeStack spans multiple hosts: Banner, Jarvis, Helicarrier, Coulson, Fury.

- **MVP:** Ensure inter-host communication uses private network (10.0.0.x). Docker networks provide container-level isolation.
- **Growth:** WireGuard mesh VPN between hosts for encrypted inter-host traffic. Firewall rules limiting which hosts can reach which services.
- **Overkill:** Zero-trust networking with mTLS between all services

### 2.4 Performance & Capacity

#### Docker Resource Monitoring

**cAdvisor + Prometheus + Grafana (Recommended)** [Grafana Labs, 2025; dockprom, GitHub; DevOps.uz, 2025]

cAdvisor (Container Advisor) by Google provides real-time container metrics (CPU, memory, network, disk I/O). The standard monitoring stack:

1. **cAdvisor** runs as a container, exposes metrics on port 8080 at `/metrics`
2. **Prometheus** scrapes cAdvisor every 15-30 seconds
3. **Grafana** visualizes via pre-built dashboards

Recommended Grafana dashboards:
- **Dashboard ID 19908:** "cAdvisor Docker Insights" -- CPU, memory, I/O, container restarts
- **Dashboard ID 15798:** "Docker Monitoring" -- multi-node, multi-service support
- **Dashboard ID 13496:** "Docker and System Monitoring" -- combined host + container view

**dockprom project** (GitHub: stefanprodan/dockprom): Complete Docker Compose stack with Prometheus, Grafana, cAdvisor, NodeExporter, and AlertManager. Can be deployed alongside existing infrastructure.

**Recommendation:**
- **MVP:** Deploy cAdvisor on Banner, add Prometheus scrape target on Coulson, import Dashboard 19908
- **Growth:** dockprom full stack on each host, AlertManager for capacity alerts
- **Overkill:** Commercial container monitoring (Datadog, Sysdig)

#### PostgreSQL Performance Monitoring

**pg_stat_statements (Essential)** [Stormatics, 2025; pganalyze, 2025]

Enable in Docker Compose:
```yaml
command: >
  postgres
  -c shared_preload_libraries=pg_stat_statements
  -c pg_stat_statements.track=all
```

Then: `CREATE EXTENSION IF NOT EXISTS pg_stat_statements;`

This provides aggregate query statistics: execution count, total/mean time, rows returned, block reads. Essential for identifying slow queries.

**PostgreSQL Prometheus Exporter** [Uptrace, 2025]

- `prometheus-community/postgres_exporter` exposes PostgreSQL metrics to Prometheus
- Tracks connections, transactions, cache hit ratio, WAL, replication lag, table/index sizes
- Grafana dashboard ID 9628: "PostgreSQL Database" -- comprehensive monitoring

**pgBadger (Growth Phase)** [Oreate AI, 2025; Medium, 2025]

- Pure Perl tool that generates HTML reports from PostgreSQL logs
- Identifies: top queries by time, frequency, and lock waits; peak load hours; autovacuum activity
- Requires structured logging configuration in PostgreSQL
- Run periodically (weekly) to generate performance reports

**pgwatch2 (Alternative)** [Uptrace, 2025]

- Dockerized, self-contained PostgreSQL monitoring with its own dashboard
- No extensions or superuser privileges required
- Lower setup effort than Prometheus + custom dashboards

**Recommendation:**
- **MVP:** pg_stat_statements enabled + PostgreSQL Prometheus exporter + Grafana dashboard
- **Growth:** pgBadger weekly reports + pgwatch2 for deeper monitoring
- **Overkill:** pganalyze (commercial) or Percona PMM (heavy)

#### NAS Throughput Monitoring

- **Synology DSM metrics:** Synology exposes SNMP metrics for disk I/O, network throughput, and volume usage
- **Prometheus SNMP Exporter:** Can scrape Synology NAS metrics into Prometheus
- **Key metrics:** Read/write IOPS, throughput (MB/s), disk latency, volume utilization percentage

**Recommendation:**
- **MVP:** Manual monitoring via Synology DSM dashboard; Prometheus alert on disk usage > 80%
- **Growth:** SNMP exporter for full NAS metrics in Grafana
- **Overkill:** Dedicated storage monitoring platform

#### Disk Usage Projections and Alerting

- Estimate storage growth: (average audio file size) * (videos/month) * (retention period)
- Prometheus recording rules can compute disk usage growth rate
- Alert thresholds: warning at 70%, critical at 85% on all volumes
- Include Grafana annotations for capacity planning

### 2.5 Logging & Observability

#### Centralized Logging with Loki (Already Deployed)

Loki is already running on Coulson. Best practices for KnowledgeStack integration [Grafana Loki Docs, 2025]:

1. **Docker log driver:** Configure Docker daemon to send container logs directly to Loki using the Loki Docker plugin, or use Promtail/Alloy as a log collection agent
2. **Label strategy:** Use labels for `service`, `host`, `environment` -- avoid high-cardinality labels (no unique IDs as labels)
3. **Structured logging:** All services should emit JSON-formatted logs with consistent field names
4. **LogQL alerting:** Create Prometheus-style alert rules from log patterns (e.g., alert on 5+ errors in 5 minutes)

#### Structured Logging Best Practices for n8n Workflows

n8n workflows should emit structured logs that include:
- `workflow_id`, `workflow_name`, `execution_id`
- `video_id` (YouTube video ID being processed)
- `stage` (rss_fetch, download, dedup, upload, transcribe, enrich)
- `status` (started, completed, failed, retried)
- `duration_ms` for each stage
- `correlation_id` (see below)

#### Correlation IDs for Pipeline Tracking

**This is critical for KnowledgeStack.** A video passes through multiple stages across multiple services. Without correlation IDs, debugging a failure requires manual log correlation across services. [Microsoft Engineering Playbook, 2025; Last9, 2025; AlgoMaster, 2025]

Implementation pattern:
1. Generate a UUID correlation ID when a video first enters the pipeline (RSS detection)
2. Pass the correlation ID through every stage: n8n workflow nodes, HTTP headers to Speakr API, database records, log entries
3. Store the correlation ID in the PostgreSQL `videos` table
4. Include `correlation_id` in every structured log entry
5. Grafana Loki query: `{service="n8n"} | json | correlation_id="<uuid>"` shows the entire lifecycle of a single video

**W3C Trace Context compatibility:** If using OpenTelemetry later, the correlation ID can be mapped to OpenTelemetry's trace ID for seamless integration with distributed tracing.

**Recommended naming convention:**
- `pipeline_id`: The correlation ID for the video processing lifecycle
- `video_id`: The YouTube video ID (also useful for searching)
- Include both in every log entry

**Recommendation:**
- **MVP:** Implement `pipeline_id` generation in the first n8n workflow node, pass through all stages, include in all logs
- **Growth:** OpenTelemetry instrumentation with trace ID as pipeline_id
- **Overkill:** Full distributed tracing across all microservices

#### Distributed Tracing (Grafana Tempo)

Grafana Tempo is the natural choice for distributed tracing, given the existing Grafana stack [Grafana Tempo Docs, 2025; InfraCloud, 2025]:

- **Cost-effective:** Index-free design stores traces in cheap object storage (MinIO or local disk)
- **Protocol support:** Accepts traces from OpenTelemetry, Jaeger, and Zipkin protocols
- **Docker Compose deployment:** Official examples available at the Grafana Tempo GitHub repository
- **Integration:** Traces link directly to Loki logs and Prometheus metrics in Grafana dashboards

**Architecture for KnowledgeStack:**
- Deploy Tempo alongside Loki on Coulson
- Use Grafana Alloy (replacement for Promtail) as the collection agent
- Instrument n8n HTTP request nodes to propagate trace context headers
- Visualize end-to-end video processing pipeline as a trace in Grafana

**Recommendation:**
- **MVP:** Correlation IDs in logs (manual tracing via Loki)
- **Growth:** Grafana Tempo deployment with OpenTelemetry instrumentation
- **Overkill:** Jaeger + Kafka + Elasticsearch (heavy, complex)

### 2.6 Health Checks & Self-Healing

#### Docker Compose Healthcheck Patterns [Last9, 2025; Docker Docs, 2025; JustAnotherUptime, 2025]

Every service in Docker Compose should have a healthcheck. Patterns for KnowledgeStack services:

**PostgreSQL:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U knowledge -d knowledge_db"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

**n8n:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "wget -qO- http://localhost:5678/healthz || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

**Speakr (API-based):**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:9000/health || exit 1"]
  interval: 60s
  timeout: 15s
  retries: 3
  start_period: 120s  # Speakr may take time to load models
```

**Generic HTTP service:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:PORT/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

#### Startup Order with Health Dependencies

Use `depends_on` with `condition: service_healthy` to ensure proper startup order:
```yaml
services:
  n8n:
    depends_on:
      postgres:
        condition: service_healthy
        restart: true
```

#### Restart Policies

**Key insight:** Docker restart policies (`restart: always`, `restart: on-failure`) only trigger when a container's main process exits. They do NOT trigger on healthcheck failure. [JustAnotherUptime, 2025]

**Recommendation:** `restart: unless-stopped` for all production services. This survives daemon restarts and handles process crashes, but respects manual stops.

#### Autoheal (Self-Healing on Unhealthy) [willfarrell/docker-autoheal, GitHub]

Since Docker's restart policy does not restart containers that are merely "unhealthy" (process still running but service degraded), use the `willfarrell/autoheal` container:

```yaml
autoheal:
  image: willfarrell/autoheal
  restart: unless-stopped
  environment:
    AUTOHEAL_CONTAINER_LABEL: all  # or use selective labels
    AUTOHEAL_INTERVAL: 60
    AUTOHEAL_START_PERIOD: 300
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

This monitors all containers with healthchecks and restarts any that become unhealthy. For selective healing, use `autoheal=true` labels on specific services.

**Caveat:** "Autoheal fixes symptoms, not root causes." If containers are constantly failing, investigate the underlying issue. [JustAnotherUptime, 2025]

#### Circuit Breaker Patterns for External APIs

KnowledgeStack calls external APIs (YouTube API, Speakr API, LiteLLM). Implement circuit breaker patterns:

**n8n approach:** Use the n8n error handling and retry mechanisms:
- Set retry counts and backoff intervals on HTTP Request nodes
- Use the Error Trigger node to catch failures and implement fallback logic
- Track consecutive failures in a workflow variable; after N failures, skip the service for a cooldown period

**Application-level approach:** If using custom code (Node.js), use libraries like `opossum` for circuit breaker implementation.

**Specific patterns:**
- YouTube API: Rate limit handling with exponential backoff (429 responses)
- Speakr API: Timeout handling (transcription can be slow for long videos)
- LiteLLM: Model fallback (if primary model fails, try secondary)

**Recommendation:**
- **MVP:** n8n retry mechanisms + error triggers to Slack
- **Growth:** Circuit breaker patterns with cooldown periods + metric tracking (Prometheus counter for circuit open/close events)
- **Overkill:** Service mesh with automatic circuit breaking (Istio, Linkerd)

#### Watchdog Patterns for n8n Workflow Execution

Monitor n8n for stuck or failed workflows:

1. **Execution monitoring:** n8n API endpoint `/executions` lists recent executions with status. Query periodically for:
   - Executions that have been "running" for longer than expected (stuck)
   - High failure rate over a time window
   - Missing scheduled executions (workflow that should run every hour but has not run in 2 hours)

2. **External watchdog:** A separate cron job or n8n workflow that:
   - Queries n8n's execution API
   - Compares against expected schedule
   - Alerts on anomalies via Slack

3. **Dead man's switch:** For critical scheduled workflows, use a "dead man's switch" pattern:
   - Workflow sends a heartbeat to a monitoring endpoint on successful completion
   - If heartbeat is missed, alert fires

**Recommendation:**
- **MVP:** n8n error trigger node to Slack for all workflow failures
- **Growth:** External watchdog workflow + dead man's switch for critical pipelines
- **Overkill:** Workflow orchestration platform with built-in monitoring (Temporal, Airflow)

### 2.7 Data Integrity

#### PostgreSQL Integrity Checks [Stackademic, 2025; PostgreSQL Docs, 2025]

**Constraint verification:**
- PostgreSQL enforces constraints (PK, FK, UNIQUE, CHECK, NOT NULL) at write time
- Periodic audit: query `pg_constraint` system catalog to list all constraints and verify they are enforced
- Check for orphaned rows: `SELECT * FROM child LEFT JOIN parent ON child.fk = parent.pk WHERE parent.pk IS NULL;`

**Physical integrity:**
- `pg_verifybackup`: Verify backup checksums against the manifest [PostgreSQL Docs, 2025]
- `pg_integrity_check` (Postgres Pro): On-demand checksum verification
- Data checksums: Enable PostgreSQL data checksums at initdb time for physical corruption detection

**WAL integrity:**
- WAL ensures durability -- every change is logged before written to disk
- pgBackRest WAL archiving provides an additional integrity layer

**Recommendation:**
- **MVP:** Enable PostgreSQL data checksums. Run monthly orphaned data audit queries.
- **Growth:** Automated integrity check scripts in cron/n8n, `pg_verifybackup` after each backup
- **Overkill:** pgAudit for full audit logging of all DML statements

#### Orphaned File Detection

KnowledgeStack stores audio files on NAS and metadata in PostgreSQL. Orphans can occur in both directions:

**Audio files without DB records:**
```sql
-- Find files on NAS that have no corresponding DB entry
-- Implementation: n8n workflow lists NAS directory,
-- queries DB for each file, reports orphans
```

**DB records without audio files:**
```sql
-- Find DB entries whose referenced audio file does not exist on NAS
SELECT id, audio_path FROM videos
WHERE audio_path IS NOT NULL
AND NOT EXISTS (
  -- Check via n8n HTTP node or script that hits NAS
  -- Cannot be done in pure SQL
);
```

**Implementation pattern:**
1. n8n workflow runs weekly
2. Lists all files in NAS audio directory
3. Lists all `audio_path` values from PostgreSQL
4. Computes set difference in both directions
5. Reports orphans via Slack with counts and sample paths
6. Manual review before cleanup (never auto-delete orphans)

**Recommendation:**
- **MVP:** Monthly manual check (SQL query + directory listing comparison)
- **Growth:** Automated n8n workflow for weekly orphan detection with Slack reporting
- **Overkill:** Real-time orphan prevention with distributed transactions

#### Deduplication Verification

The deduplication strategy is documented in `docs/research/deduplication-strategy-report.md`. Periodic audit should verify:

1. **No duplicate YouTube video IDs in the database:** `SELECT youtube_video_id, COUNT(*) FROM videos GROUP BY youtube_video_id HAVING COUNT(*) > 1;`
2. **No duplicate audio files on NAS:** Compare file hashes or filenames
3. **Dedup effectiveness metrics:** Track how many videos were deduplicated vs. processed (Prometheus counter)

**Recommendation:**
- **MVP:** Monthly SQL dedup audit query
- **Growth:** Automated weekly audit with trend reporting
- **Overkill:** Real-time dedup monitoring dashboard

#### NAS Mount Health Verification

NAS mounts (NFS/CIFS) can silently become stale. Patterns to detect this:

1. **Healthcheck script:** Write a small file, read it back, verify contents, delete it. Run every 5 minutes.
2. **Mount point check:** Verify mount point is actually mounted (not the empty local directory)
3. **Latency monitoring:** Track NAS read/write latency; alert on degradation
4. **Docker Compose integration:** Add a NAS health check service that other services depend on

```yaml
nas-health:
  image: busybox
  volumes:
    - /mnt/nas/audio:/mnt/audio
  healthcheck:
    test: ["CMD-SHELL", "echo 'healthcheck' > /mnt/audio/.healthcheck && cat /mnt/audio/.healthcheck && rm /mnt/audio/.healthcheck"]
    interval: 60s
    timeout: 10s
    retries: 3
  restart: unless-stopped
```

**Recommendation:**
- **MVP:** Simple NAS mount verification script in cron (5-minute interval)
- **Growth:** NAS health check as a Docker service with dependent services
- **Overkill:** Distributed filesystem with built-in health monitoring

---

## 3. Consolidated Recommendations

### MVP Phase (Launch)

These items are essential for a production-ready system:

| Area | Action | Effort |
|------|--------|--------|
| **Observability** | Grafana LLM plugin on existing Grafana | 1 hour |
| **Container Metrics** | Deploy cAdvisor, add Prometheus scrape, import Grafana dashboard | 2 hours |
| **PostgreSQL Monitoring** | Enable pg_stat_statements, deploy postgres_exporter, Grafana dashboard | 2 hours |
| **PostgreSQL Backup** | Daily pg_dump to NAS via cron, monthly restore test | 3 hours |
| **Docker Volume Backup** | Bind mounts + rsync to NAS + Compose files in Git | 2 hours |
| **NAS Backup** | Hyper Backup of audio folder to second volume | 1 hour |
| **Healthchecks** | Add healthcheck to every service in Docker Compose | 2 hours |
| **Autoheal** | Deploy willfarrell/autoheal container | 30 min |
| **Restart Policies** | `restart: unless-stopped` on all services | 30 min |
| **Correlation IDs** | Generate pipeline_id in first n8n node, pass through all stages | 4 hours |
| **Structured Logging** | JSON logging from all services with consistent field names | 3 hours |
| **n8n Error Alerts** | Error trigger nodes -> Slack for all workflows | 2 hours |
| **n8n Git Backup** | Deploy n8n workflow template for daily Git backup | 1 hour |
| **Security Scanning** | Weekly Trivy scan via cron, results to Slack | 1 hour |
| **AGPL Compliance** | Document Speakr isolation, verify no modifications, generate SBOM | 2 hours |
| **NAS Mount Check** | Cron script to verify NAS mount health every 5 minutes | 1 hour |
| **Dedup Audit** | Monthly SQL query for duplicate detection | 30 min |
| **Orphan Detection** | Monthly manual check for orphaned files/records | 1 hour |
| **Total MVP Effort** | | **~28 hours** |

### Growth Phase

Items to add as the system scales and stabilizes:

| Area | Action | When |
|------|--------|------|
| **LLM Observability** | Deploy Langfuse self-hosted | When AI enrichment becomes complex |
| **Distributed Tracing** | Deploy Grafana Tempo + OpenTelemetry | When multi-service debugging becomes painful |
| **Advanced Backup** | pgBackRest with WAL archiving and PITR | When data becomes business-critical |
| **Offsite Backup** | Backblaze B2 for NAS audio files | When data loss risk is unacceptable |
| **Blue-Green Deploy** | Traefik-based deployment with rollback | When downtime matters |
| **Secrets Management** | Infisical self-hosted | When team grows or secrets proliferate |
| **n8n CI/CD** | Bidirectional GitHub sync with environment promotion | When multiple environments exist |
| **LLM Log Analysis** | n8n + Ollama anomaly detection workflow | When log volume grows |
| **Automated Orphan Detection** | Weekly n8n workflow with Slack reporting | When data volume warrants automation |
| **NAS Monitoring** | SNMP exporter for full Synology metrics | When NAS performance matters |
| **pgBadger** | Weekly performance reports | When query performance matters |
| **Circuit Breakers** | Cooldown patterns for external APIs | When API reliability issues emerge |
| **Watchdog** | External n8n execution monitor | When workflow reliability is critical |

### Overkill (Avoid Unless Justified)

| Area | Why Overkill |
|------|-------------|
| Enterprise AIOps (Datadog, Dynatrace) | Cost and complexity far exceed this scale |
| Kubernetes/Docker Swarm | Docker Compose is sufficient for this architecture |
| HashiCorp Vault / OpenBao | Operational complexity disproportionate to benefit |
| Streaming replication (PostgreSQL) | Premature for single-node deployment |
| Service mesh (Istio, Linkerd) | Infrastructure complexity not justified |
| Full audit logging (pgAudit) | Compliance requirements do not demand it |
| Real-time orphan prevention | Batch detection is sufficient |
| Workflow orchestration platforms (Temporal, Airflow) | n8n already serves this role |

### Architecture Diagram (Text)

```
                    [External]
                        |
                    [Traefik] (Helicarrier)
                        |
    +---------+---------+---------+
    |         |         |         |
[KnowledgeStack] [Speakr]  [LiteLLM]  [n8n]
    (Banner)     (Jarvis?) (Banner)  (Banner)
    |         |         |         |
    +----+----+---------+----+----+
         |                   |
    [PostgreSQL]        [NAS Audio]
    (Banner)            (Fury?)
         |                   |
    [pgBackRest]        [Hyper Backup]
    -> NAS              -> Backblaze B2
         |
    [Monitoring Stack] (Coulson)
    - Grafana (+ LLM plugin)
    - Prometheus (+ cAdvisor + pg_exporter)
    - Loki (+ structured logs)
    - Tempo (Growth: distributed tracing)
    - AlertManager -> Slack
```

---

## 4. Bibliography

### AI-Native Ops Tools

- [Langfuse GitHub Repository](https://github.com/langfuse/langfuse) - Open source LLM engineering platform. MIT License.
- [Langfuse Self-Hosting Documentation](https://langfuse.com/self-hosting) - Docker Compose and Kubernetes deployment guides.
- [ClickHouse Acquires Langfuse](https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability) - Acquisition announcement, 2025.
- [Langfuse RAG Observability and Evals](https://langfuse.com/blog/2025-10-28-rag-observability-and-evals) - RAG-specific monitoring patterns.
- [Arize AI LLM Evaluation Platforms](https://arize.com/llm-evaluation-platforms-top-frameworks/) - Platform comparison guide.
- [Top 5 LLM Observability Platforms](https://www.getmaxim.ai/articles/top-5-llm-observability-platforms-for-2025-comprehensive-comparison-and-guide/) - Maxim AI comparison, 2025.
- [Top 6 LangSmith Alternatives](https://orq.ai/blog/langsmith-alternatives) - orq.ai comparison guide, 2025.
- [8 AI Observability Platforms Compared](https://softcery.com/lab/top-8-observability-platforms-for-ai-agents-in-2025) - Softcery comparison, 2025.
- [Best LLM Observability Tools](https://www.firecrawl.dev/blog/best-llm-observability-tools) - Firecrawl analysis, 2025.
- [Top 5 AI Agent Observability Platforms 2026](https://o-mega.ai/articles/top-5-ai-agent-observability-platforms-the-ultimate-2026-guide) - O-mega guide, 2026.

### AI-Powered Ops & Incident Detection

- [Grafana AI and Observability](https://grafana.com/products/cloud/ai-tools-for-observability/) - Grafana Cloud AI features.
- [Grafana LLM Plugin](https://grafana.com/grafana/plugins/grafana-llm-app/) - Open source LLM integration for Grafana OSS.
- [Top 7 AI-Powered Observability Tools](https://www.dash0.com/comparisons/ai-powered-observability-tools) - Dash0 comparison, 2026.
- [5 Best AI-Powered Incident Management Platforms](https://incident.io/blog/5-best-ai-powered-incident-management-platforms-2026) - incident.io, 2026.
- [Autonomous IT Operations 2026](https://ennetix.com/the-rise-of-autonomous-it-operations-what-aiops-platforms-must-enable-by-2026/) - Ennetix AIOps capabilities report.
- [AI-Powered Observability and Log Analysis System](https://github.com/KeerthiKeswaran/AI-Powered-Observability-and-Log-Analysis-System) - GitHub community project.
- [Streamlining Logs with Open Source Local LLMs](https://www.cncf.io/blog/2024/04/12/streamlining-logs-with-open-source-local-llms/) - CNCF blog, 2024.
- [OpenLLMetry](https://github.com/traceloop/openllmetry) - Open source GenAI observability via OpenTelemetry.

### RAG Pipeline Monitoring

- [RAG Monitoring Tools Benchmark](https://research.aimultiple.com/rag-monitoring/) - AIMultiple benchmark, 2026.
- [Best RAG Evaluation Tools](https://www.braintrust.dev/articles/best-rag-evaluation-tools) - Braintrust analysis, 2025.
- [Best RAG Evaluation Tools 2026](https://www.getmaxim.ai/articles/the-5-best-rag-evaluation-tools-you-should-know-in-2026/) - Maxim AI, 2026.

### Backup & Recovery

- [pgBackRest User Guide](https://pgbackrest.org/user-guide.html) - Official documentation.
- [pgBackRest Configuration Reference](https://pgbackrest.org/configuration.html) - Complete configuration options.
- [pgBackRest PITR in Docker](https://dataegret.com/2025/12/pgbackrest-pitr-in-docker-a-simple-demo/) - Data Egret Docker PITR demo, 2025.
- [Avoiding WAL Archives Retention Trap](https://dataegret.com/2025/02/avoiding-the-wal-archives-retention-trap-in-pgbackrest/) - Data Egret, 2025.
- [Automating Backups: pgBackRest vs Barman](https://severalnines.com/blog/automating-backups-and-disaster-recovery-in-postgresql-at-scale-pgbackrest-vs-barman/) - Severalnines comparison, 2025.
- [Easy Automated Docker Volume Backups](https://www.thepolyglotdeveloper.com/2025/05/easy-automated-docker-volume-backups-database-friendly/) - Database-friendly patterns, 2025.
- [Synology Docker Backup Guide](https://mariushosting.com/synology-how-to-back-up-docker-containers/) - Marius Hosting, 2025.
- [How to Back Up a Docker Container](https://www.wundertech.net/how-to-back-up-a-docker-container/) - WunderTech, 2025.
- [Container Manager Backup & Recovery Guide](https://www.synoforum.com/threads/container-manager-a-definitive-guide-for-backup-recovery.15461/) - SynoForum community guide.
- [Ultimate Home Lab Backup Strategy 2025](https://www.virtualizationhowto.com/2025/10/ultimate-home-lab-backup-strategy-2025-edition/) - Virtualization Howto.

### Deployment & Updates

- [Blue-Green Deployment with Docker Compose](https://technicallyshane.com/2025/08/30/blue-green-deployment-of-a-docker-compose-setup.html) - TechnicallyShane, 2025.
- [Blue/Green Deployment Using Docker Compose and GitHub Actions](https://blog.primfeed.com/2025/07/how-i-created-a-simple-blue-green-deployment-using-only-docker-compose-and-github-actions/) - Primfeed, 2025.
- [Blue/Green Deployments with Docker Compose](https://blog.riteshrana.engineer/posts/unlocking-seamless-rollbacks-bluegreen-deployments-with-docker-compose/) - Ritesh Rana, 2025.
- [How to Deploy Apps with Docker Compose in 2025](https://dokploy.com/blog/how-to-deploy-apps-with-docker-compose-in-2025) - Dokploy, 2025.
- [n8n Git Backup Workflow Template](https://n8n.io/workflows/1053-git-backup-of-workflows-and-credentials/) - Official n8n template.
- [n8n Workflow Version Control](https://www.wednesday.is/writing-articles/n8n-workflow-version-control-and-deployment-pipeline) - Wednesday.is, 2025.
- [Bidirectional GitHub Workflow Sync](https://n8n.io/workflows/5081-bidirectional-github-workflow-sync-and-version-control-for-n8n-workflows/) - Official n8n template.
- [n8n Version Control GitHub Project](https://github.com/Aadil1505/n8n-version-control) - Community tool.
- [PostgreSQL Data Compliance Guide](https://www.liquibase.com/blog/postgresql-data-compliance-guide) - Liquibase, 2025.

### Security & Access

- [Trivy vs Grype Comparison](https://opsdigest.com/digests/trivy-vs-grype-choosing-the-right-vulnerability-scanner/) - OpsDigest, 2025.
- [Open-Source Container Security: Trivy, Clair, and Grype](https://www.stakater.com/post/open-source-container-security-a-deep-dive-into-trivy-clair-and-grype) - Stakater, 2025.
- [Top 7 OSS Container Image Scanning Tools](https://www.aquasec.com/cloud-native-academy/docker-container/container-image-scanning-tools/) - Aqua Security, 2025.
- [Infisical GitHub Repository](https://github.com/Infisical/infisical) - Open source secrets management. MIT License.
- [Self-Hosting Infisical](https://infisical.com/blog/self-hosting-infisical-homelab) - Homelab deployment guide.
- [Open Source Secrets Management for DevOps](https://infisical.com/blog/open-source-secrets-management-devops) - Infisical, 2025.
- [AGPL Compliance Guide](https://vaultinum.com/blog/essential-guide-to-agpl-compliance-for-tech-companies) - Vaultinum, 2025.
- [AGPL in SaaS: Risks and Duties](https://powerpatent.com/blog/agpl-in-saas-risks-duties-and-safe-alternatives) - PowerPatent, 2025.
- [OSS License Compliance Expert on AGPL](https://fossa.com/blog/oss-license-compliance-expert-heather-meeker-agpl/) - FOSSA (Heather Meeker interview).
- [AGPL License Is a Non-Starter](https://www.opencoreventures.com/blog/agpl-license-is-a-non-starter-for-most-companies) - Open Core Ventures analysis.

### Performance & Capacity

- [cAdvisor Docker Insights Grafana Dashboard](https://grafana.com/grafana/dashboards/19908-docker-container-monitoring-with-prometheus-and-cadvisor/) - Dashboard ID 19908.
- [Docker Monitoring Grafana Dashboard](https://grafana.com/grafana/dashboards/15798-docker-monitoring/) - Dashboard ID 15798.
- [dockprom: Docker Monitoring Stack](https://github.com/stefanprodan/dockprom) - GitHub project by Stefan Prodan.
- [pg_stat_statements Guide](https://stormatics.tech/blogs/enhancing-postgresql-performance-monitoring-a-comprehensive-guide-to-pg_stat_statements) - Stormatics, 2025.
- [Enabling pg_stat_statements in Docker](https://gist.github.com/lfittl/1b0671ac07b33521ea35fcd22b0120f5) - GitHub Gist.
- [pgBadger Setup Guide](https://medium.com/@jramcloud1/postgresql-17-log-analysis-made-easy-complete-guide-to-setting-up-and-using-pgbadger-befb8e453433) - Medium, 2025.
- [Top 10 PostgreSQL Monitoring Tools](https://uptrace.dev/tools/postgresql-monitoring-tools) - Uptrace, 2025.
- [Monitoring PostgreSQL in Docker](https://pankajconnect.medium.com/monitoring-postgresql-containers-techniques-and-tools-for-docker-environments-490fbd810bd) - Medium, 2025.

### Logging & Observability

- [Grafana Loki Documentation](https://grafana.com/docs/loki/latest/) - Official docs.
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/latest/) - Official docs.
- [Deploy Tempo with Docker Compose](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/deploy/locally/docker-compose/) - Official deployment guide.
- [Distributed Tracing with Grafana Tempo and Jaeger](https://www.infracloud.io/blogs/tracing-grafana-tempo-jaeger/) - InfraCloud, 2025.
- [Self-Hosted Grafana + Prometheus + Tempo Stack](https://gate.minekube.com/guide/otel/self-hosted/grafana-stack) - Gate Proxy guide.
- [Correlation ID vs Trace ID](https://last9.io/blog/correlation-id-vs-trace-id/) - Last9, 2025.
- [Correlation IDs Engineering Playbook](https://microsoft.github.io/code-with-engineering-playbook/observability/correlation-id/) - Microsoft Engineering Fundamentals.
- [Correlation IDs System Design](https://algomaster.io/learn/system-design/correlation-ids) - AlgoMaster.

### Health Checks & Self-Healing

- [Docker Compose Health Checks Guide](https://last9.io/blog/docker-compose-health-checks/) - Last9, 2025.
- [Docker Compose and Autoheal](https://blog.justanotheruptime.com/posts/2025_06_30_docker_compose_and_autoheal/) - JustAnotherUptime, 2025.
- [Docker Compose Restart Policies and Healthchecks](https://blog.justanotheruptime.com/posts/2025_07_07_docker_compose_restart_policies_and_healthchecks/) - JustAnotherUptime, 2025.
- [docker-autoheal](https://github.com/willfarrell/docker-autoheal) - GitHub project by Will Farrell.
- [Docker Compose Startup Order](https://docs.docker.com/compose/how-tos/startup-order/) - Official Docker docs.

### Data Integrity

- [PostgreSQL Integrity Checks Using SQL](https://blog.stackademic.com/postgresql-integrity-checks-12d02d9e9fd4) - Stackademic, 2025.
- [pg_verifybackup](https://www.postgresql.org/docs/current/app-pgverifybackup.html) - PostgreSQL official docs.
- [pg_check: Data File Integrity Tool](https://github.com/tvondra/pg_check) - GitHub project.
- [Data Integrity in PostgreSQL](https://www.datasunrise.com/knowledge-center/data-integrity-in-postgresql/) - DataSunrise, 2025.
- [Data Integrity in Postgres](https://webdock.io/en/docs/how-guides/postgresql-guides/data-integrity-in-postgres) - Webdock guide.

### n8n Monitoring & AI Integration

- [Building Real-Time Data Pipelines with n8n](https://www.wednesday.is/writing-articles/building-real-time-data-pipelines-with-n8n) - Wednesday.is, 2025.
- [Multi-Agent Orchestration with n8n](https://medium.com/@angelosorte1/multi-agent-orchestration-with-n8n-in-2025-from-concept-to-practical-ai-systems-8fc6996468b2) - Angelo Sorte, 2025.
- [DevOps Workflows with AI: Ollama & n8n](https://www.hashstudioz.com/blog/devops-workflows-with-ai-my-ollama-n8n-journey/) - HashStudioz, 2025.
- [n8n AI Workflow Automation](https://n8n.io/ai/) - Official n8n AI features page.
