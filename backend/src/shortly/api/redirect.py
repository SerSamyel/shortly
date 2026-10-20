"""The hot path: GET /{code} -> 302 to the target URL, and a click event on the side."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from shortly.api.deps import Deps, DepsDep
from shortly.cache import CacheError, CachedLink
from shortly.codes import normalize_code
from shortly.db import as_utc, utcnow
from shortly.events import ClickEvent
from shortly.models import Link
from shortly.privacy import client_ip, referrer_domain, visitor_hash

log = logging.getLogger(__name__)

router = APIRouter(tags=["redirect"])

_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:32rem;margin:15vh auto;padding:0 1rem;
color:#1f2937}}h1{{font-size:1.5rem}}a{{color:#4f46e5}}</style></head>
<body><h1>{title}</h1><p>{text}</p><p><a href="/">Shortly</a></p></body></html>"""


def _page(status: int, title: str, text: str) -> HTMLResponse:
    return HTMLResponse(
        _PAGE.format(title=title, text=text),
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


def not_found() -> HTMLResponse:
    return _page(404, "Link not found", "This short link does not exist or was turned off.")


def gone() -> HTMLResponse:
    return _page(410, "Link expired", "This short link has expired.")


async def _lookup(deps: Deps, code: str) -> CachedLink | None:
    try:
        cached = await deps.store.get_link(code)
        if cached is not None:
            return cached
        cache_ok = True
    except CacheError:
        log.warning("cache unavailable, reading link from the database")
        cache_ok = False

    async with deps.sessionmaker() as session:
        link = await session.scalar(
            select(Link).where(Link.code == code, Link.deleted_at.is_(None))
        )
    if link is None:
        return None
    expires_at = as_utc(link.expires_at)
    found = CachedLink(
        id=link.id,
        target_url=link.target_url,
        is_active=link.is_active,
        expires_at=expires_at.isoformat() if expires_at else None,
    )
    if cache_ok:
        try:
            await deps.store.set_link(code, found)
        except CacheError:
            pass
    return found


async def _click_event(deps: Deps, request: Request, link_id: int) -> ClickEvent:
    now = utcnow()
    ip = client_ip(request, deps.settings.trust_proxy_headers)
    salt = await deps.store.daily_salt(now.date().isoformat())
    return ClickEvent(
        link_id=link_id,
        ts=now.isoformat(),
        referrer_domain=referrer_domain(request.headers.get("referer"), deps.settings.base_host),
        country=deps.geo.country(ip),
        visitor_hash=visitor_hash(salt, ip, request.headers.get("user-agent", "")),
    )


@router.get("/{code}", include_in_schema=False)
async def redirect(code: str, request: Request, deps: DepsDep):
    code = normalize_code(code)
    if not code or len(code) > 32:
        return not_found()

    link = await _lookup(deps, code)
    if link is None or not link.is_active:
        return not_found()
    expires_at = link.expires()
    if expires_at is not None and expires_at <= utcnow():
        return gone()

    deps.publisher.publish(await _click_event(deps, request, link.id))
    # 302, not 301: browsers must come back every time so every click is counted.
    return RedirectResponse(link.target_url, status_code=302, headers={"Cache-Control": "no-store"})
