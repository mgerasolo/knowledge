"""Video browsing and search API endpoints."""
import requests
from flask import Blueprint, jsonify, request, render_template
from config import Config

videos_bp = Blueprint('videos', __name__)

SURREAL_URL = Config.SURREAL_URL
SURREAL_NS = Config.SURREAL_NS
SURREAL_DB = Config.SURREAL_DB
SURREAL_AUTH = (Config.SURREAL_USER, Config.SURREAL_PASS)


def q(text: str) -> str:
    """Escape user input for a single-quoted SurrealQL literal.

    Search terms reach these queries straight from the query string; without
    this a quote character breaks the statement, and a crafted one could append
    clauses of its own.
    """
    if not text:
        return ""
    out = text.replace("\\", "\\\\").replace("'", "\\'")
    return "".join(c for c in out if ord(c) >= 32)


class SurrealError(RuntimeError):
    """A SurrealDB statement was rejected, or the server was unreachable."""


def surreal_query(query: str):
    """Execute a SurrealDB query and return its rows.

    Raises SurrealError instead of returning junk. SurrealDB answers HTTP 200
    even when a statement fails, putting an error STRING where the result rows
    belong — so the previous version handed callers a string they then called
    .get() on, producing an AttributeError and a blank 500. Worse, some callers
    turned that into an HTTP 200 with an error message embedded in the payload,
    which is undetectable by consumers checking status codes.
    """
    try:
        response = requests.post(
            f"{SURREAL_URL}/sql",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
                "surreal-ns": SURREAL_NS,
                "surreal-db": SURREAL_DB,
            },
            auth=SURREAL_AUTH,
            data=query.encode("utf-8"),
            timeout=30
        )
    except Exception as e:
        raise SurrealError(f"SurrealDB unreachable: {e}") from e

    if not response.ok:
        raise SurrealError(f"SurrealDB returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as e:
        raise SurrealError("SurrealDB response was not JSON") from e

    if not isinstance(payload, list) or not payload:
        raise SurrealError("unexpected response shape from SurrealDB")

    statement = payload[0]
    if not isinstance(statement, dict):
        raise SurrealError("unexpected statement shape from SurrealDB")

    if statement.get('status') != 'OK':
        raise SurrealError(str(statement.get('result', 'unknown SurrealDB error')))

    rows = statement.get('result', [])
    return rows if isinstance(rows, list) else []


def count_from(rows) -> int:
    """Read the count out of a `SELECT count() ... GROUP ALL` result."""
    if rows and isinstance(rows[0], dict):
        return rows[0].get('count', 0)
    return 0


@videos_bp.errorhandler(SurrealError)
def _handle_surreal_error(err):
    """Report a datastore failure as 503 — never as a 200 with an error inside."""
    return jsonify({'error': str(err), 'source': 'surrealdb'}), 503


# ============== UI Routes ==============

@videos_bp.route('', methods=['GET'])
def videos_list_page():
    """Video browser page."""
    return render_template('videos.html')


@videos_bp.route('/<video_id>', methods=['GET'])
def video_detail_page(video_id):
    """Video detail page."""
    return render_template('video_detail.html', video_id=video_id)


# ============== API Routes ==============

@videos_bp.route('/api/list', methods=['GET'])
def list_videos():
    """List all videos with optional search."""
    search = request.args.get('q', '').strip()
    domain = request.args.get('domain', '')
    tag = request.args.get('tag', '').strip().lower()
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))

    # Build query
    conditions = []
    if search:
        # Search in title
        conditions.append(f"string::lowercase(title) CONTAINS string::lowercase('{q(search)}')")
    if domain:
        conditions.append(f"domain = '{q(domain)}'")
    if tag:
        # Corpus tags from single-video enrollment (#46), e.g.
        # personality:myron-golden. Records that predate tagging have no
        # tags field at all; CONTAINS on NONE is simply false, so they drop
        # out of a tag-filtered list without erroring.
        conditions.append(f"tags CONTAINS '{q(tag)}'")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT youtube_id, title, channel_handle, channel_name, domain, segment_count,
           published_at, ingested_at, duration_seconds, url, has_timestamps,
           description, tags
    FROM video
    {where_clause}
    ORDER BY ingested_at DESC
    LIMIT {limit} START {offset};
    """

    videos = surreal_query(query)

    # Get total count
    count_query = f"SELECT count() FROM video {where_clause} GROUP ALL;"
    total = count_from(surreal_query(count_query))

    return jsonify({
        'videos': videos,
        'total': total,
        'limit': limit,
        'offset': offset
    })


@videos_bp.route('/api/<video_id>', methods=['GET'])
def get_video(video_id):
    """Get video details with segments."""
    # Get video metadata
    video_query = f"SELECT * FROM video WHERE youtube_id = '{q(video_id)}';"
    videos = surreal_query(video_query)

    if not videos:
        return jsonify({'error': 'Video not found'}), 404

    video = videos[0]

    # Get segments
    segments_query = f"""
    SELECT chunk_index, start_time, end_time, duration, text,
           requires_visual, domain
    FROM segment
    WHERE video_youtube_id = '{q(video_id)}'
    ORDER BY chunk_index;
    """
    segments = surreal_query(segments_query)

    return jsonify({
        'video': video,
        'segments': segments
    })


@videos_bp.route('/api/search', methods=['GET'])
def search_segments():
    """Search across all segment text."""
    query = request.args.get('q', '').strip()
    domain = request.args.get('domain', '')
    limit = min(int(request.args.get('limit', 20)), 50)

    if not query:
        return jsonify({'error': 'Query required', 'results': []}), 400

    conditions = [f"string::lowercase(text) CONTAINS string::lowercase('{q(query)}')"]
    if domain:
        conditions.append(f"domain = '{q(domain)}'")

    where_clause = f"WHERE {' AND '.join(conditions)}"

    search_query = f"""
    SELECT video_youtube_id, chunk_index, start_time, end_time, text, domain
    FROM segment
    {where_clause}
    LIMIT {limit};
    """

    results = surreal_query(search_query)

    # Enrich with video titles
    video_ids = list(set(r.get('video_youtube_id') for r in results))
    if video_ids:
        ids_str = ', '.join(f"'{q(vid)}'" for vid in video_ids)
        videos_query = f"SELECT youtube_id, title FROM video WHERE youtube_id IN [{ids_str}];"
        videos = surreal_query(videos_query)
        video_map = {v['youtube_id']: v['title'] for v in videos}

        for r in results:
            r['video_title'] = video_map.get(r.get('video_youtube_id'), 'Unknown')

    return jsonify({
        'query': query,
        'results': results,
        'count': len(results)
    })


@videos_bp.route('/api/stats', methods=['GET'])
def video_stats():
    """Get video/segment statistics."""
    stats = {}

    # Total counts
    video_count = surreal_query("SELECT count() FROM video GROUP ALL;")
    segment_count = surreal_query("SELECT count() FROM segment GROUP ALL;")

    stats['total_videos'] = count_from(video_count)
    stats['total_segments'] = count_from(segment_count)

    # By domain
    domain_stats = surreal_query("""
        SELECT domain, count() as count
        FROM video
        GROUP BY domain;
    """)
    stats['by_domain'] = domain_stats

    # Visual segments
    visual_count = surreal_query("""
        SELECT count() FROM segment WHERE requires_visual = true GROUP ALL;
    """)
    stats['visual_segments'] = count_from(visual_count)

    return jsonify(stats)


@videos_bp.route('/api/domains', methods=['GET'])
def list_domains():
    """Get list of unique domains."""
    # `SELECT DISTINCT` is not SurrealQL — it parsed but always returned nothing,
    # which read as "no content exists". GROUP BY is the correct form.
    domains = surreal_query("SELECT domain FROM video GROUP BY domain;")
    return jsonify({
        'domains': sorted({d.get('domain') for d in domains if d.get('domain')})
    })
