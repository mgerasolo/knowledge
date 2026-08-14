---
workflow: oscar-handoff
agent: oscar
mode: transition
description: Context-preserving agent transition
trigger: /oscar:handoff
code: HO
---

# Oscar Handoff Workflow

## Purpose

Hand off work to a different agent while preserving full context. Oscar packages the current state and provides it to the new agent.

## Usage

```
/oscar:handoff Dev         (hand to Dev)
/oscar:handoff TEA         (hand to TEA)
/oscar:handoff Architect   (hand to Architect)
```

## Context Preserved

- Current issue and phase
- Work completed so far
- Files modified
- Decisions made
- Open questions
- Test status

## Output

```
**Oscar** 🚦: Handing off to TEA

📦 Context package:
  Issue: #42 - Add user authentication
  Phase: 4-developing → 6-testing
  Files: src/auth/*.ts (5 files)
  Tests: 12/12 unit tests passing

**TEA (Murat)** 🧪: Got it! I'll run the full test suite
including edge cases and integration tests...
```
