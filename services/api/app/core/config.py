"""Application settings, loaded from environment / .env (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- General ----
    app_name: str = "Pulse Artwork Studio AI"
    environment: str = "local"  # local | staging | production
    debug: bool = True

    # ---- API ----
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:8080"

    # ---- Auth ----
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # ---- Data stores ----
    database_url: str = "postgresql+asyncpg://pulse:pulse@localhost:5432/pulse"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ---- Object storage (S3-compatible) ----
    s3_endpoint_url: str = "http://localhost:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "pulse-minio"
    s3_secret_key: str = "pulse-minio-secret"
    s3_region: str = "us-east-1"
    s3_bucket_originals: str = "pulse-originals"
    s3_bucket_derived: str = "pulse-derived"
    s3_bucket_exports: str = "pulse-exports"
    s3_signed_url_ttl_seconds: int = 900

    # ---- Uploads ----
    max_upload_mb: int = 100
    allowed_upload_mime: str = "image/png,image/jpeg,image/webp"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_upload_mime_set(self) -> set[str]:
        return {m.strip() for m in self.allowed_upload_mime.split(",") if m.strip()}

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so settings are parsed once per process."""
    return Settings()
