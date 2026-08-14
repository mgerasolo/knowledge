---
workflow: oscar-observe
agent: oscar
mode: toggle
description: Toggle observer mode on/off
trigger: /oscar:observe
code: OB
---

# Oscar Observe Workflow

## Purpose

Toggle observer mode which keeps Oscar present in the conversation to monitor for scope drift, agent drops, and completion signals.

## Usage

```
/oscar:observe         (toggle on/off)
/oscar:observe on      (explicitly enable)
/oscar:observe off     (explicitly disable)
```

## Observer Behaviors

When enabled, Oscar:
- Monitors for scope drift (editing files outside current issue)
- Detects when agent context is lost (missing attribution)
- Watches for completion signals
- Intervenes when TDD discipline slips
- Tracks time spent on issue

## Output

```
**Oscar** 🚦: Observer mode enabled

I'll stay in the background and watch for:
  - Scope drift (files outside #42)
  - Agent drops (lost attribution)
  - TDD violations (code before tests)
  - Completion signals

Continue working. I'll speak up if needed.
```

## Interventions

```
**Oscar** 🚦: 💡 Hold up - you're editing src/utils/helpers.ts
but #42 is about authentication. Is this:

  1. A necessary dependency
  2. A sidebar (should be separate issue)
  3. Scope creep (stop and refocus)
```
