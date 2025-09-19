from __future__ import annotations

import pytest

from legacy_web_mcp.discovery.http import FetchResult
from legacy_web_mcp.discovery.robots import analyze_robots


class StubFetcher:
    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResult:
        return self._responses[url]


@pytest.mark.asyncio()
async def test_analyze_robots_extracts_allows_and_sitemaps() -> None:
    base = "https://example.com"
    fetcher = StubFetcher(
        {
            "https://example.com/robots.txt": FetchResult(
                url="https://example.com/robots.txt",
                status=200,
                text="""
User-agent: *
Allow: /about
Sitemap: https://example.com/site.xml
""",
                content_type="text/plain",
            )
        }
    )
    analysis = await analyze_robots(fetcher, base)
    assert analysis.sitemap_urls == ("https://example.com/site.xml",)
    assert analysis.allowed_paths == ("/about",)
    assert analysis.can_fetch("https://example.com/about")


@pytest.mark.asyncio()
async def test_analyze_robots_defaults_to_allow_all_on_failure() -> None:
    base = "https://example.com"
    fetcher = StubFetcher(
        {
            "https://example.com/robots.txt": FetchResult(
                url="https://example.com/robots.txt",
                status=404,
                text="",
                content_type=None,
            )
        }
    )
    analysis = await analyze_robots(fetcher, base)
    assert analysis.sitemap_urls == ()
    assert analysis.can_fetch("https://example.com/anything")
