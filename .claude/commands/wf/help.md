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
/wf:deny # ... - Reject issue with feedback + test gap analysis
/wf:reject     - Alias for /wf:deny
/wf:detail #   - Show full issue details with location context
/wf:audit      - Audit recent completions
/wf:dash       - GitHub dashboard links
/wf:issue      - Create issue & drive through phase 3 (tests)
/wf:new        - Alias for /wf:issue
/wf:q          - Items fixed but not deployed
/wf:deploy     - Deploy pending fixes (includes deploy verification gate)
/wf:review     - Human review session (includes deploy verification gate)

DEPLOY VERIFICATION GATE:
  Before human review, the system automatically verifies:
  1. Health endpoint responds (GET /health -> 200)
  2. Version endpoint returns expected commit (GET /version)
  If verification fails, items auto-reject to phase:4.

CONVERSATIONAL SHORTCUTS:
- "approve 42" or "looks good" -> /wf:approve
- "reject 42" or "needs work" -> /wf:deny
- "what needs review?" -> /wf:pending

PHASE FLOW (10 Phases):
0-backlog -> 1-refining -> 2-designing -> 3-tests-writing ->
4-developing -> 5-tea-testing -> 6-deployment [verify gate] ->
7-human-review -> 8-docs-update -> 9-done

PHASE 3 GATE: Tests must be verified FAILING before advancing.
PHASE 6 GATE: Deploy verification must PASS before human review.
```
