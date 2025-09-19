from __future__ import annotations

from urllib import robotparser

import pytest

from legacy_web_mcp.discovery.crawler import crawl
from legacy_web_mcp.discovery.http import FetchResult
from legacy_web_mcp.discovery.robots import RobotsAnalysis


class StubFetcher:
    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResult:
        return self._responses[url]


@pytest.mark.asyncio()
async def test_crawl_discovers_internal_links() -> None:
    base = "https://example.com"
    responses = {
        "https://example.com": FetchResult(
            url="https://example.com",
            status=200,
            text='<a href="/about">About</a> <a href="https://external.com/">External</a>',
            content_type="text/html",
        ),
        "https://example.com/about": FetchResult(
            url="https://example.com/about",
            status=200,
            text="<p>About</p>",
            content_type="text/html",
        ),
    }
    fetcher = StubFetcher(responses)
    parser = robotparser.RobotFileParser()
    parser.parse([])
    robots = RobotsAnalysis(parser=parser, sitemap_urls=(), allowed_paths=())

    discovered = await crawl(
        base,
        fetcher=fetcher,
        robots=robots,
        max_depth=1,
        allowed_domains=["example.com"],
    )
    assert ("https://example.com", 0, "crawl") in discovered
    assert ("https://example.com/about", 1, "crawl") in discovered
    assert not any(url == "https://external.com/" for url, _, _ in discovered)


@pytest.mark.asyncio()
async def test_crawl_respects_robots_rules() -> None:
    base = "https://example.com"
    responses = {
        "https://example.com": FetchResult(
            url="https://example.com",
            status=200,
            text='<a href="/secret">Secret</a>',
            content_type="text/html",
        ),
        "https://example.com/secret": FetchResult(
            url="https://example.com/secret",
            status=200,
            text="<p>Secret</p>",
            content_type="text/html",
        ),
    }
    fetcher = StubFetcher(responses)
    parser = robotparser.RobotFileParser()
    parser.parse(["User-agent: *", "Disallow: /secret"])
    robots = RobotsAnalysis(parser=parser, sitemap_urls=(), allowed_paths=())

    discovered = await crawl(
        base,
        fetcher=fetcher,
        robots=robots,
        max_depth=1,
        allowed_domains=["example.com"],
    )
    assert all(url != "https://example.com/secret" for url, _, _ in discovered)
