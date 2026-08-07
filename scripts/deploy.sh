#!/bin/bash
# KnowledgeEnroll Deployment Script
# Run on Banner (10.0.0.33)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "KnowledgeEnroll Deployment"
echo "=========================================="
echo "Project: $PROJECT_DIR"
echo ""

# Check we're on Banner
if [[ "$(hostname)" != "banner" ]]; then
    echo "Warning: This script is designed for Banner (10.0.0.33)"
    read -p "Continue anyway? [y/N] " confirm
    [[ "$confirm" != [yY] ]] && exit 1
fi

cd "$PROJECT_DIR"

# Check for .env
if [[ ! -f .env ]]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env with your credentials before continuing!"
    echo "  - POSTGRES_PASSWORD"
    echo "  - SURREAL_PASS"
    echo "  - LITELLM_API_KEY"
    echo ""
    read -p "Press Enter after editing .env..."
fi

# Build and start
echo ""
echo "[1/4] Building containers..."
docker compose build

echo ""
echo "[2/4] Starting services..."
docker compose up -d

echo ""
echo "[3/4] Waiting for services to be healthy..."
sleep 10

# Health checks
echo ""
echo "[4/4] Running health checks..."
ADMIN_HEALTH=$(curl -s http://localhost:5020/health | jq -r '.status' 2>/dev/null || echo "unreachable")
EMBEDDING_HEALTH=$(curl -s http://localhost:5030/health | jq -r '.status' 2>/dev/null || echo "unreachable")

echo "  Admin API:     $ADMIN_HEALTH"
echo "  Embedding:     $EMBEDDING_HEALTH"

echo ""
echo "=========================================="
echo "Deployment Complete"
echo "=========================================="
echo ""
echo "Services:"
echo "  Admin API:     http://10.0.0.33:5020"
echo "  Embedding:     http://10.0.0.33:5030"
echo "  PostgreSQL:    10.0.0.33:5010"
echo "  SurrealDB:     http://10.0.0.33:5040"
echo ""
echo "Next steps:"
echo "  1. Import channels: docker compose exec admin-api python scripts/import_channels.py"
echo "  2. Configure Traefik routing on Helicarrier"
echo "  3. Notify Infrastructure to deploy n8n workflows (HO-3)"
echo ""
