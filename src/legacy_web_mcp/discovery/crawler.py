"""Manual crawling fallback to discover additional URLs."""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import structlog

from legacy_web_mcp.discovery.http import Fetcher
from legacy_web_mcp.discovery.robots import RobotsAnalysis

_LOGGER = structlog.get_logger(__name__)


class LinkExtractor(HTMLParser):
    """Collect anchor links from an HTML document."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:  # pragma: no cover - HTMLParser base method
        if tag.lower() != "a":
            return
        for attr, value in attrs:
            if attr.lower() == "href" and value:
                absolute = urljoin(self.base_url, value)
                self.links.append(absolute)


async def crawl(
    base_url: str,
    *,
    fetcher: Fetcher,
    robots: RobotsAnalysis,
    max_depth: int,
    allowed_domains: Iterable[str],
) -> list[tuple[str, int, str]]:
    """Return list of tuples (url, depth, source) discovered via crawl."""

    queue: deque[tuple[str, int]] = deque([(base_url, 0)])
    visited: set[str] = set()
    discovered: list[tuple[str, int, str]] = []
    allowed_domains = {domain.lower() for domain in allowed_domains}

    while queue:
        current_url, depth = queue.popleft()
        if current_url in visited:
            continue
        visited.add(current_url)

        if depth > max_depth:
            continue

        if not robots.can_fetch(current_url):
            _LOGGER.debug("crawl_skip_disallowed", url=current_url)
            continue

        result = await fetcher.fetch(current_url)
        if not result.ok:
            _LOGGER.debug("crawl_fetch_failed", url=current_url, status=result.status)
            continue

        discovered.append((current_url, depth, "crawl"))

        if depth == max_depth:
            continue

        extractor = LinkExtractor(current_url)
        extractor.feed(result.text)
        for link in extractor.links:
            parsed = urlparse(link)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.netloc.lower() not in allowed_domains:
                continue
            if link not in visited:
                queue.append((link, depth + 1))
    return discovered


__all__ = ["crawl"]
