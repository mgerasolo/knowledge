# /sidebar — Conversation Fork & Work Stack Protocol

**Source:** KnowledgeStack Party Mode (Amelia, Winston, Paige — 7 rounds)
**Date:** 2026-01-31
**Status:** Design artifact — ready for Infrastructure implementation
**Applies to:** All NLF projects using Claude Code

---

## Problem Statement

Solo developer (Matt + AI) runs 3-5 Claude Code conversations simultaneously on complex multi-product projects. Conversations naturally evolve through dependency chains discovered at runtime:

```
A (RSS pipeline)
  → discovers need for C (schema migration) — blocks A
    → C completes → back to A
  → discovers D (health endpoint) — independent of A
    → D needs E (shared utility) — blocks D
    → D needs F (deploy script) — blocks D
    → D completes → back to A
  → A completes
```

**Current failure modes:**
1. **Context loss** — Spawning new tabs for every sub-task loses the WHY context
2. **File contention** — Multiple conversations writing to shared state files (ACTIVE-WORK.md) causes overwrites and race conditions
3. **Orphaned work** — Sidebar conversations finish but parent never checks back
4. **Scope creep without awareness** — "Quick two-line fix" becomes multi-hour saga
5. **Lost tracking** — Matt can't tell which window is doing what across 5+ tabs
6. **No learning capture** — Insights from nonlinear work paths aren't recorded

---

## Core Concepts

### Three-Mode Scope Model

Every piece of work within a conversation is classified:

| Mode | Definition | Trigger | Action |
|------|-----------|---------|--------|
| **On-stack** | Current task or ancestor in dependency chain | Default state | Continue working |
| **Detour** | Blocking dependency — must complete before parent can resume | "I need X before I can finish Y" | Push to work stack, track return point |
| **Drift** | Unrelated work — no dependency arrow to anything on the stack | "While we're at it..." or touching unauthorized directories | Warn with 4 options |

**The distinction test:** Can you draw a dependency arrow from the new work back to something on the stack? Yes = detour (stay). No = drift (warn).

### Work Stack (Per-Conversation)

Each conversation maintains an internal stack of what it's working on and why:

```
WORK STACK:
→ [ACTIVE]  Schema migration for enroll-channel (detour)
  [PAUSED]  RSS pipeline integration (paused at: wrote failing test, need schema)
```

When the active item completes, the AI explicitly resumes the paused item: "Schema migration complete. Returning to RSS pipeline. We paused after writing the failing test — the schema unblocks implementation."

**Three-deep rule:** If the stack exceeds 3 levels (A → C → G), the deepest item should be sidebarred or backlogged. Three levels of nesting means the original goal is too far away to maintain coherent context.

### Sidebar vs Detour Decision

```
Discovered new work needed?
├── Does it BLOCK current task? (can't continue without it)
│   ├── YES → DETOUR — push to stack, do it here, return when done
│   └── NO → Is it related to this conversation's goal?
│       ├── YES but not blocking → SIDEBAR — new issue, new tab, check later
│       └── NO → DRIFT — warn with options
└── Is it a future nice-to-have?
    └── BACKLOG — create issue, don't start, stay focused
```

---

## Architecture

### Design Invariant

**No file is written by multiple conversations simultaneously.**

Each conversation owns its state. Cross-conversation awareness is achieved through read-time aggregation, not shared writes.

### Per-Conversation State (Ephemeral)

Each conversation creates and owns a directory under `.claude/active/`:

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
    {
      "task": "RSS pipeline integration",
      "status": "paused",
      "pausedAt": "wrote failing test, need schema before implementation",
      "type": "root"
    },
    {
      "task": "Schema migration for enroll-channel contract",
      "status": "active",
      "type": "detour",
      "reason": "RSS pipeline requires updated channel schema"
    }
  ],
  "startedAt": "2026-02-15T14:30:00Z",
  "learnings": null,
  "sidebarsSpawned": [88]
}
```

**For sidebar conversations:**

```json
{
  "slug": "sidebar-88-update-cli",
  "sessionId": "sess_b8f4c3d2",
  "type": "sidebar",
  "product": "shared",
  "branch": "sidebar/88-update-cli",
  "issues": [88],
  "primaryIssue": 88,
  "parentIssue": 42,
  "scope": ["packages/shared/", ".claude/"],
  "stack": [
    {
      "task": "Update Claude Code CLI and reconfigure hooks",
      "status": "active",
      "type": "root"
    }
  ],
  "startedAt": "2026-02-15T15:10:00Z",
  "learnings": null,
  "sidebarsSpawned": []
}
```

**Conversation types:**

| Type | Scope enforcement | Can spawn sidebars | Detour limit |
|------|------------------|-------------------|--------------|
| `feature` | Strict — drift detection active | Yes | 3 deep |
| `sidebar` | Strict — tighter than feature | No — creates backlog issues instead | 2 deep |
| `planning` | Relaxed — cross-cutting by nature | Yes | No limit |
| `bugfix` | Strict | Yes | 2 deep |

**heartbeat file:** `touch .claude/active/{slug}/heartbeat` on every AI response. If heartbeat > 2 hours old and issue is still open, session is likely abandoned.

### Durable State Files (Persist Across Conversations)

| File | Written by | Purpose |
|------|-----------|---------|
| `CURRENT-STATE.md` | Last conversation to close | Baton — what's implemented, recent decisions, what's next |
| `docs/INTEGRATION-STATUS.md` | Any conversation that changes contracts | Cross-product dependency tracking |
| `docs/LEARNINGS.md` | Extracted from state.json on shutdown | Accumulated insights across conversations |

These are committed to git. The `.claude/active/` directory is gitignored.

### GitHub Issues as Authoritative Layer

GitHub issue labels provide the durable, cross-machine, atomic coordination layer:

| Label | Meaning |
|-------|---------|
| `active-work` | Conversation currently working on this issue |
| `sidebar` | Issue was spawned by /sidebar command |
| `sidebar-complete` | Sidebar work done, results commented |

**Why GitHub, not just files:** Files are local. If Matt switches machines (laptop → desktop), local files aren't there. GitHub issue state is always accessible. Also, `gh` API operations are atomic — no race conditions.

---

## /sidebar Command Flow

### Step 1: User Invokes /sidebar

```
Matt: /sidebar Update the Claude Code CLI configuration
```

### Step 2: AI Creates GitHub Issue

```markdown
# [Sidebar] Update Claude Code CLI configuration

## Sidebar Context
- **Parent Issue:** #42 — KnowledgeEnroll RSS Monitor
- **Parent Branch:** feature/42-rss-monitor
- **Parent Conversation:** enroll-rss-pipeline
- **Trigger:** user-requested
- **Complexity:** quick | medium | significant
- **Related Files:** .claude/hooks/, CLAUDE.md

## Task
Update Claude Code CLI to latest version and reconfigure hooks
for the new active-work directory pattern.

## Why This Came Up
During RSS pipeline implementation, discovered hooks are using
the old ACTIVE-WORK.md pattern. Need to update to per-conversation
state directories.

## Acceptance Criteria
- [ ] CLI updated to latest version
- [ ] Hooks reconfigured for .claude/active/ pattern
- [ ] Existing hook tests pass
- [ ] Results commented on parent issue #42

## Sidebar Protocol
- [ ] On completion: comment results on this issue
- [ ] On completion: comment summary on parent issue #42
- [ ] If contracts modified: update INTEGRATION-STATUS.md
- [ ] If scope expands beyond ACs: create backlog issue, don't fork further
```

Labels: `sidebar`, `active-work`

### Step 3: AI Outputs Paste Prompt

```
Sidebar created: #88 — Update Claude Code CLI configuration
Paste this into a new Claude Code tab:

> Pick up sidebar issue #88. Read the issue for full context. Register in
> .claude/active/ on startup. When done: comment results on #88, comment
> summary on parent #42, deregister, close #88.
```

### Step 4: Matt Opens New Tab, Pastes Prompt

The sidebar conversation:
1. Reads issue #88 for full context
2. Creates `.claude/active/sidebar-88-update-cli/state.json`
3. Does the work within the defined scope
4. Comments results on #88
5. Comments summary on parent #42: "Sidebar #88 complete: CLI updated, hooks reconfigured for .claude/active/ pattern"
6. Deletes `.claude/active/sidebar-88-update-cli/`
7. Removes `active-work` label, adds `sidebar-complete` label
8. Closes #88

### Step 5: Parent Conversation Checks Back

Next time the parent conversation runs (or Matt asks):
```bash
gh issue list --label sidebar --search "parent:#42" --state closed
```

Or the AI checks on startup: "Sidebar #88 completed. CLI updated and hooks reconfigured. Incorporating into our work."

---

## Proactive Drift Detection → Sidebar Suggestion

The AI doesn't just respond to `/sidebar` — it proactively detects drift and suggests it:

```
⚠️ SCOPE CHECK: This sounds outside this conversation's scope.

This conversation: #42 — KnowledgeEnroll RSS Monitor
Proposed work: packages/ops/ (pipeline monitoring dashboard)

Can I draw a dependency arrow to the work stack?
  RSS pipeline → schema migration → ... → pipeline monitoring? NO.
  This is DRIFT, not a detour.

Options:
1. [/sidebar] — Create sidebar issue, paste prompt for new tab
2. [Backlog] — Create issue #89 in backlog, stay focused here
3. [Route] — Tab 'ops-health-endpoints' is active on KnowledgeOps. Add there?
4. [Continue] — Override scope check, log expansion
```

**Drift triggers:**
- Touching files outside the scope anchor's authorized directories
- Implementing features not in the acceptance criteria
- "While we're at it" / "we should also" / "let me quickly"
- Work for a different product than the scope anchor's product

---

## Conflict Detection (Read-Time Aggregation)

Before touching new files or directories, each conversation checks for overlaps:

```
BEFORE modifying packages/contracts/:

1. Glob .claude/active/*/state.json
2. Parse each file's scope and active stack
3. Check: does any other conversation's scope include packages/contracts/?

Result:
  Tab 'college-embedding' has packages/contracts/ in scope
  and is ACTIVELY modifying it (stack shows detour into contract update)

⚠️ SCOPE OVERLAP with 'college-embedding' on packages/contracts/
Options:
  1. Wait — check back after they commit
  2. Coordinate — work on non-overlapping files within contracts/
  3. Proceed — accept potential merge conflict
```

**Optimistic concurrency model:** Don't lock upfront. Check at the moment you need to act. Product directory boundaries make most work non-overlapping by design. `packages/contracts/` is the primary contention zone — the rule there is: commit before anyone else touches contracts.

---

## Startup and Shutdown Rituals

### Conversation Startup

1. **Read durable state:**
   - `CURRENT-STATE.md` — where the project stands
   - `docs/INTEGRATION-STATUS.md` — cross-product dependencies
   - `docs/LEARNINGS.md` (last 5 entries) — recent insights

2. **Scan active conversations:**
   - Glob `.claude/active/*/state.json`
   - Check for scope overlaps with planned work
   - Check for stale heartbeats (> 2 hours + issue still open = likely abandoned)
   - Clean stale entries: delete directory, log cleanup

3. **Check resolved sidebars:**
   - `gh issue list --label sidebar-complete --search "parent:#{myIssue}"`
   - Incorporate findings from completed sidebars

4. **Establish identity:**
   - Create `.claude/active/{slug}/state.json` with scope anchor and empty stack
   - Touch heartbeat file
   - Add `active-work` label to GitHub issue

### Conversation Shutdown

1. **Commit all work**
2. **Capture learnings** in state.json (if any — null is fine for routine work)
3. **Extract learnings** to `docs/LEARNINGS.md` (append, if non-null)
4. **Update `CURRENT-STATE.md`** — what was accomplished, decisions made, what's next
5. **Update `docs/INTEGRATION-STATUS.md`** — if contracts or cross-product dependencies changed
6. **Comment on GitHub issue** — summary of what was done
7. **Delete `.claude/active/{slug}/` directory**
8. **Remove `active-work` label** from GitHub issue
9. **Create PR** if work is ready for review

---

## Nesting Rules

| Level | Allowed | Example |
|-------|---------|---------|
| Root task | Always | A: RSS pipeline |
| 1 detour deep | Always | A → C: schema migration (blocks A) |
| 2 detours deep | Allowed with warning | A → C → G: index migration (blocks C) |
| 3+ detours deep | Not allowed | Sidebar or backlog the deepest item |

**Sidebar conversations cannot spawn sub-sidebars.** If a sidebar discovers additional work beyond its ACs, it creates a plain backlog issue and comments on the parent: "Discovered additional work: #89. Created as backlog item."

---

## Dashboard View (/wf:active)

```
ACTIVE CONVERSATIONS:
┌─────────┬──────────────────────────┬──────────────────────┬───────────┐
│ Issue(s) │ Slug                     │ Branch               │ Stack     │
├─────────┼──────────────────────────┼──────────────────────┼───────────┤
│ #42,#43 │ enroll-rss-pipeline      │ feature/42-rss       │ 2 deep    │
│         │  → [active] schema migr  │                      │ (detour)  │
│         │  → [paused] RSS pipeline │                      │           │
├─────────┼──────────────────────────┼──────────────────────┼───────────┤
│ #44     │ ops-health-endpoints     │ feature/44-health    │ 1 (root)  │
├─────────┼──────────────────────────┼──────────────────────┼───────────┤
│ #88     │ sidebar-88-update-cli    │ sidebar/88-cli       │ 1 (root)  │
│         │  ↳ parent: #42           │                      │ sidebar   │
└─────────┴──────────────────────────┴──────────────────────┴───────────┘

RECENTLY COMPLETED SIDEBARS:
│ #85 │ sidebar-85-fix-linting │ closed 2h ago │ parent: #42 │

STALE (no heartbeat > 2h):
│ #40 │ enroll-channel-scoring │ last beat: 6h ago │ issue: open │
```

---

## LEARNINGS.md Pattern

Captured on conversation shutdown, only when there's something worth recording:

```markdown
## 2026-02-15 — enroll-rss-pipeline (#42)
**What happened:** RSS pipeline required 4 blocking dependencies not anticipated
**Insight:** Schema migration should have been done first — define contracts before features
**Propagate:** Yes — all projects should define contracts before implementation
---

## 2026-02-15 — sidebar-88-update-cli (#88, sidebar from #42)
**What happened:** Hook config format changed between CLI versions
**Insight:** Add contract tests for tool configurations, not just API schemas
**Propagate:** Yes — affects all NLF projects using Claude Code hooks
---
```

**Rules:**
- `learnings: null` in state.json = nothing to capture (routine work) — zero friction
- Only write when there IS an insight
- `Propagate: Yes` triggers herding protocol pickup on next Infrastructure audit
- Entries are append-only, newest at top
- Keep last 20 entries; archive older to `docs/LEARNINGS-archive.md`

---

## Gitignore Rules

```gitignore
# Ephemeral conversation state (process lock files)
.claude/active/

# These are committed (durable state):
# CURRENT-STATE.md
# docs/INTEGRATION-STATUS.md
# docs/LEARNINGS.md
```

---

## Implementation Priority

1. **MVP (implement first):**
   - Per-conversation state directory (`.claude/active/{slug}/`)
   - state.json with stack tracking
   - Heartbeat file
   - Startup scan + stale cleanup
   - /sidebar command (issue creation + paste prompt)
   - /wf:active dashboard

2. **V2 (after MVP proves the pattern):**
   - Proactive drift detection with sidebar suggestion
   - GitHub label coordination (active-work, sidebar, sidebar-complete)
   - Sidebar shutdown → comment on parent issue
   - LEARNINGS.md extraction on shutdown

3. **V3 (Growth phase):**
   - Startup hook for automatic cleanup
   - Cross-machine sync (GitHub labels as authoritative, local files as cache)
   - Orphan detection comparing heartbeat age + issue state
   - /wf:cleanup command for manual tidying

---

## Durability Strategy — How Each Element Survives Compaction

Based on hooks research (16 GitHub repos, 28 sources, Jan 2026). Key finding: ~60% of CLAUDE.md behavioral instructions erode after 3-4 compactions. Every design element must map to a durable enforcement mechanism.

### Hook Implementation Plan

| Hook Event | Purpose | Implementation |
|-----------|---------|---------------|
| **SessionStart** (`startup\|resume`) | Read durable state, scan active conversations, check sidebars, register self | Command hook → `.claude/hooks/conversation-startup.sh` |
| **SessionStart** (`compact`) | Re-inject scope anchor + work stack from state.json | Command hook → `.claude/hooks/post-compact-restore.sh` (NOTE: stdout is bugged — Issue #13650. Workaround: write to file, CLAUDE.md references it) |
| **PreToolUse** (`Edit\|Write`) | Scope enforcement — check file path against scope anchor's authorized directories | Command hook → `.claude/hooks/scope-check.sh` |
| **PreToolUse** (`Bash`) | Prevent deployment to wrong host, enforce package manager | Command hook → `.claude/hooks/bash-guard.sh` |
| **Stop** | Touch heartbeat file, optionally verify task completion | Command hook → `.claude/hooks/heartbeat-touch.sh` |
| **PreCompact** | Save work stack + scope anchor + learnings to disk before compaction | Command hook → `.claude/hooks/pre-compact-save.sh` |
| **SessionEnd** | Update CURRENT-STATE.md, extract learnings, deregister from .claude/active/, archive transcript | Command hook → `.claude/hooks/conversation-shutdown.sh` |

### Durability Mapping

| Design Element | Enforcement Mechanism | Durability Tier | Notes |
|---------------|----------------------|----------------|-------|
| Per-conversation state directories | SessionStart hook creates, SessionEnd hook deletes | Tier 1 (Hook) | Fully automated |
| Work stack (detour/drift/on-stack) | state.json + PreCompact save + post-compact restore | Tier 3 (State file) | Bugged: SessionStart compact stdout dropped. Workaround: write to file |
| Scope enforcement | PreToolUse hook checks file paths vs scope anchor | Tier 1 (Hook) | Hard block — exit 2 with explanation |
| Drift detection | PreToolUse hook (file paths) + skill instructions (behavioral) | Tier 1+2 (Hook+Skill) | Hook catches file violations; skill catches conversational drift |
| /sidebar command | Skill (loaded on `/sidebar` invocation) | Tier 2 (Skill) | Full procedure loaded fresh from disk |
| Heartbeat | Stop hook touches file | Tier 1 (Hook) | Every response, automatic |
| Stale entry cleanup | SessionStart hook scans .claude/active/ | Tier 1 (Hook) | Self-healing on every startup |
| LEARNINGS.md extraction | SessionEnd hook | Tier 1 (Hook) | Cannot block exit, but runs cleanup |
| Three-deep nesting rule | Skill instructions + state.json stack depth check | Tier 2+3 | Skill provides instructions, state tracks depth |
| Sidebar nesting prohibition | state.json type field + skill logic | Tier 2+3 | `type: "sidebar"` → skill blocks sub-sidebar creation |
| GitHub label coordination | /sidebar skill + SessionEnd hook | Tier 2+1 | Skill creates labels; hook removes on shutdown |
| /wf:active dashboard | Skill (aggregates state files) | Tier 2 (Skill) | Read-only, no state to lose |
| CURRENT-STATE.md updates | SessionEnd hook + CLAUDE.md "update on shutdown" rule | Tier 1+5 | Hook automates; CLAUDE.md is backup reminder |
| Response format | Skill (loaded at start) + CLAUDE.md short rule | Tier 2+5 | Skill has full format; CLAUDE.md has "include footer" reminder |

### Known Bug Workaround — SessionStart "compact" Stdout

**Bug:** Issue #13650 (open as of Jan 2026). SessionStart hooks with `compact` matcher execute but stdout is silently dropped.

**Impact:** Post-compaction context re-injection via SessionStart hook stdout does NOT work.

**Workaround strategy:**
1. **PreCompact hook** saves critical state to `.claude/state/pre-compact-{session}.json`
2. **CLAUDE.md** contains instruction: "After compaction, read `.claude/state/` for your scope anchor and work stack"
3. **SessionStart hook** writes state to a file (not stdout), then CLAUDE.md references it
4. **Skills** are loaded fresh on invocation — the /sidebar skill and startup rituals skill always work

**When bug is fixed:** Switch to direct stdout injection from SessionStart compact hook. The file-based workaround can remain as belt-and-suspenders.

### Recommended CLAUDE.md Rules (Tier 5 — Keep Minimal)

Only put rules in CLAUDE.md that are short enough to survive summarization:

```markdown
## Critical Rules (5 words or less each)
- Never deploy to Stark
- Never use localhost
- Read .claude/active/ on startup
- Read CURRENT-STATE.md on startup
- Update CURRENT-STATE.md on shutdown
- Touch heartbeat on every response
```

Everything else → hooks or skills.

---

## Design Principles

1. **Each conversation owns its own state.** No shared writes. Ever.
2. **Cross-conversation awareness is read-only aggregation.** Glob, parse, report.
3. **GitHub issues are the durable message bus.** Survives crashes, works cross-machine.
4. **Local files are fast cache.** No network needed for scope checks.
5. **Detours are fine. Drift is the danger.** Dependency arrows = OK. No arrows = warn.
6. **Three deep, then sidebar.** Stack depth is the complexity signal.
7. **Sidebars don't nest.** One fork level, then backlog issues.
8. **Learnings are optional.** Zero friction for routine work. Capture only when there's an insight.
9. **Self-healing peers, not a manager.** Every conversation cleans up on startup.
10. **Product boundaries prevent most conflicts.** The monorepo structure is the first line of defense.
11. **Never rely on Claude remembering. Always rely on Claude reading.** Hooks enforce, skills instruct, state files persist, CLAUDE.md indexes.
