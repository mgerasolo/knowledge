# Professor spike API — built with context = spike/professor/ (see docker-compose.yml)
FROM python:3.11-slim

WORKDIR /app

COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt gunicorn

COPY api /app/api
COPY personalities /app/personalities

ENV PROFESSOR_CORPUS_PATH=/app/personalities/myron-golden.json \
    PROFESSOR_PORT=5050 \
    PYTHONUNBUFFERED=1

EXPOSE 5050

# /health returns 503 until SurrealDB is reachable AND the corpus is loaded.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:5050/health', timeout=8).status==200 else 1)"

# ONE worker so retrieval's _SCAN_LOCK is globally effective (concurrent
# unindexed cosine scans OOM-kill SurrealDB); threads keep /health responsive
# while a 40-50s /api/ask is in flight; the long timeout survives scan latency.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "300", \
     "--bind", "0.0.0.0:5050", "api.app:app"]
