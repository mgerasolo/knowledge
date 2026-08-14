---
workflow: oscar-advance
agent: oscar
mode: orchestrate
description: Advance to next phase (runs gates)
trigger: /oscar:advance
code: AD
---

# Oscar Advance Workflow

## Purpose

Advance the current issue to the next phase. Runs exit gates for current phase and entry gates for next phase.

## Usage

```
/oscar:advance           (advance current issue)
/oscar:advance --force   (bypass warning gates, not blocking)
```

## Steps

1. Verify active issue
2. Run exit gate for current phase
3. If gate passes, advance to next phase
4. Run entry gate for next phase
5. Route to appropriate agent

## Gate Behavior

- **Exit code 0**: Gate passes
- **Exit code 1**: Warning (can force)
- **Exit code 2**: BLOCKED (cannot proceed)

## Output

```
**Oscar** 🚦: Advancing #42 from test-writing to developing

🔍 Running exit gate: verify-red-phase.sh
   ✅ Tests exist: 5 test files
   ✅ Tests fail: 5/5 failing (correct for RED phase)

📍 Phase: 4-developing (TDD GREEN)
🎯 New Gate: Tests must pass

Handing to Dev to implement...
```
