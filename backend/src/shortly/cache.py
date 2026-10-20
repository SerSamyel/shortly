"""Redis-backed link cache, rate limiter and daily salt store.

Every Redis call is best effort: if Redis is down, callers fall back to the database
(cache), allow the request (rate limit) or use a process-local salt.
"""

import json
import logging
import secrets
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CachedLink:
    id: int
    target_url: str
    is_active: bool
    expires_at: str | None  # ISO 8601, UTC

    def expires(self) -> datetime | None:
        return datetime.fromisoformat(self.expires_at) if self.expires_at else None


class CacheError(Exception):
    """The cache backend failed; the caller should fall back."""


class LinkStore(Protocol):
    async def get_link(self, code: str) -> CachedLink | None: ...
    async def set_link(self, code: str, link: CachedLink) -> None: ...
    async def delete_link(self, code: str) -> None: ...
    async def hit_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool: ...
    async def daily_salt(self, day: str) -> str: ...
    async def ping(self) -> bool: ...
    async def close(self) -> None: ...


class MemoryStore:
    """In-process store used in unit tests and when no REDIS_URL is configured."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self.links: dict[str, CachedLink] = {}
        self.counters: dict[str, int] = {}
        self.salts: dict[str, str] = {}
        self.fail = False  # tests flip this to simulate an outage

    def _check(self) -> None:
        if self.fail:
            raise CacheError("cache unavailable")

    async def get_link(self, code: str) -> CachedLink | None:
        self._check()
        return self.links.get(code)

    async def set_link(self, code: str, link: CachedLink) -> None:
        self._check()
        self.links[code] = link

    async def delete_link(self, code: str) -> None:
        self._check()
        self.links.pop(code, None)

    async def hit_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        self._check()
        bucket = f"{key}:{int(time.time() // window_seconds)}"
        self.counters[bucket] = self.counters.get(bucket, 0) + 1
        return self.counters[bucket] > limit

    async def daily_salt(self, day: str) -> str:
        return self.salts.setdefault(day, secrets.token_hex(16))

    async def ping(self) -> bool:
        return not self.fail

    async def close(self) -> None:
        return None


class RedisStore:
    def __init__(self, url: str, ttl_seconds: int = 3600) -> None:
        self.redis = Redis.from_url(
            url, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5
        )
        self.ttl = ttl_seconds
        self._local_salts: dict[str, str] = {}

    async def get_link(self, code: str) -> CachedLink | None:
        try:
            raw = await self.redis.get(f"link:{code}")
        except RedisError as exc:
            raise CacheError(str(exc)) from exc
        return CachedLink(**json.loads(raw)) if raw else None

    async def set_link(self, code: str, link: CachedLink) -> None:
        try:
            await self.redis.set(f"link:{code}", json.dumps(asdict(link)), ex=self.ttl)
        except RedisError as exc:
            raise CacheError(str(exc)) from exc

    async def delete_link(self, code: str) -> None:
        try:
            await self.redis.delete(f"link:{code}")
        except RedisError as exc:
            raise CacheError(str(exc)) from exc

    async def hit_rate_limit(self, key: str, limit: int, window_seconds: int) -> bool:
        bucket = f"rl:{key}:{int(time.time() // window_seconds)}"
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                count, _ = await pipe.incr(bucket).expire(bucket, window_seconds).execute()
        except RedisError as exc:
            raise CacheError(str(exc)) from exc
        return int(count) > limit

    async def daily_salt(self, day: str) -> str:
        # One random salt per UTC day, shared by all API replicas, gone after 36 hours.
        key = f"salt:{day}"
        try:
            await self.redis.set(key, secrets.token_hex(16), nx=True, ex=36 * 3600)
            salt = await self.redis.get(key)
            if salt:
                return salt
        except RedisError:
            log.warning("redis unavailable, using a process-local visitor salt")
        return self._local_salts.setdefault(day, secrets.token_hex(16))

    async def ping(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except RedisError:
            return False

    async def close(self) -> None:
        await self.redis.aclose()
