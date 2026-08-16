"""Channel management API endpoints."""
import subprocess
import json
import re
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import quote

import requests
from flask import Blueprint, jsonify, request
from db import get_db_cursor

channels_bp = Blueprint('channels', __name__)

INGESTION_MODES = {'new_only', 'last_3_months', 'last_year', 'all', 'selected'}
def _validate_ingestion_mode(data):
    mode = data.get('ingestion_mode')
    if mode is not None and mode not in INGESTION_MODES:
        return jsonify({'error': 'Invalid ingestion_mode', 'allowed': sorted(INGESTION_MODES)}), 400
    return None


def _published_at(upload_date):
    if isinstance(upload_date, (int, float)):
        return datetime.fromtimestamp(upload_date, tz=timezone.utc)
    try:
        return datetime.strptime(str(upload_date), '%Y%m%d').replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _within_mode_cutoff(video, mode):
    days = {'last_3_months': 90, 'last_year': 365}.get(mode)
    if not days:
        return True
    published = _published_at(video.get('upload_date'))
    return published is not None and published >= datetime.now(timezone.utc) - timedelta(days=days)


def _included_content(video, channel):
    url = str(video.get('webpage_url') or video.get('url') or '')
    is_short = '/shorts/' in url or video.get('url_kind') == 'short'
    live_status = str(video.get('live_status') or '').lower()
    is_live = bool(video.get('was_live')) or live_status in {'is_live', 'was_live', 'post_live'}
    if is_short:
        return channel['include_shorts']
    if is_live:
        return channel['include_lives']
    return channel['include_videos']


def fetch_channel_videos_from_youtube(channel_id, limit=50):
    """Fetch video, live, and Shorts listings from YouTube using yt-dlp."""
    try:
        videos = []
        seen = set()
        for tab in ('videos', 'streams', 'shorts'):
            cmd = [
                'yt-dlp', '--flat-playlist', '--dump-json',
                '--playlist-end', str(limit),
                f'https://www.youtube.com/channel/{channel_id}/{tab}'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                video_id = data.get('id')
                if not video_id or video_id in seen:
                    continue
                seen.add(video_id)
                videos.append({
                    'youtube_video_id': video_id,
                    'title': data.get('title'),
                    'duration': data.get('duration'),
                    'view_count': data.get('view_count'),
                    'upload_date': data.get('upload_date') or data.get('timestamp') or data.get('release_timestamp'),
                    'webpage_url': data.get('webpage_url') or (
                        f'https://www.youtube.com/shorts/{video_id}' if tab == 'shorts'
                        else f'https://www.youtube.com/watch?v={video_id}'
                    ),
                    'url_kind': 'short' if tab == 'shorts' else 'video',
                    'live_status': data.get('live_status'),
                    'was_live': data.get('was_live') or tab == 'streams',
                    'thumbnail': data.get('thumbnail') or f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'
                })
        return videos[:limit]
    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []


@channels_bp.route('/channels', methods=['GET'])
def list_channels():
    """List all channels with optional filtering."""
    # Query params
    domain = request.args.get('domain')
    is_active = request.args.get('is_active')
    ingestion_mode = request.args.get('ingestion_mode')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    query = """
        SELECT id, youtube_handle, youtube_channel_id, name, description,
               thumbnail_url, subscriber_count, video_count,
               domain, authority_score, relevance_score, ingestion_mode,
               include_videos, include_lives, include_shorts,
               is_active, last_checked_at, last_video_at, consecutive_failures,
               created_at, updated_at
        FROM channels
        WHERE 1=1
    """
    params = []

    if domain:
        query += " AND domain = %s"
        params.append(domain)

    if is_active is not None:
        query += " AND is_active = %s"
        params.append(is_active.lower() == 'true')

    if ingestion_mode:
        query += " AND ingestion_mode = %s"
        params.append(ingestion_mode)

    query += " ORDER BY name ASC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        channels = cursor.fetchall()

        # Get total count
        cursor.execute("SELECT COUNT(*) as count FROM channels")
        total = cursor.fetchone()['count']

    return jsonify({
        'channels': [dict(c) for c in channels],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@channels_bp.route('/channels/<uuid:channel_id>', methods=['GET'])
def get_channel(channel_id):
    """Get a single channel by ID."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, youtube_handle, youtube_channel_id, name, description,
                   thumbnail_url, subscriber_count, video_count,
                   domain, authority_score, relevance_score, ingestion_mode,
                   include_videos, include_lives, include_shorts,
                   check_interval_minutes, backlog_depth_days, backlog_max_videos,
                   rss_url, last_checked_at, last_video_at, last_error,
                   consecutive_failures, is_active, is_known_exception,
                   created_at, updated_at, created_by
            FROM channels
            WHERE id = %s
        """, (str(channel_id),))
        channel = cursor.fetchone()

    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    return jsonify(dict(channel))


@channels_bp.route('/channels', methods=['POST'])
def create_channel():
    """Create a new channel."""
    data = request.get_json(silent=True) or {}
    validation_error = _validate_ingestion_mode(data or {})
    if validation_error:
        return validation_error

    # Required fields
    required = ['youtube_handle', 'name']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Build insert query
    fields = ['youtube_handle', 'name']
    values = [data['youtube_handle'], data['name']]
    placeholders = ['%s', '%s']

    # Optional fields
    optional_fields = [
        'youtube_channel_id', 'description', 'thumbnail_url',
        'subscriber_count', 'video_count', 'domain',
        'authority_score', 'relevance_score', 'ingestion_mode',
        'check_interval_minutes', 'backlog_depth_days', 'backlog_max_videos',
        'is_active', 'is_known_exception', 'created_by',
        'include_videos', 'include_lives', 'include_shorts'
    ]

    for field in optional_fields:
        if field in data:
            fields.append(field)
            values.append(data[field])
            placeholders.append('%s')

    query = f"""
        INSERT INTO channels ({', '.join(fields)})
        VALUES ({', '.join(placeholders)})
        RETURNING id, youtube_handle, name, domain, is_active, created_at
    """

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, values)
            channel = cursor.fetchone()
        return jsonify(dict(channel)), 201
    except Exception as e:
        if 'channels_youtube_handle_unique' in str(e):
            return jsonify({'error': 'Channel with this handle already exists'}), 409
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/channels/<uuid:channel_id>', methods=['PUT'])
def update_channel(channel_id):
    """Update an existing channel."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400
    validation_error = _validate_ingestion_mode(data)
    if validation_error:
        return validation_error

    # Build update query
    allowed_fields = [
        'youtube_handle', 'youtube_channel_id', 'name', 'description',
        'thumbnail_url', 'subscriber_count', 'video_count', 'domain',
        'authority_score', 'relevance_score', 'ingestion_mode',
        'check_interval_minutes', 'backlog_depth_days', 'backlog_max_videos',
        'is_active', 'is_known_exception',
        'include_videos', 'include_lives', 'include_shorts'
    ]

    updates = []
    values = []

    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = %s")
            values.append(data[field])

    if not updates:
        return jsonify({'error': 'No valid fields to update'}), 400

    values.append(str(channel_id))

    query = f"""
        UPDATE channels
        SET {', '.join(updates)}
        WHERE id = %s
        RETURNING id, youtube_handle, name, domain, is_active, updated_at
    """

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, values)
            channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

        return jsonify(dict(channel))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/channels/<uuid:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """Delete a channel."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(
            "DELETE FROM channels WHERE id = %s RETURNING id",
            (str(channel_id),)
        )
        result = cursor.fetchone()

    if not result:
        return jsonify({'error': 'Channel not found'}), 404

    return jsonify({'deleted': True, 'id': str(channel_id)})


@channels_bp.route('/channels/<uuid:channel_id>/toggle', methods=['POST'])
def toggle_channel(channel_id):
    """Toggle channel active status."""
    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE channels
            SET is_active = NOT is_active
            WHERE id = %s
            RETURNING id, youtube_handle, name, is_active
        """, (str(channel_id),))
        channel = cursor.fetchone()

    if not channel:
        return jsonify({'error': 'Channel not found'}), 404

    return jsonify(dict(channel))


@channels_bp.route('/channels/bulk', methods=['POST'])
def bulk_create_channels():
    """Bulk create channels from CSV-like data."""
    data = request.get_json()

    if 'channels' not in data:
        return jsonify({'error': 'Missing channels array'}), 400

    created = []
    errors = []

    for i, channel_data in enumerate(data['channels']):
        if 'youtube_handle' not in channel_data or 'name' not in channel_data:
            errors.append({'index': i, 'error': 'Missing required fields'})
            continue
        validation_error = _validate_ingestion_mode(channel_data)
        if validation_error:
            errors.append({'index': i, 'error': 'Invalid ingestion_mode'})
            continue

        # Build insert
        fields = ['youtube_handle', 'name']
        values = [channel_data['youtube_handle'], channel_data['name']]

        optional = ['domain', 'authority_score', 'relevance_score', 'ingestion_mode', 'description']
        for f in optional:
            if f in channel_data:
                fields.append(f)
                values.append(channel_data[f])

        placeholders = ['%s'] * len(fields)
        query = f"""
            INSERT INTO channels ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (youtube_handle) DO NOTHING
            RETURNING id, youtube_handle, name
        """

        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(query, values)
                result = cursor.fetchone()
                if result:
                    created.append(dict(result))
                else:
                    errors.append({'index': i, 'error': 'Already exists', 'handle': channel_data['youtube_handle']})
        except Exception as e:
            errors.append({'index': i, 'error': str(e)})

    return jsonify({
        'created': created,
        'created_count': len(created),
        'errors': errors,
        'error_count': len(errors)
    })


@channels_bp.route('/channels/exists', methods=['GET'])
def channel_exists():
    """Cheap duplicate check so the Add Channel form can warn on handle entry."""
    handle = request.args.get('handle', '').strip().lstrip('@')
    if not handle:
        return jsonify({'error': 'handle is required'}), 400
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name FROM channels
            WHERE LOWER(youtube_handle) = LOWER(%s)
            LIMIT 1
        """, (handle,))
        row = cursor.fetchone()
    if row:
        return jsonify({'exists': True, 'id': row['id'], 'name': row['name']})
    return jsonify({'exists': False})


@channels_bp.route('/channels/preview', methods=['GET'])
def channel_preview():
    """What enrolling this channel would ingest: recent sample per content type.

    Three yt-dlp listings (videos/streams/shorts tabs) run concurrently, five
    items each, so the Add Channel form can show counts + thumbnails before
    the user commits.
    """
    channel_id = request.args.get('channel_id', '').strip()
    if not re.fullmatch(r'UC[A-Za-z0-9_-]{22}', channel_id):
        return jsonify({'error': 'channel_id (UC...) is required'}), 400

    from concurrent.futures import ThreadPoolExecutor

    def sample(tab):
        try:
            result = subprocess.run(
                ['yt-dlp', '-J', '--flat-playlist', '--playlist-end', '5',
                 f'https://www.youtube.com/channel/{channel_id}/{tab}'],
                capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout or '{}') or {}
            entries = data.get('entries') or []
            items = [{
                'id': e['id'],
                'title': e.get('title') or '',
                'thumbnail': f"https://i.ytimg.com/vi/{e['id']}/mqdefault.jpg",
                'url': (f"https://www.youtube.com/shorts/{e['id']}" if tab == 'shorts'
                        else f"https://www.youtube.com/watch?v={e['id']}"),
            } for e in entries if e.get('id')]
            return {'count': data.get('playlist_count'), 'items': items}
        except Exception:
            # A tab the channel doesn't have (no shorts, no lives) or a slow
            # listing must not sink the whole preview.
            return {'count': None, 'items': []}

    with ThreadPoolExecutor(max_workers=3) as pool:
        videos, lives, shorts = pool.map(sample, ['videos', 'streams', 'shorts'])
    return jsonify({'videos': videos, 'lives': lives, 'shorts': shorts})


@channels_bp.route('/channels/resolve', methods=['GET'])
def resolve_channel():
    """Resolve a YouTube handle/custom URL to public channel metadata."""
    raw = request.args.get('handle', '').strip()
    if not raw:
        return jsonify({'error': 'handle is required'}), 400
    if raw.startswith(('http://', 'https://')):
        match = re.search(r'youtube\.com/((?:@|c/)[^/?#]+)', raw, re.I)
        if not match:
            return jsonify({'error': 'Only YouTube handle or /c/ URLs are supported'}), 400
        path = match.group(1)
    elif raw.startswith('/c/'):
        path = raw.lstrip('/')
    else:
        path = '@' + raw.lstrip('@')
    try:
        response = requests.get(
            'https://www.youtube.com/' + quote(path, safe='@/'),
            headers={'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'},
            timeout=5,
        )
    except requests.RequestException:
        return jsonify({'error': 'YouTube could not be reached'}), 404
    if not response.ok:
        return jsonify({'error': 'Channel not found'}), 404

    html = response.text[:8 * 1024 * 1024]
    title_match = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I
    ) or re.search(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.I
    )
    channel_match = re.search(
        r'itemprop=["\']channelId["\'][^>]+content=["\'](UC[A-Za-z0-9_-]{22})', html, re.I
    ) or re.search(r'"(?:externalId|channelId)":"(UC[A-Za-z0-9_-]{22})"', html)
    thumb_match = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.I
    )
    if not title_match or not channel_match:
        return jsonify({'error': 'Channel metadata not found'}), 404
    result = {
        'name': unescape(title_match.group(1)),
        'youtube_channel_id': channel_match.group(1),
    }
    if thumb_match:
        result['thumbnail_url'] = unescape(thumb_match.group(1))
    # Best-effort total for the ingest preview — embedded page JSON carries a
    # human-readable count ("1,234 videos"); absence is fine.
    count_match = re.search(r'"videosCountText":.{0,200}?"text":"([^"]+)"', html)
    if count_match:
        result['video_count_text'] = unescape(count_match.group(1))
    return jsonify(result)


@channels_bp.route('/channels/stats', methods=['GET'])
def channel_stats():
    """Get channel statistics."""
    with get_db_cursor() as cursor:
        # Total counts by domain
        cursor.execute("""
            SELECT domain, COUNT(*) as count,
                   SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active_count
            FROM channels
            GROUP BY domain
            ORDER BY count DESC
        """)
        by_domain = cursor.fetchall()

        # Total counts by ingestion mode
        cursor.execute("""
            SELECT ingestion_mode, COUNT(*) as count
            FROM channels
            GROUP BY ingestion_mode
        """)
        by_mode = cursor.fetchall()

        # Health status
        cursor.execute("""
            SELECT
                SUM(CASE WHEN consecutive_failures = 0 THEN 1 ELSE 0 END) as healthy,
                SUM(CASE WHEN consecutive_failures BETWEEN 1 AND 2 THEN 1 ELSE 0 END) as warning,
                SUM(CASE WHEN consecutive_failures >= 3 THEN 1 ELSE 0 END) as error,
                SUM(CASE WHEN is_known_exception THEN 1 ELSE 0 END) as exceptions
            FROM channels
        """)
        health = cursor.fetchone()

        # Total
        cursor.execute("SELECT COUNT(*) as total FROM channels")
        total = cursor.fetchone()['total']

    return jsonify({
        'total': total,
        'by_domain': [dict(d) for d in by_domain],
        'by_ingestion_mode': [dict(m) for m in by_mode],
        'health': dict(health)
    })


@channels_bp.route('/channels/<uuid:channel_id>/videos', methods=['GET'])
def get_channel_videos(channel_id):
    """Get videos for a channel - combines YouTube data with pipeline status."""
    limit = request.args.get('limit', 50, type=int)
    source = request.args.get('source', 'youtube')  # 'youtube', 'pipeline', 'both'

    with get_db_cursor() as cursor:
        # Get channel info
        cursor.execute("""
            SELECT youtube_channel_id, youtube_handle, name
            FROM channels WHERE id = %s
        """, (str(channel_id),))
        channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

        if not channel['youtube_channel_id']:
            return jsonify({'error': 'Channel has no YouTube channel ID'}), 400

        # Get existing pipeline items for this channel
        cursor.execute("""
            SELECT youtube_video_id, title, status, discovered_at, published_at
            FROM pipeline_items
            WHERE channel_id = %s
            ORDER BY discovered_at DESC
        """, (str(channel_id),))
        pipeline_items = {row['youtube_video_id']: dict(row) for row in cursor.fetchall()}

        # Also get items by youtube_video_id (for items without channel_id set)
        if not pipeline_items:
            cursor.execute("""
                SELECT youtube_video_id, title, status, discovered_at, published_at
                FROM pipeline_items
                ORDER BY discovered_at DESC
            """)
            all_items = {row['youtube_video_id']: dict(row) for row in cursor.fetchall()}
            pipeline_items = all_items

    result_videos = []

    if source in ('youtube', 'both'):
        # Fetch from YouTube
        yt_videos = fetch_channel_videos_from_youtube(channel['youtube_channel_id'], limit)

        for video in yt_videos:
            video_id = video['youtube_video_id']
            pipeline_status = pipeline_items.get(video_id)

            result_videos.append({
                **video,
                'pipeline_status': pipeline_status['status'] if pipeline_status else None,
                'discovered_at': pipeline_status['discovered_at'].isoformat() if pipeline_status and pipeline_status.get('discovered_at') else None,
                'in_pipeline': video_id in pipeline_items
            })

    if source == 'pipeline':
        # Only show pipeline items
        for video_id, item in pipeline_items.items():
            result_videos.append({
                'youtube_video_id': video_id,
                'title': item['title'],
                'pipeline_status': item['status'],
                'discovered_at': item['discovered_at'].isoformat() if item.get('discovered_at') else None,
                'in_pipeline': True
            })

    return jsonify({
        'channel': dict(channel),
        'videos': result_videos,
        'total': len(result_videos),
        'source': source
    })


@channels_bp.route('/channels/<uuid:channel_id>/settings', methods=['PUT'])
def update_channel_settings(channel_id):
    """Update channel ingestion settings."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    validation_error = _validate_ingestion_mode(data)
    if validation_error:
        return validation_error
    allowed_fields = ['ingestion_mode', 'backfill_limit', 'backlog_max_videos', 'backlog_depth_days']
    updates = []
    values = []

    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = %s")
            values.append(data[field])

    if not updates:
        return jsonify({'error': 'No valid settings to update'}), 400

    values.append(str(channel_id))

    query = f"""
        UPDATE channels
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = %s
        RETURNING id, youtube_handle, ingestion_mode, backfill_limit, backlog_max_videos, backlog_depth_days
    """

    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(query, values)
            channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

        return jsonify(dict(channel))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@channels_bp.route('/channels/<uuid:channel_id>/backfill', methods=['POST'])
def trigger_backfill(channel_id):
    """Trigger a backfill for a channel - fetch and queue last N videos."""
    data = request.get_json() or {}
    limit = data.get('limit', 20)

    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT youtube_channel_id, youtube_handle, name, ingestion_mode,
                   include_videos, include_lives, include_shorts
            FROM channels WHERE id = %s
        """, (str(channel_id),))
        channel = cursor.fetchone()

        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

        if not channel['youtube_channel_id']:
            return jsonify({'error': 'Channel has no YouTube channel ID'}), 400

    # Fetch videos from YouTube
    videos = fetch_channel_videos_from_youtube(channel['youtube_channel_id'], limit)

    if not videos:
        return jsonify({'error': 'Could not fetch videos from YouTube'}), 500

    # Determine status based on ingestion mode
    # 'all' or 'new_only' = auto-queue for processing
    # 'selected' = discovered, waiting for user to select
    initial_status = 'queued' if channel['ingestion_mode'] in (
        'all', 'new_only', 'last_3_months', 'last_year'
    ) else 'discovered'

    # Insert into pipeline_items
    inserted = 0
    skipped = 0

    with get_db_cursor(commit=True) as cursor:
        for video in videos:
            if not _within_mode_cutoff(video, channel['ingestion_mode']) or not _included_content(video, channel):
                skipped += 1
                continue
            try:
                cursor.execute("""
                    INSERT INTO pipeline_items (youtube_video_id, youtube_url, title, channel_id, status, published_at, discovered_at, queued_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), CASE WHEN %s = 'queued' THEN NOW() ELSE NULL END)
                    ON CONFLICT (youtube_video_id) DO NOTHING
                    RETURNING id
                """, (
                    video['youtube_video_id'],
                    f"https://www.youtube.com/watch?v={video['youtube_video_id']}",
                    video['title'],
                    str(channel_id),
                    initial_status,
                    _published_at(video.get('upload_date')),
                    initial_status,
                ))
                if cursor.fetchone():
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"Error inserting video {video['youtube_video_id']}: {e}")
                skipped += 1

        # Update channel's last_backfill_at
        cursor.execute("""
            UPDATE channels SET last_backfill_at = NOW(), backfill_limit = %s
            WHERE id = %s
        """, (limit, str(channel_id)))

    return jsonify({
        'success': True,
        'channel': dict(channel),
        'fetched': len(videos),
        'inserted': inserted,
        'skipped': skipped,
        'initial_status': initial_status
    })


@channels_bp.route('/channels/<uuid:channel_id>/ingest', methods=['POST'])
def ingest_selected_videos(channel_id):
    """Queue selected videos for ingestion."""
    data = request.get_json()

    if not data or 'video_ids' not in data:
        return jsonify({'error': 'Missing video_ids array'}), 400

    video_ids = data['video_ids']

    if not video_ids:
        return jsonify({'error': 'No videos selected'}), 400

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id, youtube_handle FROM channels WHERE id = %s", (str(channel_id),))
        channel = cursor.fetchone()
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

    inserted = 0
    updated = 0
    skipped = 0

    with get_db_cursor(commit=True) as cursor:
        for video_id in video_ids:
            try:
                # First try to update existing skipped/discovered items to queued
                cursor.execute("""
                    UPDATE pipeline_items
                    SET status = 'queued'
                    WHERE youtube_video_id = %s AND status IN ('discovered', 'skipped')
                    RETURNING id
                """, (video_id,))
                if cursor.fetchone():
                    updated += 1
                    continue

                # Otherwise insert new item with queued status
                cursor.execute("""
                    INSERT INTO pipeline_items (youtube_video_id, youtube_url, title, channel_id, status, discovered_at)
                    VALUES (%s, %s, %s, %s, 'queued', NOW())
                    ON CONFLICT (youtube_video_id) DO NOTHING
                    RETURNING id
                """, (
                    video_id,
                    f"https://www.youtube.com/watch?v={video_id}",
                    data.get('titles', {}).get(video_id, f"Video {video_id}"),
                    str(channel_id)
                ))
                if cursor.fetchone():
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"Error inserting video {video_id}: {e}")
                skipped += 1

    return jsonify({
        'success': True,
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped,
        'total': len(video_ids)
    })


@channels_bp.route('/channels/<uuid:channel_id>/skip', methods=['POST'])
def skip_selected_videos(channel_id):
    """Skip selected videos (user decided not to ingest)."""
    data = request.get_json()

    if not data or 'video_ids' not in data:
        return jsonify({'error': 'Missing video_ids array'}), 400

    video_ids = data['video_ids']

    if not video_ids:
        return jsonify({'error': 'No videos selected'}), 400

    with get_db_cursor() as cursor:
        cursor.execute("SELECT id, youtube_handle FROM channels WHERE id = %s", (str(channel_id),))
        channel = cursor.fetchone()
        if not channel:
            return jsonify({'error': 'Channel not found'}), 404

    skipped = 0
    already_skipped = 0

    with get_db_cursor(commit=True) as cursor:
        for video_id in video_ids:
            try:
                # First try to update existing discovered/queued items to skipped
                cursor.execute("""
                    UPDATE pipeline_items
                    SET status = 'skipped', updated_at = NOW()
                    WHERE youtube_video_id = %s AND status IN ('discovered', 'queued')
                    RETURNING id
                """, (video_id,))
                if cursor.fetchone():
                    skipped += 1
                    continue

                # Otherwise insert new item with skipped status
                cursor.execute("""
                    INSERT INTO pipeline_items (youtube_video_id, youtube_url, title, channel_id, status, discovered_at)
                    VALUES (%s, %s, %s, %s, 'skipped', NOW())
                    ON CONFLICT (youtube_video_id) DO NOTHING
                    RETURNING id
                """, (
                    video_id,
                    f"https://www.youtube.com/watch?v={video_id}",
                    data.get('titles', {}).get(video_id, f"Video {video_id}"),
                    str(channel_id)
                ))
                if cursor.fetchone():
                    skipped += 1
                else:
                    already_skipped += 1
            except Exception as e:
                print(f"Error skipping video {video_id}: {e}")
                already_skipped += 1

    return jsonify({
        'success': True,
        'skipped': skipped,
        'already_skipped': already_skipped,
        'total': len(video_ids)
    })
