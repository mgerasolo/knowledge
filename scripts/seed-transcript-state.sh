#!/usr/bin/env bash
# Seed the transcript-service Docker volume with existing state
# from the spike scripts. Run once after first deploy.
#
# Usage: ./scripts/seed-transcript-state.sh

set -euo pipefail

CONTAINER="knowledge-transcript-service"
SPIKE_DIR="$(dirname "$0")/../spike/surreal-rag/scripts"

echo "=== Seeding transcript-service state ==="

# Check if state files exist
if [[ ! -f "$SPIKE_DIR/fetch_state.json" ]]; then
    echo "ERROR: $SPIKE_DIR/fetch_state.json not found"
    exit 1
fi

if [[ ! -f "$SPIKE_DIR/video_list.json" ]]; then
    echo "ERROR: $SPIKE_DIR/video_list.json not found"
    exit 1
fi

# Copy state files into the running container
echo "Copying fetch_state.json..."
docker cp "$SPIKE_DIR/fetch_state.json" "$CONTAINER:/data/state/fetch_state.json"

echo "Copying video_list.json..."
docker cp "$SPIKE_DIR/video_list.json" "$CONTAINER:/data/state/video_list.json"

echo ""
echo "=== Verifying ==="
docker exec "$CONTAINER" cat /data/state/fetch_state.json | python3 -c "
import json, sys
state = json.load(sys.stdin)
print(f'  Fetched: {len(state.get(\"fetched\", []))}')
print(f'  Failed:  {len(state.get(\"failed\", []))}')
print(f'  Skipped: {len(state.get(\"skipped\", []))}')
"

docker exec "$CONTAINER" cat /data/state/video_list.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'  Total videos: {data.get(\"total_videos\", 0)}')
print(f'  Discovered at: {data.get(\"discovered_at\", \"unknown\")}')
"

echo ""
echo "=== Done! ==="
echo "The service will now skip already-fetched videos during backfill."
echo "Check status: curl http://10.0.0.33:5025/api/status"
