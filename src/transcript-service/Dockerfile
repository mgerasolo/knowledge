# yt-dlp needs a JavaScript runtime to solve the player challenge YouTube uses
# to gate video formats. Without one it falls back to a client that answers
# "This video is not available", which is why fetcher.py carries two override
# flags forcing a path that still works. Deno is the runtime yt-dlp documents
# and enables by default, so installing it lets the tool work as designed
# instead of us routing around the cause (issue #22).
#
# Taken from Deno's own published binary image rather than piping an installer
# script into a shell, which is forbidden. The tag floats deliberately: pinning
# means never getting security updates, and the standing rule here is no version
# pinning without a documented reason and an unpin trigger.
FROM denoland/deno:bin AS deno

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The JavaScript runtime. yt-dlp discovers it on PATH by itself — no config.
COPY --from=deno /deno /usr/local/bin/deno

# Copy application
COPY . .

# Committed shell scripts do not reliably carry the execute bit.
RUN chmod +x /app/docker-entrypoint.sh

# Create data directories
RUN mkdir -p /data/transcripts /data/state

# Ensure print() shows in docker logs
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5025

# Only refreshes yt-dlp when YTDLP_AUTO_UPDATE=true, then execs CMD unchanged.
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Single worker to ensure one backfill thread. Threads handle concurrent API requests.
CMD ["gunicorn", "--bind", "0.0.0.0:5025", "--workers", "1", "--threads", "4", "--timeout", "300", "app:app"]
