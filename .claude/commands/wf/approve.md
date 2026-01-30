---
description: Approve an issue and advance it to the next workflow phase
argument-hint: [issue-number]
allowed-tools: Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue view:*)
---

# Approve Issue

Approve issue #$ARGUMENTS and advance it to the next phase.

## Validation

1. Check issue exists
2. Verify it's in a review phase (phase:6-deployment, phase:7-human-review, or has needs:verification)

## Phase Transitions

- `needs:verification` -> Remove label, add `phase:7-human-review` (if not present)
- `phase:6-deployment` -> `phase:7-human-review`
- `phase:7-human-review` -> `phase:8-docs-update`
- `phase:8-docs-update` -> `phase:9-done`

## Execute

```bash
ISSUE=$ARGUMENTS

# Get current labels
LABELS=$(gh issue view $ISSUE --json labels --jq '.labels[].name' 2>/dev/null)

# Remove awaiting labels
gh issue edit $ISSUE --remove-label "awaiting:human-approval" 2>/dev/null
gh issue edit $ISSUE --remove-label "needs:verification" 2>/dev/null

# Determine and apply phase transition
if echo "$LABELS" | grep -q "phase:7-human-review"; then
  gh issue edit $ISSUE --remove-label "phase:7-human-review"
  gh issue edit $ISSUE --add-label "phase:8-docs-update"
  gh issue comment $ISSUE --body "Approved by human review. Moving to docs update phase."
elif echo "$LABELS" | grep -q "phase:6-deployment"; then
  gh issue edit $ISSUE --remove-label "phase:6-deployment"
  gh issue edit $ISSUE --add-label "phase:7-human-review"
  gh issue comment $ISSUE --body "Deployment verified. Moving to human review."
else
  gh issue edit $ISSUE --add-label "phase:8-docs-update"
  gh issue comment $ISSUE --body "Approved by human review."
fi

echo "Issue #$ISSUE approved and advanced to next phase."
```
