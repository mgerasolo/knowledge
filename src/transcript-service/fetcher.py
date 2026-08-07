"""
Transcript fetching and discovery logic.

Extracted and adapted from spike/surreal-rag/scripts/batch_transcript_fetcher.py
for use as a service rather than CLI tool.
"""

import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

from config import Config


# ---- State Management ----

def _state_path() -> Path:
    return Path(Config.STATE_DIR) / "fetch_state.json"


def _video_list_path() -> Path:
    return Path(Config.STATE_DIR) / "video_list.json"


def load_state() -> dict:
    """Load fetch state from file."""
    path = _state_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"fetched": [], "failed": [], "skipped": []}


def save_state(state: dict):
    """Save fetch state to file."""
    Path(Config.STATE_DIR).mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps(state, indent=2))


def load_video_list() -> dict:
    """Load the full video list."""
    path = _video_list_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"discovered_at": None, "total_videos": 0, "videos": []}


def save_video_list(data: dict):
    """Save the video list."""
    Path(Config.STATE_DIR).mkdir(parents=True, exist_ok=True)
    _video_list_path().write_text(json.dumps(data, indent=2))


def get_status() -> dict:
    """Get overall ingestion status."""
    state = load_state()
    video_list = load_video_list()

    fetched = len(state.get("fetched", []))
    failed = len(state.get("failed", []))
    skipped = len(state.get("skipped", []))
    total = video_list.get("total_videos", 0)
    pending = total - fetched - failed - skipped

    return {
        "total_videos": total,
        "fetched": fetched,
        "failed": failed,
        "skipped": skipped,
        "pending": max(0, pending),
        "discovered_at": video_list.get("discovered_at"),
        "channels": len(Config.CHANNELS),
    }


def get_pending(limit: int = 8) -> list[dict]:
    """Get the next N pending videos for backfill."""
    state = load_state()
    video_list = load_video_list()

    processed_ids = set(
        state.get("fetched", [])
        + state.get("failed", [])
        + state.get("skipped", [])
    )

    pending = [
        v for v in video_list.get("videos", []) if v["id"] not in processed_ids
    ]

    return pending[:limit]


# ---- Video Discovery ----

def discover_channel(handle: str, lookback_months: int) -> list[dict]:
    """Discover videos from a single channel using yt-dlp."""
    url = f"https://www.youtube.com/@{handle}/videos"

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(id)s|%(title)s|%(upload_date)s",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return []

        videos = []
        cutoff_date = datetime.now() - timedelta(days=lookback_months * 30)

        for line in result.stdout.strip().split("\n"):
            if not line or "|" not in line:
                continue

            parts = line.split("|", 2)
            if len(parts) >= 3:
                video_id, title, upload_date = parts[0], parts[1], parts[2]

                try:
                    if upload_date and upload_date != "NA":
                        vid_date = datetime.strptime(upload_date, "%Y%m%d")
                        if vid_date < cutoff_date:
                            continue
                except ValueError:
                    pass

                videos.append(
                    {"id": video_id, "title": title, "upload_date": upload_date}
                )

        return videos

    except (subprocess.TimeoutExpired, Exception):
        return []


def discover_new_videos(lookback_days: int = 7, on_progress=None) -> dict:
    """Check all channels for new videos not yet in our state.

    Returns dict with new_videos list and per-channel stats.

    `on_progress(index, total, handle)` is called before each channel so a
    long-running discovery can keep a liveness heartbeat fresh — a full sweep of
    50 channels takes several minutes, which otherwise looks like a hung worker.

    IMPORTANT — why this looks at only the newest N uploads per channel:
    `--dateafter` does NOT work with `--flat-playlist`, because flat mode never
    populates upload_date (yt-dlp prints "NA"). The date filter is therefore
    silently inert, and a sweep returns each channel's ENTIRE back catalogue.
    On 2026-08-07 that queued 40,072 videos in one run — months of fetching and
    an unreasonable scraping load — instead of the intended two weeks of new
    uploads. Channels list newest-first, so capping the listing with
    `--playlist-end` is what actually bounds this.
    """
    state = load_state()
    video_list = load_video_list()

    processed_ids = set(
        state.get("fetched", [])
        + state.get("failed", [])
        + state.get("skipped", [])
    )
    known_ids = {v["id"] for v in video_list.get("videos", [])}

    new_videos = []
    channel_stats = []

    # Discovery hits YouTube once per channel (50 of them). The project rule is a
    # minimum 2s gap when making more than 5 external calls in a batch; without
    # it this loop fires ~50 requests back to back and risks throttling.
    discovery_delay = float(os.getenv("DISCOVERY_DELAY_SECONDS", "3"))

    # How many of each channel's most recent uploads to consider. This — not
    # --dateafter — is what keeps a sweep bounded. Anything already known is
    # skipped, so this only needs to exceed a channel's upload rate between
    # runs, with generous headroom.
    listing_cap = int(os.getenv("DISCOVERY_PLAYLIST_END", "25"))

    total_channels = len(Config.CHANNELS)
    for index, channel in enumerate(Config.CHANNELS):
        if index > 0:
            time.sleep(discovery_delay)
        handle = channel["handle"]
        if on_progress:
            on_progress(index + 1, total_channels, handle)
        date_after = (
            datetime.now() - timedelta(days=lookback_days)
        ).strftime("%Y%m%d")

        # Use yt-dlp with date filter for efficiency
        url = f"https://www.youtube.com/@{handle}/videos"
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--playlist-end",
            str(listing_cap),
            "--dateafter",
            date_after,   # inert in flat mode; kept only for when that changes
            "--print",
            "%(id)s|%(title)s|%(upload_date)s",
            url,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            found = 0
            new_count = 0

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line or "|" not in line:
                        continue

                    parts = line.split("|", 2)
                    if len(parts) >= 3:
                        video_id, title, upload_date = (
                            parts[0],
                            parts[1],
                            parts[2],
                        )
                        found += 1

                        if (
                            video_id not in processed_ids
                            and video_id not in known_ids
                        ):
                            video = {
                                "id": video_id,
                                "title": title,
                                "upload_date": upload_date,
                                "channel_handle": handle,
                                "channel_name": channel["name"],
                                "domain": channel["domain"],
                            }
                            new_videos.append(video)
                            new_count += 1

            channel_stats.append(
                {
                    "handle": handle,
                    "name": channel["name"],
                    "recent_videos": found,
                    "new_videos": new_count,
                }
            )

        except (subprocess.TimeoutExpired, Exception) as e:
            channel_stats.append(
                {
                    "handle": handle,
                    "name": channel["name"],
                    "error": str(e),
                }
            )

    # Safety valve. A single sweep should surface tens of new uploads, not
    # thousands; anything larger means a filter broke (as --dateafter silently
    # did on 2026-08-07, queueing 40,072). Refuse the run rather than commit a
    # queue that would take months to drain and hammer YouTube doing it.
    max_new = int(os.getenv("DISCOVERY_MAX_NEW", "500"))
    if len(new_videos) > max_new:
        print(
            f"[discovery] ABORTED: {len(new_videos)} new videos exceeds the "
            f"{max_new} limit — this indicates a broken filter, not a real "
            f"backlog. Nothing was added. Raise DISCOVERY_MAX_NEW deliberately "
            f"if a bulk import is actually intended.",
            flush=True,
        )
        return {
            "new_videos": [],
            "channels_checked": len(channel_stats),
            "channel_stats": channel_stats,
            "aborted": True,
            "would_have_added": len(new_videos),
        }

    # Add new videos to the master list
    if new_videos:
        existing_videos = video_list.get("videos", [])
        existing_videos.extend(new_videos)
        video_list["videos"] = existing_videos
        video_list["total_videos"] = len(existing_videos)
        video_list["last_discovery"] = datetime.now().isoformat()
        save_video_list(video_list)

    return {
        "new_videos": new_videos,
        "new_count": len(new_videos),
        "channel_stats": channel_stats,
        "checked_at": datetime.now().isoformat(),
    }


# ---- Transcript Fetching ----

def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def fetch_transcript(video_id: str) -> Optional[list[dict]]:
    """Fetch transcript segments for a single video."""
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)

        segments = []
        for entry in transcript:
            segments.append(
                {
                    "text": entry.text,
                    "start": entry.start,
                    "duration": entry.duration,
                }
            )
        return segments

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception:
        return None


def fetch_description(video_id: str) -> Optional[str]:
    """Fetch video description using yt-dlp."""
    try:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--print",
            "%(description)s",
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def save_transcript_file(video: dict, segments: list[dict], description: Optional[str] = None) -> str:
    """Save transcript as markdown file. Returns the file path."""
    transcript_dir = Path(Config.TRANSCRIPT_DIR)
    channel_handle = video.get("channel_handle", "unknown").lower()
    channel_dir = transcript_dir / channel_handle

    # Parse upload date for directory structure
    upload_date = video.get("upload_date", "unknown")
    if upload_date and upload_date != "NA" and len(upload_date) == 8:
        year_month = f"{upload_date[:4]}-{upload_date[4:6]}"
        date_dir = channel_dir / year_month
        published_str = (
            f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
        )
    else:
        date_dir = channel_dir / "unknown"
        published_str = "unknown"

    date_dir.mkdir(parents=True, exist_ok=True)

    # Create safe filename
    title = video.get("title", "untitled")
    safe_title = "".join(
        c if c.isalnum() or c in " -_" else "" for c in title
    )
    safe_title = safe_title[:80].strip().replace(" ", "-").lower()
    filename = f"{safe_title}.md"
    filepath = date_dir / filename

    # Format transcript with timestamps
    transcript_lines = []
    for seg in segments:
        ts = _format_timestamp(seg["start"])
        transcript_lines.append(f"[{ts}] {seg['text']}")
    transcript_body = "\n".join(transcript_lines)

    # Raw segments JSON for machine parsing
    segments_json = json.dumps(segments)

    # Build description YAML block
    desc_yaml = ""
    if description:
        desc_escaped = description.replace("\\", "\\\\")
        desc_yaml = (
            "\ndescription: |\n  "
            + desc_escaped.replace("\n", "\n  ")
        )

    # Channel name
    channel_name = video.get("channel_name", channel_handle)

    # Duration
    duration = 0.0
    if segments:
        last = segments[-1]
        duration = last["start"] + last.get("duration", 0)

    escaped_title = title.replace('"', "'")

    content = f"""---
title: "{escaped_title}"
channel: "{channel_name}"
video_id: "{video['id']}"
published: "{published_str}"
url: "https://youtube.com/watch?v={video['id']}"
fetched: "{datetime.now().strftime('%Y-%m-%d')}"
domain: "{video.get('domain', 'unknown')}"
segment_count: {len(segments)}
duration_seconds: {duration:.1f}
tags: []{desc_yaml}
---

## Transcript

{transcript_body}

<!-- RAW_SEGMENTS
{segments_json}
-->
"""

    filepath.write_text(content)
    return str(filepath)


def fetch_and_save(video: dict) -> dict:
    """Fetch transcript for a video and save to disk. Updates state.

    Args:
        video: dict with at minimum 'id'. Optional: title, channel_handle,
               channel_name, domain, upload_date.

    Returns:
        dict with success, video_id, file_path, segment_count, error.
    """
    video_id = video["id"]
    state = load_state()

    # Check if already fetched
    if video_id in state.get("fetched", []):
        return {
            "success": True,
            "video_id": video_id,
            "already_fetched": True,
            "message": "Already fetched",
        }

    # Fetch transcript
    segments = fetch_transcript(video_id)

    if not segments:
        state.setdefault("failed", []).append(video_id)
        save_state(state)
        return {
            "success": False,
            "video_id": video_id,
            "error": "No transcript available",
        }

    # Fetch description
    description = fetch_description(video_id)

    # Enrich video data if needed
    if not video.get("channel_handle"):
        video["channel_handle"] = "unknown"
    if not video.get("channel_name"):
        video["channel_name"] = video["channel_handle"]

    # Save to file
    filepath = save_transcript_file(video, segments, description)

    # Update state
    state.setdefault("fetched", []).append(video_id)
    # Remove from failed if it was there (retry succeeded)
    if video_id in state.get("failed", []):
        state["failed"].remove(video_id)
    save_state(state)

    # Push into the search index. Without this the file archive grows while the
    # searchable corpus does not — EMBEDDING_SERVICE_URL was configured in three
    # places and called from none, so everything this worker fetched was
    # invisible to every consumer of the API (found 2026-08-07).
    indexed, index_error = _index_video(video, segments, description)

    return {
        "success": True,
        "video_id": video_id,
        "file_path": filepath,
        "segment_count": len(segments),
        "has_description": description is not None,
        "indexed": indexed,
        "index_error": index_error,
    }


def _index_video(video: dict, segments: list, description) -> tuple:
    """Send a freshly fetched transcript to the embedding service.

    Returns (indexed, error). The transcript file is already safely on disk by
    this point, so an indexing failure is reported but not raised — the file can
    always be replayed later with scripts/reindex_from_files.py.
    """
    payload = {
        "video_id": video["id"],
        "title": video.get("title", ""),
        "url": f"https://youtube.com/watch?v={video['id']}",
        "channel_handle": video.get("channel_handle", "unknown"),
        "channel_name": video.get("channel_name", ""),
        "domain": video.get("domain", "general"),
        "description": description or "",
        "segments": segments,
        "skip_embeddings": True,   # no semantic search consumes embeddings yet
    }

    try:
        r = requests.post(
            f"{Config.EMBEDDING_SERVICE_URL}/api/embed",
            json=payload,
            timeout=120,
        )
    except Exception as e:
        return False, f"embedding service unreachable: {e}"

    if not r.ok:
        return False, f"embedding service returned HTTP {r.status_code}"

    try:
        body = r.json()
    except ValueError:
        return False, "embedding service response was not JSON"

    # embed_video() reports real write failures now, so trust its verdict
    # rather than the status code alone.
    if not body.get("success"):
        return False, str(body.get("error", "indexing reported failure"))
    return True, None
