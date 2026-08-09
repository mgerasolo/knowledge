"""HTTP surface for the metrics layer. Serialisation only — no logic lives here.

Every route returns HTTP 200 with a named `problems` list rather than a 500 when a
source is unreadable. A dashboard that returns 500 tells the reader nothing; one
that says "the search library refused the connection" tells them where to look.
"""
from flask import Blueprint, jsonify, request

from api import metrics

metrics_bp = Blueprint('metrics', __name__)


@metrics_bp.route('/metrics/daily')
def daily():
    """Videos ingested per day, split into series.

    Query params:
      days     — how far back (default 90, capped at 400)
      group    — category | subcategory | channel
      category — when drilling down, which top-level category to filter to
    """
    try:
        days = int(request.args.get('days', 90))
    except (TypeError, ValueError):
        days = 90

    group = request.args.get('group', 'category')
    if group not in ('category', 'subcategory', 'channel'):
        group = 'category'

    category = request.args.get('category') or None

    series = metrics.daily_series(days=days, group=group, category=category)
    return jsonify({
        'days': series.days,
        'series': series.series_names,
        'totals': series.totals,
        'problems': series.problems,
        'notes': series.notes,
        'group': group,
        'category': category,
        'rebuild_day': metrics.REBUILD_DAY.isoformat(),
        'reliable_from': metrics.CORPUS_TRUTH_FROM.isoformat(),
    })


@metrics_bp.route('/metrics/freshness')
def freshness():
    """Is anything still arriving — overall, per category, per channel."""
    return jsonify(metrics.freshness())


@metrics_bp.route('/metrics/library')
def library():
    """Corpus size. Context only; deliberately not the page's headline."""
    return jsonify(metrics.library_totals())


@metrics_bp.route('/metrics/refresh', methods=['POST'])
def refresh():
    """Drop the caches so the next read hits the sources.

    Exists because the file scan is cached for a minute, and someone watching a
    backfill run wants to see it move now rather than waiting out the TTL.
    """
    metrics.invalidate_caches()
    return jsonify({'refreshed': True})
