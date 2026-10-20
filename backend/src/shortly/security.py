from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from shortly.db import utcnow

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user_id: int, secret: str, ttl_hours: int) -> str:
    now = utcnow()
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=ttl_hours)}
    return jwt.encode(payload, secret, algorithm="HS256")


def read_token(token: str, secret: str) -> int | None:
    """Return the user id from a valid token, or None for anything invalid or expired."""
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp"]})
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
