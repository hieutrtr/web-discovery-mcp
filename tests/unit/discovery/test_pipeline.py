from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest
from fastmcp import Context

from legacy_web_mcp.config.settings import MCPSettings
from legacy_web_mcp.discovery.http import FetchResult
from legacy_web_mcp.discovery.pipeline import WebsiteDiscoveryService
from legacy_web_mcp.storage.projects import ProjectStore


class StubFetcher:
    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResult:
        return self._responses.get(
            url, FetchResult(url=url, status=404, text="", content_type=None)
        )


@dataclass
class DummyContext:
    messages: list[str]

    def __init__(self) -> None:
        self.messages = []

    async def info(self, message: str) -> None:
        self.messages.append(message)

    async def error(self, message: str) -> None:
        self.messages.append(f"error:{message}")


@pytest.mark.asyncio()
async def test_discovery_pipeline_generates_inventory(tmp_path: Path) -> None:
    settings = MCPSettings(OUTPUT_ROOT=tmp_path)
    responses = {
        "https://example.com/robots.txt": FetchResult(
            url="https://example.com/robots.txt",
            status=200,
            text="""
User-agent: *
Allow: /support
Sitemap: https://example.com/sitemap.xml
""",
            content_type="text/plain",
        ),
        "https://example.com/sitemap.xml": FetchResult(
            url="https://example.com/sitemap.xml",
            status=200,
            text="""
<urlset>
    <url><loc>https://example.com/</loc></url>
    <url><loc>https://example.com/pricing</loc></url>
</urlset>
""",
            content_type="application/xml",
        ),
    }
    fetcher = StubFetcher(responses)
    store = ProjectStore(tmp_path)
    service = WebsiteDiscoveryService(settings, project_store=store, fetcher=fetcher)
    context = cast(Context, DummyContext())

    result = await service.discover(context, "https://example.com")

    assert result["summary"]["total"] == 3
    assert result["sources"]["sitemap"] is True
    assert result["sources"]["crawl"] is False
    inventory_json = Path(result["paths"]["inventory_json"])
    assert inventory_json.exists()
    dummy_context = cast(DummyContext, context)
    assert dummy_context.messages[0].startswith("Validated target URL")


@pytest.mark.asyncio()
async def test_discovery_pipeline_uses_crawl_when_no_sitemap(tmp_path: Path) -> None:
    settings = MCPSettings(OUTPUT_ROOT=tmp_path, DISCOVERY_MAX_DEPTH=1)
    responses = {
        "https://example.org/robots.txt": FetchResult(
            url="https://example.org/robots.txt",
            status=404,
            text="",
            content_type=None,
        ),
        "https://example.org": FetchResult(
            url="https://example.org",
            status=200,
            text='<a href="/about">About</a>',
            content_type="text/html",
        ),
        "https://example.org/about": FetchResult(
            url="https://example.org/about",
            status=200,
            text="<p>About</p>",
            content_type="text/html",
        ),
    }
    fetcher = StubFetcher(responses)
    store = ProjectStore(tmp_path)
    service = WebsiteDiscoveryService(settings, project_store=store, fetcher=fetcher)
    context = cast(Context, DummyContext())

    result = await service.discover(context, "https://example.org")
    assert result["sources"]["crawl"] is True
    assert result["summary"]["total"] >= 1
    dummy_context = cast(DummyContext, context)
    assert any("Manual crawl" in message for message in dummy_context.messages)
