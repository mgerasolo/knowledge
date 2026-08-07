#!/bin/bash
# Fetch recent AI-focused videos (last 3 weeks) with proper timestamps
# Focus: AI Labs, MreFlow - skip OpenClaw/Alex Finn per user

WEBHOOK_URL="https://n8n.nextlevelguild.com/webhook/youtube/transcript"
STATE_FILE="$(dirname "$0")/fetch_state.json"
LOG_FILE="/tmp/fetch_recent_ai.log"
DELAY_SECONDS=30  # Faster for recent content

# AI-focused channels only
declare -A CHANNELS=(
    ["AILABS-393"]="ai-coding"
    ["mreflow"]="ai-coding"
    ["ColeMedin"]="ai-coding"  # Cole Medin - Claude Code content
    ["IndyDevDan"]="ai-coding" # Indy Dev Dan
    ["AICodeKing"]="ai-coding" # AI Code King
)

# Date filter: 3 weeks ago
CUTOFF_DATE=$(date -d "3 weeks ago" +%Y%m%d)

echo "============================================================" | tee -a "$LOG_FILE"
echo "Re-fetch Recent AI Content (since $CUTOFF_DATE)" | tee -a "$LOG_FILE"
echo "Webhook: $WEBHOOK_URL" | tee -a "$LOG_FILE"
echo "Started: $(date)" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

# Load existing state
if [ -f "$STATE_FILE" ]; then
    FETCHED=$(jq -r '.fetched[]' "$STATE_FILE" 2>/dev/null | tr '\n' ' ')
else
    FETCHED=""
fi

total_fetched=0
total_skipped=0

for channel in "${!CHANNELS[@]}"; do
    domain="${CHANNELS[$channel]}"
    echo "" | tee -a "$LOG_FILE"
    echo "Channel: @$channel ($domain)" | tee -a "$LOG_FILE"

    # Use yt-dlp to get recent videos with metadata
    video_data=$(yt-dlp --flat-playlist --dump-json \
        "https://www.youtube.com/@${channel}/videos" 2>/dev/null | \
        jq -r 'select(.upload_date >= "'$CUTOFF_DATE'") | "\(.id) \(.upload_date) \(.title)"' 2>/dev/null | \
        head -30)

    if [ -z "$video_data" ]; then
        echo "  No recent videos found (or yt-dlp failed)" | tee -a "$LOG_FILE"
        continue
    fi

    count=0
    while IFS= read -r line; do
        video_id=$(echo "$line" | awk '{print $1}')
        upload_date=$(echo "$line" | awk '{print $2}')
        title=$(echo "$line" | cut -d' ' -f3-)

        # Skip if already fetched
        if echo "$FETCHED" | grep -q "$video_id"; then
            echo "  [SKIP] $video_id - already fetched" | tee -a "$LOG_FILE"
            ((total_skipped++))
            continue
        fi

        video_url="https://www.youtube.com/watch?v=${video_id}"
        echo "  [FETCH] $upload_date: $title" | tee -a "$LOG_FILE"

        response=$(curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$video_url\"}" 2>&1)

        # Check response
        if echo "$response" | grep -qi "error"; then
            echo "    ERROR: $response" | tee -a "$LOG_FILE"
        else
            echo "    OK" | tee -a "$LOG_FILE"
            ((count++))
            ((total_fetched++))

            # Update state file
            jq --arg id "$video_id" '.fetched += [$id]' "$STATE_FILE" > "${STATE_FILE}.tmp" && \
                mv "${STATE_FILE}.tmp" "$STATE_FILE"
        fi

        sleep "$DELAY_SECONDS"
    done <<< "$video_data"

    echo "  Processed: $count new videos" | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo "Complete: $(date)" | tee -a "$LOG_FILE"
echo "Fetched: $total_fetched new | Skipped: $total_skipped existing" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
