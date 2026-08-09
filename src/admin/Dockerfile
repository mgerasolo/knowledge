FROM python:3.11-slim

# Keep print() visible in container logs (see embedding Dockerfile for why).
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including yt-dlp
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt yt-dlp

# Vendor the charting library at BUILD time rather than loading it from a CDN in
# the browser. Two rules collide otherwise: Subresource Integrity requires an
# exact pinned version + hash, while this fleet forbids version pinning because
# pinned things stop receiving security updates. Fetching a floating major here
# satisfies both — the page loads it same-origin (nothing to tamper with in
# transit, no third party in the request path) and every image rebuild picks up
# the current 5.x release.
RUN set -eux; \
    mkdir -p /app/static/vendor; \
    curl -fsSL --retry 3 --retry-delay 2 \
      https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js \
      -o /app/static/vendor/echarts.min.js; \
    test -s /app/static/vendor/echarts.min.js

# Copy application
COPY . .

# Expose port
EXPOSE 5020

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5020", "--workers", "2", "--threads", "4", "app:app"]
