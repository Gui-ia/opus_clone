import os

import pytest

# Force mock mode for all tests
os.environ["GPU_API_MOCK"] = "true"
os.environ["SCRAPER_AGENT_MOCK"] = "true"
os.environ["APP_ENV"] = "development"
os.environ["APP_BASE_URL"] = "http://localhost:8080"
os.environ.setdefault("DATABASE_URL", "postgres://opus:test@localhost:5632/opus_clone")
os.environ.setdefault("REDIS_URL", "redis://:test@localhost:6479")
os.environ.setdefault("REDIS_PASSWORD", "test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9600")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("WEBHOOK_SHARED_SECRET", "test-secret-for-hmac")


@pytest.fixture
def anyio_backend():
    return "asyncio"
