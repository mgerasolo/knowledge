---
description: Show items fixed and tested but not yet deployed (deployment queue)
allowed-tools: Bash(gh issue list:*)
---

# Deployment Queue

Show items that have passed testing but are not yet deployed.

## Query

Find issues with:
- `phase:5-tea-testing` AND `tests:passed`
- Or ready for deployment but not yet moved

## Execute

```bash
echo "## Deployment Queue"
echo ""

# Items that passed TEA testing
echo "**Passed Testing (ready for deploy):**"
gh issue list -l "phase:5-tea-testing" -l "tests:passed" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null

# Items with tests:passed but no phase label
echo ""
echo "**Tests Passed (any phase):**"
gh issue list -l "tests:passed" --json number,title,labels --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null | head -10

COUNT=$(gh issue list -l "phase:5-tea-testing" -l "tests:passed" --json number --jq 'length' 2>/dev/null)
echo ""
echo "---"
echo "**$COUNT items ready for deployment**"
echo "Run \`/wf:deploy\` to deploy all pending items."
```
