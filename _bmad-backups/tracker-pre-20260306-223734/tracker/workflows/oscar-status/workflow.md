---
workflow: oscar-status
agent: oscar
mode: report
description: Show current workflow state
trigger: /oscar:status
code: ST
---

# Oscar Status Workflow

## Purpose

Display the current workflow state including active issue, phase, and AI-ready queue.

## Usage

```
/oscar:status
/oscar:status #42  (specific issue)
```

## Output

```
**Oscar** 🚦: Current Status

📋 Active Work:
   #42 - Add user authentication
   Phase: 4-developing (TDD GREEN)
   Gate: Tests must pass (3/5 passing)
   Agent: Dev (Amelia)

📥 AI-Ready Queue:
   #45 - Fix login redirect (phase:0-backlog)
   #48 - Add password reset (phase:1-refining)

⏸️ Blocked:
   #44 - API integration (waiting: external API access)

✅ Recently Completed:
   #41 - Setup project structure (2h ago)
```

## Information Shown

- Active issue (if any)
- Current phase and gate status
- Active agent
- AI-ready queue
- Blocked issues
- Recently completed
- Session statistics
