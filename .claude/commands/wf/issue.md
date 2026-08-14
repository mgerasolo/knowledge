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
4. **Phase 2: Designing** - Technical approach + contract schemas
5. **Phase 3: Tests Writing** - Write failing tests (TDD red phase) + VERIFY THEY FAIL
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

## Success Criteria (Gherkin-style)
- [ ] Given [precondition], when [action], then [result]
- [ ] Given [precondition], when [action], then [result]
- [ ] Given [precondition], when [action], then [result]

## Constraints
[What should NOT change]

## Verification Commands
\`\`\`bash
# Commands to verify this issue is complete (run after deploy)
curl -s http://TARGET_HOST:PORT/health | jq .status
curl -s http://TARGET_HOST:PORT/version | jq .commit
# Additional verification commands specific to this issue
\`\`\`

## Definition of Done
- [ ] Tests written and verified failing (red phase)
- [ ] Implementation passes all tests (green phase)
- [ ] Deploy verification gate passes (health + version endpoint)
- [ ] No regressions in existing tests
- [ ] Human review approved

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
- Ensure acceptance criteria are testable and in Gherkin format (Given/When/Then)
- Add any missing edge cases
- Clarify any ambiguous requirements
- Add verification commands specific to this issue
- Update the issue body if needed

When complete:
```bash
gh issue edit [NUMBER] --remove-label "phase:1-refining" --add-label "phase:2-designing"
```

---

## Step 4: Phase 2 - Designing (Architect)

As the Architect agent, determine technical approach:
- Identify files that need changes
- **Define contract schemas** (zod types for any API boundaries touched)
- Note any architectural considerations
- For simple changes, this phase can be brief

Add a comment with the technical approach:
```bash
gh issue comment [NUMBER] --body "## Technical Approach
- Files to modify: [list]
- Contract schemas: [list any zod schemas to define/update]
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
- Include contract validation tests if API boundaries are involved

**CRITICAL: Verify tests actually FAIL before advancing.**

```bash
# Run the tests and confirm they fail
npm run test -- --run tests/issue-[NUMBER]-[slug].spec.ts 2>&1 | tail -20

# If tests PASS, they are not testing anything real — fix them
# Only advance to phase 4 when tests produce RED (failures)
```

When tests are written AND verified failing:
```bash
gh issue edit [NUMBER] --remove-label "phase:3-tests-writing" --add-label "phase:4-developing"
gh issue comment [NUMBER] --body "Tests written and verified failing (red phase). X tests, all failing as expected."
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
- Phase 5: TEA Testing (run full test suite + deploy verification)
- Phase 6: Deployment (deploy + run deploy verification gate)
- Phase 7: Human Review (only if deploy verification passes)

---

## Quick Workflow Override

For `workflow:quick` issues (typos, one-liners, CSS < 10 lines):
- Skip phases 1-3
- Go directly from creation to phase 4
- Still require phase 5 (testing) and phase 6 (deploy verification)
- **Quick does NOT skip deploy verification** — still requires health + version check
- Phase 7 (human review) only if deploy verification passes
