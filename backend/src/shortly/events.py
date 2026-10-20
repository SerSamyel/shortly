"""Click events and their publisher.

Publishing is fire-and-forget: a redirect never waits for the broker and never fails
because of it. Failures are logged and counted.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClickEvent:
    link_id: int
    ts: str  # ISO 8601, UTC
    referrer_domain: str
    country: str
    visitor_hash: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ClickEvent":
        data = json.loads(raw)
        return cls(
            link_id=int(data["link_id"]),
            ts=str(data["ts"]),
            referrer_domain=str(data["referrer_domain"]),
            country=str(data["country"]),
            visitor_hash=str(data["visitor_hash"]),
            event_id=str(data["event_id"]),
        )

    @property
    def timestamp(self) -> datetime:
        return datetime.fromisoformat(self.ts)


class ClickPublisher(Protocol):
    def publish(self, event: ClickEvent) -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


class MemoryPublisher:
    """Keeps events in a list; used by tests and when no broker is configured."""

    def __init__(self) -> None:
        self.events: list[ClickEvent] = []
        self.fail = False

    def publish(self, event: ClickEvent) -> None:
        if self.fail:
            log.warning("click event dropped: publisher failing")
            return
        self.events.append(event)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None


class KafkaPublisher:
    def __init__(self, bootstrap: str, topic: str) -> None:
        self.bootstrap = bootstrap
        self.topic = topic
        self._producer = None
        self._tasks: set[asyncio.Task] = set()
        self._connect_task: asyncio.Task | None = None
        self.published = 0
        self.failed = 0

    async def start(self) -> None:
        # Connect in the background so the API starts even while the broker is down.
        self._connect_task = asyncio.create_task(self._connect_forever())

    async def _connect_forever(self) -> None:
        from aiokafka import AIOKafkaProducer

        while self._producer is None:
            producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap, acks=1, request_timeout_ms=5000, linger_ms=5
            )
            try:
                await producer.start()
            except Exception as exc:  # broker not reachable yet
                log.warning("kafka producer not connected, retrying: %s", type(exc).__name__)
                await producer.stop()
                await asyncio.sleep(5)
                continue
            self._producer = producer
            log.info("kafka producer connected")

    def publish(self, event: ClickEvent) -> None:
        if self._producer is None:
            self.failed += 1
            log.warning("click event dropped: broker not connected")
            return
        task = asyncio.create_task(self._send(event))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _send(self, event: ClickEvent) -> None:
        try:
            await self._producer.send_and_wait(
                self.topic, event.to_bytes(), key=str(event.link_id).encode()
            )
            self.published += 1
        except Exception as exc:
            self.failed += 1
            log.warning("click event publish failed: %s", type(exc).__name__)

    async def stop(self) -> None:
        if self._connect_task:
            self._connect_task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._producer is not None:
            await self._producer.stop()
