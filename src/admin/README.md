# KnowledgeEnroll Admin API

Flask-based REST API for managing YouTube channels and monitoring the ingestion pipeline.

## Endpoints

### Channels

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/channels` | List channels (with filters) |
| GET | `/api/v1/channels/<id>` | Get single channel |
| POST | `/api/v1/channels` | Create channel |
| PUT | `/api/v1/channels/<id>` | Update channel |
| DELETE | `/api/v1/channels/<id>` | Delete channel |
| POST | `/api/v1/channels/<id>/toggle` | Toggle active status |
| POST | `/api/v1/channels/bulk` | Bulk create channels |
| GET | `/api/v1/channels/stats` | Get channel statistics |

### Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/pipeline/items` | List pipeline items |
| GET | `/api/v1/pipeline/items/<id>` | Get single item |
| POST | `/api/v1/pipeline/items/<id>/retry` | Retry failed item |
| POST | `/api/v1/pipeline/items/<id>/skip` | Skip item (mark failed) |
| GET | `/api/v1/pipeline/stats` | Get pipeline statistics |
| GET | `/api/v1/pipeline/failed` | List failed items |
| POST | `/api/v1/pipeline/release-stale` | Release stale claims |
| POST | `/api/v1/pipeline/bulk-retry` | Retry all failed |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1` | API info |
| GET | `/` | Admin UI |

## Quick Start

### With Docker Compose

```bash
# From project root
docker compose up -d

# Check health
curl http://10.0.0.33:5020/health
```

### Local Development

```bash
cd src/admin
cp .env.example .env
# Edit .env with database credentials

./scripts/run_local.sh
```

## Import Channels

```bash
# From CSV (default: src/db/seed/channels.csv)
python scripts/import_channels.py

# Custom CSV
python scripts/import_channels.py --csv /path/to/channels.csv

# Dry run
python scripts/import_channels.py --dry-run
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KNOWLEDGE_DB_HOST` | 10.0.0.33 | PostgreSQL host |
| `KNOWLEDGE_DB_PORT` | 5010 | PostgreSQL port |
| `KNOWLEDGE_DB_NAME` | knowledge | Database name |
| `KNOWLEDGE_DB_USER` | knowledge | Database user |
| `KNOWLEDGE_DB_PASSWORD` | (required) | Database password |
| `FLASK_DEBUG` | false | Enable debug mode |
| `CORS_ORIGINS` | * | Allowed CORS origins |

## Admin UI

Access the admin UI at `http://localhost:5020/` (or via Traefik at `https://knowledge-admin.nextlevelguild.com`).

Features:
- View/add/edit channels
- Filter by domain and status
- Toggle channel active status
- View pipeline items and statistics
- Retry/skip failed items
- Release stale claims
