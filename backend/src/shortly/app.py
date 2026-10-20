from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from shortly.api import auth, health, links, redirect
from shortly.api.deps import Deps
from shortly.cache import MemoryStore, RedisStore
from shortly.config import Settings, get_settings
from shortly.db import make_engine, make_sessionmaker
from shortly.errors import install_error_handlers
from shortly.events import KafkaPublisher, MemoryPublisher
from shortly.geo import load_geo
from shortly.logs import setup_logging

# Client-side routes of the React app. Everything else at the root is a short code.
SPA_ROUTES = ("/", "/login", "/signup", "/app", "/app/{rest:path}")


def build_deps(settings: Settings) -> Deps:
    engine = make_engine(settings.database_url)
    store = (
        RedisStore(settings.redis_url, settings.cache_ttl_seconds)
        if settings.redis_url
        else MemoryStore(settings.cache_ttl_seconds)
    )
    publisher = (
        KafkaPublisher(settings.kafka_bootstrap, settings.clicks_topic)
        if settings.kafka_bootstrap
        else MemoryPublisher()
    )
    return Deps(
        settings=settings,
        sessionmaker=make_sessionmaker(engine),
        store=store,
        publisher=publisher,
        geo=load_geo(settings.geoip_db_path),
    )


def _mount_frontend(app: FastAPI, static_dir: str) -> None:
    root = Path(static_dir)
    index = root / "index.html"
    if not index.is_file():
        return
    if (root / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    async def spa() -> FileResponse:
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    for path in SPA_ROUTES:
        app.add_api_route(path, spa, methods=["GET"], include_in_schema=False)
    if (root / "favicon.svg").is_file():

        async def favicon() -> FileResponse:
            return FileResponse(root / "favicon.svg")

        app.add_api_route("/favicon.svg", favicon, methods=["GET"], include_in_schema=False)


def create_app(settings: Settings | None = None, deps: Deps | None = None) -> FastAPI:
    """Build the app. Tests pass ready-made `deps`; production builds them at startup."""
    settings = settings or (deps.settings if deps else get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if deps is not None:
            app.state.deps = deps
            yield
            return
        setup_logging(settings)
        built = build_deps(settings)
        app.state.deps = built
        await built.publisher.start()
        try:
            yield
        finally:
            await built.publisher.stop()
            await built.store.close()
            built.geo.close()

    app = FastAPI(title="Shortly API", version="0.1.0", lifespan=lifespan)
    if deps is not None:
        app.state.deps = deps  # httpx's ASGITransport does not run the lifespan
    install_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(links.router)
    app.include_router(health.router)
    if settings.static_dir:
        _mount_frontend(app, settings.static_dir)
    # Must be last: it matches any single path segment.
    app.include_router(redirect.router)
    return app

