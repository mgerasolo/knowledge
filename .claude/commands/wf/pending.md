---
description: List all items awaiting human approval with details on what to test
allowed-tools: Bash(gh issue list:*), Bash(gh issue view:*)
---

# Pending Human Approval

List all issues awaiting human review and approval.

## Query

Find issues with:
- `phase:7-human-review` label
- `awaiting:human-approval` label
- `needs:verification` label (legacy)

## Execute

```bash
echo "## Items Pending Human Approval"
echo ""

# Check for items with awaiting:human-approval
gh issue list -l "awaiting:human-approval" --json number,title,body --jq '.[] | "### #\(.number) - \(.title)\n\(.body | split("\n")[0:3] | join("\n"))\n"' 2>/dev/null

# Check for items in phase:7-human-review
gh issue list -l "phase:7-human-review" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null

# Check for legacy needs:verification
echo ""
echo "### Legacy (needs:verification):"
gh issue list -l "needs:verification" --json number,title --jq '.[] | "#\(.number): \(.title)"' 2>/dev/null | head -20

echo ""
echo "---"
echo "Use \`/wf:approve #\` or \`/wf:deny # {reason}\` to process."
```

## Response Format

For each item, show:
- Issue number and title
- Brief summary of what changed
- What to test in the web app
