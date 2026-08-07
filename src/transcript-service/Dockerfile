FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /data/transcripts /data/state

# Ensure print() shows in docker logs
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5025

# Single worker to ensure one backfill thread. Threads handle concurrent API requests.
CMD ["gunicorn", "--bind", "0.0.0.0:5025", "--workers", "1", "--threads", "4", "--timeout", "300", "app:app"]
