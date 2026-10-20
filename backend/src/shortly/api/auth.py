import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from shortly.api.deps import DepsDep, SessionDep, UserDep
from shortly.models import User
from shortly.schemas import AuthResponse, Credentials, UserOut
from shortly.security import create_token, hash_password, verify_password

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _auth_response(user: User, deps) -> AuthResponse:
    token = create_token(user.id, deps.settings.jwt_secret, deps.settings.jwt_ttl_hours)
    return AuthResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/signup", status_code=201, response_model=AuthResponse)
async def signup(body: Credentials, session: SessionDep, deps: DepsDep) -> AuthResponse:
    existing = await session.scalar(select(User.id).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:  # a concurrent signup with the same email won the race
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    await session.refresh(user)
    log.info("user signed up", extra={"user_id": user.id})
    return _auth_response(user, deps)


@router.post("/login", response_model=AuthResponse)
async def login(body: Credentials, session: SessionDep, deps: DepsDep) -> AuthResponse:
    user = await session.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(user.password_hash, body.password):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return _auth_response(user, deps)


@router.get("/me", response_model=UserOut)
async def me(user: UserDep) -> UserOut:
    return UserOut.model_validate(user)
