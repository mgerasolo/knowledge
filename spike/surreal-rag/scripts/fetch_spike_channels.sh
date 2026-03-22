#!/bin/bash
# Fetch videos from spike channels via n8n webhook
# Runs in background with rate limiting

WEBHOOK_URL="https://n8n.nextlevelguild.com/webhook/youtube/transcript"
LOG_FILE="/tmp/spike_channel_fetch.log"
DELAY_SECONDS=60  # Delay between requests

# Spike channel handles
CHANNELS=(
    "BibleStudyWithMyronGolden"
    "MyronGolden"
    "AlexFinnOfficial"
    "AILABS-393"
    "mreflow"
)

echo "=== Starting spike channel fetch at $(date) ===" | tee -a "$LOG_FILE"

for channel in "${CHANNELS[@]}"; do
    echo "Fetching videos for: $channel" | tee -a "$LOG_FILE"

    # Get recent video IDs using yt-dlp (if available) or YouTube RSS
    # For now, we'll trigger with channel URL and let n8n handle it
    channel_url="https://www.youtube.com/@${channel}/videos"

    # Get video IDs from the channel page
    video_ids=$(curl -s "$channel_url" 2>/dev/null | grep -oP '"videoId":"[^"]+"' | head -20 | sed 's/"videoId":"//g' | tr -d '"' | sort -u)

    if [ -z "$video_ids" ]; then
        echo "  No videos found for $channel, trying RSS..." | tee -a "$LOG_FILE"
        continue
    fi

    count=0
    for video_id in $video_ids; do
        video_url="https://www.youtube.com/watch?v=${video_id}"
        echo "  Fetching: $video_url" | tee -a "$LOG_FILE"

        response=$(curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$video_url\"}" 2>&1)

        echo "    Response: $response" | tee -a "$LOG_FILE"

        count=$((count + 1))

        # Rate limiting
        sleep "$DELAY_SECONDS"
    done

    echo "  Processed $count videos for $channel" | tee -a "$LOG_FILE"
done

echo "=== Spike channel fetch complete at $(date) ===" | tee -a "$LOG_FILE"
