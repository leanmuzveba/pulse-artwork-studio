"""Worker settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    environment: str = "local"
    debug: bool = True

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Object storage: read source artworks, write derived/exported ones.
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "pulse-minio"
    s3_secret_key: str = "pulse-minio-secret"
    s3_region: str = "us-east-1"
    s3_bucket_derived: str = "pulse-derived"
    s3_bucket_exports: str = "pulse-exports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
