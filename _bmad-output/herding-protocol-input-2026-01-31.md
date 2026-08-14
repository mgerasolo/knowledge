# Herding Protocol Input — Lessons from KnowledgeStack

**Source Project:** KnowledgeStack (knowledge)
**Date:** 2026-01-31
**Context:** Discovered during project-context.md generation (BMAD Party Mode, 8 rounds of multi-agent discussion). These are systemic problems and solutions that apply to all NLF projects using the /wf workflow system and Claude Code.

---

## Lesson 1: Deploy Verification Gate

**Problem:** Items reach human review but the service isn't deployed. Matt opens the app, sees nothing changed, rejects. This cycle repeats constantly — "I'm finding myself having to constantly do the human approval just to reject it because it's not even deployed."

**Solution:** Every deployable service exposes `GET /health` (200 OK) and `GET /version` (returns `{ commit, version, built }`). After deployment, before advancing to human review, the workflow hits these endpoints. If health check fails → auto-reject back to development. No human review triggered.

**Applies to:** All projects with /wf workflow system
**Files to update:**
- `/wf:deploy` — Add health + version check after deployment. Auto-reject on failure.
- `/wf:review` — Run verification gate before listing items for human review. Auto-reject if not deployed.
- `/wf:help` — Document the gate.
- Application code — Add `/health` and `/version` endpoints to every deployable service.

**Implementation pattern:**
```bash
# After deploy, before advancing to human review
HEALTH=$(curl -sf "http://$TARGET_HOST:$TARGET_PORT/health" 2>/dev/null)
if [ $? -ne 0 ]; then
  # Auto-reject all items back to phase:4-developing
  # Comment on issue with diagnostic details
fi
```

---

## Lesson 2: Red Phase Verification (Phase 3 Gate)

**Problem:** Phase 3 (tests writing) creates tests but nobody verifies they actually fail. Tests that pass before implementation are vacuously true — they don't test anything.

**Solution:** After writing tests in Phase 3, run them and verify they FAIL before advancing to Phase 4 (development). Add a comment to the issue confirming red state.

**Applies to:** All projects using TDD in /wf workflow
**Files to update:**
- `/wf:issue` — Phase 3 step must include test execution and failure verification

---

## Lesson 3: Test Gap Analysis on Rejection

**Problem:** When items are rejected in human review, the same class of bug can happen again because no analysis is performed on why tests didn't catch it.

**Solution:** Every `/wf:deny` rejection appends a test gap analysis checklist to the issue:
- Was this caught by any existing test?
- Should a new test be added?
- Was the deploy verification gate running?
- Is the acceptance criteria specific enough to test automatically?

**Principle:** Every human rejection is a system failure. If automation could have caught it, add a test so it does next time.

**Applies to:** All projects using /wf workflow
**Files to update:**
- `/wf:deny` — Add test gap analysis checklist to rejection comment

---

## Lesson 4: Quick Workflow Still Verifies Deployment

**Problem:** Quick workflow (typos, one-liners) skips all testing gates, but still requires human review. Even trivial changes should verify they're actually deployed.

**Solution:** Quick workflow skips phases 1-3 (refining, designing, tests) but still requires deploy verification gate. No human review unless the health endpoint responds.

**Applies to:** All projects using /wf workflow
**Files to update:**
- `/wf:issue` — Quick workflow override section

---

## Lesson 5: Gherkin-Style Acceptance Criteria

**Problem:** Prose acceptance criteria ("button should be blue") can't be automated and are ambiguous. Different AI agents interpret them differently.

**Solution:** All acceptance criteria use Given/When/Then format:
```
Given [the settings page is open], when [user clicks save], then [settings are persisted and confirmation toast appears]
```

Also add: Verification Commands (curl commands to run post-deploy) and Definition of Done checklist to every issue.

**Applies to:** All projects using /wf workflow
**Files to update:**
- `/wf:issue` — Issue template

---

## Lesson 6: Hardcoded Project References

**Problem:** WF commands contained hardcoded URLs and repo names from a previous project (poc.habitarcade.com, mgerasolo/habitarcade-poc). These leaked into issue comments and dashboard links.

**Solution:** Audit all `/wf:*.md` files for hardcoded references. Use project-specific values or environment variables.

**Applies to:** Any project that copied /wf commands from another project
**Action:** Audit and replace in all projects

---

## Lesson 7: 6-Layer Verification Architecture

**Problem:** Playwright was being used as the first line of defense for testing. It kept saying code exists when it clearly wasn't deployed. Playwright is too high-level and too fragile to be the primary verification tool.

**Solution:** 6-layer verification pyramid (cheapest/fastest first):
1. Container health — Docker HEALTHCHECK + Uptime Kuma
2. Service availability — HTTP 200 on health/version endpoints (supertest)
3. API contract integrity — zod schema validation on request/response
4. Pipeline data integrity — Vitest unit tests on business logic
5. Production smoke — post-deploy script verifies version endpoint
6. UI workflows — Playwright LAST, for critical user flows only

**Applies to:** All projects with automated testing
**Principle:** Catch issues at the cheapest layer. Don't use a browser to check if a server is running.

---

## Lesson 8: PR-Scoped Conversations

**Problem:** Long-running conversations compact and lose critical context. Matt tends to keep using the same conversation for everything, leading to context window exhaustion and lossy summarization.

**Solution:** One branch → one PR → one Claude Code conversation → one concern. When the PR merges, the conversation is done. Context never grows beyond what one feature needs.

**Applies to:** All projects using Claude Code
**Requires:**
- Git worktrees for parallel work (each conversation gets its own directory)
- Conversation naming convention: `#42-enroll-rss-monitor`
- State files that persist context between conversations (see Lessons 9-11)

---

## Lesson 9: Per-Product CURRENT-STATE.md (Baton Enhancement)

**Problem:** PR-scoped conversations solve compaction but break context continuity. Feature C depends on B which depended on A, but C's conversation doesn't know what happened in A or B.

**Solution:** Each product (or project) maintains a `CURRENT-STATE.md` file — a living baton passed between conversations. Updated as the last act before closing a conversation.

**Contents:**
- What's implemented (with PR references)
- Recent history (last 3-5 PRs with key decisions)
- Known issues / deferred items
- Dependencies on other products/components
- What's next
- Last conversation's final status block

**Applies to:** All projects using Claude Code, especially multi-component projects
**Location:** `packages/{product}/CURRENT-STATE.md` for multi-product; project root for single-product

---

## Lesson 10: ACTIVE-WORK.md (Parallel Conversation Coordination)

**Problem:** Matt runs 3-5 Claude Code conversations simultaneously on the same project. They step on each other's files, create merge conflicts, and Matt loses track of which window is doing what.

**Solution:** A `docs/ACTIVE-WORK.md` registry where each conversation registers itself on startup and deregisters on shutdown:

```markdown
| Issue | Product | Branch | Worktree | Started |
|-------|---------|--------|----------|---------|
| #42 | enroll | feature/42-... | enroll-rss-42 | 2026-02-15 |
| #44 | ops | feature/44-... | ops-health-44 | 2026-02-15 |
```

When starting, AI reads ACTIVE-WORK.md. If another conversation is modifying the same area → warn. If another conversation owns the target product and scope drift is detected → offer to route the work there.

**Applies to:** Any project where Matt runs parallel conversations
**Requires:** Git worktrees (one physical directory per conversation)

---

## Lesson 11: INTEGRATION-STATUS.md (Cross-Product Dependencies)

**Problem:** In multi-product projects, conversations working on one product don't know what other products have implemented, what contracts exist, or what APIs are available.

**Solution:** A `docs/INTEGRATION-STATUS.md` tracking:
- Per-product readiness status
- Cross-product dependencies (what's blocking what)
- Shared infrastructure (which patterns are available)
- Contract schemas defined

**Applies to:** Multi-product/multi-component projects

---

## Lesson 12: Scope Drift Detection (Per-Conversation)

**Problem:** Conversations silently expand scope. Matt says "while we're at it" and suddenly a bug fix conversation is implementing a new feature. With parallel conversations, this is especially dangerous because the scope expansion might conflict with another conversation's work.

**Solution:** Every implementation conversation establishes a scope anchor at startup (issue #, product, branch, ACs, authorized directories). The AI monitors every message against this anchor. When drift is detected:

```
⚠️ SCOPE CHECK: This sounds outside this conversation's scope.
This conversation: #42 — KnowledgeEnroll RSS Monitor
Proposed work: packages/ops/

Options:
1. [Handoff] — Update state files, generate handoff summary for new conversation
2. [Backlog] — Create GitHub issue, stay focused on current work
3. [Route to active] — Conversation #44 is working on KnowledgeOps. Add there?
4. [Continue] — Override, proceed but log scope expansion
```

**Key: scope check is per-conversation, not per-project.** Five conversations may run simultaneously — each guards its own boundaries.

**Applies to:** All projects using Claude Code

---

## Lesson 13: Commit Guardrails

**Problem:** In parallel conversations, uncommitted work is risky. One conversation merges to main while another has uncommitted changes → painful merge conflicts. Also, Matt sometimes loses work when a conversation goes stale.

**Solution:** AI prompts for commits at natural checkpoints:
- After completing a logical unit (function, schema, test)
- Before switching concerns within an issue
- Before running tests
- Before any destructive operation
- After ~15 minutes of active work without a commit

Non-blocking prompt with auto-suggested commit message using Conventional Commits format.

**Applies to:** All projects

---

## Lesson 14: n8n Workflow Version Control

**Problem:** n8n workflows live in n8n's database, not in git. Claude Code writes a workflow JSON, Matt manually imports it via n8n UI. No guarantee the running version matches git. Manual copy is error-prone and wasteful.

**Solution:** Version-control n8n workflows in repo:
```
n8n-workflows/{product}-{purpose}/
  workflow.json       # The actual workflow definition
  README.md           # What it does, triggers, dependencies
  metadata.json       # n8n instance ID, last deployed commit
```

Deploy via n8n REST API (`PUT /api/v1/workflows/:id`) using a deploy script. Claude Code calls the script directly. `metadata.json` tracks deployed version. Deploy verification compares `lastDeployedCommit` against HEAD.

**Applies to:** All projects using n8n
**Requires:** n8n API key configured, deploy script in project

---

## Lesson 15: Standardized Response Format Enhancement

**Problem:** The existing Standardized Response Format (in CLAUDE.md) works for single-conversation tracking but breaks in parallel conversations. The status block often refers to a stale request from several messages ago, and it's buried in walls of output.

**Solution:**
1. **Response footer** — Short status block at the BOTTOM of every response. Shows what was completed THIS response, what's next, and context %. Max 8 lines.
2. **Conversation checkpoint** — On-demand (`status`) or every ~5 responses. Tracks progress against the issue's acceptance criteria. Shows files modified, branch status, time active.
3. **Scope identity in header** — Issue #, product, branch visible in every status block so Matt can distinguish windows at a glance.
4. **Context % as break signal** — At 60%+ context usage, append warning to wrap up.

**Applies to:** All projects using Claude Code

---

## Lesson 16: Cross-Project Lesson Capture

**Problem:** This very list. When a project discovers improvements (like all 15 lessons above), there's no structured way to propagate them to other projects. Matt manually creates portable prompts or copies files.

**Solution:** Formalized lesson capture system:
- **Capture triggers:** AI detects cross-project insights (modifying /wf commands, adding conventions not from templates, fixing recurring frustrations)
- **Lesson files:** Standardized format in `~/Infrastructure/lessons/` with problem, solution, affected files, and diff-friendly change blocks
- **Consumption:** New conversations check for unapplied lessons at startup
- **Propagation:** `/wf:audit` shows pending propagation; generates update prompts per project

**Applies to:** The Infrastructure project itself — this IS the herding protocol

---

---

## ADDENDUM: Refined Conversation Management (Party Mode Round 2, 7 Rounds)

**Date:** 2026-01-31
**Source:** Party Mode session with Amelia (Dev), Winston (Architect), Paige (Tech Writer) — 7 rounds refining conversation management, active-work patterns, and /sidebar design. Plus Claude Code hooks research (16 GitHub repos, 28 sources).

**Supersedes:** Lesson 10 (ACTIVE-WORK.md) is replaced by Lesson 17 below. Lesson 12 (Scope Drift Detection) is enhanced by Lesson 18.

---

## Lesson 17: Per-Conversation State Directories (Replaces Lesson 10)

**Problem:** The original ACTIVE-WORK.md design (Lesson 10) has a fatal flaw: multiple conversations writing to a single shared file causes race conditions and overwrites. Matt runs 3-5 conversations simultaneously — any shared-write file becomes a corruption vector.

**Solution:** Each conversation owns its own state directory under `.claude/active/`:

```
.claude/active/
  enroll-rss-pipeline/
    state.json          # Stack, scope, issues, metadata
    heartbeat           # Timestamp file — touched on every AI response
  ops-health-endpoints/
    state.json
    heartbeat
  sidebar-88-update-cli/
    state.json
    heartbeat
```

**Design invariant:** No file is written by multiple conversations simultaneously. Each conversation creates, owns, reads, and deletes only its own directory. Cross-conversation awareness is achieved through read-time aggregation (glob + parse), not shared writes.

**state.json schema:**
```json
{
  "slug": "enroll-rss-pipeline",
  "sessionId": "sess_a7f3b2c1",
  "type": "feature",
  "product": "enroll",
  "branch": "feature/42-rss-monitor",
  "issues": [42, 43],
  "primaryIssue": 42,
  "parentIssue": null,
  "scope": ["packages/enroll/", "packages/contracts/", "n8n-workflows/enroll-*"],
  "stack": [
    { "task": "RSS pipeline integration", "status": "paused", "pausedAt": "wrote failing test", "type": "root" },
    { "task": "Schema migration", "status": "active", "type": "detour", "reason": "RSS requires updated schema" }
  ],
  "startedAt": "2026-02-15T14:30:00Z",
  "learnings": null,
  "sidebarsSpawned": [88]
}
```

**Heartbeat:** `touch .claude/active/{slug}/heartbeat` on every AI response. If heartbeat > 2 hours old and issue still open, session is likely abandoned. Other conversations clean stale entries on startup.

**Gitignore:** `.claude/active/` is ephemeral (gitignored). Durable state is CURRENT-STATE.md, INTEGRATION-STATUS.md, and LEARNINGS.md (committed).

**Applies to:** All projects using Claude Code with parallel conversations

---

## Lesson 18: Three-Mode Scope Model (Enhances Lesson 12)

**Problem:** Lesson 12's binary scope check (in-scope / out-of-scope) misses the critical distinction between blocking dependencies and unrelated tangents. Real conversation patterns flow like: A → discovers need for C (blocks A) → C completes → back to A → discovers D → D needs E and F → eventually back to A. Some forks are necessary (blocking), others are dangerous (unrelated).

**Solution:** Every piece of work is classified into one of three modes:

| Mode | Definition | Test | Action |
|------|-----------|------|--------|
| **On-stack** | Current task or ancestor | Default state | Continue working |
| **Detour** | Blocking dependency | "I need X before I can finish Y" → dependency arrow exists | Push to work stack, track return point |
| **Drift** | Unrelated work | No dependency arrow to anything on stack | Warn with 4 options |

**The distinction test:** Can you draw a dependency arrow from the new work back to something on the stack? Yes = detour (stay). No = drift (warn).

**Work Stack (Per-Conversation):**
```
WORK STACK:
→ [ACTIVE]  Schema migration for enroll-channel (detour)
  [PAUSED]  RSS pipeline integration (paused at: wrote failing test, need schema)
```

When active item completes, AI explicitly resumes paused item with context: "Schema migration complete. Returning to RSS pipeline. We paused after writing the failing test — the schema unblocks implementation."

**Nesting Rules:**
- Root task: always
- 1 detour deep: always
- 2 detours deep: allowed with warning
- 3+ detours deep: not allowed — sidebar or backlog the deepest item

**Drift Detection Triggers:**
- Touching files outside scope anchor's authorized directories
- Implementing features not in acceptance criteria
- "While we're at it" / "we should also" / "let me quickly"
- Work for a different product than scope anchor's product

**Drift Options (4 choices):**
1. `/sidebar` — Create sidebar issue, paste prompt for new tab
2. `Backlog` — Create GitHub issue, stay focused here
3. `Route` — Another active conversation is working on that area, route there
4. `Continue` — Override scope check, log expansion

**Applies to:** All projects using Claude Code

---

## Lesson 19: /sidebar Command — Conversation Fork Protocol

**Problem:** When a conversation discovers non-blocking related work, there's no structured way to hand it off to a new conversation. Matt opens a new tab and loses all context about WHY the work was needed, WHERE it came from, and WHAT results to report back.

**Solution:** `/sidebar <description>` command that creates a GitHub issue with full context and outputs a paste prompt for a new Claude Code tab.

**The /sidebar command:**
1. AI creates GitHub issue with `sidebar` + `active-work` labels
2. Issue contains: parent issue reference, parent branch, trigger context, complexity estimate, task description, acceptance criteria, sidebar protocol checklist
3. AI outputs paste prompt for new tab: "Pick up sidebar issue #88. Read the issue for full context. Register in .claude/active/ on startup. When done: comment results on #88, comment summary on parent #42, deregister, close #88."
4. Matt pastes into new tab → sidebar conversation self-manages

**Sidebar Conversation Lifecycle:**
1. Read issue for context
2. Register in `.claude/active/sidebar-{issue}-{slug}/state.json`
3. Do work within defined scope
4. Comment results on sidebar issue
5. Comment summary on parent issue
6. Delete `.claude/active/` directory
7. Remove `active-work` label, add `sidebar-complete`
8. Close sidebar issue

**Key rules:**
- Sidebar conversations cannot spawn sub-sidebars (one fork level, then backlog)
- Sidebar type has stricter scope enforcement + max 2-deep detour limit
- Parent conversation checks for completed sidebars on startup or when Matt asks

**Full design:** See `_bmad-output/analysis/sidebar-command-design-2026-01-31.md` (485 lines)

**Applies to:** All projects using Claude Code with parallel conversations

---

## Lesson 20: Conversation Types Drive Behavior

**Problem:** Not all conversations should have the same rules. A planning session that's cross-cutting by nature shouldn't trigger scope drift warnings. A sidebar should be even stricter than a feature.

**Solution:** Four conversation types with different behavior profiles:

| Type | Scope enforcement | Can spawn sidebars | Detour limit |
|------|------------------|-------------------|--------------|
| `feature` | Strict — drift detection active | Yes | 3 deep |
| `sidebar` | Strictest — tighter than feature | No — creates backlog issues instead | 2 deep |
| `planning` | Relaxed — cross-cutting by nature | Yes | No limit |
| `bugfix` | Strict | Yes | 2 deep |

The conversation type is stored in `state.json` and influences which rules the AI applies.

**Applies to:** All projects using Claude Code

---

## Lesson 21: Self-Healing Peers, Not a Manager

**Problem:** Matt wanted a manager/worker pattern where one process oversees the others. But Claude Code doesn't natively support a persistent manager process, and adding one creates a single point of failure.

**Solution:** Every conversation is a self-healing peer. On startup, each conversation:
1. Reads durable state (CURRENT-STATE.md, INTEGRATION-STATUS.md, LEARNINGS.md)
2. Scans `.claude/active/*/state.json` for scope overlaps and stale entries
3. Cleans stale entries (heartbeat > 2 hours + issue still open = abandoned)
4. Checks for completed sidebars via `gh issue list --label sidebar-complete`
5. Registers itself in `.claude/active/`

**Why no manager:** "The real manager is Matt with dashboard views." The `/wf:active` dashboard command aggregates all state files into a human-readable table for Matt to assess.

**Applies to:** All projects using Claude Code with parallel conversations

---

## Lesson 22: LEARNINGS.md — Optional Insight Capture

**Problem:** Nonlinear work paths generate insights that get lost when conversations end. Schema migration should have been done first → define contracts before features. But this lesson evaporates when the conversation closes.

**Solution:** On conversation shutdown, extract learnings from state.json to `docs/LEARNINGS.md`:

```markdown
## 2026-02-15 — enroll-rss-pipeline (#42)
**What happened:** RSS pipeline required 4 blocking dependencies not anticipated
**Insight:** Schema migration should have been done first — define contracts before features
**Propagate:** Yes — all projects should define contracts before implementation
---
```

**Rules:**
- `learnings: null` in state.json = nothing to capture (routine work) — zero friction
- Only write when there IS an insight
- `Propagate: Yes` triggers herding protocol pickup on next Infrastructure audit
- Entries are append-only, newest at top
- Keep last 20 entries; archive older

**Applies to:** All projects using Claude Code

---

## Lesson 23: Herding Directory and Hook-Based Distribution

**Problem:** When the herding protocol identifies improvements for 20 projects, there's no mechanism to notify each project that new standards are available. Matt would have to manually open each project and discuss changes.

**Solution:** Every NLF project gets a `herd/` directory for incoming herd items. Infrastructure's herding protocol writes files here. A hook notifies Matt when new data arrives.

**Directory structure:**
```
project-root/
  herd/
    incoming/                          # New items from herding protocol
      2026-02-15-deploy-gates.md       # Standardized lesson file
      2026-02-15-scope-drift.md
    applied/                           # Items reviewed and applied
    rejected/                          # Items reviewed and rejected (with reason)
```

**Hook notification:**
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-herd.sh",
            "statusMessage": "Checking for herding updates..."
          }
        ]
      }
    ]
  }
}
```

**check-herd.sh:**
```bash
#!/bin/bash
HERD_DIR="$CLAUDE_PROJECT_DIR/herd/incoming"
if [ -d "$HERD_DIR" ] && [ "$(ls -A "$HERD_DIR" 2>/dev/null)" ]; then
  COUNT=$(ls -1 "$HERD_DIR" | wc -l)
  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "HERDING PROTOCOL: $COUNT new herd item(s) in herd/incoming/. Review with Matt before applying. Files: $(ls -1 "$HERD_DIR" | tr '\n' ', ')"
  }
}
EOF
else
  echo '{}'
fi
```

**Consumption workflow:** Next conversation startup → hook injects context → AI says "There are 2 new herding items to review" → Matt decides when to discuss → AI reads files, proposes changes, Matt approves → files move to `herd/applied/`.

**Applies to:** All NLF projects (deployed by Infrastructure's herding protocol)

---

## Lesson 24: Compaction Durability Strategy

**Problem:** ~60% of CLAUDE.md behavioral instructions erode after 3-4 compactions. Long procedures, nuanced rules, and multi-step protocols get summarized away. Matt: "is there anything in what's being proposed that veers too much from the default Claude programming?"

**Solution:** Map every convention to its enforcement mechanism using the durability hierarchy:

| Durability Tier | Mechanism | Survives Compaction? | Use For |
|----------------|-----------|---------------------|---------|
| 1. Hooks (most durable) | Run automatically, no memory needed | Always | Hard rules, blocking gates, file protection, scope enforcement |
| 2. Skills | Loaded fresh from disk on invocation | Always | Multi-step procedures, workflows, agent personas |
| 3. State files + post-compaction hook | Re-injected after compaction | Always | Current work context, scope anchor, work stack |
| 4. Structural enforcement | Directory layout, import rules, linters | Always | Naming conventions, code organization, product boundaries |
| 5. CLAUDE.md short "Never" rules | Survive summarization | Usually | Critical prohibitions (max 10-15 rules, < 5 words each) |
| 6. CLAUDE.md detailed procedures | Erode through compaction | Rarely | Nothing critical (move to skills or hooks instead) |

**Principle:** "Never rely on Claude remembering. Always rely on Claude reading."

**Application to our conventions:**

| Convention | Enforcement | Tier |
|-----------|------------|------|
| Deploy verification gate | Hook (PreToolUse on Bash git push) | 1 |
| Scope drift detection | Hook (PreToolUse on Edit/Write, check file path vs scope) | 1 |
| Protected files (.env, credentials) | Hook (PreToolUse on Edit/Write) | 1 |
| Package manager enforcement | Hook (PreToolUse on Bash) | 1 |
| /sidebar workflow | Skill (loaded on invocation) | 2 |
| Response format | Skill (loaded at conversation start) | 2 |
| TDD workflow | Skill (loaded on invocation) | 2 |
| Scope anchor + work stack | state.json + post-compaction hook | 3 |
| Current state awareness | CURRENT-STATE.md + SessionStart hook | 3 |
| Product directory boundaries | Monorepo structure (physical) | 4 |
| Import boundary rules | ESLint/biome config (physical) | 4 |
| "Never use localhost" | CLAUDE.md short rule | 5 |
| "Never deploy to Stark" | CLAUDE.md short rule | 5 |
| Startup/shutdown rituals | DO NOT put in CLAUDE.md — use hooks + skills | 1+2 |

**Applies to:** All NLF projects — this is the meta-lesson about how to implement all other lessons

---

## Lesson 25: Claude Code Hooks — What's Available, What's Broken, What to Use

**Problem:** Matt: "I think we're underutilizing hooks in ways we could be making use of hooks that will help us a lot more."

**Findings from research (16 GitHub repos, 28 blog posts, official docs):**

**12 Hook Events Available:**

| Event | Fires When | Can Block? | Best Use |
|-------|-----------|-----------|----------|
| SessionStart | Session begins/resumes/compacts | No | Context injection, stale cleanup, herd notification |
| UserPromptSubmit | User sends message | Yes | Prompt validation, context injection |
| PreToolUse | Before tool executes | Yes | Scope enforcement, file protection, command blocking |
| PostToolUse | After tool succeeds | No | Auto-formatting, git staging, notification |
| Stop | Claude finishes responding | Yes | Heartbeat touch, task completion verification |
| PreCompact | Before compaction | No | State preservation to disk |
| SessionEnd | Session terminates | No | Transcript archiving, metrics, cleanup |
| SubagentStart/Stop | Subagent spawns/finishes | Yes (Stop) | Agent monitoring |
| Notification | Notification sent | No | Desktop/phone/Slack alerts |
| PermissionRequest | Permission dialog | Yes | Auto-approve safe operations |
| PostToolUseFailure | Tool fails | No | Error logging |

**CRITICAL BUG — SessionStart "compact" stdout dropped:**
Issue #13650 (still open as of Jan 2026): SessionStart hooks with "compact" matcher execute successfully but their stdout is silently dropped and NOT injected into Claude's context. **Workaround:** Write state to files that CLAUDE.md references (CLAUDE.md IS reloaded from disk after compaction), or use PreCompact to save state and rely on CLAUDE.md instructions to read it back.

**Key patterns for NLF projects:**

1. **Heartbeat via Stop hook:** Touch `.claude/active/{slug}/heartbeat` on every Stop event. This is the closest thing to a heartbeat — fires every time Claude finishes responding.

2. **Scope enforcement via PreToolUse:** Check `tool_input.file_path` against scope anchor's authorized directories. Exit 2 to block with explanation.

3. **PreCompact state preservation:** Save work stack, scope anchor, and learnings to disk before compaction erases them.

4. **SessionEnd cleanup:** Archive transcript, update CURRENT-STATE.md, extract learnings. Cannot block exit but can perform cleanup.

5. **Herd notification via SessionStart:** Check `herd/incoming/` for new items, inject count + filenames into context.

6. **Input modification (v2.0.10+):** PreToolUse can modify tool inputs (not just block). Example: automatically add `--dry-run` to dangerous commands, or fix package manager commands.

7. **Stop hooks for completion verification:** Prompt-type or agent-type Stop hooks can evaluate whether all tasks are complete before allowing Claude to stop. Always check `stop_hook_active` to prevent infinite loops.

**What NOT to rely on:**
- SessionStart stdout after compaction (bug #13650)
- PostCompact hook (doesn't exist yet, requested in #14258)
- Async hooks for decision-making (they can't return decisions)
- Hooks surviving mid-session config changes (snapshot at startup)

**Full research:** See `docs/research/claude-code-hooks-research-2026-01-31.md` (37 sources)

**Applies to:** All NLF projects using Claude Code

---

## Updated Summary for Herding Protocol

**Total lessons:** 25 (16 original + 9 addendum)
**Root cause of most lessons:** Solo developer running parallel AI conversations on complex multi-product project. Context loss, scope drift, deployment verification, cross-conversation coordination, and compaction erosion are the core challenges.

**Updated Priority for cross-project application:**

1. **Immediate (all projects):**
   - Deploy verification gate (#1)
   - Hardcoded refs audit (#6)
   - Per-conversation state directories (#17, replaces #10)
   - Durability strategy mapping (#24) — audit every convention against the enforcement hierarchy
   - Hooks research application (#25) — implement SessionStart, PreToolUse, Stop, PreCompact hooks

2. **Next sprint (projects with /wf):**
   - Red phase verification (#2)
   - Test gap analysis (#3)
   - Quick workflow gates (#4)
   - Gherkin ACs (#5)
   - Three-mode scope model (#18, enhances #12)
   - Conversation types (#20)

3. **Infrastructure build (shared tooling):**
   - /sidebar command as skill (#19)
   - Self-healing peers pattern (#21)
   - LEARNINGS.md extraction (#22)
   - Herd directory + hook notification (#23)
   - Lesson capture system (#16)

4. **As adopted (project-specific):**
   - 6-layer verification (#7)
   - PR-scoped conversations (#8)
   - State files (#9, #11)
   - n8n version control (#14)
   - Response format enhancement (#15)

**Updated Guiding Principles:**
> Every human rejection is a system failure. Every compaction is a documentation failure. Every scope drift is a conversation discipline failure. Build guardrails, not willpower.
>
> Never rely on Claude remembering. Always rely on Claude reading. Hooks enforce, skills instruct, state files persist, CLAUDE.md indexes.
>
> No file is written by multiple conversations simultaneously. Cross-conversation awareness is read-only aggregation.
