FROM python:3.11-slim

# Keep print() visible in container logs (see embedding Dockerfile for why).
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including yt-dlp
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt yt-dlp

# Copy application
COPY . .

# Expose port
EXPOSE 5020

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5020", "--workers", "2", "--threads", "4", "app:app"]
