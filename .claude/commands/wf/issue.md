---
description: Create a new GitHub issue and drive it through phase 3 (tests written)
argument-hint: <description of what you want to build or fix>
---

# Create New Issue (Full Workflow)

This command creates a new GitHub issue and drives it through the early workflow phases.

## Process Overview

1. **Clarification Gate** - Ensure requirements are crystal clear (95%+ clarity)
2. **Create Issue** - With proper labels and structure
3. **Phase 1: Refining** - Analyze and document requirements
4. **Phase 2: Designing** - Technical approach (if needed)
5. **Phase 3: Tests Writing** - Write failing tests (TDD red phase)
6. **Ask User** - Continue to implementation or stop?

---

## Step 1: Clarification Gate

Before proceeding, ensure you understand:

**Required Information:**
- What is the problem/feature? (from $ARGUMENTS)
- What type? Bug, Feature, Enhancement, or Docs
- What priority? Critical, High, Medium, or Low
- What area? UI, API, Database, Auth

**If clarity < 95%, ASK the user:**
1. "What problem are you solving?"
2. "What does success look like?"
3. "What should NOT change?"

**AC Split Rule:** If more than 3 acceptance criteria are needed, inform the user and suggest splitting into multiple issues.

---

## Step 2: Create the Issue

Determine the appropriate labels:
- **workflow:quick** - Only for: typos, one-liners, config changes, CSS < 10 lines
- **workflow:full** - Everything else (features, bugs, enhancements)

Create with this structure:

```bash
gh issue create \
  --title "[Clear, actionable title]" \
  --body "## Problem
[What problem this solves or what's broken]

## Location
- **Page:** [route or page name, e.g., /dashboard, /manage/quotes]
- **Component:** [widget or section, e.g., Habit Matrix, Right Sidebar]
- **Element:** [specific UI element, e.g., save button, row hover menu]

## Current vs Expected
- **Current:** [what happens now]
- **Expected:** [what should happen]

## Success Criteria
- [ ] [Testable AC 1]
- [ ] [Testable AC 2]
- [ ] [Testable AC 3]

## Constraints
[What should NOT change]

## Technical Notes
[Any implementation hints]" \
  --label "phase:0-backlog" \
  --label "type:[bug|feature|enhancement|docs]" \
  --label "priority:[critical|high|medium|low]" \
  --label "area:[ui|api|database|auth]" \
  --label "workflow:[full|quick]"
```

After creating, immediately update to phase 1:
```bash
gh issue edit [NUMBER] --remove-label "phase:0-backlog" --add-label "phase:1-refining"
```

---

## Step 3: Phase 1 - Refining (Analyst)

As the Analyst agent, review and refine the issue:
- Ensure acceptance criteria are testable and specific
- Add any missing edge cases
- Clarify any ambiguous requirements
- Update the issue body if needed

When complete:
```bash
gh issue edit [NUMBER] --remove-label "phase:1-refining" --add-label "phase:2-designing"
```

---

## Step 4: Phase 2 - Designing (Architect)

As the Architect agent, determine technical approach:
- Identify files that need changes
- Note any architectural considerations
- For simple changes, this phase can be brief

Add a comment with the technical approach:
```bash
gh issue comment [NUMBER] --body "## Technical Approach
- Files to modify: [list]
- Approach: [brief description]
- Risks: [any concerns]"
```

When complete:
```bash
gh issue edit [NUMBER] --remove-label "phase:2-designing" --add-label "phase:3-tests-writing"
```

---

## Step 5: Phase 3 - Tests Writing (TEA)

As the TEA agent, write failing tests:
- Create test file: `tests/issue-[NUMBER]-[slug].spec.ts`
- Tests should fail (TDD red phase)
- Cover all acceptance criteria

When tests are written:
```bash
gh issue edit [NUMBER] --remove-label "phase:3-tests-writing" --add-label "phase:4-developing"
```

---

## Step 6: Ask User

After reaching phase 4, ask the user:

"Issue #[NUMBER] is ready for development with failing tests in place.

**Options:**
1. **Continue now** - I'll implement the feature and run through remaining phases
2. **Stop here** - Issue is queued for later development

What would you like to do?"

If user chooses to continue, proceed with:
- Phase 4: Development (implement to make tests pass)
- Phase 5: TEA Testing (run tests, verify)
- Phase 6: Deployment (if tests pass)
- Phase 7: Human Review (ask user to verify via web)

---

## Quick Workflow Override

For `workflow:quick` issues (typos, one-liners, CSS < 10 lines):
- Skip phases 1-3
- Go directly from creation to phase 4
- Still require phases 5-7 (testing, deploy, review)
