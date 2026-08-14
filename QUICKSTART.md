# KnowledgeEnroll Quick Start

## What Was Built

### Services

| Service | Port | Purpose |
|---------|------|---------|
| **Admin API** | 5020 | Channel CRUD, pipeline monitoring |
| **Embedding Service** | 5030 | Transcript embedding to SurrealDB |
| **PostgreSQL** | 5010 | Pipeline state management |
| **SurrealDB** | 5040 | Vector + graph storage |

### Files Created

```
src/
├── admin/                      # Admin API (Flask)
│   ├── app.py                  # Main application
│   ├── config.py               # Configuration
│   ├── db.py                   # Database utilities
│   ├── api/
│   │   ├── channels.py         # Channel CRUD endpoints
│   │   └── pipeline.py         # Pipeline monitoring endpoints
│   ├── templates/
│   │   └── index.html          # Admin UI
│   ├── scripts/
│   │   ├── import_channels.py  # CSV import script
│   │   └── run_local.sh        # Local dev runner
│   ├── Dockerfile
│   └── requirements.txt
│
├── embedding/                  # Embedding Service (Flask)
│   ├── app.py                  # HTTP API for n8n
│   ├── config.py               # Configuration
│   ├── surreal_client.py       # SurrealDB client
│   ├── embedder.py             # Chunking + embedding logic
│   ├── Dockerfile
│   └── requirements.txt
│
└── db/
    ├── schema/
    │   └── 001_pipeline_schema.sql  # PostgreSQL schema
    └── seed/
        └── channels.csv             # 50 YouTube channels

scripts/
├── deploy.sh                   # Deployment script
└── test_api.py                 # API test suite

docs/
└── deployment/
    └── README.md               # Deployment guide
```

## Deploy to Banner

```bash
# On Banner
cd /opt/stacks/knowledge
./scripts/deploy.sh
```

## Test APIs

```bash
# From Friday or any machine
python scripts/test_api.py --verbose
```

## Admin UI

Open: http://10.0.0.33:5020

Features:
- View/add/edit channels
- Filter by domain and status
- Monitor pipeline items
- Retry/skip failed items

## n8n Workflows (Pending)

Infrastructure handoff HO-3 includes:
1. **RSS Channel Monitor** - Polls YouTube RSS feeds every 30 min
2. **Video Ingest Orchestrator** - Processes videos via existing Transcript Fetcher
3. **Embedding Sync** - Calls our Embedding Service every 5 min

Specs: [docs/architecture/n8n-workflows-spec.md](docs/architecture/n8n-workflows-spec.md)

## Port Allocation

| Port | Service |
|------|---------|
| 5000 | Speakr (future) |
| 5010 | PostgreSQL |
| 5020 | Admin API |
| 5030 | Embedding Service |
| 5040 | SurrealDB |
| 5050-5099 | Reserved |
