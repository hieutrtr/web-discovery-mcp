"""robots.txt analysis utilities."""
from __future__ import annotations

from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin

import structlog

from legacy_web_mcp.discovery.http import Fetcher
from legacy_web_mcp.discovery.utils import dedupe_preserve_order

_LOGGER = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RobotsAnalysis:
    parser: robotparser.RobotFileParser
    sitemap_urls: tuple[str, ...]
    allowed_paths: tuple[str, ...]

    def can_fetch(self, url: str) -> bool:
        return self.parser.can_fetch("*", url)


async def analyze_robots(fetcher: Fetcher, base_url: str) -> RobotsAnalysis:
    robots_url = urljoin(base_url, "/robots.txt")
    parser = robotparser.RobotFileParser()
    parser.set_url(robots_url)

    result = await fetcher.fetch(robots_url)
    if not result.ok:
        # Configure parser to allow everything when fetch fails.
        parser.parse([])
        _LOGGER.info("robots_missing", url=robots_url, status=result.status)
        return RobotsAnalysis(parser=parser, sitemap_urls=(), allowed_paths=())

    lines = result.text.splitlines()
    parser.parse(lines)

    sitemap_urls = [
        line.split(":", 1)[1].strip()
        for line in lines
        if line.lower().startswith("sitemap:")
    ]
    allowed_paths = [
        line.split(":", 1)[1].strip()
        for line in lines
        if line.lower().startswith("allow:")
    ]

    sitemap_urls = dedupe_preserve_order(sitemap_urls)
    allowed_paths = dedupe_preserve_order(allowed_paths)

    full_sitemaps = [
        url if url.startswith("http") else urljoin(base_url, url)
        for url in sitemap_urls
    ]
    _LOGGER.info(
        "robots_analyzed",
        sitemap_count=len(full_sitemaps),
        allowed_paths=len(allowed_paths),
    )
    return RobotsAnalysis(
        parser=parser,
        sitemap_urls=tuple(full_sitemaps),
        allowed_paths=tuple(allowed_paths),
    )


__all__ = ["RobotsAnalysis", "analyze_robots"]
