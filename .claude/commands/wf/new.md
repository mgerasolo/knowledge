---
description: Create a new GitHub issue and drive it through phase 3 (alias for /wf:issue)
argument-hint: <description of what you want to build or fix>
---

# Create New Issue

**This is an alias for `/wf:issue`** - both commands do the same thing.

Execute the full `/wf:issue` workflow:

1. **Clarification Gate** - Ensure 95%+ clarity on requirements
2. **Create Issue** - With proper labels and structure
3. **Phase 1: Refining** - Analyze and document requirements
4. **Phase 2: Designing** - Technical approach
5. **Phase 3: Tests Writing** - Write failing tests (TDD)
6. **Ask User** - Continue to implementation or stop?

---

## Quick Start

From the user's input in $ARGUMENTS, determine:

1. **What type?** Bug, Feature, Enhancement, or Docs
2. **What priority?** Based on impact and urgency
3. **What area?** UI, API, Database, Auth
4. **Quick or Full?** Quick only for typos/one-liners/tiny CSS

**If unclear, ASK:**
- "What problem are you solving?"
- "What does success look like?"
- "What should NOT change?"

---

## Create Issue

```bash
gh issue create \
  --title "[Clear title from $ARGUMENTS]" \
  --body "## Problem
[Extracted from user input]

## Location
- **Page:** [route or page name, e.g., /dashboard, /manage/quotes]
- **Component:** [widget or section, e.g., Habit Matrix, Right Sidebar]
- **Element:** [specific UI element, e.g., save button, row hover menu]

## Current vs Expected
- **Current:** [what happens now]
- **Expected:** [what should happen]

## Success Criteria
- [ ] [AC 1]
- [ ] [AC 2]
- [ ] [AC 3]

## Constraints
[What should NOT change]" \
  --label "phase:0-backlog" \
  --label "type:[type]" \
  --label "priority:[priority]" \
  --label "area:[area]" \
  --label "workflow:[full|quick]"
```

---

## Then Drive Through Phases

After creation, immediately progress through:

### Phase 1 → 2 → 3

For each phase, update labels and do the work:
- **Phase 1 (Refining):** Validate ACs are testable
- **Phase 2 (Designing):** Identify files, add technical comment
- **Phase 3 (Tests):** Write failing tests in `tests/issue-{num}-{slug}.spec.ts`

### Then Ask User

Once at phase 4 (ready for dev), ask:

"Issue #{NUMBER} has failing tests ready. Continue implementation now, or queue for later?"

---

## Bug Budget Check

Before creating new feature/enhancement issues, check bug count:
```bash
bug_count=$(gh issue list -l "type:bug" --state open --json number --jq 'length')
if [ $bug_count -gt 3 ]; then
  echo "⚠️ Bug budget exceeded ($bug_count/3). Fix bugs before new features."
fi
```

If bugs > 3 and this is a feature/enhancement, warn the user but allow override.
