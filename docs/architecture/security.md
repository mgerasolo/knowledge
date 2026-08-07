# Security Architecture

**Last Updated:** 2026-03-22

## Security Overview

KnowledgeStack is an **internal-only** system with no public-facing components. All services run within the 10.0.0.x network behind a firewall.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            SECURITY ZONES                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ZONE 1: INTERNAL NETWORK (10.0.0.x)                                    │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  ZONE 1A: APPLICATION TIER                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ Banner: Speakr, PostgreSQL, SurrealDB, Gateway              │  │  │
│  │  │ - User auth via Authentik                                    │  │  │
│  │  │ - API auth via API keys                                      │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ZONE 1B: WORKFLOW TIER                                           │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ Helicarrier: n8n, LiteLLM, Authentik                        │  │  │
│  │  │ - Internal access only                                       │  │  │
│  │  │ - Service accounts for automation                            │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ZONE 1C: DATA TIER                                               │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ NAS (Fury): Audio files, backups                            │  │  │
│  │  │ - SMB with authentication                                    │  │  │
│  │  │ - No direct network exposure                                 │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │                                                                    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ZONE 2: EXTERNAL (Internet)                                            │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ YouTube (content source), Slack (notifications)                   │  │
│  │ - Outbound connections only                                       │  │
│  │ - No inbound from internet                                        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Authentication

### User Authentication (Speakr)

| Method | Implementation | Users |
|--------|----------------|-------|
| OIDC/SSO | Authentik | Admin, Viewers |
| Local fallback | Speakr native | Emergency access |

**Flow:**
```
User → Speakr → Authentik (OIDC) → Speakr (session cookie)
```

### API Authentication (KnowledgeGateway)

| Method | Format | Scope |
|--------|--------|-------|
| API Key | `Bearer sk-knowledge-xxx` | Per-key scoping |

**Scopes:**
- `consumer`: Read-only search and retrieval
- `curator`: Channel management + consumer
- `admin`: Full access

### Service Authentication

| Service | Auth Method |
|---------|-------------|
| PostgreSQL | Username/password (env vars) |
| SurrealDB | Username/password (env vars) |
| LiteLLM | Master key (`LITELLM_MASTER_KEY`) |
| n8n | Internal credentials store |
| Slack | Webhook secret |

## Authorization

### Role-Based Access Control

| Role | Capabilities |
|------|-------------|
| **Admin** | Full system access, channel management, user management |
| **Curator** | Channel management, failed queue, viewer capabilities |
| **Viewer** | Search, browse, chat, tag, bookmark (read + interact) |
| **API Consumer** | Read-only API access |
| **API Curator** | Channel management via API |
| **API Admin** | Full API access |

### Permission Matrix

| Action | Admin | Curator | Viewer | API Consumer |
|--------|-------|---------|--------|--------------|
| Search transcripts | Yes | Yes | Yes | Yes |
| Per-recording chat | Yes | Yes | Yes | No |
| Tag/bookmark | Yes | Yes | Yes | No |
| Add channel | Yes | Yes | No | No |
| Manage failed queue | Yes | Yes | No | No |
| User management | Yes | No | No | No |
| System config | Yes | No | No | No |
| API: search | N/A | N/A | N/A | Yes |
| API: transcripts | N/A | N/A | N/A | Yes |
| API: channels | N/A | N/A | N/A | Yes |

## Data Protection

### Data Classification

| Data Type | Classification | Protection |
|-----------|----------------|------------|
| Transcripts | Internal | Access control |
| User credentials | Confidential | Hashed, never logged |
| API keys | Confidential | Hashed storage, rotation |
| Embeddings | Internal | No PII |
| Audio files | Internal | Access control |

### Secrets Management

**Storage:** `/mnt/foundry_devlab/secrets/env/`

| Secret | Location | Access |
|--------|----------|--------|
| PostgreSQL password | `appservices.env` | Banner containers |
| SurrealDB password | `appservices.env` | Banner containers |
| LiteLLM master key | `appbrain.env` | Helicarrier |
| Slack webhook URL | `infrastructure.env` | n8n |
| YouTube API key | `appbrain.env` | n8n |

**Access pattern:**
```bash
source ~/Infrastructure/scripts/secrets.sh
appservices_get POSTGRES_PASSWORD
```

### Encryption

| Data | At Rest | In Transit |
|------|---------|------------|
| PostgreSQL | Volume encryption (host) | Internal network (no TLS) |
| SurrealDB | Volume encryption (host) | Internal network (no TLS) |
| NAS files | Synology encryption | SMB 3.0 |
| External APIs | N/A | HTTPS |

**Note:** Internal network traffic is unencrypted. This is acceptable because:
- All hosts on isolated 10.0.0.x network
- No untrusted devices on network
- Physical security of server room

## Network Security

### Firewall Rules

```
# Inbound to Banner (10.0.0.33)
ALLOW from 10.0.0.0/24 to Banner:5000-5049  # KnowledgeStack services
ALLOW from 10.0.0.0/24 to Banner:22         # SSH

# Inbound to Helicarrier (10.0.0.27)
ALLOW from 10.0.0.0/24 to Helicarrier:5678  # n8n
ALLOW from 10.0.0.0/24 to Helicarrier:2764  # LiteLLM
ALLOW from 10.0.0.0/24 to Helicarrier:9000  # Authentik

# Outbound
ALLOW from Banner to youtube.com:443         # YouTube API
ALLOW from Banner to api.slack.com:443       # Slack
DENY all other inbound from internet
```

### Traefik Security

- TLS termination at Traefik (Helicarrier)
- Let's Encrypt certificates
- HTTPS redirect enforced
- Security headers (HSTS, X-Frame-Options, etc.)

## Audit & Logging

### What's Logged

| Event | Log Location | Retention |
|-------|--------------|-----------|
| User logins | Authentik logs | 90 days |
| API requests | Gateway access logs | 30 days |
| Pipeline executions | n8n execution history | 30 days |
| Database queries | PostgreSQL logs | 7 days |
| System events | Loki | 30 days |

### What's NOT Logged

- Transcript content (too verbose)
- Embedding vectors (no value)
- Audio file contents

### Log Access

```bash
# Grafana/Loki for aggregated logs
https://grafana.ucontrolnetwork.com

# Direct log access (Coulson)
ssh coulson
docker logs loki
```

## Incident Response

### Detection

| Threat | Detection Method |
|--------|------------------|
| Failed logins | Authentik alerts (5+ failures) |
| API abuse | Rate limit triggers |
| Service down | Health check failures → Slack |
| Disk full | Prometheus alert |

### Response Playbook

1. **Alert received** → Check Slack/Grafana
2. **Assess impact** → Which service, which users
3. **Contain** → Isolate if needed (Docker stop)
4. **Investigate** → Check logs in Loki
5. **Remediate** → Fix root cause
6. **Document** → Post-incident note in `.claude/BUGS.md`

## Security Checklist (MVP)

- [x] Authentik OIDC integration
- [x] PostgreSQL password in secrets store
- [x] SurrealDB password in secrets store
- [ ] API key generation and storage
- [ ] Rate limiting on Gateway
- [ ] Audit logging to Loki
- [ ] Backup encryption verification

## Compliance Notes

- **GDPR:** Not applicable (no EU user data)
- **HIPAA:** Not applicable (no health data)
- **SOC 2:** Not required (internal tool)
- **PCI DSS:** Not applicable (no payment data)

Internal tool with no regulatory requirements. Security measures are proportional to risk (low exposure, trusted users).
