# Oscar Memories

This file stores Oscar's persistent memory across sessions.

## Session State

```yaml
current_session: null
active_work_item: null
current_phase: null
active_agent: null
```

## Cross-Session Index

```yaml
sessions: []
# Format:
# - id: session-uuid
#   work_item: "#42"
#   phase: 4-developing
#   agent: Dev
#   last_active: 2026-03-02T22:30:00
```

## Marathon Queue

```yaml
queue: []
# Format:
# - issue: "#43"
#   priority: high
#   attempts: 0
```

## Learned Patterns

```yaml
patterns: []
# Format:
# - trigger: "deploying to wrong host"
#   response: "Redirect to Banner for dev, Hulk for prod"
#   times_used: 3
```

## Declined Suggestions

```yaml
declined: []
# Track what user declined to avoid repeating
# - suggestion: "invoke brainstorming workflow"
#   declined_at: 2026-03-02
```

---

_Oscar sidecar memory initialized_
