# Transcript Ingestion Pipeline - Deploy Guide

## Prerequisites

- SSH access to Banner (`ssh banner` must work)
- Docker context set to `banner` (`docker context use banner`)

## Step 1: Build and Start Service

```bash
cd ~/Dev/KnowledgeStack
docker compose build transcript-service
docker compose up -d transcript-service
```

## Step 2: Seed State

Seeds the 147 already-fetched video IDs so they aren't re-fetched.

```bash
./scripts/seed-transcript-state.sh
```

## Step 3: Verify

```bash
# Health check
curl http://10.0.0.33:5025/health

# Status (should show ~920 pending)
curl http://10.0.0.33:5025/api/status

# Check logs for backfill activity
docker logs -f knowledge-transcript-service --tail 20
```

The backfill worker starts automatically and will begin draining the queue
at random 30-600 second intervals. It pauses during 6:00-6:59 AM.

## Step 4: Import n8n Daily Check Workflow

1. Open https://n8n.nextlevelguild.com
2. Import `docs/n8n-workflows/ks-daily-check.json`
3. Activate the workflow

This checks all 5 channels at 6 AM daily for new videos and fetches
their transcripts with 3-minute gaps between fetches.

## Architecture

```
transcript-service (Banner:5025)
  ├── API endpoints (discovery, fetch, status)
  └── Background backfill worker thread
        ├── Fetches 1 video at a time
        ├── Random 30-600s delay between fetches
        ├── Pauses 6:00-6:59 AM (discovery window)
        └── Stops when queue empty

n8n (daily schedule)
  └── "KS - Daily New Video Check" at 6 AM
        ├── POST /api/discover (checks channels)
        └── Fetches new video transcripts
```

## Backfill Timeline

- ~920 videos remaining
- Average delay: ~315 seconds (5.25 min)
- ~274 videos/day at 24h continuous
- **Estimated completion: ~3-4 days**

## Monitoring

```bash
# Live backfill progress
docker logs -f knowledge-transcript-service 2>&1 | grep backfill

# Quick status
curl -s http://10.0.0.33:5025/api/status | python3 -m json.tool

# Per-channel breakdown
curl -s http://10.0.0.33:5025/api/channels | python3 -m json.tool
```
