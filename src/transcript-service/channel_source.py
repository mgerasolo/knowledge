"""Load the transcript discovery channel list from Postgres."""

import logging
import os
import threading

import psycopg2

from config import Config


logger = logging.getLogger(__name__)

CHANNEL_QUERY = """
    SELECT youtube_handle, youtube_channel_id, name, domain, ingestion_mode,
           include_videos, include_lives, include_shorts,
           backlog_depth_days, backlog_max_videos
    FROM channels
    WHERE is_active = TRUE
      AND ingestion_mode NOT IN ('paused', 'guest_monitor')
"""

_status_lock = threading.Lock()
_last_channel_source = None
_last_channel_count = None


def _record_status(source: str, count: int) -> None:
    global _last_channel_source, _last_channel_count
    with _status_lock:
        _last_channel_source = source
        _last_channel_count = count


def channel_source_status() -> dict:
    """Return the source and count used by the most recent discovery load."""
    with _status_lock:
        return {
            "last_channel_source": _last_channel_source,
            "last_channel_count": _last_channel_count,
        }


def load_channels() -> list[dict]:
    """Load active discovery channels, falling back to frozen config on error."""
    connection = None
    try:
        connection = psycopg2.connect(
            host=os.getenv("KNOWLEDGE_DB_HOST", "10.0.0.33"),
            port=os.getenv("KNOWLEDGE_DB_PORT", "5010"),
            dbname=os.getenv("KNOWLEDGE_DB_NAME", "knowledge"),
            user=os.getenv("KNOWLEDGE_DB_USER", "knowledge"),
            password=os.getenv("KNOWLEDGE_DB_PASSWORD", ""),
            connect_timeout=3,
        )
        with connection.cursor() as cursor:
            cursor.execute(CHANNEL_QUERY)
            rows = cursor.fetchall()

        channels = []
        for row in rows:
            (
                youtube_handle,
                youtube_channel_id,
                name,
                domain,
                ingestion_mode,
                include_videos,
                include_lives,
                include_shorts,
                backlog_depth_days,
                backlog_max_videos,
            ) = row
            tabs = ["videos"]
            if include_lives:
                tabs.append("streams")
            if include_shorts:
                tabs.append("shorts")
            channels.append({
                "handle": youtube_handle.lstrip("@"),
                "youtube_channel_id": youtube_channel_id,
                "name": name,
                "domain": domain,
                "ingestion_mode": ingestion_mode,
                "include_videos": include_videos,
                "include_lives": include_lives,
                "include_shorts": include_shorts,
                "backlog_max_videos": backlog_max_videos,
                "lookback_months": max(1, round((backlog_depth_days or 30) / 30)),
                "tabs": tabs,
            })

        _record_status("database", len(channels))
        return channels
    except Exception:
        logger.exception(
            "DISCOVERY CHANNEL DATABASE LOAD FAILED — using frozen fallback "
            "Config.CHANNELS; dashboard channel edits are not in effect"
        )
        _record_status("fallback-config", len(Config.CHANNELS))
        return Config.CHANNELS
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                # Cleanup must never turn either a successful load or the
                # mandatory fallback into a failed discovery run.
                logger.exception("Failed to close discovery channel DB connection")
