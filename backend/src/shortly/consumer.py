"""Click consumer: reads click events from the broker and updates the aggregates.

Offsets are committed only after the database transaction commits, so a crash
re-delivers events; `apply_click` skips the ones already applied.
"""

import asyncio
import logging
import signal

from shortly.aggregation import apply_click
from shortly.config import Settings, get_settings
from shortly.db import make_engine, make_sessionmaker
from shortly.events import ClickEvent
from shortly.logs import setup_logging

log = logging.getLogger("shortly.consumer")


async def handle_batch(sessionmaker, raw_values: list[bytes]) -> int:
    """Apply a batch of raw messages in one transaction. Returns how many were applied."""
    applied = 0
    async with sessionmaker() as session, session.begin():
        for raw in raw_values:
            try:
                event = ClickEvent.from_bytes(raw)
            except (ValueError, KeyError, TypeError):
                log.error("skipping malformed click event")
                continue
            if await apply_click(session, event):
                applied += 1
    return applied


async def run(settings: Settings, stop: asyncio.Event) -> None:
    from aiokafka import AIOKafkaConsumer

    if not settings.kafka_bootstrap:
        raise SystemExit("KAFKA_BOOTSTRAP is not set")

    engine = make_engine(settings.database_url)
    sessionmaker = make_sessionmaker(engine)
    consumer = AIOKafkaConsumer(
        settings.clicks_topic,
        bootstrap_servers=settings.kafka_bootstrap,
        group_id="click-aggregator",
        enable_auto_commit=False,
        auto_offset_reset="earliest",
    )
    while not stop.is_set():
        try:
            await consumer.start()
            break
        except Exception as exc:
            log.warning("broker not reachable, retrying: %s", type(exc).__name__)
            await asyncio.sleep(5)
    log.info("click consumer started", extra={"topic": settings.clicks_topic})
    try:
        while not stop.is_set():
            batches = await consumer.getmany(timeout_ms=1000, max_records=500)
            for _partition, messages in batches.items():
                if not messages:
                    continue
                applied = await handle_batch(sessionmaker, [m.value for m in messages])
                log.info("click batch applied", extra={"received": len(messages), "applied": applied})
            if batches:
                await consumer.commit()
    finally:
        await consumer.stop()
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    stop = asyncio.Event()

    async def _main() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:  # Windows
                pass
        await run(settings, stop)

    asyncio.run(_main())


if __name__ == "__main__":
    main()
