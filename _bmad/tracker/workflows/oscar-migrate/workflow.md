---
workflow: oscar-migrate
agent: oscar
mode: migration
description: Migrate from existing workflow tracking to Oscar-managed phases
trigger: /oscar:migrate
---

# Oscar Migration Workflow

## Purpose

For projects already using manual labels or another tracking method, this workflow:
1. Scans existing GitHub labels/Linear states
2. Maps them to Oscar's 10-phase workflow
3. Offers to rename/consolidate labels
4. Creates mapping config for compatibility

## When to Use

- Project has existing workflow labels (status:*, todo/done, etc.)
- Switching from another tracking system
- Consolidating multiple labeling schemes

## Steps

### Step 1: Detect Existing Tracking

**Scan for patterns:**
- `status:*` labels
- `phase:*` labels (already Oscar-compatible)
- `todo`, `in-progress`, `done`
- `needs-review`, `blocked`
- Linear/Jira status names

**Output:**
```
**Oscar** 🚦: Let me scan your current tracking setup...

Found 47 issues with workflow labels:
  - status:todo (15 issues)
  - status:in-progress (8 issues)
  - status:review (3 issues)
  - status:done (21 issues)

Also found:
  - blocked (2 issues)
  - needs-input (1 issue)
```

### Step 2: Show Current State

**Display:**
- Count of issues per status
- Unmapped issues (no workflow labels)
- Potential conflicts

### Step 3: Propose Mapping

**Suggested mappings:**
```yaml
# Your labels → Oscar phases
status:todo: phase:0-backlog
status:in-progress: phase:4-developing
status:review: phase:8-human-review
status:done: phase:10-done
blocked: next:blocked
needs-input: next:human-input
```

### Step 4: User Confirmation

**Allow user to:**
- Accept proposed mappings
- Modify individual mappings
- Skip certain labels
- Add custom mappings

### Step 5: Migration Options

**Offer three approaches:**

**a) Compatibility Mode (Recommended)**
- Oscar reads both old and new labels
- New issues get Oscar labels
- Old issues keep existing labels
- Gradual natural migration

**b) Full Migration**
- Rename all labels to Oscar format
- Update all existing issues
- Clean break from old system

**c) Parallel Systems**
- Keep both labeling systems
- Manual sync required
- Not recommended long-term

### Step 6: Apply Migration

Based on chosen option:
- Create Oscar phase labels
- Update issues (if full migration)
- Create mapping config
- Set up compatibility layer

### Step 7: Verify

**Checks:**
- Oscar can read all existing issues
- Phase labels created correctly
- Tracking adapter working
- No orphaned issues

**Output:**
```
**Oscar** 🚦: Migration complete!

Migrated: 47 issues
Created labels: 12 phase labels, 4 next-action labels
Mode: Compatibility (old labels still recognized)

Try: /oscar:status to see your current backlog
```

## Migration Mapping Config

Created at `_bmad/tracker/config/label-mappings.yaml`:

```yaml
# Label compatibility mappings
legacy_labels:
  "status:todo": "phase:0-backlog"
  "status:in-progress": "phase:4-developing"
  "status:review": "phase:8-human-review"
  "status:done": "phase:10-done"
  "blocked": "next:blocked"

# Read legacy labels? (for compatibility mode)
read_legacy: true

# Write legacy labels? (for parallel mode)
write_legacy: false
```

## Rollback

If migration causes issues:
1. Labels were not deleted (can revert)
2. Run migration again with different options
3. Manual cleanup if needed
