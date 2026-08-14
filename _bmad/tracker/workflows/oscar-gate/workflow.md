---
workflow: oscar-gate
agent: oscar
mode: check
description: Re-run gate checks for current phase
trigger: /oscar:gate
code: GT
---

# Oscar Gate Workflow

## Purpose

Re-run the gate checks for the current phase to see if requirements are now met.

## Usage

```
/oscar:gate              (run current phase gate)
/oscar:gate --verbose    (show detailed output)
```

## Output

```
**Oscar** 🚦: Running gate check for phase 4-developing

Gate: verify-green-phase.sh (tests must pass)

Results:
  ✅ Unit tests: 12/12 passing
  ❌ Integration tests: 3/5 passing
  ⏭️ E2E tests: skipped (integration failed)

Overall: ❌ BLOCKED
  Fix the 2 failing integration tests to proceed.

Failing tests:
  - auth.integration.test.ts:45 - Login redirect
  - auth.integration.test.ts:78 - Session timeout
```
