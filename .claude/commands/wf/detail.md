---
description: Show full details of an issue including location, context, and history
argument-hint: [issue-number]
allowed-tools: Bash(gh issue view:*), Bash(gh issue list:*)
---

# Issue Detail View

Show comprehensive details for an issue to understand exactly what needs to be done and where.

## Arguments

- Issue number (required)

## Execute

```bash
ISSUE=$ARGUMENTS

echo "=============================================="
echo "ISSUE #$ISSUE - FULL DETAILS"
echo "=============================================="
echo ""

# Get full issue details
gh issue view $ISSUE

echo ""
echo "=============================================="
echo "LABELS"
echo "=============================================="
gh issue view $ISSUE --json labels --jq '.labels[].name' | sort

echo ""
echo "=============================================="
echo "COMMENTS & HISTORY"
echo "=============================================="
gh issue view $ISSUE --comments
```

## After Viewing

If the issue is missing critical information, prompt to update it:

### Required Context (check if present):

1. **Location** - Where in the app?
   - Page/Route (e.g., `/dashboard`, `/manage/quotes`, `/settings`)
   - Component (e.g., "Habit Matrix widget", "Right sidebar", "Header")
   - Specific element (e.g., "the save button", "row hover menu", "icon picker")

2. **Current Behavior** - What happens now?

3. **Expected Behavior** - What should happen?

4. **Visual Reference** - Screenshot or mockup (if UI-related)

### If Missing Location Info

Suggest adding a comment or updating the issue body:

```bash
gh issue comment $ISSUE --body "## Location Details
- **Page:** [route/page name]
- **Component:** [widget/section name]
- **Element:** [specific UI element]

## Steps to Reproduce
1. Navigate to [page]
2. [action]
3. [action]

## Screenshot
[attach if available]"
```

### Offer to Update

After showing details, ask:
"Does this issue have clear location/context? Would you like me to:
1. Add location details based on my understanding
2. Ask clarifying questions
3. Mark as needs-clarification"
