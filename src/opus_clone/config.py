from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "production"
    app_log_level: str = "INFO"
    app_base_url: str = "http://localhost:8080"

    # Database
    database_url: str
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20

    # Redis
    redis_url: str
    redis_password: str = ""
    redis_db_broker: int = 0
    redis_db_cache: int = 1
    redis_db_locks: int = 2

    # MinIO
    minio_endpoint: str = "opus-minio:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket_raw: str = "raw"
    minio_bucket_clips: str = "clips"
    minio_bucket_assets: str = "assets"
    minio_secure: bool = False

    # GPU API
    gpu_api_url: str = "http://69.19.137.207"
    gpu_api_key: str = ""
    gpu_api_timeout_s: int = 60
    gpu_api_max_retries: int = 5
    gpu_api_mock: bool = False

    # Scraper Agent
    scraper_agent_url: str = ""
    scraper_agent_token: str = ""
    scraper_agent_timeout_s: int = 300
    scraper_agent_mock: bool = False

    # YouTube
    youtube_api_key: str = ""
    youtube_pubsub_callback_url: str = ""
    youtube_pubsub_hub: str = "https://pubsubhubbub.appspot.com/subscribe"

    # Webhook Auth
    webhook_shared_secret: str = ""

    # Workers
    dramatiq_concurrency: int = 4
    dramatiq_threads: int = 2

    # ngrok
    ngrok_authtoken: str = ""
    ngrok_domain: str = ""

    @property
    def database_url_async(self) -> str:
        return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)

    @property
    def redis_broker_url(self) -> str:
        return f"{self.redis_url}/{self.redis_db_broker}"

    @property
    def redis_cache_url(self) -> str:
        return f"{self.redis_url}/{self.redis_db_cache}"

    @property
    def redis_locks_url(self) -> str:
        return f"{self.redis_url}/{self.redis_db_locks}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
