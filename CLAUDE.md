# CLAUDE.md

This file provides guidance to Claude Code when working with the KnowledgeStack codebase.

## Overview

**KnowledgeStack** - YouTube transcript ingestion and RAG platform built on Speakr.

**Target Environment:** Banner (10.0.0.33)
**Port Block:** 5000-5099 (web=5000, db=5010, api=5020, cache=5030)
**Domain:** knowledge.nextlevelguild.com

## Critical Rules

**External API Rate Limiting (MANDATORY):**
- **Minimum 2 second delay** between calls to external APIs when making **more than 5 requests** in a batch
- Applies to: YouTube, MCP Gateway, Exa, Brave, or any service outside our internal 10.0.0.x network
- Prefer 3s+ delays for large batches (500+ calls)
- This limit **can be overridden with prior human authorization** (e.g., real-time trading needs faster rates)
- 5 or fewer requests: no delay required
- Internal services (SurrealDB, PostgreSQL, LiteLLM proxy on 10.0.0.x) are exempt

**Container Deployment:**
- **NEVER deploy containers to Stark or localhost** - Stark is a coding workstation only
- **Development containers → Banner (10.0.0.33)**
- **Production → the realm's NAI host when one exists; no general prod host.** (Hulk retired 2026-06-15 — never deploy there)
- This project targets: **Banner**

**URLs - Never localhost:**
- **NEVER use localhost or 127.0.0.1** - containers run on remote VMs
- **Preferred:** Fully qualified domain (requires Traefik setup)
- **Acceptable:** VM IP with port (e.g., `http://10.0.0.33:5000`)

```bash
# BEST - domain via Traefik
https://knowledge.nextlevelguild.com

# OK - direct IP to container host
http://10.0.0.33:5000

# WRONG - will not work (container not on your machine)
http://localhost:5000
http://127.0.0.1:5000
```

**Domain/Traefik Setup:**
- Traefik config: `~/Infrastructure/stacks/traefik/`
- Domain registry: `~/Infrastructure/DEPLOYMENTS.md`
- Standards: `./standards/` → `/mnt/foundry_resources/standards-shared/`

**SSH Access:**
- **ALWAYS use hostname, NEVER use IP address**
- SSH config handles port/user/key automatically

```bash
# CORRECT
ssh banner

# WRONG - will fail
ssh 10.0.0.33
```

## Technology Stack

| Purpose | Tool |
|---------|------|
| Core Platform | Speakr (Python 3.11 / Flask 2.3.3 + Vue.js 3) — AGPL-3.0 |
| Overlay Frontend | TBD (Speakr Vue.js 3 as-is; overlay UI framework open) |
| Ingestion | n8n (YouTube RSS → Speakr REST API) |
| Vector DB | Qdrant (self-hosted Docker) |
| AI Routing | LiteLLM proxy (10.0.0.27:2764) |
| Database | PostgreSQL (shared with Speakr) |
| Auth | Authentik (via Helicarrier) |
| Logging | Loki → Grafana (Coulson) |
| Monitoring | Prometheus → Grafana (Coulson) |
| Secrets | Shared .env files at `/mnt/foundry_devlab/secrets/env/` |

## Key Directories

```
knowledge/
├── .claude/                    # Baton context management
│   ├── CONVERSATION_HISTORY.md # All conversations TLDR
│   ├── BUGS.md                 # Discovered bugs (tagged by conv-id)
│   ├── DECISIONS.md            # Architecture decisions (tagged by conv-id)
│   ├── conversations/          # Per-conversation summaries
│   └── herding/                # → /mnt/foundry_resources/herding/ (protocol feedback)
├── .github/
│   └── ISSUE_TEMPLATE/         # GitHub issue templates
├── standards/                  # → /mnt/foundry_resources/standards-shared/
├── protocols/                  # → /mnt/foundry_resources/protocols/
├── src/                        # Application source code
├── docs/                       # Documentation
└── scripts/                    # Utility scripts
```

## Common Commands

```bash
# Development
npm run dev                     # Start development server
npm run build                   # Build for production
npm run test                    # Run tests

# Secrets (from Infrastructure)
source ~/Infrastructure/scripts/secrets.sh
appservices_get POSTGRES_PASSWORD
ai_apps_get OPENAI_API_KEY      # If using AI features

# Deployment (when ready)
# Use /deployment banner knowledge
```

## Secrets Management

Secrets are managed via shared `.env` files (Infisical is the CANONICAL secrets home (corrected 2026-08-07; this line previously said the opposite)).

**Location:** `/mnt/foundry_devlab/secrets/env/`

```bash
# Source helper functions
source ~/Infrastructure/scripts/secrets.sh

# Infrastructure secrets
secret_get PORTAINER_PASSWORD

# App services (PostgreSQL, Redis, etc.)
appservices_get POSTGRES_PASSWORD

# AI API keys
ai_apps_get OPENAI_API_KEY
```

**Categories:**
| File | Purpose |
|------|---------|
| `infrastructure.env` | Infrastructure admin credentials |
| `appservices.env` | App-facing services (Postgres, Redis, SMTP) |
| `appbrain.env` | AI service API keys |

## Claude Code Telemetry

Usage metrics are tracked via OpenTelemetry to Coulson's monitoring stack.

```bash
# Set project name for this session (auto-detects from git)
claude-telemetry-project

# Or set explicitly
claude-telemetry-project knowledge
```

Dashboard: https://grafana.ucontrolnetwork.com/d/claude-code-working

## Context Management (Baton Protocol)

This project uses structured context management for multi-conversation workflows.

### On Session Start
1. Check `.claude/CURRENT_CONVERSATION_ID`
2. Read `.claude/CONVERSATION_HISTORY.md` for overview
3. Read `.claude/conversations/{conv-id}/SUMMARY.md` for current work

### During Work
- Update SUMMARY.md after significant actions
- Append to BUGS.md when discovering bugs (tag with conv-id)
- Append to DECISIONS.md for architecture decisions (tag with conv-id)
- **Append to MISTAKES.md the moment you identify a mistake, misstatement, or error YOU caused** — every entry needs a root cause + prevention rule; scan its Prevention column before starting similar work (3 repeats = escalate to a hook/rule)
- **Append to GAPS.md the moment you discover something believed done that isn't** — stubbed, partial, or drifted from plan; review it during any sprint/next-work planning

### After Compaction
- IMMEDIATELY read CONVERSATION_HISTORY.md
- Read your conversation's SUMMARY.md
- Resume work with context restored

## GitHub Integration

**Repository:** https://github.com/mgerasolo/knowledge
**Project Board:** https://github.com/users/mgerasolo/projects/X

**Label Taxonomy:**
| Category | Labels |
|----------|--------|
| Type | `type:bug`, `type:feature`, `type:enhancement`, `type:docs` |
| Priority | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` |
| Area | `area:ui`, `area:api`, `area:database`, `area:auth` |
| Status | `status:active`, `status:soon`, `status:blocked`, `status:pending-approval`, `status:ai-ready` |

**At session start:** Check for `status:ai-ready` issues (pre-approved for autonomous work)

### ROADMAP.md is generated — regenerate it when you change issues

`ROADMAP.md` is not hand-maintained. It is a projection of the issue tracker,
rebuilt from scratch by a script, so it can never disagree with the issues for
longer than it takes to re-run:

```bash
python3 scripts/roadmap-sync.py
```

**Run it whenever you open, close, re-label or re-prioritise an issue**, and
commit the regenerated file in the **same commit** as that work — never
regenerate and walk away. An uncommitted `ROADMAP.md` sits dirty in a checkout
several sessions share, one `git add -A` away from being swept into someone
else's unrelated commit. Same rule as a provider updating its consumer guide in
the commit that changes the API. Those are the only events that make the
roadmap stale, which is why this is a step in issue work rather than a timer or
a git hook — a commit hook fires when nobody changed an issue, and misses every
change made in the GitHub web UI.

Two rules for anyone editing the file:

- **Only the block between `<!-- HAND-WRITTEN:START -->` and
  `<!-- HAND-WRITTEN:END -->` may be hand-edited.** That block is preserved
  verbatim on every run and is where the direction and themes live. Everything
  outside it is overwritten.
- **Never fix the roadmap by editing the roadmap.** If a line is wrong, the
  issue behind it is wrong — fix the issue and re-run.

The tree groups issues into themes that are worked out fresh on every run from
the issue's own words, so no theme is ever stored against an issue number. If
an issue turns up under **"Not yet themed"**, that is the signal to add a
matching rule to the `THEMES` list at the top of the script — not to file the
issue differently.

An issue is shown as needing your decision (`❓`) when its body carries an
unticked `- [ ] Matt has …` acceptance criterion, which is the marker the
backlog agents write. Keep using it and the roadmap keeps flagging correctly.

The script fails loudly and leaves the existing file untouched if GitHub can't
be reached, if it gets back an empty list, or if the hand-written markers are
missing or damaged. A stale roadmap is recoverable; an empty one written over a
good one is not.

## Cross-Project Coordination

**Dependencies:**
- Infrastructure (nlf-infrastructure) - Deployment, secrets, monitoring

**Before breaking changes:**
1. Check dependent projects
2. Create issue with `breaking:next-release` label
3. Notify Infrastructure project

## Security Notes

- Never commit secrets or API keys
- Use shared .env files from `/mnt/foundry_devlab/secrets/env/`
- All external API calls must go through authenticated endpoints

## Related Documentation

- Infrastructure: `~/Infrastructure/CLAUDE.md`
- Standards: `./standards/` → `/mnt/foundry_resources/standards-shared/`
- Protocols: `./protocols/` → `/mnt/foundry_resources/protocols/`
- Herding: `./.claude/herding/` → `/mnt/foundry_resources/herding/`
- Deployment Policy: `./standards/deployment-policy.md`
- Port Standard: `./standards/ports.md`
- Secrets Standard: `./standards/secrets.md`
<!-- shepard:managed:begin -->
## Standards (ShepardProtocol — auto-synced, do not edit locally)
Read into every conversation:
- .claude/rules/standards/codex-validation.md — Codex independent validation
<!-- shepard:managed:end -->
