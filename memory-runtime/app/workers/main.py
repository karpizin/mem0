from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from app.config import get_settings
from app.database import init_database
from app.logging_utils import configure_logging, log_event
from app.workers.runner import WorkerRunner

HEARTBEAT_PATH = Path("/tmp/memory_runtime_worker_heartbeat")
logger = logging.getLogger(__name__)


def run_once() -> int:
    settings = get_settings()
    configure_logging(level="DEBUG" if settings.debug else "INFO")
    if settings.auto_create_tables:
        init_database()
    touch_heartbeat()
    processed = WorkerRunner.run_pending_jobs()
    log_event(logger, "worker.run_once.completed", processed=processed)
    return processed


def initialize_database_with_retry(*, poll_seconds: float, max_attempts: int | None = None) -> None:
    configure_logging(level="DEBUG" if get_settings().debug else "INFO")
    attempts = 0
    while True:
        try:
            init_database()
            log_event(logger, "worker.database.ready", attempts=attempts)
            return
        except Exception as exc:  # noqa: BLE001
            attempts += 1
            if max_attempts is not None and attempts >= max_attempts:
                log_event(
                    logger,
                    "worker.database.retry_exhausted",
                    level=logging.ERROR,
                    attempts=attempts,
                    poll_seconds=poll_seconds,
                    error=str(exc),
                )
                raise
            log_event(
                logger,
                "worker.database.retrying",
                level=logging.WARNING,
                attempts=attempts,
                poll_seconds=poll_seconds,
                error=str(exc),
            )
            time.sleep(poll_seconds)


def touch_heartbeat() -> None:
    HEARTBEAT_PATH.write_text(str(time.time()), encoding="utf-8")


def run_forever(*, poll_seconds: float | None = None, max_cycles: int | None = None) -> int:
    settings = get_settings()
    configure_logging(level="DEBUG" if settings.debug else "INFO")
    interval = poll_seconds if poll_seconds is not None else settings.worker_poll_seconds
    if settings.auto_create_tables:
        initialize_database_with_retry(poll_seconds=interval)

    total_processed = 0
    cycles = 0
    log_event(logger, "worker.run_forever.started", poll_seconds=interval, max_cycles=max_cycles)
    while True:
        touch_heartbeat()
        total_processed += WorkerRunner.run_pending_jobs()
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            log_event(
                logger,
                "worker.run_forever.completed",
                total_processed=total_processed,
                cycles=cycles,
            )
            return total_processed
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    configure_logging(level="DEBUG" if get_settings().debug else "INFO")
    parser = argparse.ArgumentParser(description="Run the mem0plus worker.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process pending jobs once and exit.",
    )
    args = parser.parse_args(argv)

    if args.once:
        run_once()
        return 0

    run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
