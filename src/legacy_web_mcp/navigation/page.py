from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping
from urllib.parse import urlparse

try:  # pragma: no cover - optional dependency
    from playwright.async_api import async_playwright
except ModuleNotFoundError:  # pragma: no cover
    async_playwright = None  # type: ignore

from legacy_web_mcp.storage import ProjectPaths

Fetch = Callable[[str], Awaitable[str]]


@dataclass(slots=True)
class PageCapture:
    url: str
    html_path: Path
    text_path: Path
    screenshot_path: Path
    metadata: Mapping[str, Any]
    errors: list[str] = field(default_factory=list)


class _ContentExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.title: str = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data.strip()
        elif data.strip():
            self.text_parts.append(data.strip())

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


async def default_fetch(url: str) -> str:
    if async_playwright is None:
        raise RuntimeError("Playwright not installed; provide custom fetch implementation")
    async with async_playwright().start() as p:  # pragma: no cover
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        content = await page.content()
        await browser.close()
        return content


def _slugify(url: str) -> str:
    parsed = urlparse(url)
    parts = [parsed.netloc] + [segment for segment in parsed.path.split("/") if segment]
    slug = "-".join(parts) or parsed.netloc or "page"
    slug = slug.replace(":", "-")
    return slug or "page"


async def navigate_to_page(
    url: str,
    project: ProjectPaths,
    *,
    fetch: Fetch | None = None,
    headless: bool | None = None,
) -> PageCapture:
    fetch = fetch or default_fetch
    start = time.perf_counter()
    errors: list[str] = []
    try:
        html = await fetch(url)
    except Exception as exc:
        html = ""
        errors.append(f"fetch_failed:{exc}")

    extractor = _ContentExtractor()
    if html:
        extractor.feed(html)
    text_content = extractor.text
    title = extractor.title or url
    load_duration = time.perf_counter() - start

    slug = _slugify(url)
    html_path = project.analysis_dir / f"{slug}.html"
    text_path = project.analysis_dir / f"{slug}.txt"
    screenshot_path = project.analysis_dir / f"{slug}.png"

    project.analysis_dir.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    text_path.write_text(text_content, encoding="utf-8")
    if async_playwright is None:
        screenshot_path.write_text("placeholder screenshot", encoding="utf-8")
    else:  # pragma: no cover - not exercised in unit tests
        await _capture_screenshot(url, screenshot_path, headless=headless)

    metadata = {
        "url": url,
        "title": title,
        "text_length": len(text_content),
        "load_seconds": round(load_duration, 4),
        "headless": headless,
    }

    return PageCapture(
        url=url,
        html_path=html_path,
        text_path=text_path,
        screenshot_path=screenshot_path,
        metadata=metadata,
        errors=errors,
    )


async def _capture_screenshot(url: str, path: Path, *, headless: bool | None = None) -> None:
    async with async_playwright().start() as p:  # pragma: no cover
        browser = await p.chromium.launch(headless=headless if headless is not None else True)
        page = await browser.new_page()
        await page.goto(url)
        await page.screenshot(path=path)
        await browser.close()
