"""KnowledgeEnroll Admin API - Main Application."""
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from config import Config
from db import test_connection, get_db_cursor
from api.channels import channels_bp
from api.pipeline import pipeline_bp
from api.videos import videos_bp
from api.tags import tags_bp
from api.status import status_bp, build_status
from api.metrics_routes import metrics_bp

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, origins=Config.CORS_ORIGINS)


@app.context_processor
def inject_url_prefix():
    """Make URL_PREFIX available in all templates."""
    return {'url_prefix': Config.URL_PREFIX}


# Register blueprints
app.register_blueprint(channels_bp, url_prefix=Config.API_PREFIX)
app.register_blueprint(pipeline_bp, url_prefix=Config.API_PREFIX)
app.register_blueprint(videos_bp, url_prefix='/videos')
app.register_blueprint(tags_bp, url_prefix='/tags')
app.register_blueprint(status_bp, url_prefix=Config.API_PREFIX)
app.register_blueprint(metrics_bp, url_prefix=Config.API_PREFIX)


@app.route('/health')
def health():
    """Liveness check — cheap, unauthenticated, safe to poll often.

    This deliberately reports more than "the process is up". Until 2026-08-05 it
    checked Postgres alone and answered "healthy" throughout a two-week outage in
    which the search corpus was empty. It now surfaces the aggregate verdict so a
    plain status-code monitor still notices, while
    GET /api/v1/status carries the detail.
    """
    document, _ = build_status()
    state = document['status']
    return jsonify({
        'status': 'healthy' if state == 'ok' else state,
        'database': 'connected' if document['components']['postgres']['ok']
                    else 'disconnected',
        'problems': document['problems'],
        'detail': f"{Config.URL_PREFIX}/api/v1/status",
    }), 503 if state == 'down' else 200


@app.route('/api/v1')
def api_info():
    """API information endpoint."""
    return jsonify({
        'name': 'KnowledgeEnroll Admin API',
        'version': '1.0.0',
        'endpoints': {
            'channels': {
                'list': 'GET /api/v1/channels',
                'get': 'GET /api/v1/channels/<id>',
                'create': 'POST /api/v1/channels',
                'update': 'PUT /api/v1/channels/<id>',
                'delete': 'DELETE /api/v1/channels/<id>',
                'toggle': 'POST /api/v1/channels/<id>/toggle',
                'bulk_create': 'POST /api/v1/channels/bulk',
                'stats': 'GET /api/v1/channels/stats'
            },
            'pipeline': {
                'list': 'GET /api/v1/pipeline/items',
                'get': 'GET /api/v1/pipeline/items/<id>',
                'retry': 'POST /api/v1/pipeline/items/<id>/retry',
                'skip': 'POST /api/v1/pipeline/items/<id>/skip',
                'stats': 'GET /api/v1/pipeline/stats',
                'failed': 'GET /api/v1/pipeline/failed',
                'release_stale': 'POST /api/v1/pipeline/release-stale',
                'bulk_retry': 'POST /api/v1/pipeline/bulk-retry'
            }
        }
    })


@app.route('/')
def index():
    """Dashboard page."""
    return render_template('dashboard.html')


@app.route('/channels')
def channels_page():
    """Channels list page."""
    return render_template('channels.html')


@app.route('/channels/<uuid:channel_id>')
def channel_detail(channel_id):
    """Channel detail page with video list."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, youtube_handle, youtube_channel_id, name, description,
                   thumbnail_url, subscriber_count, video_count, domain,
                   ingestion_mode, backfill_limit, backlog_max_videos,
                   is_active, last_checked_at, last_backfill_at,
                   created_at, updated_at
            FROM channels WHERE id = %s
        """, (str(channel_id),))
        channel = cursor.fetchone()

        if not channel:
            return render_template('404.html', message='Channel not found'), 404

        # Get pipeline stats for this channel
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM pipeline_items
            WHERE channel_id = %s
            GROUP BY status
        """, (str(channel_id),))
        pipeline_stats = {row['status']: row['count'] for row in cursor.fetchall()}

    return render_template('channel_detail.html', channel=dict(channel), pipeline_stats=pipeline_stats)


@app.route('/control')
def control_page():
    """Ingestion control page — freshness and daily counts from the real library.

    Separate from /pipeline on purpose: that page is about work in flight, this one
    is about what we hold and whether it is still arriving.
    """
    return render_template('control.html')


@app.route('/pipeline')
def pipeline_page():
    """Pipeline status page."""
    return render_template('pipeline.html')


@app.route('/tags')
def tags_page():
    """Tag explorer page."""
    return render_template('tags.html')


@app.route('/settings')
def settings_page():
    """Settings page."""
    return render_template('settings.html')


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("Starting KnowledgeEnroll Admin API...")
    print(f"Database: {Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}")
    print(f"Debug mode: {Config.DEBUG}")
    app.run(host='0.0.0.0', port=5020, debug=Config.DEBUG)
