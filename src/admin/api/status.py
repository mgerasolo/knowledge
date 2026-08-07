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
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Blueprint, jsonify

from config import Config
from db import get_db_cursor

status_bp = Blueprint('status', __name__)

TRANSCRIPT_DIR = Path(os.getenv('TRANSCRIPT_DIR', '/mnt/foundry_resources/transcripts'))

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


def _surreal(query: str):
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
            timeout=15,
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

    rows, err = _surreal("SELECT count() FROM segment GROUP ALL;")
    segments = rows[0].get('count', 0) if rows and not err else 0

    rows, err = _surreal(
        "SELECT ingested_at FROM video ORDER BY ingested_at DESC LIMIT 1;"
    )
    newest = rows[0].get('ingested_at') if rows and not err else None

    return {
        'ok': videos > 0,
        'detail': None if videos > 0 else "namespace resolves but holds no videos",
        'videos': videos,
        'segments': segments,
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


def build_status() -> tuple[dict, int]:
    """Assemble the full status document and its HTTP code."""
    pg = check_postgres()
    surreal = check_surrealdb()
    disk = check_transcript_files()

    problems: list[str] = []

    if not pg['ok']:
        problems.append(pg['detail'])
    if not surreal['ok']:
        problems.append(f"SurrealDB: {surreal['detail']}")
    if not disk['ok']:
        problems.append(f"Transcript files: {disk['detail']}")

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
