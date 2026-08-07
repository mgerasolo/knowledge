# KnowledgeEnroll Embedding Service

HTTP API for embedding transcripts into SurrealDB. Called by n8n workflows.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (SurrealDB connectivity) |
| POST | `/api/embed` | Embed video transcript |
| POST | `/api/search` | Semantic search (not yet implemented) |
| GET | `/api/video/<id>` | Get video metadata |
| GET | `/api/stats` | Get embedding statistics |

## Embed Video

**POST /api/embed**

```json
{
    "video_id": "dQw4w9WgXcQ",
    "title": "Video Title",
    "url": "https://youtube.com/watch?v=...",
    "channel_handle": "channelname",
    "channel_name": "Channel Display Name",
    "domain": "ai-tech",
    "published_at": "2026-01-15",
    "duration_seconds": 3600,
    "transcript": "Full transcript text...",
    "segments": [
        {"start": 0, "duration": 5, "text": "First segment"},
        {"start": 5, "duration": 5, "text": "Second segment"}
    ],
    "skip_embeddings": false
}
```

**Response:**
```json
{
    "success": true,
    "video_id": "dQw4w9WgXcQ",
    "surreal_id": "video:abc123def456",
    "segment_count": 42,
    "embeddings_generated": true
}
```

## n8n Integration

The Embedding Sync workflow calls this service:

```
POST http://10.0.0.33:5030/api/embed
Content-Type: application/json

{
    "video_id": "{{ $json.youtube_video_id }}",
    "title": "{{ $json.title }}",
    "transcript": "{{ $json.transcript }}",
    "segments": {{ $json.segments }},
    ...
}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SURREAL_URL` | http://10.0.0.33:5040 | SurrealDB URL |
| `SURREAL_USER` | root | SurrealDB username |
| `SURREAL_PASS` | changeme | SurrealDB password |
| `SURREAL_NS` | knowledge | SurrealDB namespace |
| `SURREAL_DB` | transcripts | SurrealDB database |
| `LITELLM_URL` | http://10.0.0.27:2764/v1/embeddings | LiteLLM proxy URL |
| `LITELLM_API_KEY` | (required) | LiteLLM API key |
| `CHUNK_SIZE` | 500 | Characters per chunk |
| `CHUNK_OVERLAP` | 100 | Overlap between chunks |

## Quick Start

```bash
# With Docker Compose (from project root)
docker compose up -d surrealdb embedding

# Check health
curl http://10.0.0.33:5030/health

# Get stats
curl http://10.0.0.33:5030/api/stats
```

## Local Development

```bash
cd src/embedding
cp .env.example .env
# Edit .env

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

FLASK_DEBUG=true python app.py
```
