# Architecture Decision: MCP Gateway for YouTube Transcripts

**Date:** 2026-03-28
**Decision by:** Claude (autonomous session)
**Status:** Implementing

## Context

The n8n YouTube Transcript Fetcher workflow broke around March 23, 2026. It was scraping YouTube pages to extract caption URLs, but YouTube started fingerprinting requests and returning pages without caption data to n8n's HTTP Request node.

## Decision

**Move transcript fetching into the KnowledgeStack embedding service using the MCP Gateway.**

### Why MCP Gateway?

1. **Official route** - The Docker MCP Gateway uses the `youtube-transcript` library which is the sanctioned way to fetch transcripts
2. **Already working** - Tested successfully: `mcp__docker-mcp-gateway__get_timed_transcript`
3. **Centralized** - Infrastructure maintains the gateway; we just consume it
4. **No scraping** - Avoids bot detection issues entirely

### New Flow

```
BEFORE (broken):
n8n orchestrator → YouTube Transcript Fetcher (scraping) → embedding service

AFTER:
n8n orchestrator → embedding service → MCP Gateway (official API)
```

### Changes Required

1. **Embedding service** - Add MCP Gateway client, fetch transcript when video_id provided without transcript
2. **n8n orchestrator** - Skip the transcript fetcher call, pass video_id directly to embedding service
3. **No changes to** - PostgreSQL, SurrealDB, admin API

## Guiding Principles (per user)

- Do not get flagged
- Do not get rate limited
- Do not draw attention

The MCP Gateway approach satisfies all three - it uses the official YouTube transcript API which is the intended access method.

## Implementation Notes

MCP Gateway HTTP interface:
```
POST http://10.0.0.27:2780/mcp
Headers:
  Content-Type: application/json
  Accept: application/json, text/event-stream
  Mcp-Session-Id: {from init}

Step 1: Initialize session
Step 2: Call tools/call with session ID
```

## Rollback Plan

If this doesn't work, revert embedding service and update n8n workflow to call a Python-based transcript service instead.
