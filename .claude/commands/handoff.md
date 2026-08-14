# /handoff - Cross-Project Handoffs

Manage cross-project work requests via Grist.

## Usage

```
/handoff                    # Show summary + pending inbox
/handoff inbox              # Show incoming handoffs
/handoff outbox             # Show handoffs you sent
/handoff view <id>          # View details + conversation thread
/handoff claim <id>         # Take ownership
/handoff update <id> <msg>  # Add comment to thread
/handoff done <id> [notes]  # Mark complete
/handoff close <id>         # Confirm resolved (sender only)
/handoff send <proj> <title># Create handoff to another project
/handoff projects           # List valid project IDs
```

## Quick Reference

| Status | Meaning |
|--------|---------|
| `pending` | Waiting for receiver to claim |
| `claimed` | Receiver has taken ownership |
| `in_progress` | Work underway |
| `done` | Receiver marked complete, awaiting sender confirmation |
| `closed` | Sender confirmed, handoff complete |
| `reopened` | Sender rejected, needs more work |

## Lifecycle

```
Sender creates → pending
Receiver claims → claimed
Receiver works → in_progress
Receiver finishes → done (awaiting confirmation)
Sender confirms → closed
  OR
Sender rejects → reopened → back to receiver
```

## Implementation

This command wraps `/mnt/foundry_devlab/scripts/handoffs.sh`.

**When user invokes `/handoff`:**

1. Run the appropriate `handoffs.sh` subcommand
2. Display results formatted for conversation

### Default (no args) - Show Summary

```bash
/mnt/foundry_devlab/scripts/handoffs.sh
```

Shows: inbox count, outbox count, pending items needing action.

### View Specific Handoff

```bash
/mnt/foundry_devlab/scripts/handoffs.sh view <id>
```

Shows: full details, context, and conversation thread.

### Claim Handoff

```bash
/mnt/foundry_devlab/scripts/handoffs.sh claim <id>
```

Takes ownership. Notifies sender via ntfy.

### Add Update

```bash
/mnt/foundry_devlab/scripts/handoffs.sh update <id> "<message>"
```

Adds comment to thread. Use for questions, progress updates, blockers.

### Mark Done

```bash
/mnt/foundry_devlab/scripts/handoffs.sh done <id> "<resolution>" [--verify "<command>"]
```

Marks complete with optional verification command. Notifies sender.

### Send New Handoff

```bash
/mnt/foundry_devlab/scripts/handoffs.sh send <project> "<title>" [--priority high] [--blocked] [--context "<text>"]
```

Creates handoff to another project. Options:
- `--priority`: critical, high, medium, low
- `--blocked`: Mark yourself as blocked waiting
- `--context`: Additional context text

## Storage

| Component | Location |
|-----------|----------|
| **Table** | `AI_Handoffs` in Grist |
| **Comments** | `AI_Handoff_Comments` table |
| **Notifications** | ntfy channels per project |

## Difference from /inbox

| Command | Purpose |
|---------|---------|
| `/inbox` | Query SurrealDB knowledge store (saved articles, research) |
| `/handoff` | Cross-project work requests (Grist-based task handoffs) |

## Auto-Detect Project

The script auto-detects current project from:
1. `$PROJECT_ID` environment variable
2. Current directory matched against Grist `Flow_Projects` table

If detection fails, shows as "unknown" - set `PROJECT_ID` or add project to Grist.

## Example Session

```
User: /handoff
AI: [runs handoffs.sh, shows summary]

=== AI Handoffs Summary ===
Current project: infrastructure
Inbox: 1 pending, 0 active
Outbox: 0 open

Pending handoffs for you:
  HO-3: [knowledgestack] Implement KnowledgeEnroll n8n workflows

User: /handoff view 3
AI: [runs handoffs.sh view 3, shows full details]

User: /handoff claim 3
AI: [claims handoff, sender notified]

User: /handoff update 3 "Starting on RSS Monitor workflow first"
AI: [adds comment to thread]

User: /handoff done 3 "All 3 workflows deployed to n8n" --verify "curl https://n8n.nextlevelguild.com/api/health"
AI: [marks done, sender notified to confirm]
```
