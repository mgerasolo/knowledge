"""KnowledgeEnroll Embedding Service - HTTP API for n8n workflows."""
import json

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from surreal_client import test_connection
from embedder import embed_video
from mcp_transcript import fetch_transcript
from search import EmbeddingUnavailable, semantic_search

app = Flask(__name__)
CORS(app)


@app.route('/health')
def health():
    """Health check endpoint."""
    surreal_ok = test_connection()
    status = 'healthy' if surreal_ok else 'unhealthy'
    return jsonify({
        'status': status,
        'surrealdb': 'connected' if surreal_ok else 'disconnected'
    }), 200 if surreal_ok else 503


@app.route('/api/embed', methods=['POST'])
def embed():
    """Embed a video's transcript into SurrealDB.

    If transcript/segments are not provided, fetches them via MCP Gateway.

    Expected payload:
    {
        "video_id": "dQw4w9WgXcQ",
        "title": "Video Title",  // optional if fetching transcript
        "url": "https://youtube.com/watch?v=...",
        "channel_handle": "channelname",
        "channel_name": "Channel Display Name",
        "domain": "ai-tech",
        "published_at": "2026-01-15",   // real date; omitting it stores 1970-01-01
        "duration_seconds": 3600,
        "view_count": 12345,
        "like_count": 678,
        "chapters": [{"start_time": 0, "title": "Intro"}],
        "live_status": "was_live",
        "transcript": "...",  // optional - fetched via MCP Gateway if missing
        "segments": [...],    // optional - fetched via MCP Gateway if missing
        "skip_embeddings": false
    }

    Returns:
    {
        "success": true,
        "video_id": "dQw4w9WgXcQ",
        "surreal_id": "video:abc123def456",
        "segment_count": 42,
        "embeddings_generated": true
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided', 'success': False}), 400

    video_id = data.get('video_id') or data.get('youtube_id')
    if not video_id:
        return jsonify({'error': 'Missing video_id', 'success': False}), 400

    # If no transcript/segments provided, fetch via MCP Gateway
    if not data.get('transcript') and not data.get('segments'):
        print(f"No transcript provided for {video_id}, fetching via MCP Gateway...")
        transcript_data = fetch_transcript(video_id, timed=True)

        if not transcript_data:
            return jsonify({
                'error': 'Failed to fetch transcript via MCP Gateway',
                'video_id': video_id,
                'success': False
            }), 400

        # Merge fetched transcript into data
        data['transcript'] = transcript_data.get('transcript', '')
        data['segments'] = transcript_data.get('segments', [])
        if not data.get('title') and transcript_data.get('title'):
            data['title'] = transcript_data['title']

        print(f"Fetched transcript: {len(data['transcript'])} chars, {len(data['segments'])} segments")

    skip_embeddings = data.get('skip_embeddings', False)

    try:
        result = embed_video(data, skip_embeddings=skip_embeddings)
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/api/search', methods=['POST'])
def search_route():
    """Search for relevant segments using vector similarity.

    Payload: {"query": str (required, >= 3 chars),
              "domain": str (optional filter),
              "limit": int (default 10, max 100),
              "min_score": float (default 0.4; 0 disables the cutoff)}

    Status codes carry the meaning: 400 bad request · 503 retryable
    dependency failure (gateway or SurrealDB) · 200 success, INCLUDING an
    empty result set.
    """
    data = request.get_json(silent=True)

    # A JSON array/string/number is valid JSON but not a valid request —
    # without this check it would 500 on .get() instead of the promised 400.
    if not isinstance(data, dict) or not str(data.get('query', '')).strip():
        return jsonify({'error': 'Missing query', 'success': False}), 400

    query = str(data['query']).strip()
    if len(query) < 3:
        return jsonify({'error': 'Query too short (minimum 3 characters)',
                        'success': False}), 400

    domain = data.get('domain') or None
    try:
        limit = int(data.get('limit', 10))
        min_score = float(data.get('min_score', 0.4))
    except (TypeError, ValueError):
        return jsonify({'error': 'limit must be an integer and min_score a number',
                        'success': False}), 400
    limit = max(1, min(limit, 100))

    try:
        found = semantic_search(query, domain=domain, limit=limit,
                                min_score=min_score)
    except EmbeddingUnavailable as e:
        return jsonify({'error': str(e), 'success': False,
                        'retryable': True}), 503
    except RuntimeError as e:
        return jsonify({'error': str(e), 'success': False,
                        'retryable': True}), 503

    return jsonify({
        'success': True,
        'query': query,
        'results': found['results'],
        'count': len(found['results']),
        'model': found['model'],
    })


@app.route('/api/video/<video_id>')
def get_video(video_id):
    """Get video metadata and segment count from SurrealDB."""
    from surreal_client import surreal_query, create_safe_id

    video_db_id = create_safe_id(video_id)
    result = surreal_query(f"SELECT * FROM video:{video_db_id};")

    if not result or not result[0].get('result'):
        return jsonify({'error': 'Video not found', 'success': False}), 404

    video = result[0]['result'][0]
    return jsonify({
        'success': True,
        'video': video
    })


@app.route('/api/video/<video_id>/tags', methods=['POST'])
def add_video_tags(video_id):
    """Merge corpus tags onto a video record (#46 — single-video enrollment).

    MERGE, never replace: tagging a video into a second corpus must not strip
    it out of the first, and re-running an enrollment must be harmless.

    Expected payload: {"tags": ["personality:myron-golden", ...]}
    Returns the video's full tag list after the merge.
    """
    import re as _re
    from surreal_client import surreal_query, surreal_write, create_safe_id

    data = request.get_json(silent=True) or {}
    tags = data.get('tags')
    if not isinstance(tags, list) or not tags:
        return jsonify({'error': 'tags must be a non-empty list', 'success': False}), 400

    # Same shape single_video.py enforces; re-checked here because this is the
    # boundary where the values land in a SurrealQL statement.
    tag_re = _re.compile(r"^[a-z0-9][a-z0-9:._-]{0,79}$")
    cleaned = []
    for tag in tags:
        text = str(tag).strip().lower()
        if not tag_re.match(text):
            return jsonify({
                'error': f'invalid tag: {str(tag)[:80]} (want lowercase slugs '
                         'like personality:myron-golden)',
                'success': False,
            }), 400
        if text not in cleaned:
            cleaned.append(text)

    video_db_id = create_safe_id(video_id)

    # Refuse to tag a video the index does not hold — an UPSERT here would
    # plant an empty stub record that looks like a real video to every query.
    existing = surreal_query(f"SELECT youtube_id FROM video:{video_db_id};")
    if (not existing or not isinstance(existing[0], dict)
            or not existing[0].get('result')):
        return jsonify({'error': 'Video not in the index', 'success': False}), 404

    tags_json = json.dumps(cleaned)
    # Two statements so this works on any SurrealDB version: normalize a
    # missing field to [], then merge and dedupe.
    ok, err = surreal_write(
        f"UPDATE video:{video_db_id} SET tags = [] WHERE tags = NONE;"
    )
    if ok:
        ok, err = surreal_write(
            f"UPDATE video:{video_db_id} SET "
            f"tags = array::distinct(array::concat(tags, {tags_json}));"
        )
    if not ok:
        return jsonify({'error': f'tag write failed: {err}', 'success': False}), 503

    final = surreal_query(f"SELECT tags FROM video:{video_db_id};")
    final_tags = []
    if final and isinstance(final[0], dict) and final[0].get('result'):
        final_tags = final[0]['result'][0].get('tags') or []

    return jsonify({'success': True, 'video_id': video_id, 'tags': final_tags}), 200


@app.route('/api/stats')
def stats():
    """Get embedding statistics."""
    from surreal_client import surreal_query

    def count_of(table):
        """Return the row count for a table, or None if the query failed.

        On error SurrealDB puts a message STRING where the result rows would be,
        so indexing straight into [0].get() raised AttributeError and returned a
        500 instead of a usable answer (seen throughout July 2026).
        """
        payload = surreal_query(f"SELECT count() FROM {table} GROUP ALL;")
        if not payload or not isinstance(payload, list):
            return None
        stmt = payload[0]
        if not isinstance(stmt, dict) or stmt.get('status') != 'OK':
            return None
        rows = stmt.get('result')
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return 0
        return rows[0].get('count', 0)

    counts = {t: count_of(t) for t in ('video', 'segment', 'channel')}
    failed = [t for t, c in counts.items() if c is None]

    if failed:
        return jsonify({
            'success': False,
            'error': f"could not read counts for: {', '.join(failed)}",
        }), 503

    return jsonify({
        'success': True,
        'videos': counts['video'],
        'segments': counts['segment'],
        'channels': counts['channel'],
    })


@app.route('/')
def index():
    """API info."""
    return jsonify({
        'name': 'KnowledgeEnroll Embedding Service',
        'version': '1.1.0',
        'endpoints': {
            'health': 'GET /health',
            'embed': 'POST /api/embed',
            'search': 'POST /api/search',
            'video': 'GET /api/video/<id>',
            'video_tags': 'POST /api/video/<id>/tags',
            'stats': 'GET /api/stats'
        }
    })


if __name__ == '__main__':
    print("Starting KnowledgeEnroll Embedding Service...")
    print(f"SurrealDB: {Config.SURREAL_URL}")
    print(f"Port: {Config.PORT}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=Config.DEBUG)
