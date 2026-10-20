import logging
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from shortly.api.deps import Deps, DepsDep, SessionDep, UserDep
from shortly.cache import CacheError
from shortly.codes import RESERVED_WORDS, generate_code, target_url_error
from shortly.db import as_utc, utcnow
from shortly.errors import FieldError
from shortly.models import ClickCountry, ClickDaily, ClickReferrer, ClickVisitor, Link
from shortly.schemas import (
    DailyClicks,
    LinkCreate,
    LinkOut,
    LinkPage,
    LinkStats,
    LinkUpdate,
    NamedCount,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/links", tags=["links"])

ANALYTICS_TABLES = (ClickDaily, ClickReferrer, ClickCountry, ClickVisitor)


def link_status(link: Link) -> str:
    if not link.is_active:
        return "disabled"
    expires_at = as_utc(link.expires_at)
    if expires_at is not None and expires_at <= utcnow():
        return "expired"
    return "active"


def to_out(link: Link, deps: Deps) -> LinkOut:
    return LinkOut(
        id=link.id,
        code=link.code,
        short_url=f"{deps.settings.base_url}/{link.code}",
        target_url=link.target_url,
        status=link_status(link),
        is_active=link.is_active,
        expires_at=as_utc(link.expires_at),
        created_at=as_utc(link.created_at),
        total_clicks=link.total_clicks or 0,
    )


async def _owned_link(session, user_id: int, link_id: int) -> Link:
    link = await session.scalar(
        select(Link).where(
            Link.id == link_id, Link.owner_id == user_id, Link.deleted_at.is_(None)
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


async def _forget_cached(deps: Deps, code: str) -> None:
    try:
        await deps.store.delete_link(code)
    except CacheError:
        # The entry expires on its own; until then the redirect re-checks status from the
        # cached copy, which is why disable and delete must try hard to invalidate.
        log.error("cache invalidation failed", extra={"cache_key": "link"})


@router.post("", status_code=201, response_model=LinkOut)
async def create_link(body: LinkCreate, user: UserDep, session: SessionDep, deps: DepsDep):
    error = target_url_error(body.target_url, deps.settings.base_host)
    if error:
        raise FieldError("target_url", error)
    expires_at = as_utc(body.expires_at)
    if expires_at is not None and expires_at <= utcnow():
        raise FieldError("expires_at", "Expiration must be in the future")

    try:
        limited = await deps.store.hit_rate_limit(
            f"create:{user.id}", deps.settings.links_per_minute, 60
        )
    except CacheError:
        limited = False  # fail open: the rate limit protects us, not the user's data
    if limited:
        raise HTTPException(status_code=429, detail="Too many links created, try again in a minute")

    if body.alias:
        link = Link(
            code=body.alias, owner_id=user.id, target_url=body.target_url, expires_at=expires_at
        )
        session.add(link)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=409, detail="This alias is already taken") from None
    else:
        for _ in range(5):
            code = generate_code()
            if code in RESERVED_WORDS:
                continue
            link = Link(
                code=code, owner_id=user.id, target_url=body.target_url, expires_at=expires_at
            )
            session.add(link)
            try:
                await session.commit()
                break
            except IntegrityError:
                await session.rollback()
        else:
            raise HTTPException(status_code=503, detail="Could not generate a code, try again")

    await session.refresh(link)
    log.info("link created", extra={"link_id": link.id, "custom_alias": bool(body.alias)})
    return to_out(link, deps)


@router.get("", response_model=LinkPage)
async def list_links(
    user: UserDep,
    session: SessionDep,
    deps: DepsDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    visible = (Link.owner_id == user.id, Link.deleted_at.is_(None))
    total = await session.scalar(select(func.count()).select_from(Link).where(*visible))
    rows = await session.scalars(
        select(Link)
        .where(*visible)
        .order_by(Link.created_at.desc(), Link.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return LinkPage(
        items=[to_out(link, deps) for link in rows],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{link_id}", response_model=LinkOut)
async def get_link(link_id: int, user: UserDep, session: SessionDep, deps: DepsDep):
    return to_out(await _owned_link(session, user.id, link_id), deps)


@router.patch("/{link_id}", response_model=LinkOut)
async def update_link(
    link_id: int, body: LinkUpdate, user: UserDep, session: SessionDep, deps: DepsDep
):
    link = await _owned_link(session, user.id, link_id)
    link.is_active = body.is_active
    await session.commit()
    await _forget_cached(deps, link.code)
    log.info("link updated", extra={"link_id": link.id, "is_active": body.is_active})
    return to_out(link, deps)


@router.delete("/{link_id}", status_code=204)
async def delete_link(link_id: int, user: UserDep, session: SessionDep, deps: DepsDep):
    link = await _owned_link(session, user.id, link_id)
    link.deleted_at = utcnow()
    link.is_active = False
    link.total_clicks = 0
    for table in ANALYTICS_TABLES:
        await session.execute(table.__table__.delete().where(table.link_id == link.id))
    await session.commit()
    await _forget_cached(deps, link.code)
    log.info("link deleted", extra={"link_id": link.id})
    return Response(status_code=204)


@router.get("/{link_id}/stats", response_model=LinkStats)
async def link_stats(
    link_id: int,
    user: UserDep,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
):
    link = await _owned_link(session, user.id, link_id)
    today = utcnow().date()
    start = today - timedelta(days=days - 1)

    clicks_by_day = dict(
        (
            await session.execute(
                select(ClickDaily.day, ClickDaily.clicks).where(
                    ClickDaily.link_id == link.id, ClickDaily.day >= start
                )
            )
        ).all()
    )
    uniques_by_day = dict(
        (
            await session.execute(
                select(ClickVisitor.day, func.count())
                .where(ClickVisitor.link_id == link.id, ClickVisitor.day >= start)
                .group_by(ClickVisitor.day)
            )
        ).all()
    )
    daily = [
        DailyClicks(
            date=day,
            clicks=clicks_by_day.get(day, 0),
            unique_visitors=uniques_by_day.get(day, 0),
        )
        for day in (start + timedelta(days=i) for i in range(days))
    ]

    async def top(model, column) -> list[NamedCount]:
        total = func.sum(model.clicks).label("total")
        rows = await session.execute(
            select(column, total)
            .where(model.link_id == link.id, model.day >= start)
            .group_by(column)
            .order_by(total.desc(), column)
            .limit(10)
        )
        return [NamedCount(name=name, clicks=int(count)) for name, count in rows.all()]

    return LinkStats(
        link_id=link.id,
        total_clicks=link.total_clicks or 0,
        daily=daily,
        referrers=await top(ClickReferrer, ClickReferrer.domain),
        countries=await top(ClickCountry, ClickCountry.country),
    )
