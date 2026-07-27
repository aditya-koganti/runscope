import asyncio
import logging

from runscope_api.config import get_settings
from runscope_api.db import SessionFactory
from runscope_api.logging import configure_logging

from runscope_scheduler.service import schedule_once

logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    delay = settings.scheduler_poll_seconds
    while True:
        try:
            async with SessionFactory() as session:
                assigned = await schedule_once(session, settings)
                if assigned:
                    logger.info("Scheduled queued runs", extra={"assigned_count": assigned})
            delay = settings.scheduler_poll_seconds
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduler iteration failed")
            delay = min(max(delay * 2, 1), 10)
        await asyncio.sleep(delay)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
