---
workflow: oscar-gates-list
agent: oscar
mode: report
description: List all phase gates and their status
trigger: /oscar:gates-list
code: GL
---

# Oscar Gates List Workflow

## Purpose

Display all phase gates, their requirements, and current status for the active issue.

## Usage

```
/oscar:gates-list              (show all gates)
/oscar:gates-list --verbose    (show gate scripts)
```

## Output

```
**Oscar** 🚦: Phase Gates for #42

Phase                Gate                    Status
──────────────────────────────────────────────────
0-backlog            workflow_assigned       ✅ PASSED
1-refining           criteria_testable       ✅ PASSED
2-designing          approach_documented     ✅ PASSED
3-test-writing       tests_fail (RED)        ✅ PASSED
3.5-ready-to-dev     human_approved          ✅ PASSED
4-developing         tests_pass (GREEN)      🔄 IN PROGRESS
5-audit              all_audits_pass         ⬜ PENDING
6-testing            full_suite_passes       ⬜ PENDING
7-deployment         health_check_passes     ⬜ PENDING
8-human-review       approval_or_denial      ⬜ PENDING
9-docs-update        docs_updated            ⬜ PENDING
10-done              (complete)              ⬜ PENDING

Current: 4-developing
  Gate: tests_pass
  Status: 8/12 tests passing
  Remaining: 4 failing tests
```
