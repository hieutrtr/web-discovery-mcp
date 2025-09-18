from __future__ import annotations

import asyncio
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Awaitable, Callable, Iterable

try:  # pragma: no cover - optional dependency for production
    import aiohttp
except ModuleNotFoundError:  # pragma: no cover
    aiohttp = None  # type: ignore

from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.discovery.models import DiscoveredUrl, DiscoveryReport

Fetch = Callable[[str], Awaitable[str]]

ASSET_EXTENSIONS = {"css", "js", "png", "jpg", "jpeg", "gif", "svg", "ico", "pdf"}
DEFAULT_MAX_DEPTH = 1


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            for attr, value in attrs:
                if attr.lower() == "href" and value:
                    self.links.append(value)
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data.strip()


async def default_fetch(url: str) -> str:
    if aiohttp is None:
        raise RuntimeError(
            "aiohttp is required for network fetching. Install aiohttp or provide a custom fetcher."
        )
    async with aiohttp.ClientSession() as session:  # type: ignore[unreachable]
        async with session.get(url, timeout=20) as response:
            response.raise_for_status()
            return await response.text()


def normalize_root(url: str) -> str:
    parsed = urllib.parse.urlparse(url, scheme="https")
    if not parsed.netloc:
        raise ValueError("URL must include a hostname")
    normalized = parsed._replace(path="/").geturl()
    return normalized.rstrip("/")


def is_asset(url: str) -> bool:
    path = urllib.parse.urlparse(url).path
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return ext in ASSET_EXTENSIONS


def make_absolute(root: str, url: str) -> str:
    return urllib.parse.urljoin(root + "/", url)




async def fetch_sitemap(root: str, fetch: Fetch) -> list[str]:
    sitemap_url = urllib.parse.urljoin(root + "/", "sitemap.xml")
    try:
        xml_text = await fetch(sitemap_url)
    except Exception:
        return []
    try:
        tree = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    urls = []
    for element in tree.findall("{*}url/{*}loc"):
        if element.text:
            urls.append(element.text.strip())
    return urls


async def fetch_robots(root: str, fetch: Fetch) -> list[str]:
    robots_url = urllib.parse.urljoin(root + "/", "robots.txt")
    try:
        text = await fetch(robots_url)
    except Exception:
        return []
    allowed_paths: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("allow:"):
            allowed_paths.append(line.split(":", 1)[1].strip())
    return [make_absolute(root, path) for path in allowed_paths if path]


async def crawl(
    root: str,
    fetch: Fetch,
    start_urls: list[str],
    *,
    max_depth: int,
) -> list[tuple[str, int, str | None, list[str]]]:
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque((url, 0) for url in start_urls)
    results: list[tuple[str, int, str | None, list[str]]] = []
    while queue:
        url, depth = queue.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            html = await fetch(url)
        except Exception:
            continue
        parser = LinkExtractor()
        parser.feed(html)
        title = parser.title
        child_links = [make_absolute(root, link) for link in parser.links]
        results.append((url, depth, title, child_links))
        if depth < max_depth:
            for link in child_links:
                if link not in visited and link.startswith(root):
                    queue.append((link, depth + 1))
    return results


async def discover_website(
    url: str,
    *,
    fetch: Fetch | None = None,
    settings: Settings | None = None,
    output_root: Path | None = None,
) -> DiscoveryReport:
    fetch = fetch or default_fetch
    settings = settings or load_settings()
    root = normalize_root(url)
    max_depth = max(settings.max_concurrent_browsers - 1, DEFAULT_MAX_DEPTH)

    from legacy_web_mcp.storage import initialize_project, save_url_inventory

    base_path = Path(output_root) if output_root is not None else Path(settings.analysis_output_root)
    project = initialize_project(root, base_path=base_path, settings=settings)
    report = DiscoveryReport(root_url=root)
    report.progress.append(f"project_created:{project.project_id}")

    sitemap_urls = await fetch_sitemap(root, fetch)
    if sitemap_urls:
        report.progress.append(f"sitemap_discovered:{len(sitemap_urls)}")
    robots_urls = await fetch_robots(root, fetch)
    if robots_urls:
        report.progress.append(f"robots_allow:{len(robots_urls)}")

    start_urls = sitemap_urls or robots_urls or [make_absolute(root, '/')]
    crawl_results = await crawl(root, fetch, start_urls, max_depth=max_depth)
    report.progress.append(f"crawl_completed:{len(crawl_results)}")

    seen: set[str] = set()
    for url_entry, depth, title, child_links in crawl_results:
        if url_entry in seen:
            continue
        seen.add(url_entry)
        item = DiscoveredUrl(
            url=url_entry,
            source="crawl" if url_entry not in sitemap_urls else "sitemap",
            depth=depth,
            url_type="asset" if is_asset(url_entry) else "page",
            title=title,
            description=None,
        )
        if item.url_type == "page":
            report.pages.append(item)
        else:
            report.assets.append(item)
        for child in child_links:
            if is_asset(child) and child not in seen:
                report.assets.append(
                    DiscoveredUrl(
                        url=child,
                        source="link",
                        depth=depth + 1,
                        url_type="asset",
                    )
                )
                seen.add(child)

    save_url_inventory(project, report)
    report.progress.append("persisted")
    return report
