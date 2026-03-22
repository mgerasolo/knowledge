#!/bin/bash
# Ingest existing transcripts via n8n webhook
# This script reads transcript files and triggers n8n for processing

WEBHOOK_URL="https://n8n.nextlevelguild.com/webhook/youtube/transcript"
TRANSCRIPT_DIR="/mnt/foundry_resources/transcripts"
LOG_FILE="/tmp/spike_ingest.log"
DELAY_SECONDS=30  # Delay between requests to avoid rate limiting

echo "Starting transcript ingestion at $(date)" | tee -a "$LOG_FILE"

# Process each markdown file
find "$TRANSCRIPT_DIR" -name "*.md" -type f | while read -r file; do
    # Extract video URL from frontmatter
    video_url=$(grep -m1 "^url:" "$file" | sed 's/url: *//' | tr -d '"')

    if [ -n "$video_url" ]; then
        echo "Processing: $video_url" | tee -a "$LOG_FILE"

        # Trigger n8n webhook
        response=$(curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"url\": \"$video_url\"}" 2>&1)

        echo "  Response: $response" | tee -a "$LOG_FILE"

        # Rate limiting delay
        sleep "$DELAY_SECONDS"
    else
        echo "Skipping (no URL): $file" | tee -a "$LOG_FILE"
    fi
done

echo "Ingestion complete at $(date)" | tee -a "$LOG_FILE"
