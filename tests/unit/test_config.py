import os

import pytest


def test_settings_load(monkeypatch):
    """Config loads from environment variables."""
    monkeypatch.delenv("APP_ENV", raising=False)
    from opus_clone.config import Settings

    settings = Settings(
        database_url="postgres://user:pass@localhost/db",
        redis_url="redis://localhost:6379",
        _env_file=None,
    )
    assert settings.database_url == "postgres://user:pass@localhost/db"
    assert settings.app_env == "production"
    assert settings.db_pool_size == 10


def test_database_url_async():
    from opus_clone.config import Settings

    settings = Settings(
        database_url="postgres://user:pass@localhost/db",
        redis_url="redis://localhost:6379",
    )
    assert settings.database_url_async == "postgresql+asyncpg://user:pass@localhost/db"


def test_redis_urls():
    from opus_clone.config import Settings

    settings = Settings(
        database_url="postgres://user:pass@localhost/db",
        redis_url="redis://:mypass@localhost:6379",
    )
    assert settings.redis_broker_url == "redis://:mypass@localhost:6379/0"
    assert settings.redis_cache_url == "redis://:mypass@localhost:6379/1"
    assert settings.redis_locks_url == "redis://:mypass@localhost:6379/2"


def test_mock_mode_defaults(monkeypatch):
    monkeypatch.delenv("GPU_API_MOCK", raising=False)
    monkeypatch.delenv("SCRAPER_AGENT_MOCK", raising=False)
    from opus_clone.config import Settings

    settings = Settings(
        database_url="postgres://user:pass@localhost/db",
        redis_url="redis://localhost:6379",
        _env_file=None,
    )
    assert settings.gpu_api_mock is False
    assert settings.scraper_agent_mock is False
