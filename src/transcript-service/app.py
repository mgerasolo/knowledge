"""KnowledgeStack Transcript Service - HTTP API for n8n workflows.

Handles YouTube video discovery and transcript fetching.
Includes a background backfill worker that continuously drains the queue.
"""
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from fetcher import (
    get_status,
    get_pending,
    discover_new_videos,
    fetch_and_save,
    load_state,
    proxy_status,
)
from backfill_worker import start_backfill_thread, worker_status
from single_video import EnrollError, enroll_video
from tooling import tooling_status, tooling_summary

app = Flask(__name__)
CORS(app)

_BACKFILL_ENABLED = os.getenv('BACKFILL_ENABLED', 'true').lower() == 'true'


def _ensure_backfill():
    """Start the backfill worker if enabled. Idempotent.

    Called at import/boot time so the worker starts on container start without
    needing inbound traffic (fixes the 2026-05-01 cold-start dormancy). Also
    invoked as a before_request fallback in case a gunicorn preload/fork left
    the import-time start in the master rather than the worker process.
    """
    if _BACKFILL_ENABLED:
        start_backfill_thread()  # idempotent — no-op if already alive


# Start at boot, not merely on first request.
_ensure_backfill()


@app.before_request
def _backfill_fallback():
    """Belt-and-suspenders: ensure the worker is running (idempotent)."""
    _ensure_backfill()


@app.route('/health')
def health():
    """Health check endpoint.

    Returns 503 when the backfill worker is enabled but not alive, so the
    container healthcheck surfaces a dead/never-started worker instead of
    reporting healthy while ingestion is silently stalled.

    Tooling facts are REPORTED here but never fail this endpoint. A stale or
    broken yt-dlp is a real problem, and it is named in GET /api/tooling and in
    the admin API's aggregate status — but failing the container healthcheck
    over it would hand the problem to the restart pipeline, which cannot fix a
    downloader and would only interrupt the backfill queue.
    """
    ws = worker_status()
    if _BACKFILL_ENABLED and not ws['alive']:
        return jsonify({
            'status': 'unhealthy',
            'service': 'transcript-service',
            'reason': 'backfill worker not running',
            'backfill': ws,
        }), 503
    return jsonify({
        'status': 'healthy',
        'service': 'transcript-service',
        'backfill': ws if _BACKFILL_ENABLED else 'disabled',
        # Whether YouTube traffic is going out through a proxy is the first
        # thing you need to know when ingestion stalls, and it is invisible
        # otherwise. Never includes the credential — mode and scope only.
        'proxy': proxy_status(),
        'tooling': tooling_summary(),
    }), 200


@app.route('/api/tooling')
def tooling():
    """Is the downloader itself present, current, and able to make a real call?

    Lives on this service because yt-dlp is installed in THIS container and
    nowhere else. The admin API reads it across the container boundary to build
    the `downloader` component of GET /api/v1/status.

    The live YouTube calls behind this are cached for an hour; `?force=true`
    re-runs them, which is what you want when you have just changed something
    and do not want to wait out the cache.
    """
    force = request.args.get('force', '').lower() in ('1', 'true', 'yes')
    document = tooling_status(force_probe=force)
    return jsonify(document), 200


@app.route('/')
def index():
    """API info."""
    return jsonify({
        'name': 'KnowledgeStack Transcript Service',
        'version': '1.0.0',
        'endpoints': {
            'health': 'GET /health',
            'tooling': 'GET /api/tooling',
            'status': 'GET /api/status',
            'channels': 'GET /api/channels',
            'pending': 'GET /api/pending?limit=8',
            'fetch': 'POST /api/fetch',
            'enroll': 'POST /api/enroll',
            'discover': 'POST /api/discover',
        }
    })


@app.route('/api/status')
def status():
    """Get overall ingestion status."""
    return jsonify({
        'success': True,
        **get_status(),
    })


@app.route('/api/channels')
def channels():
    """List monitored YouTube channels."""
    state = load_state()
    fetched_ids = set(state.get('fetched', []))

    # Count fetched per channel (approximate from video list)
    from fetcher import load_video_list
    video_list = load_video_list()

    channel_counts = {}
    for video in video_list.get('videos', []):
        handle = video.get('channel_handle', 'unknown')
        channel_counts.setdefault(handle, {'total': 0, 'fetched': 0})
        channel_counts[handle]['total'] += 1
        if video['id'] in fetched_ids:
            channel_counts[handle]['fetched'] += 1

    enriched = []
    for ch in Config.CHANNELS:
        counts = channel_counts.get(ch['handle'], {'total': 0, 'fetched': 0})
        enriched.append({
            **ch,
            'total_videos': counts['total'],
            'fetched': counts['fetched'],
            'pending': counts['total'] - counts['fetched'],
        })

    return jsonify({'success': True, 'channels': enriched})


@app.route('/api/pending')
def pending():
    """Get next N pending videos for backfill.

    Query params:
        limit: max videos to return (default 8)
    """
    limit = request.args.get('limit', Config.BACKFILL_BATCH_SIZE, type=int)
    videos = get_pending(limit=limit)

    return jsonify({
        'success': True,
        'count': len(videos),
        'videos': videos,
    })


@app.route('/api/fetch', methods=['POST'])
def fetch():
    """Fetch transcript for a single video.

    Expected payload:
    {
        "id": "video_id",
        "title": "Video Title",           // optional
        "channel_handle": "ChannelHandle", // optional
        "channel_name": "Channel Name",    // optional
        "domain": "business",              // optional
        "upload_date": "20260101"          // optional
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided', 'success': False}), 400

    video_id = data.get('id') or data.get('video_id')
    if not video_id:
        return jsonify({'error': 'Missing video id', 'success': False}), 400

    # Normalize the video dict
    video = {
        'id': video_id,
        'title': data.get('title', 'Unknown'),
        'channel_handle': data.get('channel_handle', 'unknown'),
        'channel_name': data.get('channel_name', ''),
        'domain': data.get('domain', 'unknown'),
        'upload_date': data.get('upload_date', 'NA'),
    }

    result = fetch_and_save(video)

    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@app.route('/api/enroll', methods=['POST'])
def enroll():
    """Enroll ONE video without enrolling its channel (#46).

    The channel path needs the caller to supply channel metadata; this one
    looks everything up from the video itself, so a guest appearance on a
    show we don't follow can join a personality corpus.

    Expected payload:
    {
        "video_id": "hiQW6FZkA9o",        // or "url": any YouTube URL shape
        "tags": ["personality:myron-golden"],  // optional corpus tags
        "domain": "business"               // optional, default "general"
    }

    Status codes: 200 ingested/already-held · 400 bad input · 404 unreadable
    video · 409 stream not finished · 422 no captions · 429 rate-limited.
    """
    data = request.get_json(silent=True) or {}
    video_ref = data.get('video_id') or data.get('url') or data.get('id')
    try:
        result, status_code = enroll_video(
            video_ref,
            tags=data.get('tags'),
            domain=data.get('domain'),
        )
    except EnrollError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify(result), status_code


@app.route('/api/discover', methods=['POST'])
def discover():
    """Check all channels for new videos.

    Optional payload:
    {
        "lookback_days": 7  // how far back to check (default 7)
    }
    """
    data = request.get_json(silent=True) or {}
    lookback_days = data.get('lookback_days', 7)

    result = discover_new_videos(lookback_days=lookback_days)

    return jsonify({
        'success': True,
        **result,
    })


if __name__ == '__main__':
    print("Starting KnowledgeStack Transcript Service...")
    print(f"Transcript dir: {Config.TRANSCRIPT_DIR}")
    print(f"State dir: {Config.STATE_DIR}")
    print(f"Port: {Config.PORT}")
    print(f"Channels: {len(Config.CHANNELS)}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
