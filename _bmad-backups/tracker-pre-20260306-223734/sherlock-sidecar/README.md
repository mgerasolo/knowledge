# Sherlock Sidecar

This folder stores persistent memory for the **Sherlock** agent (Cross-Domain Root Cause Investigator).

## Purpose

Sherlock maintains investigation history, pattern databases, and recovery state across sessions. This enables:
- Pattern detection for recurring issues
- Investigation continuity across compaction
- Historical root cause reference for faster diagnosis

## Files

| File | Purpose |
|------|---------|
| `memories.md` | Investigation patterns, learned behaviors, project-specific insights |
| `instructions.md` | Startup protocols, methodology reminders, user preferences |
| `case-log.md` | Rolling investigation log (problem, root_cause, when, system, project, pattern_tag) |
| `patterns.md` | Extracted recurring patterns from case-log analysis |

## Directories

| Directory | Purpose |
|-----------|---------|
| `recovery/` | Active investigation state (survives compaction) |
| `logs/` | Investigation event logs |
| `feedback/` | User corrections and methodology improvements |
| `skills/` | External skill references for specialized debugging |

## Runtime Access

After BMAD installation, this folder will be accessible at:
`{project-root}/_bmad/_memory/sherlock-sidecar/`

## Case Log Schema

Each investigation entry in `case-log.md` follows this structure:

```yaml
- date: YYYY-MM-DD
  project: project-name
  symptom: "Brief description of observed behavior"
  root_cause: "The actual cause identified"
  domain: code | config | infrastructure | process | external
  resolution: "What was done to fix it"
  pattern_tag: "keyword for pattern matching"
  similar_to: [optional list of related case IDs]
```
