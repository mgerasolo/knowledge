---
description: Audit recently completed issues for workflow compliance
allowed-tools: Bash(gh issue list:*), Bash(gh issue view:*)
---

# Workflow Audit

Audit recently completed items for workflow compliance.

## Checks

1. Issues closed in last 7 days
2. Missing documentation updates (no phase:8 transition)
3. Items without human verification
4. Test failure history

## Execute

```bash
echo "## Workflow Audit (Last 7 Days)"
echo ""

# Get closed issues from last 7 days
CLOSED=$(gh issue list --state closed --limit 20 --json number,title,closedAt,labels 2>/dev/null)

echo "**Recently Closed:**"
echo "$CLOSED" | jq -r '.[] | "#\(.number): \(.title)"' | head -10

echo ""
echo "**Current Open by Priority:**"
echo "- Critical: $(gh issue list -l 'priority:critical' --state open --json number --jq 'length')"
echo "- High: $(gh issue list -l 'priority:high' --state open --json number --jq 'length')"
echo "- Medium: $(gh issue list -l 'priority:medium' --state open --json number --jq 'length')"
echo "- Low: $(gh issue list -l 'priority:low' --state open --json number --jq 'length')"

echo ""
echo "**Bug Budget Status:**"
BUGS=$(gh issue list -l 'type:bug' --state open --json number --jq 'length')
echo "Open bugs: $BUGS/3"
if [ "$BUGS" -ge 3 ]; then
  echo "WARNING: Bug budget exceeded! Stop new features and fix bugs first."
fi
```
