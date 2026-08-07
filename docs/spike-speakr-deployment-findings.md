# Speakr Deployment Spike - Findings

**Date:** 2026-03-18
**Status:** COMPLETE
**Conversation:** conv-20260129-200801

## Summary

Successfully deployed Speakr as the transcript repository foundation for KnowledgeStack. The spike validated that Speakr meets our needs for transcript storage, playback, search, and diarization.

## Deployment Details

| Component | Value |
|-----------|-------|
| **Container** | `learnedmachine/speakr:latest` (4.4GB) |
| **Host** | Banner (10.0.0.33) |
| **Port** | 5000 (internal), 8899 (container) |
| **Public URL** | https://transcripts.nextlevelguild.com |
| **Admin Email** | matt@gerasolo.com |

## Configuration

### Environment Variables (deploy/.env)

```bash
TEXT_MODEL_BASE_URL=http://10.0.0.27:2764/v1
TEXT_MODEL_API_KEY=<REDACTED — fetch from the secrets store, never inline>  # LiteLLM project key
TEXT_MODEL_NAME=gpt-4o-mini
TRANSCRIPTION_CONNECTOR=openai_transcribe
TRANSCRIPTION_MODEL=gpt-4o-transcribe-diarize
ADMIN_EMAIL=matt@gerasolo.com
ALLOW_REGISTRATION=true
```

### Key Files

- `deploy/docker-compose.yml` - Container configuration
- `deploy/.env` - Environment variables (gitignored)
- `deploy/data/` - Persistent storage (gitignored)

## Validation Results

| Test | Result | Notes |
|------|--------|-------|
| Container startup | PASS | Pulls and runs successfully |
| Admin login | PASS | matt@gerasolo.com working |
| Audio upload | PASS | Files accepted and processed |
| Transcription | PASS | gpt-4o-transcribe via LiteLLM |
| Diarization | PASS | Speaker labels generated |
| Summary generation | PASS | LiteLLM integration working |
| Public URL | PASS | https://transcripts.nextlevelguild.com |

## Diarization Quality

Speaker diarization works but quality depends on:
- Audio clarity
- Speaker voice distinctiveness
- Recording environment

User feedback: "not as clean as I would have liked for direction, but good enough"

## Integration Points Validated

1. **LiteLLM Proxy** (10.0.0.27:2764)
   - Project-specific virtual key required
   - Text model: gpt-4o-mini
   - Transcription model: gpt-4o-transcribe-diarize

2. **Traefik Routing** (Helicarrier)
   - Route added to `/opt/traefik/config/banner.yml`
   - Cloudflare Tunnel configured via Zero Trust dashboard

3. **Cloudflare DNS**
   - CNAME record: transcripts.nextlevelguild.com

## Fabric Integration Research

Analyzed danielmiessler/fabric (200+ prompt patterns). Key patterns for KnowledgeStack:

| Pattern | Use Case |
|---------|----------|
| `extract_wisdom` | Core transcript enrichment (IDEAS, INSIGHTS, QUOTES, FACTS) |
| `summarize` | 20-word summary + main points |
| `create_video_chapters` | Timestamp extraction |
| `extract_recommendations` | Actionable takeaways |
| `label_and_rate` | Content quality scoring (S/A/B/C/D tiers) |

**Integration options:**
1. Use Fabric CLI directly (`cat transcript | fabric -p extract_wisdom`)
2. Copy patterns as prompt templates in n8n workflows
3. Run Fabric REST API server for programmatic access

## Issues Encountered & Resolved

| Issue | Resolution |
|-------|------------|
| Disk space on Banner (98% full) | `docker system prune -af --volumes` freed 10GB |
| Diarization not enabled | Set `TRANSCRIPTION_CONNECTOR=openai_transcribe` explicitly |
| Admin login failed | Database persisted old email; deleted `data/instance/*` |
| LiteLLM 401 error | Created project-specific virtual key |
| 404 on public URL | Infrastructure #642 - Cloudflare Tunnel route added |

## Next Steps (Separate Conversations)

1. **n8n Pipeline** - YouTube RSS monitoring → Speakr ingestion (in progress)
2. **PRD Steps 10-11** - NFRs + Final with PM John
3. **Fabric Integration** - Enrichment layer on top of Speakr transcripts

## Architecture Confirmed

```
YouTube Channels
      │
      ▼
    n8n (RSS monitoring + orchestration)
      │
      ▼
   Speakr (transcript repository)
      │
      ▼
   Qdrant (vector embeddings - future)
      │
      ▼
  KnowledgeStack UI (intelligence overlay - future)
```

## References

- Speakr: https://github.com/murtaza-nasir/speakr
- Fabric: https://github.com/danielmiessler/fabric
- PRD: `_bmad-output/planning-artifacts/prd.md`
- Research: `_bmad-output/planning-artifacts/research/technical-knowledgestack-research-2026-01-30.md`
