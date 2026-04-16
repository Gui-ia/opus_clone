#!/usr/bin/env bash
set -euo pipefail

# Opus Clone — Bootstrap script for first deploy on VPS
# Run: bash scripts/bootstrap.sh

echo "=== Opus Clone Bootstrap ==="

# 1. Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "[1/6] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.cargo/env" 2>/dev/null || source "$HOME/.local/bin/env" 2>/dev/null || true
else
    echo "[1/6] uv already installed: $(uv --version)"
fi

# 2. Generate .env from .env.example if not exists
if [ ! -f .env ]; then
    echo "[2/6] Generating .env with random secrets..."
    cp .env.example .env

    PG_PASS=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    REDIS_PASS=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    MINIO_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")
    MINIO_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(24))")
    WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    sed -i "s|POSTGRES_PASSWORD=CHANGE_ME|POSTGRES_PASSWORD=${PG_PASS}|g" .env
    sed -i "s|DATABASE_URL=postgres://opus:CHANGE_ME@|DATABASE_URL=postgres://opus:${PG_PASS}@|g" .env
    sed -i "s|REDIS_PASSWORD=CHANGE_ME|REDIS_PASSWORD=${REDIS_PASS}|g" .env
    sed -i "s|REDIS_URL=redis://:CHANGE_ME@|REDIS_URL=redis://:${REDIS_PASS}@|g" .env
    sed -i "s|MINIO_ACCESS_KEY=CHANGE_ME|MINIO_ACCESS_KEY=${MINIO_KEY}|g" .env
    sed -i "s|MINIO_SECRET_KEY=CHANGE_ME|MINIO_SECRET_KEY=${MINIO_SECRET}|g" .env
    sed -i "s|WEBHOOK_SHARED_SECRET=CHANGE_ME|WEBHOOK_SHARED_SECRET=${WEBHOOK_SECRET}|g" .env

    echo "    -> .env created. EDIT IT to fill GPU_API_KEY, SCRAPER_AGENT_TOKEN, YOUTUBE_API_KEY, NGROK_AUTHTOKEN"
else
    echo "[2/6] .env already exists, skipping"
fi

# 3. Start infrastructure containers
echo "[3/6] Starting infrastructure containers..."
docker compose up -d opus-postgres opus-redis opus-minio

# 4. Wait for postgres to be healthy
echo "[4/6] Waiting for Postgres to be ready..."
for i in $(seq 1 30); do
    if docker exec opus-postgres pg_isready -U opus -d opus_clone &>/dev/null; then
        echo "    -> Postgres is ready"
        break
    fi
    sleep 2
done

# 5. Apply migrations
echo "[5/6] Applying migrations..."
docker exec -i opus-postgres psql -U opus -d opus_clone < migrations/001_initial.sql
echo "    -> Schema applied"

# 6. Create MinIO buckets
echo "[6/6] Creating MinIO buckets..."
sleep 3  # wait for MinIO to fully start

# Use mc inside the minio container
docker exec opus-minio mc alias set local http://localhost:9000 "${MINIO_ACCESS_KEY:-$(grep MINIO_ACCESS_KEY .env | cut -d= -f2)}" "${MINIO_SECRET_KEY:-$(grep MINIO_SECRET_KEY .env | cut -d= -f2)}" 2>/dev/null || true
docker exec opus-minio mc mb local/raw local/clips local/assets 2>/dev/null || echo "    -> Buckets already exist"

echo ""
echo "=== Bootstrap complete ==="
echo "Next steps:"
echo "  1. Edit .env to fill remaining secrets (GPU_API_KEY, NGROK_AUTHTOKEN, etc.)"
echo "  2. Run: docker compose up -d --build"
echo "  3. Test: curl http://localhost:8080/health"
