FROM python:3.11-slim

# Without this, Python buffers stdout when it isn't a TTY, so every print() in
# the service — including the SurrealDB error messages — is swallowed and the
# container logs stay empty while requests fail. Diagnosing the 2026-08-07
# indexing failure was blocked on exactly this.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5030

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5030", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
