---
workflow: oscar-upgrade
agent: oscar
mode: maintenance
description: Upgrade tracker module to latest version
trigger: /oscar:upgrade
---

# Oscar Upgrade Workflow

## Purpose

Upgrade the tracker module from current version to latest available version. Handles changelog review, backup, migration, and verification.

## Steps

### Step 1: Version Check
- Read current installed version from `_bmad/tracker/VERSION`
- Read available version from `/mnt/foundry_resources/protocols/tracker/VERSION`
- Compare versions

**Output:**
```
Current version: 1.0.0
Available version: 1.1.0

Changes in 1.1.0:
- Added /oscar:migrate workflow
- Improved error messages
- Fixed gate script permissions
```

### Step 2: Changelog Review
- Show breaking changes (if any)
- Show new features
- Show bug fixes
- Confirm user wants to proceed

### Step 3: Backup
- Create backup at `_bmad-backups/tracker-pre-upgrade-{timestamp}`
- Backup: tracker module, sidecar, customization

### Step 4: Apply Upgrade
- Copy new files from protocol source
- Preserve user configuration
- Update VERSION file
- Update manifest version

### Step 5: Migration (if needed)
- Run any migration scripts for version changes
- Convert config format if changed
- Update deprecated settings

### Step 6: Verification
- Run `/oscar:health`
- Verify all checks pass
- Report any issues

### Step 7: Complete
```
**Oscar** 🚦: Upgrade complete!

Upgraded: 1.0.0 → 1.1.0
Backup: _bmad-backups/tracker-pre-upgrade-20260303

New features:
- /oscar:migrate now available

Run /oscar:health to verify everything works.
```

## Rollback

If upgrade fails:
```bash
# Restore from backup
cp -r _bmad-backups/tracker-pre-upgrade-{timestamp}/tracker _bmad/
```
