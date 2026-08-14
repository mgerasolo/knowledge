---
description: Start an interactive human review session for deployed items
allowed-tools: Bash(gh issue list:*), Bash(gh issue view:*), Bash(gh issue edit:*), Bash(gh issue comment:*), AskUserQuestion
---

# Human Review Session

Start an interactive session to review deployed items via the web app.

## Pre-Review: Deploy Verification Gate

**Before showing items for human review, verify they are actually deployed.**

For each item in phase:6-deployment or phase:7-human-review, run the deploy verification gate:

```bash
echo "## Deploy Verification Gate"
echo ""

# Get deployment target from project config
# Default: Banner (10.0.0.33)
TARGET_HOST="${DEPLOY_HOST:-10.0.0.33}"
TARGET_PORT="${DEPLOY_PORT:-3350}"

echo "Checking deployment at $TARGET_HOST:$TARGET_PORT..."

# Layer 1: Health check
HEALTH=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/health" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "FAIL: Health endpoint not responding at http://$TARGET_HOST:$TARGET_PORT/health"
  echo "Service is NOT deployed or NOT running. Auto-rejecting all items."
  echo ""

  # Auto-reject all items in phase:6 or phase:7
  for num in $(gh issue list -l "phase:6-deployment" --json number --jq '.[].number' 2>/dev/null); do
    gh issue edit $num --remove-label "phase:6-deployment" --remove-label "awaiting:human-approval"
    gh issue edit $num --add-label "phase:4-developing"
    gh issue comment $num --body "**Auto-rejected by deploy verification gate:**

Health endpoint not responding. Service is not deployed or not running.

Returned to development phase. Fix deployment before requesting human review."
    echo "  Auto-rejected #$num (health check failed)"
  done
  exit 0
fi

echo "Health: OK"

# Layer 2: Version check
VERSION=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/version" 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "WARNING: Version endpoint not available. Proceeding but cannot verify commit SHA."
else
  echo "Version: $(echo $VERSION | jq -r '.commit // "unknown"' 2>/dev/null)"
fi

echo ""
echo "Deploy verification passed. Proceeding to human review."
```

## Process

1. Run deploy verification gate (above)
2. List all items awaiting human review
3. For each item, show what to test
4. Wait for human verdict: approve or deny
5. Process the verdict and advance/return the issue

## Execute

After verification passes, gather items for review:

```bash
echo "## Human Review Session"
echo ""
echo "Test items at: https://knowledge.nextlevelguild.com"
echo "  (or direct: http://10.0.0.33:3350)"
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
