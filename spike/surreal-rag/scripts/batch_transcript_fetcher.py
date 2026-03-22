#!/usr/bin/env python3
"""
Batch YouTube Transcript Fetcher

Fetches transcripts from YouTube channels with rate limiting and random delays.
Uses youtube-transcript-api (same method as Glasp and similar tools).

Usage:
    # Fetch all videos from channels (creates video list)
    python batch_transcript_fetcher.py --discover

    # Fetch transcripts in batches
    python batch_transcript_fetcher.py --fetch --batch-size 20

    # Continue from where you left off
    python batch_transcript_fetcher.py --fetch --resume
"""

import os
import sys
import json
import random
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

# Configuration
CONFIG = {
    "channels": [
        {"handle": "BibleStudyWithMyronGolden", "name": "Bible Study with Myron Golden", "domain": "religion", "lookback_months": 36},
        {"handle": "MyronGolden", "name": "Myron Golden", "domain": "business", "lookback_months": 36},
        {"handle": "AlexFinnOfficial", "name": "Alex Finn", "domain": "ai-automation", "lookback_months": 3},
        {"handle": "AILABS-393", "name": "AI Labs", "domain": "ai-coding", "lookback_months": 12},
        {"handle": "mreflow", "name": "MreFlow", "domain": "ai-coding", "lookback_months": 12},
    ],
    "output_dir": Path("/mnt/foundry_resources/transcripts"),
    "state_file": Path(__file__).parent / "fetch_state.json",
    "video_list_file": Path(__file__).parent / "video_list.json",
    "min_delay_seconds": 30,
    "max_delay_seconds": 400,  # Occasional longer gaps
    "batch_pause_seconds": 600,  # 10 min pause between batches
}


def random_delay():
    """Sleep for a random duration between min and max delay."""
    delay = random.randint(CONFIG["min_delay_seconds"], CONFIG["max_delay_seconds"])
    print(f"  Waiting {delay} seconds...")
    time.sleep(delay)


def get_channel_videos(handle: str, lookback_months: int) -> list[dict]:
    """Get all video IDs from a channel using yt-dlp."""
    print(f"\nDiscovering videos for @{handle}...")

    url = f"https://www.youtube.com/@{handle}/videos"

    # Use yt-dlp to get video metadata
    cmd = [
        "yt-dlp", "--flat-playlist",
        "--print", "%(id)s|%(title)s|%(upload_date)s",
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"  Error: {result.stderr[:200]}")
            return []

        videos = []
        cutoff_date = datetime.now() - timedelta(days=lookback_months * 30)

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue

            parts = line.split("|")
            if len(parts) >= 3:
                video_id, title, upload_date = parts[0], parts[1], parts[2]

                # Parse date and filter by lookback
                try:
                    if upload_date and upload_date != "NA":
                        vid_date = datetime.strptime(upload_date, "%Y%m%d")
                        if vid_date < cutoff_date:
                            continue
                except ValueError:
                    pass

                videos.append({
                    "id": video_id,
                    "title": title,
                    "upload_date": upload_date,
                    "channel_handle": handle
                })

        print(f"  Found {len(videos)} videos within lookback period")
        return videos

    except subprocess.TimeoutExpired:
        print(f"  Timeout getting videos for {handle}")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def discover_all_videos():
    """Discover videos from all channels and save to file."""
    all_videos = []

    for channel in CONFIG["channels"]:
        videos = get_channel_videos(channel["handle"], channel["lookback_months"])

        # Enrich with channel metadata
        for video in videos:
            video["channel_name"] = channel["name"]
            video["domain"] = channel["domain"]

        all_videos.extend(videos)

        # Small delay between channel discoveries
        time.sleep(5)

    # Save video list
    with open(CONFIG["video_list_file"], "w") as f:
        json.dump({
            "discovered_at": datetime.now().isoformat(),
            "total_videos": len(all_videos),
            "videos": all_videos
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Total videos discovered: {len(all_videos)}")
    print(f"Saved to: {CONFIG['video_list_file']}")

    # Estimate time
    avg_delay = (CONFIG["min_delay_seconds"] + CONFIG["max_delay_seconds"]) / 2
    total_hours = (len(all_videos) * avg_delay) / 3600
    print(f"Estimated fetch time: {total_hours:.1f} hours")
    print(f"{'='*60}")


def fetch_transcript(video_id: str) -> Optional[list[dict]]:
    """Fetch transcript for a single video with timestamps preserved."""
    try:
        # Create API instance (required in v1.2+)
        api = YouTubeTranscriptApi()

        # Fetch transcript directly - will get best available
        transcript = api.fetch(video_id)

        # Preserve timestamps: return list of {text, start, duration}
        segments = []
        for entry in transcript:
            segments.append({
                "text": entry.text,
                "start": entry.start,  # seconds from video start
                "duration": entry.duration,  # segment duration in seconds
            })
        return segments

    except TranscriptsDisabled:
        print(f"    Transcripts disabled for {video_id}")
        return None
    except VideoUnavailable:
        print(f"    Video unavailable: {video_id}")
        return None
    except Exception as e:
        print(f"    Error fetching {video_id}: {e}")
        return None


def fetch_video_description(video_id: str) -> Optional[str]:
    """Fetch video description using yt-dlp."""
    try:
        cmd = [
            "yt-dlp", "--skip-download",
            "--print", "%(description)s",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"    Could not fetch description: {e}")
    return None


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def save_transcript(video: dict, segments: list[dict], description: Optional[str] = None):
    """Save transcript as markdown file with timestamps preserved."""
    channel_dir = CONFIG["output_dir"] / video["channel_handle"].lower()

    # Parse upload date for directory structure
    upload_date = video.get("upload_date", "unknown")
    if upload_date and upload_date != "NA" and len(upload_date) == 8:
        year_month = f"{upload_date[:4]}-{upload_date[4:6]}"
        date_dir = channel_dir / year_month
        published_str = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    else:
        date_dir = channel_dir / "unknown"
        published_str = "unknown"

    date_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in video["title"])
    safe_title = safe_title[:80].strip().replace(" ", "-").lower()
    filename = f"{safe_title}.md"

    filepath = date_dir / filename

    # Escape description for YAML (multiline)
    desc_yaml = ""
    if description:
        # Use YAML literal block scalar for multiline
        desc_escaped = description.replace("\\", "\\\\")
        desc_yaml = f'\ndescription: |\n  ' + desc_escaped.replace("\n", "\n  ")

    # Format transcript with timestamps
    # Store as JSON array in frontmatter for machine parsing,
    # and human-readable format in body
    transcript_lines = []
    for seg in segments:
        ts = format_timestamp(seg["start"])
        transcript_lines.append(f"[{ts}] {seg['text']}")

    transcript_body = "\n".join(transcript_lines)

    # Also save raw segments as JSON for the loader
    segments_json = json.dumps(segments)

    content = f"""---
title: "{video['title'].replace('"', "'")}"
channel: "{video['channel_name']}"
video_id: "{video['id']}"
published: "{published_str}"
url: "https://youtube.com/watch?v={video['id']}"
fetched: "{datetime.now().strftime('%Y-%m-%d')}"
domain: "{video['domain']}"
segment_count: {len(segments)}
duration_seconds: {segments[-1]['start'] + segments[-1]['duration'] if segments else 0:.1f}
tags: []{desc_yaml}
---

## Transcript

{transcript_body}

<!-- RAW_SEGMENTS
{segments_json}
-->
"""

    filepath.write_text(content)
    return filepath


def load_state() -> dict:
    """Load fetch state from file."""
    if CONFIG["state_file"].exists():
        with open(CONFIG["state_file"]) as f:
            return json.load(f)
    return {"fetched": [], "failed": [], "skipped": []}


def save_state(state: dict):
    """Save fetch state to file."""
    with open(CONFIG["state_file"], "w") as f:
        json.dump(state, f, indent=2)


def fetch_batch(batch_size: int = 20, resume: bool = False):
    """Fetch transcripts in batches with delays."""

    # Load video list
    if not CONFIG["video_list_file"].exists():
        print("No video list found. Run with --discover first.")
        return

    with open(CONFIG["video_list_file"]) as f:
        data = json.load(f)

    videos = data["videos"]
    state = load_state() if resume else {"fetched": [], "failed": [], "skipped": []}

    # Filter out already processed videos
    processed_ids = set(state["fetched"] + state["failed"] + state["skipped"])
    pending = [v for v in videos if v["id"] not in processed_ids]

    print(f"\n{'='*60}")
    print(f"Total videos: {len(videos)}")
    print(f"Already processed: {len(processed_ids)}")
    print(f"Pending: {len(pending)}")
    print(f"Batch size: {batch_size}")
    print(f"{'='*60}\n")

    if not pending:
        print("All videos have been processed!")
        return

    # Process batch
    batch = pending[:batch_size]

    for i, video in enumerate(batch, 1):
        print(f"\n[{i}/{len(batch)}] {video['title'][:60]}...")
        print(f"  Video ID: {video['id']}")
        print(f"  Channel: {video['channel_name']}")

        segments = fetch_transcript(video["id"])

        if segments:
            # Fetch description (adds ~2s but worth it for metadata)
            description = fetch_video_description(video["id"])
            filepath = save_transcript(video, segments, description)
            print(f"  Saved: {filepath} ({len(segments)} segments)")
            state["fetched"].append(video["id"])
        else:
            state["failed"].append(video["id"])

        save_state(state)

        # Random delay before next video (unless last in batch)
        if i < len(batch):
            random_delay()

    # Summary
    print(f"\n{'='*60}")
    print(f"Batch complete!")
    print(f"  Fetched: {len([v for v in batch if v['id'] in state['fetched']])}")
    print(f"  Failed: {len([v for v in batch if v['id'] in state['failed']])}")
    print(f"  Remaining: {len(pending) - len(batch)}")

    if len(pending) > batch_size:
        print(f"\nRun again with --resume to continue fetching.")
        print(f"Suggested wait before next batch: {CONFIG['batch_pause_seconds'] // 60} minutes")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Batch YouTube Transcript Fetcher")
    parser.add_argument("--discover", action="store_true", help="Discover videos from all channels")
    parser.add_argument("--fetch", action="store_true", help="Fetch transcripts")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of videos per batch")
    parser.add_argument("--resume", action="store_true", help="Resume from last state")
    parser.add_argument("--status", action="store_true", help="Show current status")

    args = parser.parse_args()

    if args.status:
        state = load_state()
        print(f"Fetched: {len(state.get('fetched', []))}")
        print(f"Failed: {len(state.get('failed', []))}")
        print(f"Skipped: {len(state.get('skipped', []))}")
        return

    if args.discover:
        discover_all_videos()
    elif args.fetch:
        fetch_batch(batch_size=args.batch_size, resume=args.resume)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
