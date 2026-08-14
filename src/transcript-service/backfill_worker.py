"""
Background backfill worker.

Continuously fetches one pending transcript at a time with random delays
between 30-600 seconds. Pauses during the discovery window (6:00-7:00 AM)
to avoid overlapping with the daily new-video check.

The worker exposes a heartbeat + idempotent start so the service can (a) start
it reliably at boot (not merely on first HTTP request) and (b) report real
liveness from /health. This closes the 2026-05-01 cold-start bug where the
worker only started on first request and never resumed after a container
restart with no inbound traffic.
"""

import os
import random
import threading
import time
from datetime import datetime

from config import Config
from fetcher import get_pending, fetch_and_save, get_status, discover_new_videos


# Configurable via env
MIN_DELAY = int(Config.MIN_DELAY_SECONDS)  # default 30
MAX_DELAY = int(Config.MAX_DELAY_SECONDS)  # default 600
DISCOVERY_PAUSE_HOUR = 6  # Pause during 6:00-6:59 AM

# How often the worker runs discovery itself when it has nothing left to fetch.
# Nothing used to refill the queue: discovery existed only as a manual POST to
# /api/discover, so once the March 2026 video list was drained the worker sat
# idle indefinitely while new uploads were never picked up. It looked healthy
# the whole time, because the thread was alive and looping.
DISCOVERY_INTERVAL_HOURS = int(os.getenv("DISCOVERY_INTERVAL_HOURS", "12"))

# How long to stand down when YouTube rate-limits caption requests for our whole
# IP. Retrying through a block just extends it, and the heartbeat keeps ticking
# so this reads as "waiting", not "dead".
BLOCKED_COOLDOWN_SECONDS = int(os.getenv("BLOCKED_COOLDOWN_SECONDS", "1800"))
DISCOVERY_LOOKBACK_DAYS = int(os.getenv("DISCOVERY_LOOKBACK_DAYS", "14"))

_last_discovery = None  # epoch seconds of the last self-triggered discovery

# --- Worker state (for idempotent start + liveness reporting) ---
_state_lock = threading.Lock()
_worker_thread = None          # type: threading.Thread | None
_last_heartbeat = None         # epoch seconds of the most recent loop iteration
_last_activity = None          # human note of the most recent action


def _beat(activity: str = None):
    """Record a heartbeat (and optionally the current activity)."""
    global _last_heartbeat, _last_activity
    _last_heartbeat = time.time()
    if activity is not None:
        _last_activity = activity


def _in_discovery_window() -> bool:
    """Check if we're in the discovery pause window."""
    return datetime.now().hour == DISCOVERY_PAUSE_HOUR


def _random_delay() -> int:
    """Return a random delay between MIN and MAX."""
    return random.randint(MIN_DELAY, MAX_DELAY)


def _discovery_due() -> bool:
    """True when the worker should look for new uploads itself."""
    if _last_discovery is None:
        return True
    return (time.time() - _last_discovery) >= DISCOVERY_INTERVAL_HOURS * 3600


def _run_discovery():
    """Look for new uploads and add them to the queue.

    Runs in the worker thread. Discovery paces itself between channels, so this
    takes a couple of minutes for the full channel list — that is fine here,
    since we only get called when there is nothing else to do.
    """
    global _last_discovery
    _beat("discovery")
    print(
        f"[backfill] Queue empty — discovering new videos "
        f"(lookback {DISCOVERY_LOOKBACK_DAYS}d)...",
        flush=True,
    )
    def _progress(done, total, handle):
        # Keeps /health honest during a multi-minute sweep.
        _beat(f"discovery {done}/{total}")
        if done == 1 or done % 10 == 0:
            print(f"[backfill] Discovery {done}/{total} ({handle})", flush=True)

    try:
        result = discover_new_videos(
            lookback_days=DISCOVERY_LOOKBACK_DAYS, on_progress=_progress
        )
        found = len(result.get("new_videos", []))
        print(f"[backfill] Discovery added {found} new video(s)", flush=True)
    except Exception as e:
        print(f"[backfill] Discovery failed: {e}", flush=True)
        found = 0
    finally:
        # Record the attempt either way, so a persistent failure cannot turn
        # into a hot loop hammering YouTube.
        _last_discovery = time.time()

    if not found:
        _beat("discovery-empty")
        time.sleep(1800)


def backfill_loop():
    """Main backfill loop. Runs forever in a background thread."""
    print("[backfill] Worker started")
    print(f"[backfill] Delay range: {MIN_DELAY}-{MAX_DELAY}s")
    print(f"[backfill] Pauses during hour {DISCOVERY_PAUSE_HOUR}:00")

    _beat("started")

    # Initial delay to let the service start up
    time.sleep(10)

    consecutive_empty = 0

    while True:
        try:
            _beat("tick")

            # Pause during discovery window
            if _in_discovery_window():
                print("[backfill] In discovery window, sleeping 60s...")
                _beat("discovery-window")
                time.sleep(60)
                continue

            # Get next pending video
            pending = get_pending(limit=1)

            if not pending:
                consecutive_empty += 1
                if consecutive_empty == 1:
                    status = get_status()
                    print(
                        f"[backfill] Queue empty. "
                        f"Fetched: {status['fetched']}, "
                        f"Failed: {status['failed']}, "
                        f"Total: {status['total_videos']}"
                    )

                # An empty queue means there is nothing left to fetch from the
                # known video list — which is exactly when we should go looking
                # for new uploads rather than idling.
                if _discovery_due():
                    _run_discovery()
                    continue

                # Back off when queue is empty — check every 30 min
                _beat("queue-empty")
                time.sleep(1800)
                continue

            consecutive_empty = 0
            video = pending[0]
            video_id = video["id"]
            title = video.get("title", "Unknown")[:60]

            print(f"[backfill] Fetching: {title}... ({video_id})")
            _beat(f"fetching {video_id}")

            result = fetch_and_save(video)

            if result.get("blocked"):
                # Whole-IP rate limit: every other video would fail the same way,
                # so stop hammering and let it cool off rather than marching the
                # queue into a wall.
                print(
                    f"[backfill] BLOCKED by YouTube — pausing "
                    f"{BLOCKED_COOLDOWN_SECONDS}s ({video_id} left queued)",
                    flush=True,
                )
                _beat("blocked")
                time.sleep(BLOCKED_COOLDOWN_SECONDS)
                continue

            if result.get("success"):
                seg_count = result.get("segment_count", "?")
                # Report indexing separately from fetching: a transcript on disk
                # that never reached the search index is invisible to every
                # consumer, and used to pass silently as a success.
                if result.get("already_fetched"):
                    index_note = ""
                elif result.get("indexed"):
                    index_note = " indexed"
                else:
                    index_note = f" NOT INDEXED ({result.get('index_error')})"
                print(f"[backfill] OK: {video_id} ({seg_count} segments){index_note}")
                _beat(f"fetched {video_id}")
            else:
                error = result.get("error", "unknown")
                print(f"[backfill] FAIL: {video_id} — {error}")
                _beat(f"failed {video_id}")

            # Random delay before next fetch
            delay = _random_delay()
            print(f"[backfill] Sleeping {delay}s...")
            time.sleep(delay)

        except Exception as e:
            print(f"[backfill] Error: {e}")
            _beat(f"error: {e}")
            time.sleep(60)


def start_backfill_thread():
    """Start the backfill worker as a daemon thread (idempotent).

    Safe to call multiple times (import-time + before_request fallback):
    if a live worker thread already exists, this is a no-op and returns it.
    """
    global _worker_thread
    with _state_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return _worker_thread
        _worker_thread = threading.Thread(
            target=backfill_loop, daemon=True, name="backfill"
        )
        _worker_thread.start()
        return _worker_thread


def worker_status() -> dict:
    """Report worker liveness for health checks / observability.

    Longest legitimate gap between heartbeats is the empty-queue backoff
    (1800s), so `stalled` uses a conservative threshold above that.
    """
    alive = _worker_thread is not None and _worker_thread.is_alive()
    now = time.time()
    age = None if _last_heartbeat is None else round(now - _last_heartbeat, 1)
    return {
        "alive": alive,
        "seconds_since_heartbeat": age,
        "last_activity": _last_activity,
        "stalled": bool(alive and age is not None and age > 2400),
    }
