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

Restarts are cheap on purpose. A run skips both what is already held and what
is already known to have no captions, so re-entering an interrupted channel
costs nothing for the ground it has already covered. Pass --retry-failed to
re-attempt the caption-less ones, which is worth doing occasionally because a
channel does sometimes add captions to an old video.
"""

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from fetcher import (  # noqa: E402
    TranscriptBlocked,
    YTDLP_SINGLE_VIDEO_ARGS,
    ytdlp_base_cmd,
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
        cmd = ytdlp_base_cmd() + [
            "--flat-playlist",
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


def fetch_metadata(video_id: str) -> dict:
    """One yt-dlp call -> everything that call already knows about the video.

    We were paying for this request and keeping only the description. Duration,
    view/like counts, live status and chapter markers all ride along in the same
    response, so taking them costs nothing extra — which matters when request
    volume is the thing that gets us blocked.
    """
    fields = ["upload_date", "duration", "view_count", "like_count",
              "live_status", "chapters", "description"]
    cmd = ytdlp_base_cmd() + YTDLP_SINGLE_VIDEO_ARGS + [
        "--skip-download",
        # Description last and on its own line: it is multi-line free text, so
        # anything printed after it could not be told apart from its body.
        *sum(([("--print"), f"%({f})j" if f == "chapters" else f"%({f})s"]
              for f in fields), []),
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    empty = {f: "" for f in fields}
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return empty
    if res.returncode != 0:
        return empty

    lines = res.stdout.split("\n")
    out = dict(empty)
    for i, f in enumerate(fields[:-1]):
        val = lines[i].strip() if i < len(lines) else ""
        out[f] = "" if val in ("NA", "None", "null") else val
    out["description"] = "\n".join(lines[len(fields) - 1:]).strip()
    return out


def live_status_of(video_id: str) -> str | None:
    """Cheap check for whether a video is a stream that hasn't finished.

    Only called when a video has no transcript, to tell "this will never have
    captions" apart from "this is broadcasting right now and will have captions
    once it ends" — the second must not be recorded as a permanent failure.

    Returns None when the probe could not answer (timeout, non-zero exit, empty
    output). That is deliberately NOT the same as "not live": the caller writes
    a permanent failure on the strength of this answer, so an unanswered probe
    must not be read as a licence to condemn the video.
    """
    cmd = ytdlp_base_cmd() + YTDLP_SINGLE_VIDEO_ARGS + [
        "--skip-download", "--print", "%(live_status)s",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    if res.returncode != 0 or not res.stdout.strip():
        return None
    return res.stdout.strip().splitlines()[-1].strip()


UNFINISHED_STREAM = ("is_live", "is_upcoming", "post_live")


def partition_todo(videos: list[dict], state: dict, retry_failed: bool) -> tuple[list[dict], int, int]:
    """Split discovered videos into what to fetch and what to leave alone.

    Returns (todo, held, caption_less) so the caller can account for every
    video it discovered. Silent filtering is how a corpus quietly stops growing
    without anyone noticing, so the counts are reported, not just the work.
    """
    held = set(state.get("fetched", []))
    caption_less = set(state.get("failed", [])) - held
    skip = held if retry_failed else held | caption_less
    todo = [v for v in videos if v["id"] not in skip]
    return (
        todo,
        sum(1 for v in videos if v["id"] in held),
        sum(1 for v in videos if v["id"] in caption_less),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handle", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--domain", default="general")
    ap.add_argument("--delay", type=float, default=8.0,
                    help="average seconds between videos that produced a transcript")
    ap.add_argument("--miss-delay", type=float, default=2.0,
                    help="seconds after a video with no transcript (1 call, not 2)")
    ap.add_argument("--deadline-minutes", type=float, default=0,
                    help="stop starting new videos after this long (0 = no limit)")
    ap.add_argument("--limit", type=int, default=0,
                    help="process at most N videos (0 = all) — for smoke tests")
    ap.add_argument("--tabs", default=",".join(TABS),
                    help="comma-separated channel tabs to discover")
    ap.add_argument("--retry-failed", action="store_true",
                    help="also re-attempt videos already recorded as having no "
                         "captions (a channel sometimes adds them later)")
    args = ap.parse_args()

    started = time.time()
    deadline = started + args.deadline_minutes * 60 if args.deadline_minutes else None

    log(f"=== Priority ingest: @{args.handle} ({args.name}, domain={args.domain}) ===")
    videos = discover(args.handle, tuple(t for t in args.tabs.split(",") if t))
    if not videos:
        log("FATAL: discovery returned nothing — refusing to report success")
        return 1

    state = load_state()
    todo, held, caption_less = partition_todo(videos, state, args.retry_failed)
    tally = f"{len(videos)} on channel · {held} already held"
    if args.retry_failed:
        tally += f" · {caption_less} known caption-less (RE-ATTEMPTING)"
    else:
        tally += f" · {caption_less} known caption-less (skipped)"
    log(f"{tally} · {len(todo)} to fetch")
    if args.limit:
        todo = todo[: args.limit]
        log(f"--limit {args.limit}: processing {len(todo)} of them this run")

    stats = {"ok": 0, "no_transcript": 0, "not_indexed": 0, "error": 0,
             "skipped_deadline": 0, "block_waits": 0, "block_minutes": 0,
             "live_deferred": 0}
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
                # A stream that is upcoming or mid-broadcast has no captions
                # YET. Recording that as a permanent failure would blacklist
                # the sermon that is being preached as we look at it.
                status = live_status_of(vid)
                if status is None or status in UNFINISHED_STREAM:
                    stats["live_deferred"] += 1
                    why = ("could not read live status"
                           if status is None else f"still live ({status})")
                    log(f"    {why} — leaving it for a later run")
                    time.sleep(args.miss_delay)
                    continue

                # Record it so the standing worker doesn't retry forever.
                state = load_state()
                if vid not in state.setdefault("failed", []):
                    state["failed"].append(vid)
                save_state(state)
                stats["no_transcript"] += 1
                log(f"    no transcript available")
                time.sleep(args.miss_delay)
                continue

            meta = fetch_metadata(vid)
            description = meta.get("description", "")
            video = {
                "id": vid,
                "title": v["title"],
                "channel_handle": args.handle,
                "channel_name": args.name,
                "domain": args.domain,
                "upload_date": meta.get("upload_date") or "NA",
                # Extra fields ride along in the file's frontmatter only. They
                # are deliberately NOT added to the indexer payload yet: the
                # search datastore is SCHEMAFULL and silently rejected every
                # write the last time it was handed fields it did not declare.
                "extra_metadata": {
                    k: meta.get(k, "") for k in
                    ("duration", "view_count", "like_count", "live_status", "chapters")
                    if meta.get(k)
                },
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

        # Jittered, not fixed. Each video costs one caption call (through the
        # proxy, so a fresh IP each time) plus one metadata call straight from
        # our own address — and it is that second one, arriving like a metronome
        # for over an hour, that looks like a scraper. The jitter costs nothing
        # and makes the pattern unremarkable.
        time.sleep(random.uniform(args.delay * 0.7, args.delay * 1.3))

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
