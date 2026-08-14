# oscar-sidecar

This folder stores persistent memory for the **Oscar** agent.

## Purpose

Oscar is the Chief Orchestrator for BMAD workflows. This sidecar enables:
- Session state persistence across compaction
- Cross-session awareness for multi-conversation coordination
- Marathon queue for autonomous batch processing
- Learned patterns for proactive suggestions
- Declined suggestion tracking to avoid annoyance

## Files

| File | Purpose |
|------|---------|
| `memories.md` | Session state, cross-session index, marathon queue, learned patterns |
| `instructions.md` | Startup protocols, behavioral boundaries, integration points |

## Runtime Access

After BMAD installation, this folder will be accessible at:
```
{project-root}/_bmad/_memory/oscar-sidecar/
```

## Context Efficiency

Oscar is designed for minimal context footprint:
- **Hot memory:** ~200 tokens (always loaded)
- **Warm memory:** ~500 tokens (loaded on reference)
- **Cold memory:** Query on demand (never preloaded)

---

_Oscar sidecar created 2026-03-02_
