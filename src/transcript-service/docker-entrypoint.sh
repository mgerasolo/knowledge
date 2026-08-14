#!/bin/sh
# Optionally refresh yt-dlp before the service starts, then hand off to gunicorn.
#
# Why this exists: yt-dlp is in a permanent cat-and-mouse with YouTube, so the
# version baked into the image goes stale on its own with no code change on our
# side. Without this, the only way to update it is an image rebuild — and a
# rebuild interrupts the backfill queue, which can be a multi-hour job. This
# makes "get current" a container restart instead.
#
# Off by default, on purpose. An unattended upgrade of the component that talks
# to YouTube can break ingestion as easily as it can fix it, so it is a lever
# someone pulls when GET /api/tooling reports yt-dlp has gone stale — not a
# default that changes the downloader underneath a running backfill.
set -e

_auto_update=$(printf '%s' "${YTDLP_AUTO_UPDATE:-false}" | tr '[:upper:]' '[:lower:]')

if [ "$_auto_update" = "true" ]; then
    echo "[entrypoint] YTDLP_AUTO_UPDATE=true — upgrading yt-dlp before start"
    if pip install --no-cache-dir --upgrade yt-dlp; then
        echo "[entrypoint] yt-dlp now at $(yt-dlp --version 2>/dev/null || echo 'unknown')"
    else
        # Never fail the boot over this. A container that will not start is a
        # worse outcome than one running a slightly old downloader, and the
        # staleness is reported by GET /api/tooling either way.
        echo "[entrypoint] WARNING: yt-dlp upgrade failed — starting on the version baked into the image" >&2
    fi
else
    echo "[entrypoint] yt-dlp auto-update off — set YTDLP_AUTO_UPDATE=true and restart to upgrade in place"
fi

exec "$@"
