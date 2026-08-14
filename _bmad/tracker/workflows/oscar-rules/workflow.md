---
workflow: oscar-rules
agent: oscar
mode: configure
description: Manage .claude/rules/ activation
trigger: /oscar:rules
code: RL
---

# Oscar Rules Workflow

## Purpose

View and manage which rules from `.claude/rules/` are active for the current context.

## Usage

```
/oscar:rules                  (list active rules)
/oscar:rules enable <rule>    (enable a rule)
/oscar:rules disable <rule>   (disable a rule)
```

## Output

```
**Oscar** 🚦: Active Rules

Project Rules (.claude/rules/):
  ✅ network-architecture.md
  ✅ deployment-targets.md
  ✅ port-standards.md
  ✅ credential-handling.md
  ⬜ maintenance-windows.md (disabled)

User Rules (~/.claude/rules/):
  ✅ response-format.md
  ✅ domains.md
  ✅ speech-input.md

Phase-specific Rules:
  ✅ tdd-enforcement.md (active for phase 4-developing)
  ⬜ deployment-checks.md (active for phase 7-deployment)

Toggle: /oscar:rules enable maintenance-windows
```
