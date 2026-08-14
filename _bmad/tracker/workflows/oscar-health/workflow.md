---
workflow: oscar-health
agent: oscar
mode: diagnostic
description: Diagnose Oscar installation and configuration issues
trigger: /oscar:health
---

# Oscar Health Check

## Purpose

Diagnose Oscar installation, configuration, and runtime issues. Produces a health report with recommendations.

## When to Use

- After installation to verify everything works
- When experiencing issues with Oscar
- As part of troubleshooting
- Periodic health checks

## Checks Performed

### 1. Installation Integrity

| Check | Pass | Fail |
|-------|------|------|
| Tracker module directory exists | ✅ | `_bmad/tracker/` not found |
| Oscar agent file present | ✅ | Missing oscar.agent.yaml |
| Agent file is valid YAML | ✅ | YAML parse error |
| VERSION file exists | ✅ | Cannot determine version |
| All workflow directories exist | ✅ | Missing workflow: X |
| Config templates present | ✅ | Missing config files |

### 2. Sidecar Health

| Check | Pass | Fail |
|-------|------|------|
| Sidecar directory exists | ✅ | `_memory/oscar-sidecar/` not found |
| memories.md readable | ✅ | Cannot read memories |
| memories.md writable | ✅ | Cannot write to memories |
| instructions.md readable | ✅ | Cannot read instructions |
| logs/ directory writable | ✅ | Cannot write logs |
| feedback/ directory writable | ✅ | Cannot capture feedback |
| recovery/ directory writable | ✅ | Cannot save recovery data |

### 3. Configuration

| Check | Pass | Fail |
|-------|------|------|
| Project config exists | ✅ | Run `/oscar:setup` |
| Config is valid YAML | ✅ | YAML syntax error at line X |
| Tracking system configured | ✅ | No tracking.type set |
| Tracking adapter exists | ✅ | Unknown adapter: X |
| Adapter can connect | ✅ | Connection failed: reason |
| Phase definitions valid | ✅ | Unknown phase: X |
| Gate scripts exist | ✅ | Missing gate: X |

### 4. Integration

| Check | Pass | Fail |
|-------|------|------|
| Manifest entry present | ✅ | Tracker not in manifest |
| Version matches | ✅ | Version mismatch (upgrade?) |
| Agent customization exists | ✅ | Missing customization file |
| Hooks executable | ✅ | Hook not executable: X |
| Baton integration | ✅ | Baton not configured |
| Herding integration | ✅ | Herding not available |

### 5. Runtime

| Check | Pass | Fail |
|-------|------|------|
| No stale lock files | ✅ | Lock file from X |
| Recent activity | ✅ | No activity in X days |
| Log rotation working | ✅ | Logs exceed X MB |
| Feedback capture working | ✅ | Feedback not being captured |

## Output Format

```
Oscar Health Check - 2026-03-03 14:30
======================================

Installation:  ✅ OK
Sidecar:       ✅ OK
Configuration: ⚠️ WARNING - tracking adapter not configured
Integration:   ✅ OK
Runtime:       ✅ OK

Details:
  - Config: tracking.config.repo is empty
  - Config: tracking.config.project_board is empty

Recommendations:
  1. Run /oscar:setup to configure tracking adapter
  2. Set tracking.config.repo in oscar.yaml

Overall: HEALTHY with warnings

Log: /tmp/tracker-health-20260303-1430.log
```

## Health Status Levels

| Level | Meaning | Action |
|-------|---------|--------|
| ✅ HEALTHY | All checks pass | None needed |
| ⚠️ WARNING | Non-critical issues | Fix when convenient |
| ❌ DEGRADED | Some features broken | Fix soon |
| ❌ CRITICAL | Oscar cannot function | Fix immediately |

## Automated Fixes

For some issues, Oscar can offer automated fixes:

| Issue | Auto-Fix |
|-------|----------|
| Missing sidecar dirs | Create directories |
| Missing .gitkeep files | Create files |
| Stale lock files | Remove with confirmation |
| Missing manifest entry | Add entry |

```
⚠️ Found 2 issues that can be auto-fixed:
  1. Missing recovery/ directory
  2. Stale lock file from yesterday

Auto-fix these issues? [Y/n]
```

## Error Recovery

If health check reveals critical issues:

1. Try `/oscar:setup` to reconfigure
2. Try reinstalling: `install.sh`
3. Check backup directory for recovery
4. Report to herding if issue persists
