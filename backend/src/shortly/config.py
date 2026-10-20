from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    version: str = "dev"

    database_url: str = "sqlite+aiosqlite:///./shortly.db"
    redis_url: str | None = None
    kafka_bootstrap: str | None = None
    clicks_topic: str = "clicks"

    base_url: str = "http://localhost:8000"
    jwt_secret: str = "change-me-in-production-please-32b"
    jwt_ttl_hours: int = 24

    links_per_minute: int = 30
    cache_ttl_seconds: int = 3600

    geoip_db_path: str | None = None
    trust_proxy_headers: bool = False
    static_dir: str | None = None

    @field_validator("database_url")
    @classmethod
    def use_async_driver(cls, value: str) -> str:
        # Accept plain URLs from the environment and switch them to async drivers.
        if value.startswith("postgres://"):
            value = "postgresql://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
        if value.startswith("sqlite:///"):
            return "sqlite+aiosqlite:///" + value.removeprefix("sqlite:///")
        return value

    @field_validator("base_url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @property
    def base_host(self) -> str:
        return (urlsplit(self.base_url).hostname or "").lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()
