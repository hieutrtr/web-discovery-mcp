"""HTTP utilities for discovery fetching."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import aiohttp
import structlog

_LOGGER = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FetchResult:
    url: str
    status: int
    text: str
    content_type: str | None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResult:  # pragma: no cover - Protocol definition
        ...


class AiohttpFetcher:
    """Thin wrapper around aiohttp for testable fetch operations."""

    def __init__(self, *, timeout: float) -> None:
        self._timeout = timeout

    async def fetch(self, url: str) -> FetchResult:
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.get(url) as response:
                    content_type = response.headers.get("Content-Type")
                    text = await response.text()
                    _LOGGER.debug("http_fetch", url=url, status=response.status)
                    return FetchResult(
                        url=url,
                        status=response.status,
                        text=text,
                        content_type=content_type,
                    )
            except Exception as exc:
                _LOGGER.warning("http_fetch_failed", url=url, error=str(exc))
                return FetchResult(url=url, status=599, text="", content_type=None)


__all__ = ["FetchResult", "Fetcher", "AiohttpFetcher"]
