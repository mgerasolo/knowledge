#!/usr/bin/env python3
"""Priority ingest of a single YouTube channel — every video, in one pass.

Runs INSIDE the transcript-service container (it imports `fetcher` and needs
/data/transcripts + /data/state):

    docker cp scripts/priority_ingest_channel.py knowledge-transcript-service:/app/
    docker exec -d knowledge-transcript-service python3 /app/priority_ingest_channel.py \
        --handle PastorChrisDurkin --name "Pastor Chris Durkin" --domain faith

Why this exists rather than the standing backfill worker: the worker deliberately
sleeps 30-600s between videos, so a 600-video channel would take weeks. This does
the same per-video work (transcript -> file -> search index -> state) at a paced
but purposeful rate for one channel that has been asked for now.

Differences from fetcher.fetch_and_save(), on purpose:
  * Discovers /videos, /streams AND /shorts — a church channel keeps its sermons
    under /streams, which the standing discovery (which only reads /videos)
    never sees.
  * Gets upload_date and description from ONE yt-dlp call per video, so files
    land in the normal <channel>/<YYYY-MM>/ layout instead of .../unknown/.
    Flat-playlist listing reports upload_date as "NA", which is what would
    otherwise dump an entire channel into one undated directory.
  * Skips the yt-dlp call entirely when no transcript exists — no transcript
    means no file, so the metadata would be thrown away.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from fetcher import (  # noqa: E402
    TranscriptBlocked,
    _index_video,
    fetch_transcript,
    load_state,
    load_video_list,
    save_state,
    save_transcript_file,
    save_video_list,
)

TABS = ("videos", "streams", "shorts")

# YouTube rate-limits caption requests per IP (HTTP 429 on the timedtext
# endpoint) and gives no Retry-After. Waiting it out is the only lever we have
# from this network, so the run parks and re-probes rather than giving up — the
# channel then drains on its own the moment the block lifts.
BLOCK_BACKOFF = [300, 600, 900, 1800, 1800, 3600]  # seconds, then repeat last


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def discover(handle: str, tabs=TABS) -> list[dict]:
    """List every video on the channel across the given tabs, deduped."""
    seen: dict[str, dict] = {}
    for tab in tabs:
        url = f"https://www.youtube.com/@{handle}/{tab}"
        cmd = [
            "yt-dlp", "--flat-playlist",
            "--print", "%(id)s|%(title)s",
            url,
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except subprocess.TimeoutExpired:
            log(f"discover {tab}: TIMED OUT — continuing without it")
            continue
        count = 0
        for line in res.stdout.splitlines():
            if "|" not in line:
                continue
            vid, title = line.split("|", 1)
            vid = vid.strip()
            if vid and vid not in seen:
                seen[vid] = {"id": vid, "title": title.strip(), "tab": tab}
                count += 1
        log(f"discover {tab}: {count} new (running total {len(seen)})")
        time.sleep(3)  # courtesy gap between external calls
    return list(seen.values())


def fetch_metadata(video_id: str) -> tuple[str, str]:
    """One yt-dlp call -> (upload_date, description). Empty strings on failure."""
    cmd = [
        "yt-dlp", "--skip-download",
        "--print", "%(upload_date)s",
        "--print", "%(description)s",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "", ""
    if res.returncode != 0:
        return "", ""
    out = res.stdout.split("\n", 1)
    upload_date = out[0].strip() if out else ""
    description = out[1].strip() if len(out) > 1 else ""
    if upload_date in ("NA", "None"):
        upload_date = ""
    return upload_date, description


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--domain", default="general")
    ap.add_argument("--delay", type=float, default=5.0,
                    help="seconds between videos that produced a transcript")
    ap.add_argument("--miss-delay", type=float, default=2.0,
                    help="seconds after a video with no transcript (1 call, not 2)")
    ap.add_argument("--deadline-minutes", type=float, default=0,
                    help="stop starting new videos after this long (0 = no limit)")
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N videos (0 = all) — for smoke tests")
    ap.add_argument("--tabs", default=",".join(TABS),
                    help="comma-separated channel tabs to discover")
    args = ap.parse_args()

    started = time.time()
    deadline = started + args.deadline_minutes * 60 if args.deadline_minutes else None

    log(f"=== Priority ingest: @{args.handle} ({args.name}, domain={args.domain}) ===")
    videos = discover(args.handle, tuple(t for t in args.tabs.split(",") if t))
    if not videos:
        log("FATAL: discovery returned nothing — refusing to report success")
        return 1

    state = load_state()
    already = set(state.get("fetched", []))
    todo = [v for v in videos if v["id"] not in already]
    log(f"{len(videos)} videos on channel · {len(videos) - len(todo)} already held · "
        f"{len(todo)} to fetch")
    if args.limit:
        todo = todo[: args.limit]
        log(f"--limit {args.limit}: processing {len(todo)} of them this run")

    stats = {"ok": 0, "no_transcript": 0, "not_indexed": 0, "error": 0,
             "skipped_deadline": 0, "block_waits": 0, "block_minutes": 0}
    total = len(todo)

    stop = False

    for i, v in enumerate(todo, 1):
        if stop:
            break
        if deadline and time.time() > deadline:
            stats["skipped_deadline"] = total - i + 1
            log(f"Deadline reached — {stats['skipped_deadline']} video(s) left unstarted")
            break

        vid = v["id"]
        title = v["title"][:60]
        log(f"[{i}/{total}] {vid} — {title}")

        try:
            segments = None
            attempt = 0
            while True:
                try:
                    segments = fetch_transcript(vid)
                    break
                except TranscriptBlocked as e:
                    wait = BLOCK_BACKOFF[min(attempt, len(BLOCK_BACKOFF) - 1)]
                    attempt += 1
                    stats["block_waits"] += 1
                    stats["block_minutes"] += wait / 60
                    if deadline and time.time() + wait > deadline:
                        log(f"    BLOCKED and the deadline would pass while "
                            f"waiting — stopping here. ({e})")
                        stats["skipped_deadline"] = total - i + 1
                        stop = True
                        break
                    log(f"    BLOCKED by YouTube (attempt {attempt}) — "
                        f"waiting {wait // 60}m then retrying this same video")
                    time.sleep(wait)

            if stop:
                break
            if not segments:
                # Record it so the standing worker doesn't retry forever.
                state = load_state()
                if vid not in state.setdefault("failed", []):
                    state["failed"].append(vid)
                save_state(state)
                stats["no_transcript"] += 1
                log(f"    no transcript available")
                time.sleep(args.miss_delay)
                continue

            upload_date, description = fetch_metadata(vid)
            video = {
                "id": vid,
                "title": v["title"],
                "channel_handle": args.handle,
                "channel_name": args.name,
                "domain": args.domain,
                "upload_date": upload_date or "NA",
            }
            path = save_transcript_file(video, segments, description or None)

            # Re-read state immediately before writing: the standing backfill
            # worker writes this same file, and a stale copy would drop its work.
            state = load_state()
            if vid not in state.setdefault("fetched", []):
                state["fetched"].append(vid)
            if vid in state.get("failed", []):
                state["failed"].remove(vid)
            save_state(state)

            indexed, index_error = _index_video(video, segments, description)
            if indexed:
                stats["ok"] += 1
            else:
                stats["not_indexed"] += 1
                log(f"    NOT INDEXED: {index_error}")
            log(f"    {len(segments)} segments -> {path}")

        except Exception as e:  # keep going; one bad video must not end the run
            stats["error"] += 1
            log(f"    ERROR: {e}")

        time.sleep(args.delay)

    # Register the channel's videos in the master list last, in one write, so a
    # concurrent discovery sweep has the smallest possible window to clobber it.
    try:
        vl = load_video_list()
        known = {x["id"] for x in vl.get("videos", [])}
        added = [
            {
                "id": v["id"], "title": v["title"], "upload_date": "NA",
                "channel_handle": args.handle, "channel_name": args.name,
                "domain": args.domain,
            }
            for v in videos if v["id"] not in known
        ]
        if added:
            vl["videos"] = vl.get("videos", []) + added
            vl["total_videos"] = len(vl["videos"])
            vl["last_priority_ingest"] = datetime.now(timezone.utc).isoformat()
            save_video_list(vl)
        log(f"video_list.json: +{len(added)} entries")
    except Exception as e:
        log(f"video_list.json update failed (transcripts are safe on disk): {e}")

    mins = (time.time() - started) / 60
    log(f"=== DONE in {mins:.1f}m — {json.dumps(stats)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
