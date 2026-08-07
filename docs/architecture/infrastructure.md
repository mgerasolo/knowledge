# Infrastructure & Deployment Architecture

**Last Updated:** 2026-03-22

## Network Topology

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTERNAL NETWORK (10.0.0.x)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    BANNER (10.0.0.33) - Dev Host                 │   │
│  │                                                                   │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────────┐   │   │
│  │  │ Speakr  │  │PostgreSQL│  │ SurrealDB│  │ KnowledgeGateway│   │   │
│  │  │  :5000  │  │  :5010   │  │  :5040   │  │     :5020       │   │   │
│  │  └─────────┘  └──────────┘  └──────────┘  └─────────────────┘   │   │
│  │                                                                   │   │
│  │  ┌─────────────────┐                                             │   │
│  │  │    Admin UI     │                                             │   │
│  │  │     :5030       │                                             │   │
│  │  └─────────────────┘                                             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                      │                                   │
│                                      │ HTTP/SQL                          │
│                                      ▼                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              HELICARRIER (10.0.0.27) - Workflow Host             │   │
│  │                                                                   │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐                        │   │
│  │  │   n8n   │  │ LiteLLM  │  │ Authentik│                        │   │
│  │  │  :5678  │  │  :2764   │  │  :9000   │                        │   │
│  │  └─────────┘  └──────────┘  └──────────┘                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                      │                                   │
│                                      │ HTTP                              │
│                                      ▼                                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   JARVIS (10.0.0.XX) - GPU Host                  │   │
│  │                                                                   │   │
│  │  ┌─────────────────────────────────────────────────────────┐     │   │
│  │  │                    WhisperX (GPU)                       │     │   │
│  │  │               Audio → Transcript                         │     │   │
│  │  └─────────────────────────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │               COULSON (10.0.0.XX) - Observability Host           │   │
│  │                                                                   │   │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────┐                      │   │
│  │  │ Grafana │  │   Loki   │  │ Prometheus │                      │   │
│  │  │  :3000  │  │  :3100   │  │   :9090    │                      │   │
│  │  └─────────┘  └──────────┘  └────────────┘                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    FURY (NAS) - Storage                          │   │
│  │                                                                   │
│  │  /volume1/MattVault/transcripts/    - Transcript markdown files  │   │
│  │  /volume1/KnowledgeStack/audio/     - Audio files (WAV/MP3)      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                │
│                                                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                                 │
│  │ YouTube │  │  Slack  │  │ Traefik │                                 │
│  │ RSS/API │  │ Webhook │  │ Routing │                                 │
│  └─────────┘  └─────────┘  └─────────┘                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Host Inventory

| Host | IP | Role | Services |
|------|-----|------|----------|
| **Banner** | 10.0.0.33 | Development | Speakr, PostgreSQL, SurrealDB, KnowledgeStack services |
| **Helicarrier** | 10.0.0.27 | Workflow | n8n, LiteLLM, Authentik |
| **Jarvis** | 10.0.0.XX | GPU | WhisperX transcription |
| **Coulson** | 10.0.0.XX | Observability | Grafana, Loki, Prometheus |
| **Fury** | NAS | Storage | Audio files, transcript archives |
| **Hulk** | 10.0.0.32 | Production | (Future production deployment) |

## Container Deployment

### Banner (10.0.0.33)

```yaml
# docker-compose.yml (simplified)
services:
  speakr:
    image: ghcr.io/speakr/speakr:latest
    ports: ["5000:5000"]
    environment:
      - DATABASE_URL=postgresql://speakr:${POSTGRES_PASSWORD}@postgres:5432/speakr
      - ASR_BASE_URL=http://jarvis:9000
      - LITELLM_URL=http://helicarrier:2764
    volumes:
      - /mnt/nas/KnowledgeStack/audio:/app/media

  postgres:
    image: postgres:16
    ports: ["5010:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=speakr

  surrealdb:
    image: surrealdb/surrealdb:v2
    ports: ["5040:8000"]
    command: start --user root --pass ${SURREAL_PASSWORD}
    volumes:
      - surreal_data:/data

  knowledge-gateway:
    build: ./gateway
    ports: ["5020:5020"]
    environment:
      - SURREAL_URL=http://surrealdb:8000
      - POSTGRES_URL=postgresql://...

  admin-ui:
    build: ./admin-ui
    ports: ["5030:80"]

volumes:
  postgres_data:
  surreal_data:
```

### Port Allocation Standard

| Range | Purpose |
|-------|---------|
| 5000-5009 | Web UIs |
| 5010-5019 | Databases |
| 5020-5029 | APIs |
| 5030-5039 | Admin services |
| 5040-5049 | Auxiliary databases |

## Storage Architecture

### NAS Mounts

```
/mnt/nas/                          (Banner mount point)
├── KnowledgeStack/
│   ├── audio/                     Audio files (WAV/MP3)
│   │   ├── <channel>/
│   │   │   └── <video_id>.wav
│   │   └── ...
│   └── backups/
│       ├── postgres/              Daily PostgreSQL dumps
│       └── surreal/               SurrealDB exports
│
└── MattVault/
    └── transcripts/               Markdown transcripts (historical)
        ├── <channel>/
        │   └── <video_id>.md
        └── ...
```

### Storage Projections

| Data | Current | 10K Videos | Storage Location |
|------|---------|------------|------------------|
| PostgreSQL | ~20 MB | ~1 GB | Banner local SSD |
| SurrealDB | ~65 MB | ~4.5 GB | Banner local SSD |
| Audio files | ~5 GB | ~500 GB | NAS (Fury) |
| Transcripts | ~50 MB | ~5 GB | NAS (Fury) |

## Networking

### DNS / Traefik Routes

| Domain | Target | Service |
|--------|--------|---------|
| `knowledge.nextlevelguild.com` | Banner:5000 | Speakr UI |
| `knowledge-api.nextlevelguild.com` | Banner:5020 | KnowledgeGateway |
| `knowledge-admin.nextlevelguild.com` | Banner:5030 | Admin UI |
| `surreal.nextlevelguild.com` | Banner:5040 | SurrealDB (Surrealist UI) |

### Firewall Rules

| Source | Destination | Port | Purpose |
|--------|-------------|------|---------|
| Internal | Banner | 5000-5049 | KnowledgeStack services |
| Internal | Helicarrier | 2764 | LiteLLM proxy |
| Banner | Helicarrier | 5678 | n8n webhooks |
| Banner | Jarvis | 9000 | WhisperX |
| Banner | NAS | 445 | SMB mount |

## Deployment Process

### Development (Banner)

```bash
# Deploy updated stack
cd /home/mgerasolo/Dev/KnowledgeStack
docker compose up -d

# Verify health
curl http://10.0.0.33:5000/api/health
curl http://10.0.0.33:5040/health
```

### Production (Hulk - Future)

1. Build images on Banner
2. Push to registry (ghcr.io or Harbor)
3. Pull and deploy on Hulk
4. Update Traefik routes
5. Health check and smoke test

## Backup Strategy

| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| PostgreSQL | Daily | 30 days | NAS + offsite |
| SurrealDB | Daily | 30 days | NAS + offsite |
| Audio files | N/A | Indefinite | NAS (can re-download) |
| Transcripts | N/A | Indefinite | NAS + transcript files |

### Recovery Procedures

```bash
# PostgreSQL restore
docker exec -i postgres psql -U speakr < /mnt/nas/backups/postgres/latest.sql

# SurrealDB restore
surreal import --conn http://localhost:5040 --ns knowledge --db transcripts backup.surql
```

## Monitoring Integration

### Prometheus Targets

```yaml
# prometheus.yml (on Coulson)
scrape_configs:
  - job_name: 'knowledge-speakr'
    static_configs:
      - targets: ['10.0.0.33:5000']

  - job_name: 'knowledge-surrealdb'
    static_configs:
      - targets: ['10.0.0.33:5040']

  - job_name: 'knowledge-gateway'
    static_configs:
      - targets: ['10.0.0.33:5020']
```

### Grafana Dashboards

| Dashboard | Purpose |
|-----------|---------|
| KnowledgeStack Overview | Pipeline health, ingestion rate |
| SurrealDB Metrics | Vector operations, query latency |
| Channel Coverage | Per-channel ingestion status |

### Loki Log Collection

```yaml
# promtail.yml (on Banner)
scrape_configs:
  - job_name: knowledge-containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

## Resource Requirements

### Banner VM Sizing

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8 cores |
| RAM | 16 GB | 32 GB |
| Storage | 100 GB SSD | 250 GB SSD |
| Network | 1 Gbps | 1 Gbps |

### Container Resource Limits

| Container | Memory Limit | CPU Limit |
|-----------|--------------|-----------|
| Speakr | 4 GB | 2 cores |
| PostgreSQL | 4 GB | 2 cores |
| SurrealDB | 8 GB | 4 cores |
| Gateway | 1 GB | 1 core |
| Admin UI | 512 MB | 0.5 core |
