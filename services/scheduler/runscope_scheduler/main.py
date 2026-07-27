import asyncio
import logging

from redis.asyncio import Redis
from runscope_api.config import get_settings
from runscope_api.db import SessionFactory
from runscope_api.logging import configure_logging

from runscope_scheduler.service import schedule_once

logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    redis = Redis.from_url(settings.redis_url)
    delay = settings.scheduler_poll_seconds
    try:
        while True:
            try:
                async with SessionFactory() as session:
                    assigned = await schedule_once(session, settings)
                    if assigned:
                        logger.info(
                            "Scheduled queued runs",
                            extra={"assigned_count": assigned},
                        )
                try:
                    await redis.set(
                        "runscope:scheduler:heartbeat",
                        "online",
                        ex=max(3, settings.worker_stale_seconds),
                    )
                except Exception:
                    logger.warning("Scheduler heartbeat publish failed")
                delay = settings.scheduler_poll_seconds
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduler iteration failed")
                delay = min(max(delay * 2, 1), 10)
            await asyncio.sleep(delay)
    finally:
        await redis.aclose()


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
