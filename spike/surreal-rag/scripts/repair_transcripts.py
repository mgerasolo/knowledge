#!/usr/bin/env python3
"""
Repair Transcripts - Fix missing upload dates without re-fetching

This script:
1. Finds transcripts in 'unknown' folders
2. Extracts video_id from frontmatter
3. Fetches actual upload date from YouTube via yt-dlp
4. Updates frontmatter with correct date
5. Moves file to proper date folder

Usage:
    python repair_transcripts.py --scan          # Show what needs repair
    python repair_transcripts.py --repair        # Actually repair files
    python repair_transcripts.py --repair --dry-run  # Preview without changes
"""

import os
import re
import sys
import argparse
import subprocess
import time
import random
from pathlib import Path
from datetime import datetime
import shutil

# Configuration
TRANSCRIPTS_DIR = Path("/mnt/foundry_resources/transcripts")
STATE_FILE = Path(__file__).parent / "repair_state.json"

# Human-like rate limiting
MIN_DELAY = 8       # Minimum seconds between requests
MAX_DELAY = 25      # Maximum seconds between requests
BATCH_SIZE = 15     # Take a longer break every N files
BATCH_PAUSE_MIN = 60   # Minimum batch pause (seconds)
BATCH_PAUSE_MAX = 180  # Maximum batch pause (seconds)


def load_repair_state() -> set:
    """Load set of already-repaired video IDs."""
    if STATE_FILE.exists():
        import json
        with open(STATE_FILE) as f:
            return set(json.load(f).get("repaired", []))
    return set()


def save_repair_state(repaired: set):
    """Save repaired video IDs to state file."""
    import json
    with open(STATE_FILE, "w") as f:
        json.dump({"repaired": list(repaired), "updated": datetime.now().isoformat()}, f, indent=2)

def extract_frontmatter(filepath: Path) -> dict:
    """Extract frontmatter from markdown file."""
    content = filepath.read_text()

    if not content.startswith("---"):
        return {}

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}

    frontmatter = content[3:end_idx]
    data = {}

    for line in frontmatter.strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"').strip("'")

    return data


def get_video_metadata(video_id: str) -> dict:
    """Get video metadata from YouTube via yt-dlp."""
    cmd = [
        "yt-dlp", "--skip-download",
        "--print", "%(upload_date)s|%(duration)s|%(description)s",
        f"https://www.youtube.com/watch?v={video_id}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            parts = result.stdout.strip().split("|", 2)
            if len(parts) >= 2:
                return {
                    "upload_date": parts[0] if parts[0] != "NA" else None,
                    "duration_seconds": int(parts[1]) if parts[1].isdigit() else None,
                    "description": parts[2] if len(parts) > 2 else None
                }
    except Exception as e:
        print(f"    Error fetching metadata: {e}")

    return {}


def repair_file(filepath: Path, dry_run: bool = False) -> bool:
    """Repair a single transcript file."""
    print(f"\n  Processing: {filepath.name}")

    # Extract current frontmatter
    fm = extract_frontmatter(filepath)
    video_id = fm.get("video_id")

    if not video_id:
        print(f"    SKIP: No video_id in frontmatter")
        return False

    print(f"    Video ID: {video_id}")

    # Get actual metadata from YouTube
    meta = get_video_metadata(video_id)

    if not meta.get("upload_date"):
        print(f"    SKIP: Could not fetch upload date")
        return False

    upload_date = meta["upload_date"]
    formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    folder_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

    print(f"    Upload date: {formatted_date}")

    # Read file content
    content = filepath.read_text()

    # Fix the broken published field - match entire line including broken template
    # Pattern matches: published: "..." or published: "..." if len... etc.
    content = re.sub(
        r'^published:.*$',
        f'published: "{formatted_date}"',
        content,
        flags=re.MULTILINE
    )

    # Add duration_seconds if we have it and it's not already there
    if meta.get("duration_seconds"):
        frontmatter_section = content.split("---")[1] if "---" in content else ""
        if "duration_seconds:" not in frontmatter_section and "duration:" not in frontmatter_section:
            # Insert after published line
            content = re.sub(
                r'(published: "[^"]+")',
                f'\\1\nduration_seconds: {meta["duration_seconds"]}',
                content
            )

    # Determine new path
    channel_dir = filepath.parent.parent  # Go up from unknown/
    new_date_dir = channel_dir / folder_date
    new_filepath = new_date_dir / filepath.name

    if dry_run:
        print(f"    [DRY-RUN] Would update frontmatter and move to: {new_date_dir}/")
        return True

    # Create directory and write file
    new_date_dir.mkdir(parents=True, exist_ok=True)
    new_filepath.write_text(content)

    # Remove old file
    filepath.unlink()

    # Clean up empty unknown folder if now empty
    unknown_dir = filepath.parent
    if not list(unknown_dir.iterdir()):
        unknown_dir.rmdir()

    print(f"    MOVED: {unknown_dir.name}/ → {folder_date}/")
    return True


def scan_unknown_folders():
    """Find all transcripts in 'unknown' folders."""
    unknown_files = []

    for channel_dir in TRANSCRIPTS_DIR.iterdir():
        if not channel_dir.is_dir():
            continue

        unknown_dir = channel_dir / "unknown"
        if unknown_dir.exists():
            files = list(unknown_dir.glob("*.md"))
            unknown_files.extend(files)

    return unknown_files


def main():
    parser = argparse.ArgumentParser(description="Repair transcript upload dates")
    parser.add_argument("--scan", action="store_true", help="Scan for files needing repair")
    parser.add_argument("--repair", action="store_true", help="Repair files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of files to process")

    args = parser.parse_args()

    if not args.scan and not args.repair:
        parser.print_help()
        return

    print("=" * 60)
    print("Transcript Repair Tool")
    print("=" * 60)

    unknown_files = scan_unknown_folders()

    print(f"\nFound {len(unknown_files)} files in 'unknown' folders:\n")

    # Group by channel
    by_channel = {}
    for f in unknown_files:
        channel = f.parent.parent.name
        by_channel.setdefault(channel, []).append(f)

    for channel, files in sorted(by_channel.items()):
        print(f"  {channel}: {len(files)} files")

    if args.scan:
        return

    if args.repair:
        # Load state to support resume
        repaired_ids = load_repair_state()
        print(f"\nAlready repaired (from previous runs): {len(repaired_ids)}")

        # Filter out already-repaired files
        files_to_process = []
        for f in unknown_files:
            fm = extract_frontmatter(f)
            vid = fm.get("video_id")
            if vid and vid not in repaired_ids:
                files_to_process.append(f)

        if args.limit:
            files_to_process = files_to_process[:args.limit]

        # Estimate time
        avg_delay = (MIN_DELAY + MAX_DELAY) / 2
        batch_pauses = len(files_to_process) // BATCH_SIZE
        avg_batch_pause = (BATCH_PAUSE_MIN + BATCH_PAUSE_MAX) / 2
        est_minutes = (len(files_to_process) * avg_delay + batch_pauses * avg_batch_pause) / 60
        print(f"Estimated time: ~{est_minutes:.0f} minutes ({est_minutes/60:.1f} hours)")

        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Repairing {len(files_to_process)} files...")

        success_count = 0
        for i, filepath in enumerate(files_to_process, 1):
            print(f"\n[{i}/{len(files_to_process)}] {filepath.parent.parent.name}")

            fm = extract_frontmatter(filepath)
            video_id = fm.get("video_id")

            if repair_file(filepath, dry_run=args.dry_run):
                success_count += 1
                if video_id and not args.dry_run:
                    repaired_ids.add(video_id)
                    save_repair_state(repaired_ids)

            # Human-like rate limiting
            if not args.dry_run and i < len(files_to_process):
                # Regular delay with randomization
                delay = random.randint(MIN_DELAY, MAX_DELAY)

                # Batch pause every N files
                if i % BATCH_SIZE == 0:
                    batch_pause = random.randint(BATCH_PAUSE_MIN, BATCH_PAUSE_MAX)
                    print(f"\n    [BATCH PAUSE] Taking a {batch_pause}s break after {i} files...")
                    time.sleep(batch_pause)
                else:
                    print(f"    Waiting {delay}s...")
                    time.sleep(delay)

        print(f"\n{'=' * 60}")
        print(f"Complete! {success_count}/{len(files_to_process)} files repaired")
        print(f"State saved to: {STATE_FILE}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
