---
description: Deploy all items that passed testing and update their workflow phase
allowed-tools: Bash(gh issue edit:*), Bash(gh issue comment:*), Bash(gh issue list:*)
---

# Deploy Pending Items

Deploy all items that have passed testing and advance them to deployment phase.

## Steps

1. List items ready for deployment
2. Confirm with human
3. Run deployment (or note manual deployment needed)
4. Update labels for each issue

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

# Process each item
for num in $(echo "$ITEMS" | jq -r '.[].number'); do
  echo "Processing #$num..."
  gh issue edit $num --remove-label "phase:5-tea-testing"
  gh issue edit $num --add-label "phase:6-deployment"
  gh issue edit $num --add-label "awaiting:human-approval"
  gh issue comment $num --body "Deployed for human verification. Test via web app at poc.habitarcade.com"
done

echo ""
echo "---"
echo "Items deployed. Run \`/wf:review\` to start human verification."
```
