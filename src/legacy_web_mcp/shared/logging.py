"""Logging configuration helpers for the Legacy Web MCP server."""

from __future__ import annotations

import logging
from typing import Final, cast

import structlog

_DEFAULT_LOG_LEVEL: Final[int] = logging.INFO


def configure_logging() -> None:
    """Configure structlog for JSON-formatted logs.

    This is idempotent to guard against repeated configuration when modules import
    the logging utilities multiple times across the modular monolith.
    """
    if cast(bool, getattr(configure_logging, "_configured", False)):
        return

    logging.basicConfig(level=_DEFAULT_LOG_LEVEL)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(_DEFAULT_LOG_LEVEL),
    )

    configure_logging._configured = True  # type: ignore[attr-defined]


__all__ = ["configure_logging"]
