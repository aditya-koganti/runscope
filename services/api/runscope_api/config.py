from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RUNSCOPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://runscope:runscope-local@localhost:5432/runscope"
    redis_url: str = "redis://localhost:6379/0"
    broker_bootstrap_servers: str = "localhost:19092"
    broker_topic: str = "runscope.events.v1"
    outbox_dispatcher_enabled: bool = True
    outbox_poll_seconds: float = 0.5
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "runscope-local"
    s3_secret_key: str = "change-me-local-only"
    s3_bucket: str = "runscope-artifacts"
    artifact_backend: str = "local"
    local_artifact_dir: str = ".artifacts"
    jwt_secret: str = "change-me-local-development-only"
    jwt_issuer: str = "runscope"
    access_token_minutes: int = 30
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
