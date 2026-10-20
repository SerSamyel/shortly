"""Integration tests run against real Postgres and Redis (start them with `make deps-up`).

The schema is created by running the real Alembic migrations, so the migrations are
tested too. Every test starts from empty tables and an empty Redis database.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from shortly.api.deps import Deps
from shortly.app import create_app
from shortly.cache import RedisStore
from shortly.config import Settings
from shortly.db import make_engine, make_sessionmaker
from shortly.events import MemoryPublisher
from shortly.geo import NoGeo

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASE_URL = "http://short.test"

DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://shortly:shortly@localhost:5432/shortly_test"
)
REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
KAFKA_BOOTSTRAP = os.environ.get("TEST_KAFKA_BOOTSTRAP")

TABLES = "processed_events, click_visitors, click_countries, click_referrers, click_daily, links, users"


async def _ensure_database(url: str) -> None:
    parts = urlsplit(url.replace("+asyncpg", ""))
    name = parts.path.lstrip("/")
    admin = await asyncpg.connect(
        host=parts.hostname,
        port=parts.port or 5432,
        user=parts.username,
        password=parts.password,
        database="postgres",
    )
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    try:
        asyncio.run(_ensure_database(DATABASE_URL))
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.exit(f"Postgres is not reachable at {DATABASE_URL}: {exc}. Run `make deps-up`.", 2)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
        check=True,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        redis_url=REDIS_URL,
        base_url=BASE_URL,
        jwt_secret="integration-secret-integration-secret",
    )


@pytest.fixture
async def sessionmaker(settings):
    engine = make_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))
    yield make_sessionmaker(engine)
    await engine.dispose()


@pytest.fixture
async def store(settings):
    redis_store = RedisStore(settings.redis_url)
    if not await redis_store.ping():
        pytest.exit(f"Redis is not reachable at {settings.redis_url}. Run `make deps-up`.", 2)
    await redis_store.redis.flushdb()
    yield redis_store
    await redis_store.close()


@pytest.fixture
def publisher() -> MemoryPublisher:
    return MemoryPublisher()


@pytest.fixture
def deps(settings, sessionmaker, store, publisher) -> Deps:
    return Deps(
        settings=settings, sessionmaker=sessionmaker, store=store, publisher=publisher, geo=NoGeo()
    )


@pytest.fixture
async def client(deps):
    app = create_app(deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        yield c
