# API Contracts & Interfaces

**Last Updated:** 2026-03-22

## External APIs

### KnowledgeGateway REST API (Vision Phase)

Base URL: `https://knowledge-api.nextlevelguild.com/v1`

#### Authentication

```http
Authorization: Bearer <API_KEY>
```

API keys scoped by tier:
- **Consumer:** Read-only search and retrieval
- **Curator API:** Channel management + consumer
- **Admin API:** Full access

#### Endpoints

##### Search

```http
GET /search
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query |
| `mode` | string | No | `semantic`, `keyword`, `hybrid` (default: hybrid) |
| `domain` | string | No | Filter by domain |
| `channel` | string | No | Filter by channel handle |
| `speaker` | string | No | Filter by speaker name |
| `from_date` | date | No | Published after (ISO 8601) |
| `to_date` | date | No | Published before (ISO 8601) |
| `limit` | int | No | Results per page (default: 20, max: 100) |
| `offset` | int | No | Pagination offset |

**Response:**

```json
{
  "results": [
    {
      "segment_id": "segment:abc123",
      "text": "The key to business success is...",
      "score": 0.85,
      "video": {
        "youtube_id": "dQw4w9WgXcQ",
        "title": "Business Principles That Work",
        "channel": "Myron Golden",
        "published_at": "2026-01-15T00:00:00Z",
        "url": "https://youtube.com/watch?v=dQw4w9WgXcQ"
      },
      "timestamp": {
        "start_seconds": 1234,
        "end_seconds": 1289,
        "link": "https://youtube.com/watch?v=dQw4w9WgXcQ&t=1234"
      }
    }
  ],
  "total": 145,
  "limit": 20,
  "offset": 0
}
```

##### Get Transcript

```http
GET /transcripts/{video_id}
```

**Response:**

```json
{
  "video": {
    "youtube_id": "dQw4w9WgXcQ",
    "title": "Business Principles That Work",
    "channel": "Myron Golden",
    "duration_seconds": 3600,
    "published_at": "2026-01-15T00:00:00Z"
  },
  "segments": [
    {
      "index": 0,
      "text": "Welcome everyone...",
      "start_seconds": 0,
      "end_seconds": 15
    }
  ],
  "entities": {
    "speakers": ["Myron Golden"],
    "topics": ["business", "entrepreneurship"]
  }
}
```

##### List Channels

```http
GET /channels
```

**Response:**

```json
{
  "channels": [
    {
      "handle": "myron-golden",
      "name": "Myron Golden",
      "domain": "business",
      "video_count": 523,
      "last_ingested": "2026-03-20T14:30:00Z"
    }
  ]
}
```

##### Get Speaker

```http
GET /speakers/{normalized_name}
```

**Response:**

```json
{
  "speaker": {
    "name": "Myron Golden",
    "normalized": "myron-golden",
    "bio": "Business coach and author...",
    "is_host": true
  },
  "credibility": [
    {
      "domain": "business",
      "tier": "top",
      "reasoning": "Author of multiple bestselling books..."
    }
  ],
  "recent_segments": 50,
  "total_appearances": 523
}
```

#### Error Responses

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Try again in 60 seconds.",
    "retry_after": 60
  }
}
```

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | API key lacks required scope |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

### KnowledgeGateway MCP Server (Vision Phase)

Protocol: Model Context Protocol (MCP)
Transport: HTTP/SSE

#### Tools

##### search

Search the knowledge repository.

```json
{
  "name": "search",
  "description": "Search transcript segments by topic, speaker, or content",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": { "type": "string", "description": "Search query" },
      "domain": { "type": "string", "description": "Filter by domain" },
      "speaker": { "type": "string", "description": "Filter by speaker" },
      "limit": { "type": "integer", "default": 10 }
    },
    "required": ["query"]
  }
}
```

##### get_transcript

Retrieve full transcript for a video.

```json
{
  "name": "get_transcript",
  "description": "Get the full transcript and metadata for a video",
  "inputSchema": {
    "type": "object",
    "properties": {
      "video_id": { "type": "string", "description": "YouTube video ID" }
    },
    "required": ["video_id"]
  }
}
```

##### list_channels

List monitored channels.

```json
{
  "name": "list_channels",
  "description": "List all channels in the knowledge repository",
  "inputSchema": {
    "type": "object",
    "properties": {
      "domain": { "type": "string", "description": "Filter by domain" }
    }
  }
}
```

##### get_speaker_content

Get content from a specific speaker.

```json
{
  "name": "get_speaker_content",
  "description": "Get recent content and credibility for a speaker",
  "inputSchema": {
    "type": "object",
    "properties": {
      "speaker": { "type": "string", "description": "Speaker name" },
      "domain": { "type": "string", "description": "Filter by domain" }
    },
    "required": ["speaker"]
  }
}
```

---

## Internal APIs

### Speakr API (Tier 2)

Documentation: Speakr upstream (AGPL-3.0)

Key endpoints used by KnowledgeEnroll:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/recordings` | POST | Upload new recording |
| `/api/recordings/{id}` | GET | Check transcription status |
| `/api/health` | GET | Service health check |

### SurrealDB API (Tier 3)

Protocol: HTTP/WebSocket
Port: 5040

```http
POST /sql
Content-Type: application/json
Authorization: Basic base64(user:pass)
surreal-ns: knowledgespike
surreal-db: transcripts

SELECT * FROM segment WHERE embedding <|20|> $query_embedding LIMIT 10
```

### n8n Webhooks (Tier 1)

| Webhook | Trigger | Payload |
|---------|---------|---------|
| `/webhook/new-video` | Manual submission | `{ "url": "..." }` |
| `/webhook/speakr-complete` | Speakr callback | `{ "recording_id": "..." }` |
| `/webhook/retry-failed` | Admin retry | `{ "item_id": "..." }` |

---

## Data Contracts

### Pipeline Item (PostgreSQL)

```sql
CREATE TABLE pipeline_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    youtube_id VARCHAR(11) UNIQUE NOT NULL,
    status pipeline_status NOT NULL DEFAULT 'discovered',
    retry_count INT DEFAULT 0,
    channel_id UUID REFERENCES channels(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    claimed_by VARCHAR(100),
    claimed_at TIMESTAMP,
    error_message TEXT
);

CREATE TYPE pipeline_status AS ENUM (
    'discovered', 'queued', 'downloading', 'transcribing',
    'embedding', 'indexing', 'indexed_light', 'indexed_full',
    'upgrading', 'failed'
);
```

### Segment (SurrealDB)

```surql
DEFINE TABLE segment SCHEMAFULL;
DEFINE FIELD text ON segment TYPE string;
DEFINE FIELD start_time ON segment TYPE float;
DEFINE FIELD end_time ON segment TYPE float;
DEFINE FIELD embedding ON segment TYPE option<array<float>>;
DEFINE FIELD video_youtube_id ON segment TYPE string;
DEFINE FIELD domain ON segment TYPE option<string>;
DEFINE FIELD published_at ON segment TYPE option<datetime>;
DEFINE FIELD ingested_at ON segment TYPE datetime;
```

---

## Rate Limits

| API | Limit | Window | Scope |
|-----|-------|--------|-------|
| KnowledgeGateway | 100 req | 1 minute | Per API key |
| KnowledgeGateway | 1000 req | 1 hour | Per API key |
| SurrealDB (internal) | No limit | - | Internal only |
| YouTube Data API | 10,000 units | Day | Global |
| Transcript scraping | 4 req | 1 minute | Global |
