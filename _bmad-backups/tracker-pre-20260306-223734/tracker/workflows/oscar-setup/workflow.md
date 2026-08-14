---
workflow: oscar-setup
agent: oscar
mode: create
description: First-time setup wizard for Oscar in a new project
trigger: /oscar:setup
---

# Oscar Setup Wizard

## Purpose

Interactive setup to configure Oscar for a new project. Creates config files, validates settings, and confirms everything works.

## When to Use

- First time using Oscar in a project
- After a fresh tracker module installation
- To reconfigure existing settings

## Steps

### Step 1: Welcome & Prerequisites Check

**Actions:**
1. Display welcome message with Oscar persona
2. Verify BMAD is installed (`_bmad/` exists)
3. Verify tracker module is installed (`_bmad/tracker/` exists)
4. Check for existing config (offer to reconfigure or keep)

**Output:**
```
**Oscar** 🚦: Let's get you set up! First, let me check a few things...

✅ BMAD installed
✅ Tracker module installed
⚠️ No configuration found - let's create one!
```

### Step 2: Tracking System Selection

**Ask user:**
- Which tracking system? (GitHub Issues / Linear / BMAD Artifacts)
- If GitHub: Repository (e.g., `mgerasolo/my-project`)
- If GitHub: Project board URL (optional)
- If Linear: Workspace and team

**Validation:**
- Test connection to tracking system
- Verify permissions to read/write issues

### Step 3: Phase Configuration

**Ask user:**
- Full ATDD workflow (10 phases) or Quick mode (5 phases)?
- Default workflow for new issues?
- Strict gate enforcement (block) or warning mode (advise)?

**Explain tradeoffs:**
- Full: More oversight, best for features
- Quick: Faster iteration, good for small changes
- Strict gates: Enforces TDD discipline
- Warning mode: Flexible but requires discipline

### Step 4: Team Configuration (Optional)

**Ask user:**
- Custom agent assignments? (or use defaults)
- Any phases that should use specific agents?

**Show defaults:**
```yaml
refining: [analyst, pm]
designing: [architect]
test-writing: [tea, dev]
developing: [dev]
```

### Step 5: Observer & Marathon Settings

**Ask user:**
- Enable observer mode? (monitors for drift)
- Enable marathon mode? (autonomous batch processing)
- If marathon: Max attempts per issue?

**Explain:**
- Observer: Oscar watches for scope drift, agent drops
- Marathon: Process AI-ready queue without user interaction

### Step 5.5: Resource Discovery (Important!)

**Purpose:** Oscar should know what tools and systems already exist to avoid suggesting duplicates.

**Discover automatically:**
1. Check for `DEPLOYMENTS.md` or equivalent
2. Look for n8n workflows (if n8n URL known)
3. Identify existing dashboards (Grafana, etc.)
4. Find container management (Portainer, Dockhand)
5. Check for maintenance tracking system

**Ask user:**
- "Do you have access to n8n workflows?"
  - If yes: What's the URL?
- "Is there a maintenance tracking system?"
  - If yes: Where? (Grist, GitHub Issues, Linear, etc.)
- "What observability tools are available?"
  - Options: Grafana, Loki, Prometheus, Sentry, None
- "Any deployment registry or service catalog?"
  - If yes: Path or URL?

**Explain why:**
```
**Oscar** 🚦: I'm asking about existing tools so I don't suggest building
something that already exists. "Let's create a monitoring dashboard" is
embarrassing when you already have Grafana set up!
```

**For Infrastructure projects specifically, also ask:**
- Available hosts (Banner, Hulk, Parker, etc.)
- Forbidden hosts (Stark, Friday)
- Key paths (stacks, protocols, standards)

### Step 6: Write Configuration

**Actions:**
1. Create `_bmad/tracker/config/oscar.yaml` from template
2. Update `_bmad/_config/agents/tracker-oscar.customize.yaml`
3. Ensure sidecar directories exist

**Confirm before writing:**
```
Here's your configuration:

Tracking: GitHub Issues (mgerasolo/my-project)
Phases: Full ATDD (10 phases)
Gates: Strict enforcement
Observer: Enabled
Marathon: Enabled (max 3 attempts)

Save this configuration? [Y/n]
```

### Step 7: Validation

**Run checks:**
- [ ] Config file is valid YAML
- [ ] Tracking adapter can connect
- [ ] Can read issues from tracking system
- [ ] Sidecar directories are writable
- [ ] Gate scripts exist (if using custom)

**Report any errors with remediation steps.**

### Step 8: Complete

**Show summary:**
```
**Oscar** 🚦: All set! Here's your quick reference:

📋 Commands:
  /oscar:work #N    Start work on issue #N
  /oscar:status     Show current state
  /oscar:advance    Advance to next phase
  /oscar:marathon   Autonomous mode

🎯 Your Settings:
  Tracking: GitHub Issues
  Phases: Full ATDD
  Gates: Strict

Ready to work? Try: /oscar:status
```

## Error Handling

| Error | Message | Fix |
|-------|---------|-----|
| No BMAD | "BMAD not installed" | Run `/bmad install` first |
| No tracker | "Tracker module not found" | Run install.sh |
| Bad credentials | "Cannot connect to GitHub" | Check repo access |
| Permission denied | "Cannot write config" | Check file permissions |

## Files Created/Modified

- `_bmad/tracker/config/oscar.yaml`
- `_bmad/_config/agents/tracker-oscar.customize.yaml`
