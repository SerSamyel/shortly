from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shortly.cache import LinkStore
from shortly.config import Settings
from shortly.events import ClickPublisher
from shortly.geo import CountryLookup
from shortly.models import User
from shortly.security import read_token


@dataclass
class Deps:
    """Everything request handlers need; built once at startup (or by tests)."""

    settings: Settings
    sessionmaker: async_sessionmaker
    store: LinkStore
    publisher: ClickPublisher
    geo: CountryLookup


def get_deps(request: Request) -> Deps:
    return request.app.state.deps


async def get_session(deps: Annotated[Deps, Depends(get_deps)]) -> AsyncIterator[AsyncSession]:
    async with deps.sessionmaker() as session:
        yield session


_bearer = HTTPBearer(auto_error=False)


async def current_user(
    deps: Annotated[Deps, Depends(get_deps)],
    session: Annotated[AsyncSession, Depends(get_session)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = read_token(credentials.credentials, deps.settings.jwt_secret)
    if user_id is None:
        raise unauthorized
    user = await session.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


DepsDep = Annotated[Deps, Depends(get_deps)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
UserDep = Annotated[User, Depends(current_user)]
