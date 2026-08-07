# Claude Code Hooks: Best Practices and Community Patterns Research

**Date:** 2026-01-31
**Researcher:** Claude Opus 4.5 (automated research)
**Scope:** Late 2025 through January 2026 community patterns, official documentation, GitHub repositories, blog posts, and known issues

---

## Executive Summary

1. **Hooks are the deterministic enforcement layer** that complements CLAUDE.md's "should-do" suggestions. The community consensus is that hooks are the single most important feature for enterprise/team use of Claude Code, providing guaranteed execution regardless of context window pressure or model reasoning.

2. **Multi-agent coordination is a solved (but immature) problem.** Projects like claude-cognitive, Continuous-Claude-v3, and claude-code-hooks-multi-agent-observability demonstrate working patterns for file-based coordination, pool-based state sharing, and real-time monitoring across concurrent sessions. However, these are community projects, not official features.

3. **Context preservation across compaction remains the biggest pain point.** There is a confirmed bug (Issue #15174, duplicate of #13650) where SessionStart hooks with "compact" matcher execute but their stdout is silently dropped. The workaround is writing critical state to CLAUDE.md or disk files, then reading them back. The community project Continuous-Claude-v3 provides the most sophisticated solution with its "Compound, don't compact" architecture.

4. **The hookify plugin democratizes hook creation.** Anthropic's official hookify plugin allows creating hooks from conversation analysis or natural language instructions without editing JSON, using simple markdown files with YAML frontmatter and regex patterns.

5. **Hook reliability has been a significant issue.** Multiple regressions were reported in 2025 (v2.0.27 broke subdirectory hooks, v2.0.31 regressed after v2.0.30 fix), and Windows support has been problematic. The v2.1.0 release in January 2026 brought significant improvements including agent hooks in frontmatter and wildcard tool permissions.

---

## 1. Community-Shared Hook Patterns

### Key GitHub Repositories

| Repository | Stars | Description |
|-----------|-------|-------------|
| [claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) | High | Captures all 8 lifecycle events with JSON payloads; uses UV single-file Python scripts |
| [claude-code-hooks](https://github.com/karanb192/claude-code-hooks) | Growing | Ready-to-use hooks: safety, automation, notifications. Copy-paste-customize approach |
| [claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) | High | Comprehensive configuration with hooks, skills, agents, commands, and GitHub Actions |
| [everything-claude-code](https://github.com/affaan-m/everything-claude-code) | High | Battle-tested configs from an Anthropic hackathon winner, all rewritten in Node.js |
| [claude-hooks](https://github.com/decider/claude-hooks) | Moderate | Lightweight Python-based hooks for clean code practices |
| [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | High | Curated list of skills, hooks, slash-commands, agent orchestrators, and plugins |
| [claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) | Moderate | Real-world patterns including skill auto-activation via hooks |

### Most Popular Hook Patterns [Community-Wide]

**Auto-format on edit (PostToolUse):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write \"$(echo $0 | jq -r '.tool_input.file_path')\"",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

**Block dangerous commands (PreToolUse):**
```bash
#!/bin/bash
# .claude/hooks/block-rm.sh
COMMAND=$(jq -r '.tool_input.command')

if echo "$COMMAND" | grep -q 'rm -rf'; then
  echo '{"decision":"block","reason":"Destructive command blocked by hook"}'
else
  exit 0
fi
```

**Auto-stage git changes (PostToolUse):**
Automatically `git add` files after Claude modifies them, keeping a granular trail of agent work.

**Enforce package manager (PreToolUse):**
Block `npm` commands in a bun/pnpm-only project by matching Bash commands and returning `{"decision": "block", "reason": "Use pnpm, not npm"}`.

[Anthropic Official Docs, 2026; karanb192/claude-code-hooks; disler/claude-code-hooks-mastery]

---

## 2. Multi-Conversation Coordination

### claude-cognitive: Pool-Based Coordination
[Source: GMaN1911/claude-cognitive on GitHub]

The most sophisticated multi-instance coordination system found. Key architecture:

**Pool Coordinator Pattern:**
```markdown
```pool
INSTANCE: A
ACTION: completed
TOPIC: Fixed authentication bug
SUMMARY: Resolved race condition in token refresh. Added mutex.
AFFECTS: auth.py, session_handler.py
BLOCKS: Session management refactor can proceed
```
```

**How it works:**
- Instances communicate via pool blocks written to `~/.claude/pool/instance_state.jsonl` (append-only log)
- **Automatic mode**: Detects completions/blockers from conversation patterns every 5 minutes
- **Manual mode**: Explicit pool blocks for critical coordination
- Per-terminal instance IDs: `export CLAUDE_INSTANCE=A` / `export CLAUDE_INSTANCE=B`
- SessionStart hooks inject prior completions/blockers into new session context
- UserPromptSubmit hooks auto-detect completion patterns
- Stop hooks extract and persist manual pool blocks

**Context Router (Attention Dynamics):**
- HOT (>0.8): Full file injection for active development
- WARM (0.25-0.8): Headers only for background awareness
- COLD (<0.25): Evicted from context window
- Files decay when not mentioned but reactivate on keyword matching

### claude-code-hooks-multi-agent-observability
[Source: disler/claude-code-hooks-multi-agent-observability on GitHub]

Real-time monitoring dashboard for concurrent Claude Code agents:

**Architecture:** Claude agents -> hook scripts -> HTTP POST -> Bun server -> SQLite (WAL mode) -> WebSocket -> Vue client

```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [
        {"type": "command", "command": "uv run .claude/hooks/pre_tool_use.py"},
        {"type": "command", "command": "uv run .claude/hooks/send_event.py --source-app YOUR_APP --event-type PreToolUse"}
      ]
    }]
  }
}
```

- Session-based color coding for visual distinction across agents
- Dual-color system: app colors (left border) + session colors (second border)
- Centralized SQLite with WAL mode for concurrent write access
- WebSocket broadcasting for synchronized real-time updates

### GitButler: Session-Isolated Git Branches
[Source: docs.gitbutler.com/features/ai-integration/claude-code-hooks]

GitButler's approach uses hooks to isolate each Claude Code session's file changes into separate git branches:

- **PreToolUse**: Captures session ID, creates a new git index for that session populated from HEAD
- **PostToolUse**: Adds modified files (and only them) to the session-specific index
- **Stop**: Commits the session index's tree to `refs/heads/claude/<session-id>`

This means multiple simultaneous Claude Code instances can each work on files without interfering, because each session's changes are captured in isolated virtual branches.

### Shared Communication Files Pattern
[Source: dev.to/holasoymalva; community discussions]

A simpler approach: set up shared files like `coms.md` and `cloth.md` where different Claude Code agents can be assigned specific roles (debugging, testing, documentation). Combined with Git worktrees for complete code isolation, each worktree gets its own Claude Code instance.

---

## 3. Context Preservation Patterns

### The Compaction Problem

When Claude Code's context window fills up, compaction summarizes older conversation parts. This loses nuanced understanding, specific decisions, and behavioral instructions. The community has developed several approaches:

### Pattern A: PreCompact + SessionStart Round-Trip

**Concept:** Save critical state to disk in PreCompact, read it back in SessionStart with "compact" matcher.

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/save-state-before-compact.sh"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/restore-state-after-compact.sh"
          }
        ]
      }
    ]
  }
}
```

**CRITICAL BUG:** As of v2.0.76, SessionStart hooks with "compact" matcher execute but their stdout is **silently dropped** and not injected into Claude's context (Issues #15174, #13650, #12151, #12117). The workaround is to write state to CLAUDE.md instead, which IS loaded fresh from disk after compaction.

[Source: GitHub Issue #15174; Claude Code Docs]

### Pattern B: CLAUDE.md as State Container

Since CLAUDE.md files are loaded fresh from disk after every compaction, some teams dynamically update CLAUDE.md with current project state:

```bash
#!/bin/bash
# PreCompact hook: append current state to CLAUDE.md
STATE_FILE="$CLAUDE_PROJECT_DIR/.claude/current-state.md"
cat >> "$CLAUDE_PROJECT_DIR/CLAUDE.md" << EOF

## Current Session State (Auto-Generated)
$(cat "$STATE_FILE" 2>/dev/null || echo "No state file found")
EOF
```

[Source: Community workaround for Issue #15174]

### Pattern C: Continuous-Claude-v3 "Compound, Don't Compact"
[Source: parcadei/Continuous-Claude-v3 on GitHub]

The most sophisticated solution. Rather than hoping context survives compaction, this system proactively extracts and structures what matters before compaction occurs.

**Architecture:**
```
SessionStart -> Load context (ledger, handoff, memory, TLDR cache)
Working      -> Track changes (file claims, dirty flags)
             -> PostToolUse hooks index handoffs and skills
             -> SubagentStop hooks capture agent reports
PreCompact   -> Auto-handoff triggered (YAML format)
             -> TLDR re-indexing if dirty > 20
SessionEnd   -> Daemon spawns with thinking blocks
             -> Archival memory extraction
             -> Ledger finalization
/clear       -> Fresh context + preserved state
```

**Key components:**
- **Continuity Ledgers** (`thoughts/ledgers/CONTINUITY_*.md`): Human-readable markdown with decisions, architectural insights, discovered patterns
- **Handoffs** (`thoughts/shared/handoffs/*.yaml`): Token-efficient YAML with task status, discoveries, blockers, architectural decisions, next steps
- **TLDR Code Analysis**: 5-layer semantic index (AST, Call Graph, CFG, DFG, PDG) achieving 95% token savings vs raw code
- **Archival Memory**: BGE-large-en-v1.5 embeddings in PostgreSQL with pgvector for semantic recall across sessions
- **File Claims**: Prevents concurrent modification conflicts across sessions

---

## 4. Workflow Enforcement (PreToolUse)

### Sensitive File Protection

```python
#!/usr/bin/env python3
import json, sys

data = json.load(sys.stdin)
file_path = data.get('tool_input', {}).get('file_path', '')

PROTECTED_PATTERNS = ['.env', 'package-lock.json', '.git/', 'credentials', 'secrets']

for pattern in PROTECTED_PATTERNS:
    if pattern in file_path:
        print(f"Protected file: {pattern} files cannot be modified", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
```

[Source: Anthropic Official Docs; paddo.dev/blog/claude-code-hooks-guardrails]

### Directory Escape Prevention

```python
#!/usr/bin/env python3
import json, sys

data = json.load(sys.stdin)
cmd = data.get('tool_input', {}).get('command', '')
cwd = data.get('cwd', '')

if '../' in cmd or (cmd.startswith('cd /') and not cmd.startswith(f'cd {cwd}')):
    print("Command attempts to escape project directory", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
```

[Source: paddo.dev/blog/claude-code-hooks-guardrails]

### UV/Package Manager Enforcement

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/enforce-uv.py"
          }
        ]
      }
    ]
  }
}
```

Where `enforce-uv.py` checks if the command uses `pip install`, `python -m pip`, or `pip3` and blocks them with a message to use `uv` instead.

[Source: pydevtools.com/blog/claude-code-hooks-for-uv]

### Block-at-Submit Strategy (Not Block-at-Write)

**Best practice from Anthropic:** Do NOT use hooks to block Edit/Write operations mid-plan. Instead, let Claude finish its plan, then validate at commit time:

```bash
#!/bin/bash
# PreToolUse hook on Bash(git commit)
# Check if tests passed
if [ ! -f "/tmp/agent-pre-commit-pass" ]; then
  echo "Tests must pass before committing. Run tests first." >&2
  exit 2
fi
exit 0
```

This avoids "frustrating" the agent mid-plan while still enforcing quality gates.

[Source: Anthropic Best Practices; blog.sshh.io]

### Input Modification (v2.0.10+)

Starting in v2.0.10, PreToolUse hooks can modify tool inputs instead of just blocking:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": {
      "command": "npm run lint --dry-run"
    },
    "additionalContext": "Running in dry-run mode for safety."
  }
}
```

This enables transparent sandboxing, automatic dry-run flags, secret redaction, and commit message formatting without blocking and retrying.

[Source: Claude Code Docs v2.0.10+]

---

## 5. Stop Hooks for Verification

### Command-Based Verification

```bash
#!/bin/bash
# .claude/hooks/verify-tests-ran.sh
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')

# Prevent infinite loops
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0
fi

# Check if tests were run in this session
if ! grep -q "npm test\|pytest\|cargo test" "$TRANSCRIPT" 2>/dev/null; then
  echo '{"decision":"block","reason":"Tests have not been run. Please run the test suite before finishing."}'
else
  exit 0
fi
```

[Source: Anthropic Official Docs; stevekinney.com]

### Prompt-Based Stop Hooks (LLM Evaluation)

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "You are evaluating whether Claude should stop working. Context: $ARGUMENTS\n\nAnalyze the conversation and determine if:\n1. All user-requested tasks are complete\n2. Any errors need to be addressed\n3. Follow-up work is needed\n\nRespond with JSON: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"your explanation\"} to continue working.",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

This uses Haiku by default to evaluate task completion. The SubagentStop variant works identically for subagent verification.

[Source: Claude Code Official Docs]

### Agent-Based Stop Hooks (Multi-Turn Verification)

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "agent",
            "prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS",
            "timeout": 120
          }
        ]
      }
    ]
  }
}
```

Agent-based hooks spawn a subagent that can Read, Grep, Glob files and actually run commands to verify conditions. Up to 50 turns of tool use.

[Source: Claude Code Official Docs]

### Infinite Loop Prevention

The `stop_hook_active` field is `true` when Claude is already continuing due to a stop hook. **Always check this** to prevent infinite continuation loops:

```bash
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0  # Allow stopping on second attempt
fi
```

[Source: Claude Code Official Docs; GitHub Issue #15485]

---

## 6. SessionEnd Hooks for Cleanup

### Session State Capture

```bash
#!/bin/bash
# .claude/hooks/session-end-capture.sh
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
REASON=$(echo "$INPUT" | jq -r '.reason')
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Archive the session transcript
ARCHIVE_DIR="$CLAUDE_PROJECT_DIR/.claude/archives"
mkdir -p "$ARCHIVE_DIR"
cp "$TRANSCRIPT" "$ARCHIVE_DIR/session-${SESSION_ID}-${TIMESTAMP}.jsonl"

# Log session metadata
echo "{\"session_id\":\"$SESSION_ID\",\"reason\":\"$REASON\",\"ended\":\"$TIMESTAMP\"}" \
  >> "$ARCHIVE_DIR/session-log.jsonl"
```

[Source: DataCamp tutorial; claude-code-hooks-mastery]

### Learning Extraction (Continuous-Claude-v3)

When a session ends, Continuous-Claude-v3's daemon:
1. Detects stale heartbeats
2. Spawns headless Claude (Sonnet) to analyze thinking blocks
3. Extracts learnings to archival memory (PostgreSQL + pgvector)
4. Identifies: design patterns discovered, debugging techniques, edge cases, performance insights

[Source: parcadei/Continuous-Claude-v3]

### Cost and Duration Reporting

```bash
#!/bin/bash
# Push session metrics to observability platform
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
# Calculate session duration from transcript timestamps
# Push to Datadog/OpenTelemetry/Prometheus
```

[Source: DataCamp tutorial; community patterns]

### SessionEnd Limitations

- SessionEnd hooks **cannot block session termination** -- they are purely reactive
- Reason values: `clear`, `logout`, `prompt_input_exit`, `bypass_permissions_disabled`, `other`
- Introduced in v1.0.85

[Source: Claude Code Official Docs]

---

## 7. Hook-Based Notification Systems

### ntfy.sh (Push Notifications to Phone/Desktop)
[Source: andrewford.co.nz/articles/claude-code-instant-notifications-ntfy]

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "permission_prompt|idle_prompt",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/notify-ntfy.sh"
          }
        ]
      }
    ]
  }
}
```

```bash
#!/bin/bash
# .claude/hooks/notify-ntfy.sh
INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.message')
TITLE=$(echo "$INPUT" | jq -r '.title // "Claude Code"')
TYPE=$(echo "$INPUT" | jq -r '.notification_type')

curl -s \
  -H "Title: $TITLE" \
  -H "Priority: high" \
  -H "Tags: robot" \
  -d "$MESSAGE" \
  "https://ntfy.sh/your-topic"
```

### macOS Native Notifications
[Source: khromov.se/claude-code-hooks-for-simple-macos-notifications]

```bash
#!/bin/bash
INPUT=$(cat)
MESSAGE=$(echo "$INPUT" | jq -r '.message')
osascript -e "display notification \"$MESSAGE\" with title \"Claude Code\""
```

### CodeInbox (Slack Integration)
[Source: github.com/codeinbox/codeinbox]

Install via Homebrew; uses MagicBell to deliver notifications from Claude Code hooks to Slack and other channels.

### Smart Notifications Plugin
[Source: 777genius on Medium]

Categorizes notifications by type (Plan Ready, Question, Review, Done, Error) and supports desktop alerts, sounds, and Slack webhooks.

### Multi-Tab Awareness Challenge
[Source: kane.mx/posts/2025/claude-code-notification-hooks]

**Problem:** Claude Code hooks run as detached processes without a controlling terminal (TTY_NR: 0). All processes show no controlling terminal, making it impossible to determine which VSCode window spawned the hook.

**Solution:** Use the `VSCODE_IPC_HOOK_CLI` environment variable. Each VSCode instance has a unique UUID identifier. Extract this UUID and maintain a mapping to terminal devices for targeted notifications.

### Cross-Platform: code-notify
[Source: github.com/mylee04/code-notify]

Cross-platform desktop notifications for Claude Code/Codex/Gemini. Customizable triggers: `idle_prompt`, `permission_prompt`, etc.

---

## 8. PreCompact Hooks

### Basic State Preservation

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/pre-compact-save.sh"
          }
        ]
      }
    ]
  }
}
```

```bash
#!/bin/bash
# .claude/hooks/pre-compact-save.sh
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRIGGER=$(echo "$INPUT" | jq -r '.trigger')
CUSTOM=$(echo "$INPUT" | jq -r '.custom_instructions')

# Save current state to disk
STATE_FILE="$CLAUDE_PROJECT_DIR/.claude/state/pre-compact-${SESSION_ID}.json"
mkdir -p "$(dirname "$STATE_FILE")"

echo "{
  \"session_id\": \"$SESSION_ID\",
  \"trigger\": \"$TRIGGER\",
  \"custom_instructions\": \"$CUSTOM\",
  \"timestamp\": \"$(date -Iseconds)\",
  \"git_branch\": \"$(git branch --show-current 2>/dev/null)\",
  \"git_status\": \"$(git status --short 2>/dev/null)\"
}" > "$STATE_FILE"

# Output custom instructions for compaction
echo "Preserve API documentation and test patterns"
```

### PreCompact Matchers

| Matcher  | When it fires |
|----------|---------------|
| `manual` | User runs `/compact` |
| `auto`   | Auto-compact when context window is full |

### PreCompact Limitations

- PreCompact hooks **cannot block compaction** -- they are informational only
- stdout from PreCompact hooks can include custom instructions for the compaction process
- The `custom_instructions` field in input contains what the user passes to `/compact` (empty for auto)

### Feature Request: PostCompact Hook
[Source: GitHub Issue #14258]

Community has requested a PostCompact hook event for:
- Re-injecting behavioral frameworks after compaction
- Verifying compaction quality
- Reloading state files written during PreCompact

This would solve the SessionStart "compact" matcher bug since it would fire at the right time with guaranteed context injection.

[Source: Claude Code Official Docs; GitHub Issues #14258, #15174]

---

## 9. Hookify Tool Usage

### What Hookify Does
[Source: github.com/anthropics/claude-code/tree/main/plugins/hookify]

Hookify is Anthropic's official plugin that creates custom hooks from either:
1. **Conversation analysis** -- analyzes recent conversation to find behaviors you corrected or were frustrated by
2. **Explicit instructions** -- natural language descriptions of what to block/warn

### Commands

```
/hookify                    # Analyze conversation for unwanted patterns
/hookify Don't use console.log in TypeScript files
/hookify:list              # List all active rules
/hookify:configure         # Enable/disable rules interactively
/hookify:help              # Get help
```

### Rule Format (Markdown + YAML Frontmatter)

```yaml
---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf
action: block
---

**Dangerous rm command detected!**

This command could delete important files. Please:
- Verify the path is correct
- Consider using a safer approach
```

### Advanced Conditions

```yaml
---
name: warn-sensitive-files
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.env$|credentials|secrets
  - field: new_text
    operator: contains
    pattern: KEY
---
```

**All conditions must match** for the rule to trigger.

### Event Types

| Event | Triggers On |
|-------|-------------|
| `bash` | Bash tool commands |
| `file` | Edit, Write, MultiEdit tools |
| `stop` | When Claude wants to stop |
| `prompt` | User prompt submission |
| `all` | All events |

### Operators

| Operator | Description |
|----------|-------------|
| `regex_match` | Pattern must match (most common) |
| `contains` | String must contain pattern |
| `equals` | Exact string match |
| `not_contains` | String must NOT contain pattern |
| `starts_with` | String starts with pattern |
| `ends_with` | String ends with pattern |

### Key Advantage

Rules take effect **immediately on the next tool use** -- no restart needed. Files are stored as `.claude/hookify.*.local.md` (gitignored by default).

### Conversation Analyzer

The conversation analyzer agent:
1. Scans recent conversation history
2. Identifies patterns where you corrected Claude or expressed frustration
3. Generates rule suggestions automatically
4. Creates corresponding `.claude/hookify.*.local.md` files

[Source: anthropics/claude-code plugins/hookify; deepwiki.com]

---

## 10. Known Limitations and Workarounds

### Critical Bugs (as of January 2026)

| Issue | Version | Status | Description |
|-------|---------|--------|-------------|
| [#15174](https://github.com/anthropics/claude-code/issues/15174) | v2.0.72+ | Closed (dup of #13650) | SessionStart "compact" matcher stdout silently dropped |
| [#13650](https://github.com/anthropics/claude-code/issues/13650) | v2.0.72+ | Open | SessionStart hook stdout silently dropped despite valid JSON |
| [#12151](https://github.com/anthropics/claude-code/issues/12151) | Multiple | Open | Plugin hook output not captured (UserPromptSubmit, SessionStart) |
| [#10367](https://github.com/anthropics/claude-code/issues/10367) | v2.0.27 | Fixed | Hooks non-functional in subdirectories |
| [#10814](https://github.com/anthropics/claude-code/issues/10814) | v2.0.31 | Fixed | Regression after v2.0.30 fix -- all hooks broken |
| [#10450](https://github.com/anthropics/claude-code/issues/10450) | v2.0.27 | Fixed | Windows: no hooks working at all |

### SessionStart "compact" Workaround

Since SessionStart stdout is not reliably injected after compaction:

1. **Write state to CLAUDE.md** during PreCompact (CLAUDE.md IS loaded fresh after compaction)
2. **Write state to disk files** and have Claude read them via instructions in CLAUDE.md
3. **Use Continuous-Claude-v3** which has its own state management layer

### Context Window Shrinkage from MCP Tools

Enabling too many MCP servers can shrink your 200k context window to ~70k. Only enable the MCP servers you need for the current task.

[Source: community discussions; sankalp.bearblog.dev]

### Hook Execution Timeout

- Default timeout changed from 60 seconds to 10 minutes (600 seconds)
- Async hooks also default to 10 minutes
- Prompt hooks default to 30 seconds
- Agent hooks default to 60 seconds

### Async Hook Limitations

- Only `type: "command"` hooks support `async: true`
- Cannot block or return decisions (action has already proceeded)
- Output delivered on next conversation turn only
- No deduplication across multiple firings

### Shell Profile Interference

If your shell profile (.bashrc, .zshrc) prints text on startup, it can interfere with JSON parsing of hook output. Solutions:
- Guard profile output: `[ -z "$PS1" ] && return` at top of profile
- Use explicit `#!/bin/bash` shebang
- Redirect profile output to /dev/null in hook scripts

### Stop Hook Infinite Loops

Stop hooks that always block will create infinite loops. Always check `stop_hook_active`:

```bash
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active')
if [ "$STOP_ACTIVE" = "true" ]; then
  exit 0  # Allow stopping on second attempt
fi
```

### Hook Priority/Layering

When multiple control mechanisms apply:
1. `continue: false` overrides everything (stops Claude entirely)
2. JSON `"decision": "block"` (blocks the specific action)
3. Exit code 2 (simpler blocking mechanism)

### Matchers Only Filter by Tool Name

Matchers only filter by tool name (for tool events), not by file paths or arguments. To filter by file path, you must check `tool_input.file_path` inside your hook script.

### Hooks Snapshot at Startup

Claude Code captures a snapshot of hooks at startup and uses it throughout the session. Mid-session changes to hooks files are NOT applied automatically -- Claude warns you and requires review in `/hooks` menu.

---

## Recommendations for Your Project (knowledge)

Based on this research and your Baton Protocol context management system, here are specific recommendations:

### 1. PreCompact State Preservation
Given the SessionStart "compact" bug, write your Baton state to a file that CLAUDE.md references:

```json
{
  "hooks": {
    "PreCompact": [{
      "hooks": [{
        "type": "command",
        "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/baton-pre-compact.sh"
      }]
    }]
  }
}
```

### 2. SessionEnd State Capture
Archive conversation summaries and update CONVERSATION_HISTORY.md:

```json
{
  "hooks": {
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/baton-session-end.sh"
      }]
    }]
  }
}
```

### 3. Workflow Enforcement
Protect deployment configs and enforce your container deployment rules:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/enforce-deployment-rules.sh"
        }]
      }
    ]
  }
}
```

### 4. Stop Hook for Summary Generation
Before Claude stops, ensure SUMMARY.md is updated:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "prompt",
        "prompt": "Analyze the conversation: $ARGUMENTS. Check if Claude has updated .claude/conversations/SUMMARY.md. If not, respond {\"ok\": false, \"reason\": \"Please update your conversation SUMMARY.md before finishing.\"}. If it has been updated, respond {\"ok\": true}.",
        "timeout": 30
      }]
    }]
  }
}
```

---

## Bibliography

### Official Documentation
1. [Hooks Reference - Claude Code Docs](https://code.claude.com/docs/en/hooks) -- Anthropic, 2026
2. [Hooks Guide - Claude Code Docs](https://code.claude.com/docs/en/hooks-guide) -- Anthropic, 2026
3. [Claude Code: Best Practices for Agentic Coding](https://www.anthropic.com/engineering/claude-code-best-practices) -- Anthropic, 2025
4. [How to Configure Hooks](https://claude.com/blog/how-to-configure-hooks) -- Anthropic Blog, 2025

### GitHub Repositories
5. [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) -- Lifecycle event capture & UV scripts
6. [disler/claude-code-hooks-multi-agent-observability](https://github.com/disler/claude-code-hooks-multi-agent-observability) -- Real-time multi-agent monitoring
7. [karanb192/claude-code-hooks](https://github.com/karanb192/claude-code-hooks) -- Ready-to-use hook collection
8. [ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase) -- Comprehensive configuration example
9. [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) -- Hackathon winner's battle-tested configs
10. [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) -- Curated list of Claude Code resources
11. [diet103/claude-code-infrastructure-showcase](https://github.com/diet103/claude-code-infrastructure-showcase) -- Skill auto-activation via hooks
12. [decider/claude-hooks](https://github.com/decider/claude-hooks) -- Lightweight Python hook system
13. [GMaN1911/claude-cognitive](https://github.com/GMaN1911/claude-cognitive) -- Multi-instance coordination & working memory
14. [parcadei/Continuous-Claude-v3](https://github.com/parcadei/Continuous-Claude-v3) -- Context management with ledgers & handoffs
15. [anthropics/claude-code/plugins/hookify](https://github.com/anthropics/claude-code/tree/main/plugins/hookify) -- Official hookify plugin
16. [ruvnet/claude-flow](https://github.com/ruvnet/claude-flow) -- Multi-agent orchestration platform

### Blog Posts and Tutorials
17. [Automate Your AI Workflows with Claude Code Hooks](https://blog.gitbutler.com/automate-your-ai-workflows-with-claude-code-hooks) -- GitButler Blog, 2025
18. [Claude Code Hook Examples](https://stevekinney.com/courses/ai-development/claude-code-hook-examples) -- Steve Kinney, 2025
19. [Claude Code Hooks: Guardrails That Actually Work](https://paddo.dev/blog/claude-code-hooks-guardrails/) -- Paddo.dev, 2025
20. [Claude Code Hooks for uv Projects](https://pydevtools.com/blog/claude-code-hooks-for-uv/) -- Python Developer Tooling Handbook, 2025
21. [How I Use Every Claude Code Feature](https://blog.sshh.io/p/how-i-use-every-claude-code-feature) -- Shrivu Shankar, 2025
22. [Get Instant Notifications When Claude Code Needs You](https://andrewford.co.nz/articles/claude-code-instant-notifications-ntfy/) -- Andrew Ford, 2025
23. [Claude Code Hooks for Simple macOS Notifications](https://khromov.se/claude-code-hooks-for-simple-macos-notifications/) -- Stanislav Khromov, 2025
24. [Desktop Notifications for Claude Code](https://kane.mx/posts/2025/claude-code-notification-hooks/) -- Kane.mx, 2025
25. [Claude Code Hooks: The Feature You're Ignoring](https://medium.com/@lakshminp/claude-code-hooks-the-feature-youre-ignoring-while-babysitting-your-ai-789d39b46f6c) -- Lakshmi Narasimhan, Jan 2026
26. [A Complete Guide to Hooks in Claude Code](https://www.eesel.ai/blog/hooks-in-claude-code) -- Eesel.ai, 2025
27. [Claude Code Hooks: A Practical Guide](https://www.datacamp.com/tutorial/claude-code-hooks) -- DataCamp, 2025
28. [How to Add Smart Notifications to Claude Code](https://777genius.medium.com/how-to-add-smart-notifications-to-claude-code-types-plan-ready-question-review-done-error-7bece0fc015c) -- 777genius, Dec 2025

### Bug Reports and Feature Requests
29. [Issue #15174: SessionStart hook compact matcher output not injected](https://github.com/anthropics/claude-code/issues/15174) -- GitHub
30. [Issue #14258: PostCompact Hook Event request](https://github.com/anthropics/claude-code/issues/14258) -- GitHub
31. [Issue #10367: Hooks non-functional in subdirectories](https://github.com/anthropics/claude-code/issues/10367) -- GitHub
32. [Issue #10814: Hooks regression in v2.0.31](https://github.com/anthropics/claude-code/issues/10814) -- GitHub
33. [Issue #15485: Stop hooks output structure clarification](https://github.com/anthropics/claude-code/issues/15485) -- GitHub

### Notification Tools
34. [codeinbox/codeinbox](https://github.com/codeinbox/codeinbox) -- Slack notifications via MagicBell
35. [mylee04/code-notify](https://github.com/mylee04/code-notify) -- Cross-platform desktop notifications
