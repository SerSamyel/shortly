from datetime import UTC, datetime, timedelta

from shortly.aggregation import apply_click
from shortly.consumer import handle_batch
from shortly.events import ClickEvent
from tests.conftest import create_link


def click(link_id: int, *, ts: datetime | None = None, ref="direct", country="unknown", visitor="v1"):
    return ClickEvent(
        link_id=link_id,
        ts=(ts or datetime.now(UTC)).isoformat(),
        referrer_domain=ref,
        country=country,
        visitor_hash=visitor,
    )


async def apply_all(sessionmaker, events):
    async with sessionmaker() as session, session.begin():
        return [await apply_click(session, e) for e in events]


async def test_stats_for_a_new_link_are_zero_filled(client, auth):
    link = await create_link(client, auth)
    stats = (await client.get(f"/api/links/{link['id']}/stats?days=7", headers=auth)).json()
    assert stats["total_clicks"] == 0
    assert len(stats["daily"]) == 7
    assert all(d["clicks"] == 0 and d["unique_visitors"] == 0 for d in stats["daily"])
    assert stats["daily"][-1]["date"] == datetime.now(UTC).date().isoformat()
    assert stats["referrers"] == [] and stats["countries"] == []


async def test_clicks_are_aggregated_by_day_referrer_country_and_visitor(
    client, auth, sessionmaker
):
    link = await create_link(client, auth)
    yesterday = datetime.now(UTC) - timedelta(days=1)
    await apply_all(
        sessionmaker,
        [
            click(link["id"], ref="t.me", country="DE", visitor="a"),
            click(link["id"], ref="t.me", country="DE", visitor="a"),
            click(link["id"], ref="google.com", country="RU", visitor="b"),
            click(link["id"], ts=yesterday, ref="t.me", country="DE", visitor="a"),
        ],
    )
    stats = (await client.get(f"/api/links/{link['id']}/stats?days=7", headers=auth)).json()

    assert stats["total_clicks"] == 4
    today, prev = stats["daily"][-1], stats["daily"][-2]
    assert (today["clicks"], today["unique_visitors"]) == (3, 2)
    assert (prev["clicks"], prev["unique_visitors"]) == (1, 1)
    assert stats["referrers"] == [{"name": "t.me", "clicks": 3}, {"name": "google.com", "clicks": 1}]
    assert stats["countries"] == [{"name": "DE", "clicks": 3}, {"name": "RU", "clicks": 1}]

    listed = (await client.get("/api/links", headers=auth)).json()["items"][0]
    assert listed["total_clicks"] == 4


async def test_reprocessing_an_event_does_not_double_count(client, auth, sessionmaker):
    link = await create_link(client, auth)
    event = click(link["id"])
    assert await apply_all(sessionmaker, [event, event]) == [True, False]
    assert await apply_all(sessionmaker, [event]) == [False]
    stats = (await client.get(f"/api/links/{link['id']}/stats", headers=auth)).json()
    assert stats["total_clicks"] == 1


async def test_clicks_for_deleted_links_are_ignored(client, auth, sessionmaker):
    link = await create_link(client, auth)
    await client.delete(f"/api/links/{link['id']}", headers=auth)
    assert await apply_all(sessionmaker, [click(link["id"]), click(999_999)]) == [False, False]


async def test_deleting_a_link_removes_its_analytics(client, auth, sessionmaker):
    link = await create_link(client, auth, alias="soon-gone")
    await apply_all(sessionmaker, [click(link["id"])])
    await client.delete(f"/api/links/{link['id']}", headers=auth)
    from sqlalchemy import func, select

    from shortly.models import ClickDaily

    async with sessionmaker() as session:
        rows = await session.scalar(select(func.count()).select_from(ClickDaily))
    assert rows == 0


async def test_consumer_batch_skips_malformed_messages(client, auth, sessionmaker):
    link = await create_link(client, auth)
    good = click(link["id"]).to_bytes()
    applied = await handle_batch(sessionmaker, [b"not json", b'{"link_id": 1}', good])
    assert applied == 1


async def test_redirect_to_stats_end_to_end_in_process(client, auth, sessionmaker, publisher):
    link = await create_link(client, auth)
    for agent in ("Firefox", "Firefox", "Chrome"):
        await client.get(f"/{link['code']}", headers={"User-Agent": agent})
    await apply_all(sessionmaker, publisher.events)
    stats = (await client.get(f"/api/links/{link['id']}/stats", headers=auth)).json()
    assert stats["total_clicks"] == 3
    assert stats["daily"][-1]["unique_visitors"] == 2
    assert stats["referrers"] == [{"name": "direct", "clicks": 3}]
