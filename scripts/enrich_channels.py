#!/usr/bin/env python3
"""
Enrich channel metadata from YouTube.
Fetches avatars, descriptions, and other metadata for each channel.
"""

import requests
import re
import time
import json
import subprocess
import sys

# Database connection via Admin API
ADMIN_API = "https://knowledge-admin.nextlevelguild.com"

def get_channels():
    """Fetch all channels from the Admin API."""
    resp = requests.get(
        f"{ADMIN_API}/api/v1/channels",
        params={"limit": 100},
        headers={"Host": "knowledge-admin.nextlevelguild.com"},
        verify=False  # For local testing
    )
    return resp.json().get("channels", [])

def fetch_channel_metadata(youtube_handle):
    """Fetch channel metadata from YouTube page."""
    url = f"https://www.youtube.com/@{youtube_handle}"
    try:
        resp = requests.get(url, timeout=30)
        html = resp.text

        # Extract avatar URL
        avatar_match = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)', html)
        avatar_url = avatar_match.group(1) if avatar_match else None

        # Extract subscriber count (approximate)
        sub_match = re.search(r'"subscriberCountText":\{"simpleText":"([^"]+)', html)
        sub_text = sub_match.group(1) if sub_match else None

        # Extract channel description
        desc_match = re.search(r'"description":\{"simpleText":"([^"]+)', html)
        description = desc_match.group(1) if desc_match else None

        return {
            "thumbnail_url": avatar_url,
            "subscriber_text": sub_text,
            "description": description
        }
    except Exception as e:
        print(f"  Error fetching {youtube_handle}: {e}")
        return None

def update_channel_metadata(channel_id, metadata):
    """Update channel metadata via direct database call."""
    if not metadata or not metadata.get("thumbnail_url"):
        return False

    # Build SQL update
    sql_parts = []
    if metadata.get("thumbnail_url"):
        sql_parts.append(f"thumbnail_url = '{metadata['thumbnail_url']}'")
    if metadata.get("description"):
        # Escape single quotes
        desc = metadata['description'].replace("'", "''")[:500]
        sql_parts.append(f"description = '{desc}'")

    if not sql_parts:
        return False

    sql = f"UPDATE channels SET {', '.join(sql_parts)} WHERE id = '{channel_id}'::uuid;"

    # Execute via SSH to Banner
    cmd = f'ssh banner "docker exec knowledge-postgres psql -U knowledge -d knowledge -c \\"{sql}\\""'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return "UPDATE 1" in result.stdout

def main():
    print("Fetching channels...")
    channels = get_channels()
    print(f"Found {len(channels)} channels")

    # Filter to channels without thumbnails
    to_enrich = [c for c in channels if not c.get("thumbnail_url")]
    print(f"{len(to_enrich)} channels need enrichment")

    for i, channel in enumerate(to_enrich):
        handle = channel.get("youtube_handle")
        print(f"[{i+1}/{len(to_enrich)}] Enriching {handle}...")

        metadata = fetch_channel_metadata(handle)
        if metadata:
            success = update_channel_metadata(channel["id"], metadata)
            print(f"  Avatar: {metadata.get('thumbnail_url', 'none')[:60]}...")
            print(f"  Updated: {success}")

        # Rate limit: 5 second delay
        time.sleep(5)

    print("\nDone!")

if __name__ == "__main__":
    main()
