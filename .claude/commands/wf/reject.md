---
description: Reject an issue with feedback (alias for /wf:deny)
argument-hint: [issue-number] [reason...]
allowed-tools: Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue view:*)
---

# Reject Issue (Alias for /wf:deny)

Reject issue and return it to a prior phase with feedback.

## Arguments

- First argument: Issue number
- Remaining arguments: Reason for rejection

## Execute

```bash
# Parse arguments - first is issue number, rest is reason
ISSUE=$(echo "$ARGUMENTS" | awk '{print $1}')
REASON=$(echo "$ARGUMENTS" | cut -d' ' -f2-)

if [ -z "$REASON" ]; then
  REASON="Rejected - needs more work"
fi

# Remove from current phase
gh issue edit $ISSUE --remove-label "phase:7-human-review" 2>/dev/null
gh issue edit $ISSUE --remove-label "phase:6-deployment" 2>/dev/null
gh issue edit $ISSUE --remove-label "awaiting:human-approval" 2>/dev/null
gh issue edit $ISSUE --remove-label "needs:verification" 2>/dev/null

# Return to development phase
gh issue edit $ISSUE --add-label "phase:4-developing"

# Add rejection comment
gh issue comment $ISSUE --body "**Rejected by human review:**

$REASON

Returned to development phase for fixes."

echo "Issue #$ISSUE rejected and returned to phase:4-developing"
echo "Reason: $REASON"
```
