import redis.asyncio as aioredis
from fastapi import APIRouter
from minio import Minio
from sqlalchemy import text

from opus_clone.config import get_settings
from opus_clone.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    settings = get_settings()
    checks = {}

    # Postgres
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_broker_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # MinIO
    try:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        client.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        **checks,
    }
