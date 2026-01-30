---
description: Start an interactive human review session for deployed items
allowed-tools: Bash(gh issue list:*), Bash(gh issue view:*), Bash(gh issue edit:*), Bash(gh issue comment:*), AskUserQuestion
---

# Human Review Session

Start an interactive session to review deployed items via the web app.

## Process

1. List all items awaiting human review
2. For each item, show what to test
3. Wait for human verdict: approve or deny
4. Process the verdict and advance/return the issue

## Execute

First, gather items for review:

```bash
echo "## Human Review Session"
echo ""
echo "Test items at: https://poc.habitarcade.com"
echo ""

# Get items awaiting review (check multiple labels)
echo "### Items Ready for Review:"
echo ""

# Phase 6 (just deployed)
gh issue list -l "phase:6-deployment" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null

# Phase 7 (in review)
gh issue list -l "phase:7-human-review" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null

# Legacy needs:verification
gh issue list -l "needs:verification" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null | head -20

echo ""
echo "---"
echo "For each item, respond with:"
echo "  - 'approve #' to approve"
echo "  - 'deny # reason' to reject with feedback"
echo "  - 'done' to exit review session"
```

## Interactive Loop

After showing the list, wait for human input and process:
- "approve 42" -> Run /wf:approve 42
- "deny 42 button alignment off" -> Run /wf:deny 42 button alignment off
- "done" -> End session with summary
