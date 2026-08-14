# Workflow Improvement Prompt — Portable for All Projects

**Context:** This prompt describes improvements to a GitHub issue-based development workflow (10-phase: backlog → refining → designing → tests-writing → developing → tea-testing → deployment → human-review → docs-update → done). These changes were identified through systematic analysis of recurring failures across projects. Apply to any project using this workflow system.

---

## Problem Statement

The following recurring problems waste human review time and cause unnecessary back-and-forth:

1. **"Not deployed" false positives** — Items reach human review but the service isn't running. Human opens the app, sees nothing changed, rejects. Repeat.
2. **Tests that don't actually test** — Phase 3 (tests writing) creates tests, but nobody verifies they *fail* before implementation. Tests that pass vacuously prove nothing.
3. **No automated deploy verification** — Between deployment and human review, nothing confirms the code is actually live. The human becomes the deploy verification tool.
4. **Rejections don't improve the system** — When an item is rejected, the same class of bug can happen again because no test gap analysis is performed.
5. **Quick workflow skips all gates** — Typo fixes bypass testing entirely, but still require human review. Even trivial changes should verify deployment.
6. **Hardcoded project references** — URLs and repo names from other projects leak into workflow commands.
7. **Acceptance criteria aren't machine-verifiable** — Prose descriptions can't be automated. Gherkin-style (Given/When/Then) format enables future automation.

---

## Changes to Apply

### 1. Deploy Verification Gate (Phase 6)

**Add to `/wf:deploy` and `/wf:review`:**

Every deployable service must expose:
- `GET /health` → returns 200 OK when service is running
- `GET /version` → returns `{ "commit": "<sha>", "version": "<semver>", "built": "<iso8601>" }`

After deployment, before advancing to human review:
```bash
# Hit health endpoint
curl -sf "http://$TARGET_HOST:$TARGET_PORT/health"

# Hit version endpoint, compare commit SHA
DEPLOYED_COMMIT=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/version" | jq -r '.commit')
```

**If health check fails → auto-reject all items back to phase:4-developing.** No human review triggered. Comment on issue with diagnostic details.

**If version mismatch → warn but proceed** (version endpoint is recommended, not blocking in v1).

### 2. Red Phase Verification (Phase 3)

**Add to `/wf:issue` Phase 3 step:**

After writing tests, **run them and verify they FAIL**:
```bash
npm run test -- --run tests/issue-[NUMBER]-[slug].spec.ts 2>&1 | tail -20
# If tests PASS → they are not testing the unimplemented feature. Fix tests.
# Only advance to phase 4 when tests produce FAILURES.
```

Add comment to issue: "Tests written and verified failing (red phase). X tests, all failing as expected."

### 3. Test Gap Analysis on Rejection (Phase 7 deny)

**Add to `/wf:deny`:**

When rejecting an issue, append a test gap analysis checklist:
```markdown
**Test Gap Analysis:**
This rejection indicates a gap in automated verification. Before re-implementing:
- [ ] Was this caught by any existing test? If not, why?
- [ ] Should a new test be added to prevent this specific failure?
- [ ] Was the deploy verification gate running? Did it pass?
- [ ] Is the acceptance criteria specific enough to test automatically?

**Action required:** Fix the issue, add a test that would have caught this, then re-run.
```

### 4. Quick Workflow Still Verifies Deployment

**Change `/wf:issue` quick workflow:**

Quick workflow (typos, one-liners, CSS < 10 lines):
- Still skips phases 1-3 (refining, designing, tests)
- Still requires phase 5 (run existing test suite — no regressions)
- **Still requires deploy verification gate** (health + version check)
- Phase 7 human review only triggers if deploy verification passes

### 5. Gherkin-Style Acceptance Criteria

**Change issue template in `/wf:issue`:**

Replace prose ACs:
```markdown
## Success Criteria
- [ ] Button should be blue
- [ ] It should work on mobile
```

With Gherkin format:
```markdown
## Success Criteria (Gherkin-style)
- [ ] Given [the settings page is open], when [user clicks save], then [settings are persisted and confirmation toast appears]
- [ ] Given [mobile viewport (375px)], when [page loads], then [all controls are accessible without horizontal scroll]
```

### 6. Verification Commands in Issue Template

**Add to issue template in `/wf:issue`:**

```markdown
## Verification Commands
```bash
# Commands to verify this issue is complete (run after deploy)
curl -s http://TARGET_HOST:PORT/health | jq .status
curl -s http://TARGET_HOST:PORT/version | jq .commit
# Additional verification commands specific to this issue
```
```

### 7. Definition of Done Checklist

**Add to issue template in `/wf:issue`:**

```markdown
## Definition of Done
- [ ] Tests written and verified failing (red phase)
- [ ] Implementation passes all tests (green phase)
- [ ] Deploy verification gate passes (health + version endpoint)
- [ ] No regressions in existing tests
- [ ] Human review approved
```

### 8. Fix Hardcoded References

**Audit all `/wf:*.md` files for:**
- Hardcoded URLs from other projects (e.g., `poc.habitarcade.com`)
- Hardcoded GitHub repo paths (e.g., `mgerasolo/habitarcade-poc`)
- Replace with project-specific values or environment variables

---

## Implementation Checklist

For each project using this workflow:

- [ ] Add `GET /health` and `GET /version` endpoints to every deployable service
- [ ] Update `/wf:deploy` to include deploy verification gate
- [ ] Update `/wf:review` to run deploy verification before listing items
- [ ] Update `/wf:issue` Phase 3 to verify tests fail before advancing
- [ ] Update `/wf:issue` template with Gherkin ACs, verification commands, Definition of Done
- [ ] Update `/wf:deny` to include test gap analysis
- [ ] Update `/wf:help` to document the gates
- [ ] Update `/wf:dash` to use correct repo URL
- [ ] Audit all `/wf:*.md` for hardcoded project references
- [ ] Update quick workflow to still require deploy verification

---

## Guiding Principle

> **Every human review rejection is a system failure.** If the human caught something, automation should have caught it first. The goal is not zero rejections (humans verify UX, product fit, aesthetics) — the goal is zero rejections for things automation can verify (service running, code deployed, tests passing, contracts met).
