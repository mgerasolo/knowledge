---
description: Show current workflow status across all phases with issue counts
allowed-tools: Bash(gh issue list:*)
---

# Workflow Status

Show the current workflow status by querying GitHub for issues in each phase.

## Steps

1. Query issues by phase label
2. Count bugs for bug budget check
3. Check for test failures
4. Display summary table

## Execute

Run these commands to gather status:

```bash
echo "## Workflow Status"
echo ""
echo "| Phase | Count | Issues |"
echo "|-------|-------|--------|"

for phase in "phase:0-backlog" "phase:1-refining" "phase:2-designing" "phase:3-tests-writing" "phase:4-developing" "phase:5-tea-testing" "phase:6-deployment" "phase:7-human-review" "phase:8-docs-update"; do
  issues=$(gh issue list -l "$phase" --json number --jq '.[].number' 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
  count=$(gh issue list -l "$phase" --json number --jq 'length' 2>/dev/null)
  echo "| ${phase#phase:} | ${count:-0} | ${issues:-none} |"
done

echo ""
echo "**Bug Budget:** $(gh issue list -l 'type:bug' --state open --json number --jq 'length')/3"
echo "**Needs Verification:** $(gh issue list -l 'needs:verification' --json number --jq 'length') items"
```
