import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from shortly import models  # noqa: F401
from shortly.api.deps import Deps
from shortly.app import create_app
from shortly.cache import MemoryStore
from shortly.config import Settings
from shortly.db import Base
from shortly.events import MemoryPublisher
from shortly.geo import NoGeo

BASE_URL = "http://short.test"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite://",
        base_url=BASE_URL,
        jwt_secret="test-secret-test-secret-test-secret",
        links_per_minute=30,
    )


@pytest.fixture
async def sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
def store() -> MemoryStore:
    return MemoryStore()


@pytest.fixture
def publisher() -> MemoryPublisher:
    return MemoryPublisher()


@pytest.fixture
def deps(settings, sessionmaker, store, publisher) -> Deps:
    return Deps(
        settings=settings,
        sessionmaker=sessionmaker,
        store=store,
        publisher=publisher,
        geo=NoGeo(),
    )


@pytest.fixture
async def client(deps):
    app = create_app(deps=deps)
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as c:
        yield c


async def signup(client: AsyncClient, email: str = "owner@example.com") -> dict:
    response = await client.post(
        "/api/auth/signup", json={"email": email, "password": "correct-horse"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def auth(client) -> dict:
    return await signup(client)


async def create_link(client: AsyncClient, auth: dict, **body) -> dict:
    body.setdefault("target_url", "https://example.com/some/long/path?x=1")
    response = await client.post("/api/links", json=body, headers=auth)
    assert response.status_code == 201, response.text
    return response.json()
