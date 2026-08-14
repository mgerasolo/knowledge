# knowledge Command Cheat Sheet

## Contents

1. [Project Commands](#project-commands)
2. [Core Commands](#core-commands)
3. [Workflows](#workflows)
4. [Progress Tree](#progress-tree)

---

## Project Commands

Commands specific to knowledge.

*No project-specific commands defined.*

---

## Core Commands

Deployed via Shepherd to all projects.

### Session Tracking (/wl)

| Command | Purpose |
|---------|---------|
| `/wl` | Show all open sessions |
| `/wl wrap` | Wrap-up summary when stepping away |
| `/wl hot` | Sessions marked for resumption |
| `/wl recent` | Sessions with activity in last 24h |
| `/wl mark <id> resume` | Mark session to pick up later |
| `/wl mark <id> deferred` | Push session to later |
| `/wl mark <id> done` | Mark session complete |

### Issue Workflow (/wf)

| Command | Purpose |
|---------|---------|
| `/wf status` | Current workflow status by phase |
| `/wf pending` | Items awaiting human approval |
| `/wf approve <#>` | Approve issue, advance to next phase |
| `/wf deny <#> [reason]` | Reject issue with feedback |
| `/wf issue` | Create new issue |
| `/wf help` | List all workflow commands |

### Context & Forking

| Command | Purpose |
|---------|---------|
| `/baton` | Context recovery after compaction |
| `/baton save` | Manually save context |
| `/sidebar <description>` | Fork conversation for tangential work |

### Git & Development

| Command | Purpose |
|---------|---------|
| `/worktree create <name>` | Create new worktree |
| `/worktree list` | List active worktrees |
| `/worktree cleanup` | Clean merged worktrees |
| `/push-all` | Commit and push all changes |

### Utilities

| Command | Purpose |
|---------|---------|
| `/research <topic>` | Structured research workflow |
| `/yt <url>` | Fetch YouTube transcript |
| `/name-chat` | Name current conversation |

---

## /wf vs /wl

| System | Level | Purpose |
|--------|-------|---------|
| `/wf` | Issue (deliverable) | What needs to be done |
| `/wl` | Session (work period) | What happened while doing it |

---

## Workflows

### Starting Work

```
gh issue list --label "status:ai-ready"    # Check for tasks
claude --resume <session-id>               # Resume session
```

### Stepping Away

```
/wl wrap                    # See summary
/wl mark <id> resume        # Will return to
/wl mark <id> deferred      # Can wait
```

### Returning

```
/wl hot                     # See what to pick up
claude --resume <id>        # Resume session
```

---

## Progress Tree

```
[Session Title or Issue]
├─✅ Completed task
├─🔄 Current task in progress
│  └─⬜ Next subtask
├─⬜ Pending task
└─📌 SIDEBAR: Tangential issue → #XXX

**Next:** [what to work on next]
**You:** [action needed from user, if any]
```

| Icon | Meaning |
|------|---------|
| ✅ Completed | ⬜ Pending | 🔄 In Progress | ❌ Blocked | 📌 Sidebar |

---

*Generated from cheatsheet protocol v1.0.0*
