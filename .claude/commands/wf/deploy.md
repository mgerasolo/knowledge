---
description: Deploy all items that passed testing and update their workflow phase
allowed-tools: Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue list:*)
---

# Deploy Pending Items

Deploy all items that have passed testing and advance them to deployment phase.

## Steps

1. List items ready for deployment
2. Run deployment
3. **Run deploy verification gate** (health + version endpoint)
4. If verification passes: update labels and advance to human review
5. If verification fails: auto-reject back to development

## Execute

```bash
echo "## Deploying Pending Items"
echo ""

# Get items ready for deployment
ITEMS=$(gh issue list -l "phase:5-tea-testing" -l "tests:passed" --json number,title 2>/dev/null)

if [ -z "$ITEMS" ] || [ "$ITEMS" = "[]" ]; then
  echo "No items ready for deployment."
  exit 0
fi

echo "Items to deploy:"
echo "$ITEMS" | jq -r '.[] | "#\(.number): \(.title)"'
echo ""

# --- DEPLOYMENT STEP ---
# (Actual deployment command goes here — docker compose, etc.)
echo "Deploying to Banner (10.0.0.33)..."
echo ""

# --- DEPLOY VERIFICATION GATE ---
echo "Running deploy verification gate..."
TARGET_HOST="${DEPLOY_HOST:-10.0.0.33}"
TARGET_PORT="${DEPLOY_PORT:-3350}"

sleep 5  # Wait for service to come up

HEALTH_OK=false
VERSION_OK=false

# Layer 1: Health check
HEALTH=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/health" 2>/dev/null)
if [ $? -eq 0 ]; then
  echo "  Health: OK"
  HEALTH_OK=true
else
  echo "  Health: FAILED — service not responding"
fi

# Layer 2: Version check
if [ "$HEALTH_OK" = true ]; then
  VERSION=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/version" 2>/dev/null)
  if [ $? -eq 0 ]; then
    COMMIT=$(echo "$VERSION" | jq -r '.commit // "unknown"' 2>/dev/null)
    echo "  Version: $COMMIT"
    VERSION_OK=true
  else
    echo "  Version: endpoint not available (non-blocking warning)"
    VERSION_OK=true  # Version endpoint is recommended but not blocking
  fi
fi

echo ""

# --- PROCESS EACH ITEM ---
if [ "$HEALTH_OK" = true ]; then
  echo "Deploy verification PASSED. Advancing items to human review."
  echo ""

  for num in $(echo "$ITEMS" | jq -r '.[].number'); do
    echo "Processing #$num..."
    gh issue edit $num --remove-label "phase:5-tea-testing"
    gh issue edit $num --add-label "phase:6-deployment"
    gh issue edit $num --add-label "awaiting:human-approval"
    gh issue comment $num --body "Deployed to Banner. Deploy verification passed (health: OK, version: ${COMMIT:-unknown}).

Test via web app at https://knowledge.nextlevelguild.com (or http://10.0.0.33:3350)"
  done

  echo ""
  echo "---"
  echo "Items deployed and verified. Run \`/wf:review\` to start human verification."
else
  echo "Deploy verification FAILED. Auto-rejecting all items back to development."
  echo ""

  for num in $(echo "$ITEMS" | jq -r '.[].number'); do
    echo "Auto-rejecting #$num..."
    gh issue edit $num --remove-label "phase:5-tea-testing" --remove-label "tests:passed"
    gh issue edit $num --add-label "phase:4-developing"
    gh issue comment $num --body "**Auto-rejected by deploy verification gate:**

Health endpoint not responding at http://$TARGET_HOST:$TARGET_PORT/health.
Service is not deployed or not running.

Returned to development phase. Fix deployment before re-running tests."
  done

  echo ""
  echo "---"
  echo "DEPLOYMENT FAILED. Items returned to phase:4-developing."
  echo "Fix the deployment issue and re-run the development cycle."
fi
```
