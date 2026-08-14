"""Single-video enrollment API (#46).

Thin proxy: the transcript service owns the actual pipeline (it is the only
container with yt-dlp and the transcript state), so this endpoint forwards the
request across the container boundary and passes the verdict straight back.
It exists so consumers have ONE api surface — /api/v1 — instead of needing to
know which internal service does what.
"""
import os

import requests
from flask import Blueprint, jsonify, request

enroll_bp = Blueprint('enroll', __name__)

# Same default as api/status.py uses for the tooling probe.
TRANSCRIPT_SERVICE_URL = os.getenv(
    'TRANSCRIPT_SERVICE_URL', 'http://knowledge-transcript-service:5025'
)

# Enrollment is synchronous end-to-end: metadata lookup + caption fetch +
# indexing. Minutes-long only when YouTube is slow; normally well under one.
ENROLL_TIMEOUT_SECONDS = int(os.getenv('ENROLL_TIMEOUT_SECONDS', '300'))


@enroll_bp.route('/videos/enroll', methods=['POST'])
def enroll_video():
    """Ingest one video — a guest appearance — without enrolling its channel.

    Payload: {"video_id": "..." | "url": "...", "tags": [...], "domain": "..."}
    Response and status code come from the transcript service unchanged:
    200 ingested/already-held · 400 bad input · 404 unreadable video ·
    409 stream not finished · 422 no captions · 429 YouTube rate-limited.
    """
    data = request.get_json(silent=True) or {}
    if not (data.get('video_id') or data.get('url') or data.get('id')):
        return jsonify({
            'success': False,
            'error': 'provide video_id or url',
        }), 400

    try:
        upstream = requests.post(
            f"{TRANSCRIPT_SERVICE_URL}/api/enroll",
            json=data,
            timeout=ENROLL_TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'transcript service timed out — the video may still be '
                     'ingesting; check /videos/api/<video_id> before retrying',
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'transcript service unreachable: {e}',
        }), 502

    try:
        body = upstream.json()
    except ValueError:
        return jsonify({
            'success': False,
            'error': f'transcript service returned non-JSON '
                     f'(HTTP {upstream.status_code})',
        }), 502

    return jsonify(body), upstream.status_code
