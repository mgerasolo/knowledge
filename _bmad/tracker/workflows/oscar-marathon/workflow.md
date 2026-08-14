---
workflow: oscar-marathon
agent: oscar
mode: autonomous
description: Autonomous batch processing of AI-ready issues
trigger: /oscar:marathon
code: MR
---

# Oscar Marathon Workflow

## Purpose

Process the AI-ready queue autonomously without user interaction. Oscar works through issues until queue is empty or a blocking issue is encountered.

## Usage

```
/oscar:marathon                    (process all ai-ready)
/oscar:marathon --max 5            (limit to 5 issues)
/oscar:marathon --until-blocked    (stop on first block)
```

## Behavior

1. Load AI-ready queue
2. For each issue:
   - Start work (`/oscar:work`)
   - Process through phases automatically
   - Advance when gates pass
   - Stop if human gate reached
3. Report progress periodically
4. Summary when complete

## Output

```
**Oscar** 🚦: Starting marathon mode

📋 Queue: 5 issues

[1/5] #45 - Fix login redirect
  Phase: 0-backlog → 3-test-writing → 4-developing → done ✅

[2/5] #48 - Add password reset
  Phase: 1-refining → 2-designing
  ⏸️ Needs human input (questions pending)

[3/5] #49 - Update error messages
  Phase: 0-backlog → 10-done ✅ (quick mode)

Marathon complete:
  ✅ Completed: 2
  ⏸️ Paused: 1 (human input needed)
  📋 Remaining: 2

Continue with: /oscar:marathon
```
