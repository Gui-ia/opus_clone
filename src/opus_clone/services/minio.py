from minio import Minio

from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("minio_service")

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def ensure_buckets() -> None:
    settings = get_settings()
    client = get_minio_client()
    for bucket in [settings.minio_bucket_raw, settings.minio_bucket_clips, settings.minio_bucket_assets]:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("bucket_created", bucket=bucket)


def generate_presigned_put(bucket: str, key: str, expires: int = 3600) -> str:
    from datetime import timedelta

    client = get_minio_client()
    return client.presigned_put_object(bucket, key, expires=timedelta(seconds=expires))


def generate_presigned_get(bucket: str, key: str, expires: int = 3600) -> str:
    from datetime import timedelta

    client = get_minio_client()
    return client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires))


def upload_file(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    import io

    client = get_minio_client()
    client.put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)
    logger.info("file_uploaded", bucket=bucket, key=key, size=len(data))


def download_file(bucket: str, key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def file_exists(bucket: str, key: str) -> bool:
    client = get_minio_client()
    try:
        client.stat_object(bucket, key)
        return True
    except Exception:
        return False


def delete_file(bucket: str, key: str) -> None:
    client = get_minio_client()
    client.remove_object(bucket, key)
