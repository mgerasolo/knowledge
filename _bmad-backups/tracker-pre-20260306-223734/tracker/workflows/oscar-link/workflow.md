---
workflow: oscar-link
agent: oscar
mode: link
description: Link this conversation to a work item
trigger: /oscar:link
code: LK
---

# Oscar Link Workflow

## Purpose

Link the current conversation to a specific work item without starting full work mode. Useful for discussions, research, or planning related to an issue.

## Usage

```
/oscar:link #42
/oscar:link PROJ-123
```

## Output

```
**Oscar** 🚦: Linked to #42 - Add user authentication

This conversation is now associated with #42.
I'll track context and can add notes to the issue.

To start active work: /oscar:work #42
```
