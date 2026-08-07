# ADR-002: Adopt Speakr for Transcript Repository

**Status:** Accepted
**Date:** 2026-01-30
**Deciders:** Matt
**Context:** Build vs Buy evaluation for transcript storage

## Context

KnowledgeStack needs a transcript repository with:
- Full-text search
- Per-recording AI chat (RAG)
- User authentication
- Tagging, bookmarks, playlists
- Multi-user access
- Video playback synchronized with transcripts

Building these features from scratch would take approximately 1 year of development time.

## Decision

**Adopt Speakr** (AGPL-3.0 open-source) as the lecture hall layer (KnowledgeLecture), running it unmodified.

## Rationale

### What Speakr Provides

| Feature | Speakr | Build Time Saved |
|---------|--------|------------------|
| Transcript display | Full UI | 2-3 months |
| Full-text search | Built-in | 1-2 months |
| Per-recording chat | Whisper + LLM | 2-3 months |
| User auth | OIDC support | 1-2 months |
| Tags/bookmarks | Complete | 1 month |
| Video sync | YouTube embed | 1 month |
| Multi-user | Role-based | 1 month |

**Total saved:** ~10-12 months

### What Speakr Does NOT Provide

These become KnowledgeStack's value-add:
- Automated channel monitoring (→ KnowledgeEnroll)
- Cross-repository semantic search (→ KnowledgeCollege)
- Entity enrichment (→ KnowledgeCollege)
- Pipeline monitoring (→ KnowledgeOps)
- External API access (→ KnowledgeGateway)

### Technical Fit

- **Stack:** Python 3.11 / Flask + Vue.js 3 (familiar)
- **Database:** PostgreSQL (shared with our pipeline)
- **Transcription:** WhisperX via API (already deployed on Jarvis)
- **LLM:** Configurable (LiteLLM proxy compatible)
- **Auth:** OIDC (Authentik ready)

## Consequences

### Positive

- **Massive time savings** (~1 year of UI/auth/search work)
- **Proven features** (search, chat, playback work out of the box)
- **Active maintenance** (upstream fixes)
- **AGPL-compatible** (we can deploy and extend)

### Negative

- **Vendor dependency** (need to track upstream changes)
- **Limited customization** (we run unmodified)
- **AGPL license** (derivative work must be open-source)
- **Feature gaps** (no cross-repo search, no channel management)

### Architectural Impact

```
┌─────────────────────────────────────────────────────────────────┐
│ KnowledgeStack Platform                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  KnowledgeEnroll ──► SPEAKR (KnowledgeLecture) ──► KnowledgeCollege │
│      (We build)           (Adopt)                    (We build)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

Speakr becomes a "black box" in Tier 2 -- we push content in via API, users access via its UI, and we sync data out for enrichment.

## Alternatives Considered

### Alternative 1: Build Custom Repository

- **Pro:** Full control, no license constraints
- **Con:** ~1 year of development time
- **Why rejected:** Solo developer, too much scope

### Alternative 2: Podcast Index + Custom UI

- **Pro:** Existing transcript APIs
- **Con:** YouTube-focused, not podcast-focused
- **Why rejected:** Different use case

### Alternative 3: Notion/Obsidian as Repository

- **Pro:** Flexible, familiar tools
- **Con:** No per-recording chat, limited search
- **Why rejected:** Missing core features

## References

- Speakr GitHub: https://github.com/speakr/speakr
- Speakr Research: `docs/research/speakr-comprehensive-research.md`
- Spike Findings: `docs/spike-speakr-deployment-findings.md`
