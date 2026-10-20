"""Full user flows through the API, Postgres, Redis and the click consumer."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from shortly.consumer import handle_batch
from shortly.models import Link
from tests_integration.conftest import KAFKA_BOOTSTRAP


async def signup(client, email="owner@example.com"):
    response = await client.post(
        "/api/auth/signup", json={"email": email, "password": "correct-horse"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def drain(publisher, sessionmaker) -> int:
    """Hand everything the API published to the consumer, as the broker would."""
    events = [e.to_bytes() for e in publisher.events]
    publisher.events.clear()
    return await handle_batch(sessionmaker, events)


async def test_signup_create_redirect_and_see_the_click(client, publisher, sessionmaker):
    auth = await signup(client)
    login = await client.post(
        "/api/auth/login", json={"email": "owner@example.com", "password": "correct-horse"}
    )
    assert login.status_code == 200

    created = await client.post(
        "/api/links",
        json={"target_url": "https://example.com/talk-slides", "alias": "my-talk"},
        headers=auth,
    )
    assert created.status_code == 201
    link = created.json()

    for agent in ("Firefox", "Firefox", "Safari"):
        response = await client.get(
            "/my-talk", headers={"User-Agent": agent, "Referer": "https://t.me/channel"}
        )
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com/talk-slides"

    assert await drain(publisher, sessionmaker) == 3
    stats = (await client.get(f"/api/links/{link['id']}/stats", headers=auth)).json()
    assert stats["total_clicks"] == 3
    assert stats["daily"][-1] == {
        "date": datetime.now(UTC).date().isoformat(),
        "clicks": 3,
        "unique_visitors": 2,
    }
    assert stats["referrers"] == [{"name": "t.me", "clicks": 3}]


async def test_data_survives_new_connections(client, settings, store, publisher):
    """The bug class an in-memory store hides: data must be in Postgres, not in the process."""
    from httpx import ASGITransport, AsyncClient

    from shortly.api.deps import Deps
    from shortly.app import create_app
    from shortly.db import make_engine, make_sessionmaker
    from shortly.geo import NoGeo

    auth = await signup(client)
    await client.post("/api/links", json={"target_url": "https://example.com"}, headers=auth)

    engine = make_engine(settings.database_url)
    fresh = Deps(
        settings=settings,
        sessionmaker=make_sessionmaker(engine),
        store=store,
        publisher=publisher,
        geo=NoGeo(),
    )
    transport = ASGITransport(app=create_app(deps=fresh))
    async with AsyncClient(transport=transport, base_url="http://short.test") as other:
        page = (await other.get("/api/links", headers=auth)).json()
    await engine.dispose()
    assert page["total"] == 1


async def test_redis_cache_is_filled_and_invalidated_on_disable(client, store):
    auth = await signup(client)
    link = (
        await client.post(
            "/api/links", json={"target_url": "https://example.com", "alias": "cached"}, headers=auth
        )
    ).json()
    assert (await client.get("/cached")).status_code == 302
    assert await store.get_link("cached") is not None

    await client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=auth)
    assert await store.get_link("cached") is None
    assert (await client.get("/cached")).status_code == 404


async def test_deleted_link_is_404_and_its_alias_stays_taken(client):
    auth = await signup(client)
    link = (
        await client.post(
            "/api/links", json={"target_url": "https://example.com", "alias": "bye"}, headers=auth
        )
    ).json()
    await client.get("/bye")
    assert (await client.delete(f"/api/links/{link['id']}", headers=auth)).status_code == 204
    assert (await client.get("/bye")).status_code == 404
    again = await client.post(
        "/api/links", json={"target_url": "https://example.org", "alias": "bye"}, headers=auth
    )
    assert again.status_code == 409


async def test_expired_link_is_410(client, sessionmaker):
    auth = await signup(client)
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    link = (
        await client.post(
            "/api/links",
            json={"target_url": "https://example.com", "alias": "soon", "expires_at": future},
            headers=auth,
        )
    ).json()
    async with sessionmaker() as session:
        await session.execute(
            update(Link)
            .where(Link.id == link["id"])
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()
    assert (await client.get("/soon")).status_code == 410


async def test_redirect_survives_a_redis_outage(client, store):
    auth = await signup(client)
    await client.post(
        "/api/links", json={"target_url": "https://example.com", "alias": "resilient"}, headers=auth
    )
    await store.redis.aclose()
    # Point the store at a port nothing listens on: every Redis call now fails.
    from redis.asyncio import Redis

    store.redis = Redis.from_url("redis://localhost:1/0", socket_connect_timeout=0.2)
    assert (await client.get("/resilient")).status_code == 302


async def test_rate_limit_is_shared_through_redis(client, settings):
    settings.links_per_minute = 2
    auth = await signup(client)
    codes = []
    for _ in range(3):
        response = await client.post(
            "/api/links", json={"target_url": "https://example.com"}, headers=auth
        )
        codes.append(response.status_code)
    assert codes == [201, 201, 429]


async def test_redelivered_events_are_counted_once(client, publisher, sessionmaker):
    auth = await signup(client)
    link = (
        await client.post("/api/links", json={"target_url": "https://example.com"}, headers=auth)
    ).json()
    await client.get(f"/{link['code']}")
    raw = [e.to_bytes() for e in publisher.events]
    assert await handle_batch(sessionmaker, raw) == 1
    assert await handle_batch(sessionmaker, raw) == 0
    stats = (await client.get(f"/api/links/{link['id']}/stats", headers=auth)).json()
    assert stats["total_clicks"] == 1


@pytest.mark.skipif(not KAFKA_BOOTSTRAP, reason="TEST_KAFKA_BOOTSTRAP not set")
async def test_click_goes_through_the_real_broker(client, deps, sessionmaker):
    import uuid

    from aiokafka import AIOKafkaConsumer

    from shortly.events import KafkaPublisher

    topic = f"clicks-test-{uuid.uuid4().hex[:8]}"
    kafka = KafkaPublisher(KAFKA_BOOTSTRAP, topic)
    await kafka.start()
    for _ in range(50):
        if kafka._producer is not None:
            break
        await asyncio.sleep(0.2)
    deps.publisher = kafka

    auth = await signup(client)
    link = (
        await client.post("/api/links", json={"target_url": "https://example.com"}, headers=auth)
    ).json()
    assert (await client.get(f"/{link['code']}")).status_code == 302
    await kafka.stop()

    consumer = AIOKafkaConsumer(
        topic, bootstrap_servers=KAFKA_BOOTSTRAP, auto_offset_reset="earliest", group_id=topic
    )
    await consumer.start()
    try:
        batches = await consumer.getmany(timeout_ms=10_000)
    finally:
        await consumer.stop()
    values = [m.value for messages in batches.values() for m in messages]
    assert await handle_batch(sessionmaker, values) == 1
