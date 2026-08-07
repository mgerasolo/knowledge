"""Pipeline monitoring API endpoints."""
from flask import Blueprint, jsonify, request
from db import get_db_cursor

pipeline_bp = Blueprint('pipeline', __name__)


@pipeline_bp.route('/pipeline/items', methods=['GET'])
def list_pipeline_items():
    """List pipeline items with filtering."""
    status = request.args.get('status')
    channel_id = request.args.get('channel_id')
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = """
        SELECT pi.id, pi.youtube_video_id, pi.youtube_url, pi.title,
               pi.status, pi.retry_count, pi.claimed_by,
               pi.discovered_at, pi.started_at, pi.completed_at,
               pi.last_error, pi.error_stage,
               c.name as channel_name, c.youtube_handle as channel_handle
        FROM pipeline_items pi
        LEFT JOIN channels c ON pi.channel_id = c.id
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND pi.status = %s"
        params.append(status)

    if channel_id:
        query += " AND pi.channel_id = %s"
        params.append(channel_id)

    query += " ORDER BY pi.discovered_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        items = cursor.fetchall()

        # Get count
        count_query = "SELECT COUNT(*) as count FROM pipeline_items WHERE 1=1"
        count_params = []
        if status:
            count_query += " AND status = %s"
            count_params.append(status)
        if channel_id:
            count_query += " AND channel_id = %s"
            count_params.append(channel_id)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['count']

    return jsonify({
        'items': [dict(i) for i in items],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@pipeline_bp.route('/pipeline/items/<uuid:item_id>', methods=['GET'])
def get_pipeline_item(item_id):
    """Get a single pipeline item."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT pi.*, c.name as channel_name, c.youtube_handle as channel_handle
            FROM pipeline_items pi
            LEFT JOIN channels c ON pi.channel_id = c.id
            WHERE pi.id = %s
        """, (str(item_id),))
        item = cursor.fetchone()

    if not item:
        return jsonify({'error': 'Item not found'}), 404

    return jsonify(dict(item))


@pipeline_bp.route('/pipeline/items/<uuid:item_id>/retry', methods=['POST'])
def retry_pipeline_item(item_id):
    """Reset a failed item to queued for retry."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE pipeline_items
            SET status = 'queued',
                retry_count = 0,
                claimed_by = NULL,
                claimed_at = NULL,
                last_error = NULL,
                error_stage = NULL
            WHERE id = %s AND status = 'failed'
            RETURNING id, youtube_video_id, title, status
        """, (str(item_id),))
        item = cursor.fetchone()

    if not item:
        return jsonify({'error': 'Item not found or not in failed state'}), 404

    return jsonify(dict(item))


@pipeline_bp.route('/pipeline/items/<item_id>/skip', methods=['POST'])
def skip_pipeline_item(item_id):
    """Mark an item as skipped (cancel it)."""
    with get_db_cursor(commit=True) as cursor:
        # Try by youtube_video_id first (11-char string), then by UUID
        cursor.execute("""
            UPDATE pipeline_items
            SET status = 'skipped'
            WHERE youtube_video_id = %s
              AND status IN ('discovered', 'queued')
            RETURNING id, youtube_video_id, title, status
        """, (item_id,))
        item = cursor.fetchone()

        if not item:
            # Try by UUID
            cursor.execute("""
                UPDATE pipeline_items
                SET status = 'skipped'
                WHERE id::text = %s
                  AND status IN ('discovered', 'queued')
                RETURNING id, youtube_video_id, title, status
            """, (item_id,))
            item = cursor.fetchone()

    if not item:
        return jsonify({'error': 'Item not found or not in cancellable state'}), 404

    return jsonify(dict(item))


@pipeline_bp.route('/pipeline/stats', methods=['GET'])
def pipeline_stats():
    """Get pipeline statistics with optional time period filter."""
    # Time period filter: 24h, 7d, 30d, all (default)
    period = request.args.get('period', 'all')
    period_map = {
        '24h': "INTERVAL '24 hours'",
        '7d': "INTERVAL '7 days'",
        '30d': "INTERVAL '30 days'",
        'all': None
    }
    interval = period_map.get(period)

    with get_db_cursor() as cursor:
        # Build time filter clause
        time_filter = ""
        if interval:
            time_filter = f"WHERE discovered_at > NOW() - {interval}"

        # Status distribution (with optional time filter)
        cursor.execute(f"""
            SELECT status, COUNT(*) as count
            FROM pipeline_items
            {time_filter}
            GROUP BY status
            ORDER BY count DESC
        """)
        by_status = cursor.fetchall()

        # Total (with optional time filter)
        cursor.execute(f"SELECT COUNT(*) as total FROM pipeline_items {time_filter}")
        total = cursor.fetchone()['total']

        # Recent activity (always last 24h for the activity indicators)
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE discovered_at > NOW() - INTERVAL '24 hours') as discovered_24h,
                COUNT(*) FILTER (WHERE completed_at > NOW() - INTERVAL '24 hours') as completed_24h,
                COUNT(*) FILTER (WHERE status = 'failed' AND discovered_at > NOW() - INTERVAL '24 hours') as failed_24h
            FROM pipeline_items
        """)
        recent = cursor.fetchone()

        # Stale claims (always check all)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pipeline_items
            WHERE claimed_at < NOW() - INTERVAL '15 minutes'
              AND status IN ('downloading', 'uploading', 'transcribing', 'embedding', 'indexing')
        """)
        stale = cursor.fetchone()['count']

    return jsonify({
        'total': total,
        'period': period,
        'by_status': [dict(s) for s in by_status],
        'recent_24h': dict(recent),
        'stale_claims': stale
    })


@pipeline_bp.route('/pipeline/failed', methods=['GET'])
def list_failed_items():
    """List failed items (dead letter queue)."""
    limit = request.args.get('limit', 50, type=int)

    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT pi.id, pi.youtube_video_id, pi.youtube_url, pi.title,
                   pi.retry_count, pi.last_error, pi.error_stage,
                   pi.discovered_at,
                   c.name as channel_name, c.youtube_handle as channel_handle
            FROM pipeline_items pi
            LEFT JOIN channels c ON pi.channel_id = c.id
            WHERE pi.status = 'failed'
            ORDER BY pi.discovered_at DESC
            LIMIT %s
        """, (limit,))
        items = cursor.fetchall()

    return jsonify({
        'items': [dict(i) for i in items],
        'count': len(items)
    })


@pipeline_bp.route('/pipeline/release-stale', methods=['POST'])
def release_stale_claims():
    """Release stale claims (items stuck in processing)."""
    timeout_minutes = request.args.get('timeout', 15, type=int)

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("SELECT release_stale_claims(%s) as released", (timeout_minutes,))
        released = cursor.fetchone()['released']

    return jsonify({
        'released': released,
        'timeout_minutes': timeout_minutes
    })


@pipeline_bp.route('/pipeline/bulk-retry', methods=['POST'])
def bulk_retry_failed():
    """Retry all failed items or a specific list."""
    data = request.get_json() or {}
    item_ids = data.get('item_ids')

    with get_db_cursor(commit=True) as cursor:
        if item_ids:
            cursor.execute("""
                UPDATE pipeline_items
                SET status = 'queued',
                    retry_count = 0,
                    claimed_by = NULL,
                    claimed_at = NULL,
                    last_error = NULL,
                    error_stage = NULL
                WHERE id = ANY(%s) AND status = 'failed'
                RETURNING id
            """, (item_ids,))
        else:
            cursor.execute("""
                UPDATE pipeline_items
                SET status = 'queued',
                    retry_count = 0,
                    claimed_by = NULL,
                    claimed_at = NULL,
                    last_error = NULL,
                    error_stage = NULL
                WHERE status = 'failed'
                RETURNING id
            """)

        results = cursor.fetchall()

    return jsonify({
        'retried': len(results),
        'item_ids': [str(r['id']) for r in results]
    })
