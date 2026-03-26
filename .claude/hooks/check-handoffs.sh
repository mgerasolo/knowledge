#!/bin/bash
# check-handoffs.sh - Check for handoffs on session start
# Queries Grist AI_Handoffs table for:
# - Incoming: items targeting current project
# - Outbound: items FROM current project awaiting response

set -euo pipefail

GRIST_API_KEY="1753a7c6558accfa3ec02e8cf51a77c8bf443976"
GRIST_URL="http://10.0.0.33:3390"
DOC_ID="uNZG8PhepVScStYXVQKfR3"

# Detect project from directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if [[ "$PROJECT_DIR" =~ Infrastructure ]]; then
    PROJECT="infrastructure"
elif [[ "$PROJECT_DIR" =~ KnowledgeStack ]]; then
    PROJECT="knowledgestack"
elif [[ "$PROJECT_DIR" =~ the-keep ]]; then
    PROJECT="the-keep"
else
    # Try to detect from Grist Flow_Projects
    PROJECT=$(curl -s "${GRIST_URL}/api/docs/${DOC_ID}/tables/Flow_Projects/records" \
        -H "Authorization: Bearer ${GRIST_API_KEY}" 2>/dev/null | \
        jq -r --arg path "$PROJECT_DIR" '.records[] | select(.fields.RootDir == $path) | .fields.ProjectId' | head -1)
    PROJECT="${PROJECT:-unknown}"
fi

# Query all handoffs
response=$(curl -s -X GET "${GRIST_URL}/api/docs/${DOC_ID}/tables/AI_Handoffs/records" \
    -H "Authorization: Bearer ${GRIST_API_KEY}" 2>/dev/null || echo '{"records":[]}')

# Count INCOMING pending handoffs (to this project)
pending=$(echo "$response" | jq --arg proj "$PROJECT" '[.records[] | select(.fields.ToProject == $proj) | select(.fields.Status == "pending" or .fields.Status == "reopened")] | length' 2>/dev/null || echo "0")

# Count INCOMING active handoffs (claimed by us)
active=$(echo "$response" | jq --arg proj "$PROJECT" '[.records[] | select(.fields.ToProject == $proj) | select(.fields.Status == "claimed" or .fields.Status == "in_progress")] | length' 2>/dev/null || echo "0")

# Count OUTBOUND handoffs awaiting response (we sent, waiting for completion)
outbound_pending=$(echo "$response" | jq --arg proj "$PROJECT" '[.records[] | select(.fields.FromProject == $proj) | select(.fields.Status == "pending" or .fields.Status == "claimed" or .fields.Status == "in_progress")] | length' 2>/dev/null || echo "0")

# Count OUTBOUND done (awaiting our confirmation)
outbound_done=$(echo "$response" | jq --arg proj "$PROJECT" '[.records[] | select(.fields.FromProject == $proj) | select(.fields.Status == "done")] | length' 2>/dev/null || echo "0")

if [[ "$pending" -gt 0 ]] || [[ "$active" -gt 0 ]] || [[ "$outbound_done" -gt 0 ]]; then
    echo "📬 HANDOFFS:"

    # Incoming pending
    if [[ "$pending" -gt 0 ]]; then
        echo "  📥 ${pending} INCOMING (need action):"
        echo "$response" | jq -r --arg proj "$PROJECT" '
            .records[] |
            select(.fields.ToProject == $proj) |
            select(.fields.Status == "pending" or .fields.Status == "reopened") |
            "    HO-\(.id): [\(.fields.FromProject)] \(.fields.Title | .[0:50])"
        ' 2>/dev/null || true
    fi

    # Incoming active
    if [[ "$active" -gt 0 ]]; then
        echo "  🔄 ${active} IN PROGRESS:"
        echo "$response" | jq -r --arg proj "$PROJECT" '
            .records[] |
            select(.fields.ToProject == $proj) |
            select(.fields.Status == "claimed" or .fields.Status == "in_progress") |
            "    HO-\(.id): [\(.fields.FromProject)] \(.fields.Title | .[0:50])"
        ' 2>/dev/null || true
    fi

    # Outbound done - needs confirmation
    if [[ "$outbound_done" -gt 0 ]]; then
        echo "  ✅ ${outbound_done} COMPLETED (confirm with /handoff close):"
        echo "$response" | jq -r --arg proj "$PROJECT" '
            .records[] |
            select(.fields.FromProject == $proj) |
            select(.fields.Status == "done") |
            "    HO-\(.id): [\(.fields.ToProject)] \(.fields.Title | .[0:50])"
        ' 2>/dev/null || true
    fi

    echo "Run: /handoff"
fi