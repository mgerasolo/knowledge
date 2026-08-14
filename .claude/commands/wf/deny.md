---
description: Reject an issue with feedback and return it to development phase
argument-hint: [issue-number] [reason...]
allowed-tools: Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue view:*)
---

# Deny/Reject Issue

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

# Add rejection comment with test gap analysis
gh issue comment $ISSUE --body "**Rejected by human review:**

$REASON

**Test Gap Analysis:**
This rejection indicates a gap in automated verification. Before re-implementing, evaluate:
- [ ] Was this caught by any existing test? If not, why?
- [ ] Should a new test be added to prevent this specific failure?
- [ ] Was the deploy verification gate running? Did it pass?
- [ ] Is the acceptance criteria specific enough to test automatically?

**Action required:** Fix the issue, add a test that would have caught this, then re-run the development cycle.

Returned to development phase for fixes."

echo "Issue #$ISSUE rejected and returned to phase:4-developing"
echo "Reason: $REASON"
echo ""
echo "NOTE: A test gap analysis has been added to the issue."
echo "The developer should add a test that would have caught this before re-implementing."
```
