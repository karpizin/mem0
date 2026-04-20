from __future__ import annotations

import json
import logging
from collections.abc import Mapping


def configure_logging(*, level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    else:
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))


def log_event(
    logger: logging.Logger,
    event: str,
    /,
    *,
    level: int = logging.INFO,
    **fields: object,
) -> None:
    payload: dict[str, object] = {"event": event}
    payload.update(_drop_none(fields))
    logger.log(
        level,
        json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str),
    )


def _drop_none(fields: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in fields.items() if value is not None}
