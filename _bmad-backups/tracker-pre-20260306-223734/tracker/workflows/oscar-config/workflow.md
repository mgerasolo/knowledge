---
workflow: oscar-config
agent: oscar
mode: configure
description: View and manage project configuration
trigger: /oscar:config
code: CF
---

# Oscar Config Workflow

## Purpose

View and modify Oscar's project configuration. Shows current settings and allows changes.

## Usage

```
/oscar:config                    (show current config)
/oscar:config tracking.type      (show specific setting)
/oscar:config --edit             (interactive edit)
```

## Output

```
**Oscar** 🚦: Current Configuration

📊 Tracking: github (mgerasolo/my-project)
📍 Phases: full (10 phases)
🚧 Gates: strict enforcement
👁️ Observer: enabled
🏃 Marathon: enabled (max 3 attempts)

Config file: _bmad/tracker/config/oscar.yaml

To change: /oscar:config --edit
Or edit the file directly.
```
