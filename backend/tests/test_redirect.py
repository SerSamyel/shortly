from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from shortly.models import Link
from tests.conftest import create_link


async def test_redirect_is_302_to_target_and_publishes_a_click(client, auth, publisher):
    link = await create_link(client, auth, target_url="https://example.com/landing")
    response = await client.get(
        f"/{link['code']}",
        headers={"Referer": "https://www.google.com/search?q=x", "User-Agent": "pytest"},
    )
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/landing"
    assert response.headers["cache-control"] == "no-store"

    [event] = publisher.events
    assert event.link_id == link["id"]
    assert event.referrer_domain == "google.com"
    assert event.country == "unknown"
    assert len(event.visitor_hash) == 64


async def test_click_event_never_contains_the_ip_or_target_url(client, auth, publisher):
    link = await create_link(client, auth, target_url="https://example.com/private-path")
    await client.get(f"/{link['code']}", headers={"X-Forwarded-For": "203.0.113.9"})
    raw = publisher.events[0].to_bytes().decode()
    assert "203.0.113.9" not in raw
    assert "127.0.0.1" not in raw
    assert "private-path" not in raw


async def test_codes_are_case_insensitive(client, auth):
    await create_link(client, auth, alias="my-talk")
    assert (await client.get("/MY-Talk")).status_code == 302


async def test_unknown_code_is_404_html(client, publisher):
    response = await client.get("/doesnotexist")
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert publisher.events == []


async def test_disabled_link_is_404_and_counts_nothing(client, auth, publisher):
    link = await create_link(client, auth)
    await client.get(f"/{link['code']}")  # warms the cache
    await client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=auth)
    assert (await client.get(f"/{link['code']}")).status_code == 404
    assert len(publisher.events) == 1


async def test_re_enabled_link_redirects_again(client, auth):
    link = await create_link(client, auth)
    await client.patch(f"/api/links/{link['id']}", json={"is_active": False}, headers=auth)
    await client.get(f"/{link['code']}")
    await client.patch(f"/api/links/{link['id']}", json={"is_active": True}, headers=auth)
    assert (await client.get(f"/{link['code']}")).status_code == 302


async def test_deleted_link_is_404_even_when_it_was_cached(client, auth):
    link = await create_link(client, auth)
    await client.get(f"/{link['code']}")
    await client.delete(f"/api/links/{link['id']}", headers=auth)
    assert (await client.get(f"/{link['code']}")).status_code == 404


async def test_expired_link_is_410(client, auth, sessionmaker, publisher):
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    link = await create_link(client, auth, expires_at=future)
    async with sessionmaker() as session:
        await session.execute(
            update(Link)
            .where(Link.id == link["id"])
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()

    response = await client.get(f"/{link['code']}")
    assert response.status_code == 410
    assert publisher.events == []
    status = (await client.get(f"/api/links/{link['id']}", headers=auth)).json()["status"]
    assert status == "expired"


async def test_cache_is_used_after_the_first_lookup(client, auth, store):
    link = await create_link(client, auth)
    await client.get(f"/{link['code']}")
    assert link["code"] in store.links


async def test_redirect_falls_back_to_the_database_when_cache_is_down(client, auth, store):
    link = await create_link(client, auth)
    store.fail = True
    assert (await client.get(f"/{link['code']}")).status_code == 302


async def test_redirect_works_when_the_broker_is_down(client, auth, publisher):
    link = await create_link(client, auth)
    publisher.fail = True
    assert (await client.get(f"/{link['code']}")).status_code == 302


async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
