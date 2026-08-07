---
description: List all available workflow commands and their usage
---

# Workflow Commands Help

Display all available workflow commands:

```
WORKFLOW COMMANDS (/wf:*)
=========================
/wf:help       - Show this help message
/wf:status     - Current workflow status by phase
/wf:pending    - List items awaiting human approval
/wf:approve #  - Approve issue, advance to next phase
/wf:deny # ... - Reject issue with feedback
/wf:reject     - Alias for /wf:deny
/wf:detail #   - Show full issue details with location context
/wf:audit      - Audit recent completions
/wf:dash       - GitHub dashboard links
/wf:issue      - Create issue & drive through phase 3 (tests)
/wf:new        - Alias for /wf:issue
/wf:q          - Items fixed but not deployed
/wf:deploy     - Deploy pending fixes
/wf:review     - Human review session

CONVERSATIONAL SHORTCUTS:
- "approve 42" or "looks good" -> /wf:approve
- "reject 42" or "needs work" -> /wf:deny
- "what needs review?" -> /wf:pending

PHASE FLOW (10 Phases):
0-backlog -> 1-refining -> 2-designing -> 3-tests-writing ->
4-developing -> 5-tea-testing -> 6-deployment -> 7-human-review ->
8-docs-update -> 9-done
```
