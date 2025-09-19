"""Sitemap discovery utilities."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Iterable
from urllib.parse import urljoin

import structlog

from legacy_web_mcp.discovery.http import Fetcher, FetchResult
from legacy_web_mcp.discovery.utils import dedupe_preserve_order

_LOGGER = structlog.get_logger(__name__)


async def fetch_sitemaps(
    fetcher: Fetcher,
    base_url: str,
    *,
    additional_candidates: Iterable[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Fetch sitemap documents and return discovered URLs and error messages."""

    candidates = [urljoin(base_url, "/sitemap.xml")]
    if additional_candidates:
        for candidate in additional_candidates:
            candidates.append(candidate)

    discovered: list[str] = []
    errors: list[str] = []
    queue = deque(dedupe_preserve_order(candidates))
    visited: set[str] = set()

    while queue:
        candidate = queue.popleft()
        if candidate in visited:
            continue
        visited.add(candidate)
        result = await fetcher.fetch(candidate)
        if not result.ok:
            if result.status != 404:
                errors.append(f"Failed to fetch {candidate} (status {result.status})")
            continue
        try:
            urls, additional = _parse_sitemap_document(result)
        except ET.ParseError as exc:
            errors.append(f"Invalid XML in {candidate}: {exc}")
            continue
        _LOGGER.info(
            "sitemap_parsed",
            candidate=candidate,
            url_count=len(urls),
            nested=len(additional),
        )
        discovered.extend(urls)
        for nested in additional:
            queue.append(nested)
    return dedupe_preserve_order(discovered), errors


def _parse_sitemap_document(result: FetchResult) -> tuple[list[str], list[str]]:
    root = ET.fromstring(result.text)
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}")[0] + "}"

    urls: list[str] = []
    nested: list[str] = []
    if root.tag.endswith("sitemapindex"):
        for element in root.findall(f"{namespace}sitemap/{namespace}loc"):
            if element.text:
                nested.append(element.text.strip())
        return urls, nested

    for element in root.findall(f"{namespace}url/{namespace}loc"):
        if element.text:
            urls.append(element.text.strip())
    return urls, nested


__all__ = ["fetch_sitemaps"]
