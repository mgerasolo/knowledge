# Augie Sidecar

Persistent memory for Augie, the Read-Only Compliance Enforcer.

## Directory Structure

```
augie-sidecar/
├── memories.md              # Learned patterns, adjustments
├── instructions.md          # Startup protocols, methodology
├── project-context.yaml     # Project-specific config (from /augie:setup)
├── audit-log.md             # Rolling log of all audits
├── violations.md            # Tracked violations with status
├── README.md                # This file
├── rules/                   # Rule definitions by source
│   ├── security.yaml        # Universal security rules
│   ├── bmad-standards.yaml  # BMAD platform rules
│   ├── lessons-learned.yaml # Rules from Oscar/Sherlock/user feedback
│   └── project/             # Project-specific rules
│       ├── code.yaml        # Code conventions
│       ├── docs.yaml        # Documentation requirements
│       └── process.yaml     # Workflow requirements
├── exemptions/              # Approved rule exemptions
│   └── *.md                 # Individual exemption records
├── feedback/                # User corrections
│   └── *.md                 # Feedback entries
├── logs/                    # Event logs
│   └── YYYY-MM-DD.log       # Daily log files
└── reports/                 # Generated compliance reports
    └── *.md                 # Report files
```

## Key Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| memories.md | Learned patterns | As patterns emerge |
| instructions.md | Methodology | Rarely |
| audit-log.md | Audit history | Every audit |
| violations.md | Violation tracking | Every finding |

## Rules Directory

Place custom ruleset YAML files here:

```yaml
# Example: security.yaml
rules:
  - id: SEC-001
    name: "No hardcoded credentials"
    severity: CRITICAL
    pattern: "(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]"
    scope: ["*.py", "*.js", "*.ts"]
    enabled: true
```

## Exemptions Directory

Store approved exemptions as markdown files:

```markdown
# Exemption: SEC-001 on config.example.js

- **Rule:** SEC-001 (No hardcoded credentials)
- **Artifact:** config.example.js
- **Justification:** Example file with placeholder values
- **Approver:** @developer
- **Granted:** 2026-03-04
- **Expires:** 2026-06-04
```

## Integration

Augie coordinates with:
- **Oscar** - Provides PASS/FAIL at gate checks
- **Sherlock** - Escalates suspicious security patterns

## Feedback Loops

Augie learns from its teammates:

| Source | Flow | Storage |
|--------|------|---------|
| Oscar → Augie | Lessons learned from issues | `rules/lessons-learned.yaml` |
| Sherlock → Augie | Patterns from investigations | `rules/lessons-learned.yaml` |
| User → Augie | Project-specific conventions | `rules/project/*.yaml` |

Use `/augie:lesson` to record new lessons. Use `/augie:why` to explain rule provenance.

## Rule Provenance

Every rule tracks its source:

```yaml
provenance:
  source: oscar-lesson  # oscar-lesson | sherlock-pattern | user-input | specification
  date: 2026-03-04
  context: "What triggered this rule"
  original_issue: null  # GitHub issue if applicable
```

## Maintenance

- Exemptions should be reviewed monthly
- Audit log rotates daily
- Reports retained for 90 days
- Run `/augie:trends` to review compliance patterns
