# KnowledgeEnroll Deployment Guide

## Overview

KnowledgeEnroll runs on **Banner (10.0.0.33)** using Docker Compose.

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5010 | Pipeline state database |
| Admin API | 5020 | Channel/pipeline management |
| Embedding | 5030 | SurrealDB embedding service |
| SurrealDB | 5040 | Vector + graph database |

## Prerequisites

1. Docker and Docker Compose on Banner
2. Traefik configured on Helicarrier (for HTTPS routing)
3. LiteLLM API key for embeddings
4. n8n workflows deployed (handled by Infrastructure)

## Deployment Steps

### 1. Clone Repository

```bash
ssh banner
cd /opt/stacks
git clone https://github.com/mgerasolo/knowledge.git knowledge
cd knowledge
```

### 2. Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit with actual credentials
nano .env
```

Required variables:
```
POSTGRES_PASSWORD=<strong password>
SURREAL_PASS=<strong password>
LITELLM_API_KEY=<from /mnt/foundry_devlab/secrets/env/appbrain.env>
```

### 3. Initialize Database Schema

The schema is automatically applied when PostgreSQL starts:
- `src/db/schema/001_pipeline_schema.sql`

### 4. Start Services

```bash
# Start all services
docker compose up -d

# Verify health
curl http://localhost:5020/health
curl http://localhost:5030/health
```

### 5. Import Seed Data

```bash
# Enter admin container
docker compose exec admin-api bash

# Import channels
cd /app/scripts
python import_channels.py

# Verify
curl http://localhost:5020/api/v1/channels/stats
```

### 6. Configure Traefik

Add routes in `/opt/stacks/traefik/config/dynamic/knowledge.yml`:

```yaml
http:
  routers:
    knowledge-admin:
      rule: "Host(`knowledge-admin.nextlevelguild.com`)"
      service: knowledge-admin
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

    knowledge-embedding:
      rule: "Host(`knowledge-embedding.nextlevelguild.com`)"
      service: knowledge-embedding
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    knowledge-admin:
      loadBalancer:
        servers:
          - url: "http://10.0.0.33:5020"

    knowledge-embedding:
      loadBalancer:
        servers:
          - url: "http://10.0.0.33:5030"
```

## Verification

```bash
# Run test suite
python scripts/test_api.py --verbose

# Check admin UI
open https://knowledge-admin.nextlevelguild.com

# Check stats
curl http://10.0.0.33:5020/api/v1/channels/stats
curl http://10.0.0.33:5030/api/stats
```

## n8n Workflows (Infrastructure Handoff)

The following n8n workflows are needed (HO-3):

| Workflow | Trigger | Webhook |
|----------|---------|---------|
| RSS Channel Monitor | Schedule (30 min) | - |
| Video Ingest Orchestrator | Webhook | `/webhook/knowledge/ingest-video` |
| Embedding Sync | Schedule (5 min) | - |

See `docs/architecture/n8n-workflows-spec.md` for specifications.

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U knowledge -c "SELECT 1"
```

### SurrealDB Not Responding

```bash
# Check SurrealDB status
docker compose ps surrealdb
docker compose logs surrealdb

# Test connection
curl http://10.0.0.33:5040/health
```

### Embedding Failures

1. Check LiteLLM proxy connectivity:
   ```bash
   curl http://10.0.0.27:2764/v1/models
   ```

2. Verify API key in environment

3. Check embedding service logs:
   ```bash
   docker compose logs embedding
   ```

## Maintenance

### Backup

```bash
# PostgreSQL
docker compose exec postgres pg_dump -U knowledge knowledge > backup.sql

# SurrealDB (export)
# TODO: Add SurrealDB backup procedure
```

### Updates

```bash
cd /opt/stacks/knowledge
git pull
docker compose build
docker compose up -d
```

### Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f admin-api
```
