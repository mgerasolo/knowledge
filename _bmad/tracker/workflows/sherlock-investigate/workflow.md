---
workflow: sherlock-investigate
agent: sherlock
mode: investigate
description: Start investigation on issue
trigger: /sherlock:investigate
code: IN
---

# Sherlock Investigate Workflow

## Purpose

Begin new investigation following 7-phase methodology.

## Usage

```
/sherlock:investigate "Tests failing unexpectedly"
/sherlock:investigate #42
```

## Steps

### Phase 0: INTAKE
- Classify domain (code|config|infrastructure|process|external)
- Check pattern database for similar issues

### Phase 1: ENVIRONMENT
- Capture host, project, git state
- Note recent deployments

### Phase 2: SYMPTOMS
- Document observed vs expected behavior
- Gather error messages, logs

### Phase 3: HYPOTHESES
- Form theories ranked by likelihood
- Define testable predictions for each

### Phase 4: INVESTIGATION
- Test hypotheses systematically
- Document evidence gathered

### Phase 5: ROOT CAUSE
- Apply 5-Whys until true cause isolated
- Distinguish root cause from symptoms

### Phase 6: RESOLUTION
- Identify owner (code/infrastructure/process/external)
- Define specific fix

### Phase 7: REPORTING
- Document for Oscar handback
- Add to case-log.md for patterns
