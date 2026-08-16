"""Aggregate status endpoint — the one place that answers "is this stack OK?".

Written 2026-08-05 after a two-week outage that every existing health check
reported as healthy. The lesson driving this module: a health check that only
proves a process is listening will report "healthy" while the corpus it serves
is empty. Every check here asserts something about the DATA, not just the
process, and each one names the failure in plain language.

Consumers: poll GET /enroll/api/v1/status and alert on `status != "ok"`.
HTTP 200 means reachable (status may still be "degraded"); 503 means "down".
"""
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Blueprint, jsonify

from config import Config
from db import get_db_cursor

status_bp = Blueprint('status', __name__)

# Counting the segment table means scanning rows that each carry a 1536-dim
# embedding vector (since 2026-08-14) — ~40s+ for the full corpus. That count
# therefore runs on a background timer with its own generous budget, and the
# endpoint serves the cached figure. Counting per request made every
# monitoring poll launch a fresh scan; the scans stacked, queries queued, and
# the endpoint flapped "down" while the datastore was fine.
SEGMENT_COUNT_REFRESH_SECONDS = int(os.getenv('SEGMENT_COUNT_REFRESH_SECONDS', '600'))
SEGMENT_COUNT_TIMEOUT_SECONDS = int(os.getenv('SEGMENT_COUNT_TIMEOUT_SECONDS', '120'))

# count/counted_at are BOTH null until the first background count lands —
# "not counted yet" must never render as 0 (a timed-out count reported as
# segments: 0 reads exactly like the empty-corpus disaster this module was
# written to catch).
_SEGMENT_COUNT_CACHE = {'count': None, 'counted_at': None}
_REFRESHER_LOCK = threading.Lock()
_REFRESHER_STARTED = False

TRANSCRIPT_DIR = Path(os.getenv('TRANSCRIPT_DIR', '/mnt/foundry_resources/transcripts'))

# yt-dlp — the tool that actually does the fetching — is installed in the
# transcript-service container, not this one. So this check ASKS that service
# rather than inspecting a filesystem that has no downloader on it and would
# happily report a confident answer about nothing.
TRANSCRIPT_SERVICE_URL = os.getenv(
    'TRANSCRIPT_SERVICE_URL', 'http://knowledge-transcript-service:5025'
).rstrip('/')

# The tooling probe caches its YouTube calls, so this is a local read of an
# already-computed document. Short timeout: a slow neighbour must not make the
# status endpoint slow.
TOOLING_TIMEOUT_SECONDS = int(os.getenv('TOOLING_TIMEOUT_SECONDS', '10'))

# A corpus that hasn't grown in this long means discovery or fetching has stopped.
STALE_INGEST_HOURS = int(os.getenv('STALE_INGEST_HOURS', '72'))

# Postgres may legitimately run a little ahead of SurrealDB while a batch is in
# flight. Beyond this, the two stores genuinely disagree about what exists.
CONSISTENCY_TOLERANCE = int(os.getenv('CONSISTENCY_TOLERANCE', '25'))


def _now():
    return datetime.now(timezone.utc)


def _hours_since(ts) -> float | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return round((_now() - ts).total_seconds() / 3600, 1)


def _surreal(query: str, timeout: int = 15):
    """Run a SurrealDB query. Returns (rows, error)."""
    try:
        r = requests.post(
            f"{Config.SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": Config.SURREAL_NS,
                "surreal-db": Config.SURREAL_DB,
            },
            auth=(Config.SURREAL_USER, Config.SURREAL_PASS),
            data=query.encode('utf-8'),
            timeout=timeout,
        )
    except Exception as e:
        return None, f"unreachable: {e}"

    if not r.ok:
        return None, f"HTTP {r.status_code}"
    try:
        payload = r.json()
    except ValueError:
        return None, "response was not JSON"
    if not isinstance(payload, list) or not payload:
        return None, "unexpected response shape"

    stmt = payload[0]
    if not isinstance(stmt, dict) or stmt.get('status') != 'OK':
        return None, str(stmt.get('result', 'unknown error'))

    rows = stmt.get('result')
    return (rows if isinstance(rows, list) else []), None


def check_postgres() -> dict:
    """Postgres is reachable and the pipeline table answers."""
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM pipeline_items")
            total = cur.fetchone()['n']
            cur.execute(
                "SELECT COUNT(*) AS n FROM pipeline_items "
                "WHERE status = 'indexed_surreal'"
            )
            indexed = cur.fetchone()['n']
            cur.execute("SELECT MAX(completed_at) AS t FROM pipeline_items")
            newest = cur.fetchone()['t']
    except Exception as e:
        return {'ok': False, 'detail': f"Postgres query failed: {e}"}

    return {
        'ok': True,
        'pipeline_items': total,
        'marked_indexed': indexed,
        'newest_completed_at': newest.isoformat() if newest else None,
        'hours_since_newest': _hours_since(newest),
    }


def _refresh_segment_count() -> None:
    """One long-budget segment count into the cache, then reschedule.

    Daemon-timer only — never the request path (see the cache constants above
    for why). A failed count leaves the previous cached figure (and its
    timestamp) in place rather than overwriting it with a lie.
    """
    rows, err = _surreal("SELECT count() FROM segment GROUP ALL;",
                         timeout=SEGMENT_COUNT_TIMEOUT_SECONDS)
    if not err:
        _SEGMENT_COUNT_CACHE['count'] = rows[0].get('count', 0) if rows else 0
        _SEGMENT_COUNT_CACHE['counted_at'] = _now().isoformat()
    timer = threading.Timer(SEGMENT_COUNT_REFRESH_SECONDS, _refresh_segment_count)
    timer.daemon = True
    timer.start()


def start_segment_count_refresher() -> None:
    """Idempotent kick-off of the background segment counter."""
    global _REFRESHER_STARTED
    with _REFRESHER_LOCK:
        if _REFRESHER_STARTED:
            return
        _REFRESHER_STARTED = True
    threading.Thread(target=_refresh_segment_count, daemon=True).start()


def check_surrealdb() -> dict:
    """SurrealDB is reachable, our namespace resolves, and it holds content.

    The namespace check matters: a running SurrealDB with a missing namespace
    answers HTTP 200 to a bare connection test, which is how "connected" was
    reported for two weeks while the corpus was empty.
    """
    rows, err = _surreal("SELECT count() FROM video GROUP ALL;")
    if err:
        return {'ok': False, 'detail': f"namespace '{Config.SURREAL_NS}': {err}"}
    videos = rows[0].get('count', 0) if rows else 0

    rows, err = _surreal(
        "SELECT ingested_at FROM video ORDER BY ingested_at DESC LIMIT 1;"
    )
    newest = rows[0].get('ingested_at') if rows and not err else None

    return {
        'ok': videos > 0,
        'detail': None if videos > 0 else "namespace resolves but holds no videos",
        'videos': videos,
        # From the background cache; null + null timestamp = "not counted yet
        # since boot", never 0. See cache constants at the top of the module.
        'segments': _SEGMENT_COUNT_CACHE['count'],
        'segments_counted_at': _SEGMENT_COUNT_CACHE['counted_at'],
        'newest_ingested_at': newest,
        'hours_since_newest': _hours_since(newest),
    }


def check_transcript_files() -> dict:
    """The markdown corpus on disk — the real source of truth."""
    try:
        files = list(TRANSCRIPT_DIR.rglob('*.md'))
    except Exception as e:
        return {'ok': False, 'detail': f"cannot read {TRANSCRIPT_DIR}: {e}"}

    if not files:
        return {'ok': False, 'detail': f"no transcript files under {TRANSCRIPT_DIR}"}

    newest = max(f.stat().st_mtime for f in files)
    newest_dt = datetime.fromtimestamp(newest, tz=timezone.utc)
    return {
        'ok': True,
        'files': len(files),
        'newest_file_at': newest_dt.isoformat(),
        'hours_since_newest': _hours_since(newest_dt),
    }


def check_downloader() -> dict:
    """yt-dlp itself: present, current, and able to make a real call?

    Every other check here asks about our own services and our own data. None
    of them ask about the tool doing the fetching — so if yt-dlp went missing,
    broke, or fell far enough behind YouTube's changes to stop working, all of
    them would still report healthy, and the eventual symptom would be a
    72-hour freshness warning blaming "ingestion" rather than naming the cause.

    Answered across the container boundary because that is where the truth is.
    The alternative — checking this container's own filesystem — would be
    checking a machine that has never had yt-dlp on it.
    """
    url = f"{TRANSCRIPT_SERVICE_URL}/api/tooling"
    try:
        r = requests.get(url, timeout=TOOLING_TIMEOUT_SECONDS)
    except Exception as e:
        return {
            'ok': False,
            'detail': f"transcript service unreachable at {url}: {e}",
            'source': url,
        }

    if r.status_code == 404:
        # Specific on purpose: this is what a transcript-service image built
        # before the tool check existed looks like, and it reads very
        # differently from "the downloader is broken".
        return {
            'ok': False,
            'detail': (
                f"the transcript service is running an image built before this "
                f"check existed ({url} returned 404) — yt-dlp cannot be verified "
                f"until that container is rebuilt"
            ),
            'source': url,
        }

    if not r.ok:
        return {
            'ok': False,
            'detail': f"{url} returned HTTP {r.status_code}",
            'source': url,
        }

    try:
        payload = r.json()
    except ValueError:
        return {'ok': False, 'detail': f"{url} did not return JSON", 'source': url}

    ytdlp = payload.get('yt_dlp') or {}
    js = payload.get('js_runtime') or {}
    probe = payload.get('live_probe') or {}
    overrides = payload.get('override_flags') or {}

    return {
        'ok': bool(payload.get('ok')),
        'detail': '; '.join(payload.get('problems') or []) or None,
        'source': url,
        'yt_dlp_version': ytdlp.get('version'),
        'yt_dlp_age_days': ytdlp.get('age_days'),
        'yt_dlp_latest_version': ytdlp.get('latest_version'),
        'yt_dlp_update_available': ytdlp.get('update_available'),
        'js_runtime': js.get('name'),
        'js_runtime_available': js.get('available'),
        'override_flags_still_needed': overrides.get('still_needed'),
        'last_real_call': {
            'ok': probe.get('ok'),
            'checked_at': probe.get('checked_at'),
            'cached': probe.get('cached'),
        },
    }


def build_status() -> tuple[dict, int]:
    """Assemble the full status document and its HTTP code."""
    pg = check_postgres()
    surreal = check_surrealdb()
    disk = check_transcript_files()
    downloader = check_downloader()

    problems: list[str] = []

    if not pg['ok']:
        problems.append(pg['detail'])
    if not surreal['ok']:
        problems.append(f"SurrealDB: {surreal['detail']}")
    if not disk['ok']:
        problems.append(f"Transcript files: {disk['detail']}")

    # Named as a downloader problem, never left to surface 72 hours later as a
    # generic freshness warning. It does NOT contribute to the 503 below: the
    # corpus stays complete and queryable with a broken downloader — it just
    # stops growing — and "down" here means consumers cannot read.
    if not downloader['ok']:
        problems.append(f"downloader: {downloader['detail']}")

    # The check that would have caught the July-August 2026 outage on day one:
    # Postgres said 1,086 videos were indexed while SurrealDB held zero.
    if pg['ok'] and surreal['ok']:
        claimed = pg['marked_indexed']
        actual = surreal['videos']
        if claimed - actual > CONSISTENCY_TOLERANCE:
            problems.append(
                f"consistency: pipeline reports {claimed} videos indexed but "
                f"SurrealDB holds {actual} — indexing is reporting success "
                f"without writing"
            )

    # Freshness. Two independent ingestion paths feed this stack and they fail
    # separately, so they are reported separately:
    #   - the n8n path writes straight to SurrealDB and leaves NO file
    #   - the transcript-service backfill writes .md files to the NAS
    # A stalled file path is not visible in SurrealDB freshness, and vice versa.
    surreal_stale = surreal.get('hours_since_newest')
    if surreal['ok'] and surreal_stale is not None and surreal_stale > STALE_INGEST_HOURS:
        problems.append(
            f"freshness (search index): no new video indexed in "
            f"{surreal_stale:.0f}h (threshold {STALE_INGEST_HOURS}h) — the n8n "
            f"discovery/ingest path has stalled"
        )

    disk_stale = disk.get('hours_since_newest')
    if disk['ok'] and disk_stale is not None and disk_stale > STALE_INGEST_HOURS:
        problems.append(
            f"freshness (file archive): no new transcript file in "
            f"{disk_stale:.0f}h (threshold {STALE_INGEST_HOURS}h) — the "
            f"transcript-service backfill has stalled. Videos ingested while "
            f"this is stalled exist ONLY in SurrealDB and cannot be rebuilt "
            f"from disk if it is lost"
        )

    dependencies_down = not (pg['ok'] and surreal['ok'] and disk['ok'])
    if dependencies_down:
        state, code = 'down', 503
    elif problems:
        state, code = 'degraded', 200
    else:
        state, code = 'ok', 200

    return {
        'status': state,
        'problems': problems,
        'checked_at': _now().isoformat(),
        'components': {
            'postgres': pg,
            'surrealdb': surreal,
            'transcript_files': disk,
            'downloader': downloader,
        },
        'thresholds': {
            'stale_ingest_hours': STALE_INGEST_HOURS,
            'consistency_tolerance': CONSISTENCY_TOLERANCE,
        },
    }, code


@status_bp.route('/status')
def status():
    """Deep status for other systems to poll. Alert on status != "ok"."""
    document, code = build_status()
    return jsonify(document), code


# Import-time kick-off: daemon threads only, idempotent, and the first count
# starts immediately so the null-until-counted window is as short as the
# count itself.
start_segment_count_refresher()
