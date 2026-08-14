---
workflow: oscar-adapters
agent: oscar
mode: configure
description: Configure tracking system adapters
trigger: /oscar:adapters
code: AP
---

# Oscar Adapters Workflow

## Purpose

Configure and test tracking system adapters (GitHub, Linear, BMAD artifacts).

## Usage

```
/oscar:adapters                (list available adapters)
/oscar:adapters github         (configure GitHub adapter)
/oscar:adapters test           (test current adapter)
```

## Available Adapters

| Adapter | Description | Status |
|---------|-------------|--------|
| github | GitHub Issues via gh CLI | ✅ Implemented |
| linear | Linear via GraphQL API | 📋 Planned |
| bmad-artifacts | BMAD sprint-status.yaml | 📋 Planned |

## Output

```
**Oscar** 🚦: Tracking Adapters

Current: github
Status: ✅ Connected

Adapter: github
  Repo: mgerasolo/my-project
  Project: https://github.com/users/mgerasolo/projects/2
  Permissions: read, write, admin

Test connection: /oscar:adapters test
Change adapter: /oscar:adapters <name>
```
