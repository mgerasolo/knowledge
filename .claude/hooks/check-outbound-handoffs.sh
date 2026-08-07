#!/bin/bash
# check-outbound-handoffs.sh - Check for state changes on handoffs YOU sent
# Run on UserPromptSubmit to notify when handoffs you're waiting on change state

set -euo pipefail

GRIST_API_KEY="${GRIST_API_KEY:-1753a7c6558accfa3ec02e8cf51a77c8bf443976}"
GRIST_URL="${GRIST_URL:-http://10.0.0.33:3390}"
DOC_ID="${GRIST_DOC_ID:-uNZG8PhepVScStYXVQKfR3}"
STATE_FILE="${CLAUDE_PROJECT_DIR:-.}/.claude/handoff-state.json"

# Get project ID
PROJECT="${PROJECT_ID:-}"
if [[ -z "$PROJECT" ]]; then
    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
    if [[ "$PROJECT_DIR" =~ Infrastructure ]]; then
        PROJECT="infrastructure"
    elif [[ "$PROJECT_DIR" =~ KnowledgeStack ]]; then
        PROJECT="knowledgestack"
    else
        PROJECT=$(curl -s "${GRIST_URL}/api/docs/${DOC_ID}/tables/Flow_Projects/records" \
            -H "Authorization: Bearer ${GRIST_API_KEY}" 2>/dev/null | \
            jq -r --arg path "$PROJECT_DIR" '.records[] | select(.fields.RootDir == $path) | .fields.ProjectId' | head -1)
        PROJECT="${PROJECT:-unknown}"
    fi
fi

[[ "$PROJECT" == "unknown" ]] && exit 0

# Query outbound handoffs (ones we sent that aren't closed)
response=$(curl -s "${GRIST_URL}/api/docs/${DOC_ID}/tables/AI_Handoffs/records" \
    -H "Authorization: Bearer ${GRIST_API_KEY}" 2>/dev/null || echo '{"records":[]}')

# Get current state of our outbound handoffs
current_state=$(echo "$response" | jq --arg proj "$PROJECT" '
    [.records[] | select(.fields.FromProject == $proj) | select(.fields.Status != "closed") |
    {id: .id, status: .fields.Status, title: .fields.Title, to: .fields.ToProject}]
' 2>/dev/null || echo "[]")

# Load previous state
previous_state="[]"
if [[ -f "$STATE_FILE" ]]; then
    previous_state=$(cat "$STATE_FILE" 2>/dev/null || echo "[]")
fi

# Save current state for next check
mkdir -p "$(dirname "$STATE_FILE")"
echo "$current_state" > "$STATE_FILE"

# Compare states and report changes
changes=""

while IFS= read -r handoff; do
    [[ -z "$handoff" || "$handoff" == "null" ]] && continue

    id=$(echo "$handoff" | jq -r '.id')
    status=$(echo "$handoff" | jq -r '.status')
    title=$(echo "$handoff" | jq -r '.title | .[0:50]')
    to_proj=$(echo "$handoff" | jq -r '.to')

    # Get previous status for this handoff
    prev_status=$(echo "$previous_state" | jq -r --argjson id "$id" '
        (.[] | select(.id == $id) | .status) // "new"
    ')

    # Detect state transitions
    if [[ "$prev_status" != "$status" ]]; then
        case "$status" in
            pending)
                [[ "$prev_status" == "new" ]] && continue
                ;;
            claimed)
                changes+="  📥 HO-${id} CLAIMED by ${to_proj}: ${title}\n"
                ;;
            in_progress)
                changes+="  🔄 HO-${id} IN PROGRESS (${to_proj}): ${title}\n"
                ;;
            done)
                changes+="  ✅ HO-${id} COMPLETED! Run: /handoff close ${id}\n     ${title}\n"
                ;;
            reopened)
                changes+="  🔁 HO-${id} REOPENED: ${title}\n"
                ;;
        esac
    fi
done < <(echo "$current_state" | jq -c '.[]')

# Output changes if any
if [[ -n "$changes" ]]; then
    echo "📬 HANDOFF UPDATES:"
    echo -e "$changes"
fi

# Show done items needing confirmation (always, not just on change)
done_list=$(echo "$current_state" | jq -r '.[] | select(.status == "done") | "  HO-\(.id): \(.title | .[0:40])..."')
if [[ -n "$done_list" ]]; then
    echo "⏳ Awaiting your confirmation (/handoff close):"
    echo "$done_list"
fi
