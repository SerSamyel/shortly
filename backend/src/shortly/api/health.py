import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from shortly.api.deps import DepsDep

log = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(deps: DepsDep) -> JSONResponse:
    try:
        async with deps.sessionmaker() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        log.exception("health check: database unreachable")
        return JSONResponse(
            {"status": "degraded", "version": deps.settings.version}, status_code=503
        )
    return JSONResponse({"status": "ok", "version": deps.settings.version})
