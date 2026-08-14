---
workflow: oscar-work
agent: oscar
mode: orchestrate
description: Start work on a specific issue/story
trigger: /oscar:work
code: WK
---

# Oscar Work Workflow

## Purpose

Start work on a specific issue. Links the current conversation to the issue, loads context, and routes to the appropriate agent based on phase.

## Usage

```
/oscar:work #42
/oscar:work PROJ-123
```

## Steps

### Step 1: Load Issue
- Parse issue ID from command
- Fetch issue details from tracking system
- Load any existing Oscar state for this issue

### Step 2: Verify Phase
- Determine current phase
- Check if phase allows AI work
- Verify no blocking gates

### Step 3: Link Session
- Link this conversation to the issue
- Update sidecar with session ID
- Note in issue comments (optional)

### Step 4: Load Context
- Load relevant files mentioned in issue
- Load previous conversation context (if any)
- Load phase-specific guidance

### Step 5: Route to Agent
- Determine appropriate agent for current phase
- Hand off with context summary
- Enable observer mode

## Output

```
**Oscar** 🚦: Working on #42 - Add user authentication

📍 Phase: 3-test-writing (TDD RED)
🎯 Gate: Tests must fail
👤 Agent: TEA

Loading context... done.
Handing to TEA for test writing.

**TEA (Murat)** 🧪: I'll write failing acceptance tests...
```

## Error Handling

| Error | Action |
|-------|--------|
| Issue not found | Show similar issues |
| Phase blocked | Explain why, show requirements |
| Agent unavailable | Suggest alternative |
