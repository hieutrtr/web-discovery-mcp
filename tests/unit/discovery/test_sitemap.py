from __future__ import annotations

import pytest

from legacy_web_mcp.discovery.http import FetchResult
from legacy_web_mcp.discovery.sitemap import fetch_sitemaps


class StubFetcher:
    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResult:
        return self._responses.get(
            url, FetchResult(url=url, status=404, text="", content_type=None)
        )


@pytest.mark.asyncio()
async def test_fetch_sitemaps_handles_index_and_url(tmp_path: str) -> None:
    base = "https://example.com"
    fetcher = StubFetcher(
        responses={
            "https://example.com/sitemap.xml": FetchResult(
                url="https://example.com/sitemap.xml",
                status=200,
                text="""
                    <sitemapindex>
                        <sitemap><loc>https://example.com/section.xml</loc></sitemap>
                    </sitemapindex>
                """,
                content_type="application/xml",
            ),
            "https://example.com/section.xml": FetchResult(
                url="https://example.com/section.xml",
                status=200,
                text="""
                    <urlset>
                        <url><loc>https://example.com/a</loc></url>
                        <url><loc>https://example.com/b</loc></url>
                    </urlset>
                """,
                content_type="application/xml",
            ),
        }
    )

    urls, errors = await fetch_sitemaps(fetcher, base)
    assert urls == ["https://example.com/a", "https://example.com/b"]
    assert errors == []


@pytest.mark.asyncio()
async def test_fetch_sitemaps_records_errors() -> None:
    base = "https://example.com"
    fetcher = StubFetcher(
        responses={
            "https://example.com/sitemap.xml": FetchResult(
                url="https://example.com/sitemap.xml",
                status=500,
                text="",
                content_type=None,
            )
        }
    )

    urls, errors = await fetch_sitemaps(fetcher, base)
    assert urls == []
    assert errors == ["Failed to fetch https://example.com/sitemap.xml (status 500)"]
