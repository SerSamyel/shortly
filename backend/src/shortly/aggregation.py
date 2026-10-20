"""Apply click events to the daily aggregate tables.

`apply_click` is idempotent: an event whose id was already processed changes nothing.
It works on both Postgres and SQLite (tests) through dialect-specific upserts.
"""

from sqlalchemy import update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from shortly.events import ClickEvent
from shortly.models import (
    ClickCountry,
    ClickDaily,
    ClickReferrer,
    ClickVisitor,
    Link,
    ProcessedEvent,
)


def _insert(session: AsyncSession):
    name = session.get_bind().dialect.name
    return postgresql.insert if name == "postgresql" else sqlite.insert


async def _increment(session: AsyncSession, model, values: dict) -> None:
    insert = _insert(session)
    stmt = insert(model).values(**values, clicks=1)
    keys = [col.name for col in model.__table__.primary_key.columns]
    stmt = stmt.on_conflict_do_update(
        index_elements=keys, set_={"clicks": model.__table__.c.clicks + 1}
    )
    await session.execute(stmt)


async def apply_click(session: AsyncSession, event: ClickEvent) -> bool:
    """Add one click to the aggregates. Returns False if the event was already applied
    or the link no longer exists. The caller commits."""
    insert = _insert(session)

    link = await session.get(Link, event.link_id)
    if link is None or link.deleted_at is not None:
        return False

    claimed = await session.execute(
        insert(ProcessedEvent)
        .values(event_id=event.event_id)
        .on_conflict_do_nothing(index_elements=["event_id"])
    )
    if claimed.rowcount == 0:
        return False

    day = event.timestamp.date()
    await _increment(session, ClickDaily, {"link_id": event.link_id, "day": day})
    await _increment(
        session,
        ClickReferrer,
        {"link_id": event.link_id, "day": day, "domain": event.referrer_domain},
    )
    await _increment(
        session, ClickCountry, {"link_id": event.link_id, "day": day, "country": event.country}
    )
    await session.execute(
        insert(ClickVisitor)
        .values(link_id=event.link_id, day=day, visitor_hash=event.visitor_hash)
        .on_conflict_do_nothing()
    )
    await session.execute(
        update(Link).where(Link.id == event.link_id).values(total_clicks=Link.total_clicks + 1)
    )
    return True
