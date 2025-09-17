import asyncio
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.discovery import discover_website


class StubFetcher:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    async def __call__(self, url: str) -> str:  # type: ignore[override]
        if url not in self.mapping:
            raise KeyError(url)
        return self.mapping[url]


def test_discover_website_uses_sitemap_and_persists(tmp_path: Path) -> None:
    root = "https://example.com"
    mapping = {
        f"{root}/sitemap.xml": """
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
              <url><loc>https://example.com/</loc></url>
              <url><loc>https://example.com/about</loc></url>
            </urlset>
        """,
        f"{root}/robots.txt": "User-agent: *\nAllow: /docs\n",
        f"{root}/": "<html><head><title>Home</title></head><body><a href='/styles.css'>Style</a></body></html>",
        f"{root}/about": "<html><head><title>About</title></head><body></body></html>",
        f"{root}/docs": "<html><head><title>Docs</title></head><body></body></html>",
        f"{root}/styles.css": "body { color: black; }",
    }
    fetcher = StubFetcher(mapping)
    settings = Settings(max_concurrent_browsers=3, analysis_output_root=str(tmp_path))

    report = asyncio.run(discover_website(
        root,
        fetch=fetcher.__call__,
        settings=settings,
    ))

    assert report.pages
    urls = {page.url for page in report.pages}
    assert f"{root}/" in urls
    assert f"{root}/about" in urls
    assert any(asset.url.endswith("styles.css") for asset in report.assets)
    assert report.metadata_path is not None
    saved = Path(report.metadata_path)
    assert saved.exists()
    data = saved.read_text()
    assert "example.com/about" in data


def test_discover_website_fallback_to_crawl(tmp_path: Path) -> None:
    root = "https://fallback.test"
    mapping = {
        f"{root}/robots.txt": "",
        f"{root}/": "<html><head><title>Root</title></head><body><a href='page1'>P1</a></body></html>",
        f"{root}/page1": "<html><head><title>Page1</title></head><body></body></html>",
    }
    fetcher = StubFetcher(mapping)
    settings = Settings(max_concurrent_browsers=2, analysis_output_root=str(tmp_path))

    report = asyncio.run(discover_website(
        root,
        fetch=fetcher.__call__,
        settings=settings,
    ))

    assert any(page.url.endswith("page1") for page in report.pages)
    assert report.progress[0].startswith("project_created:")
    assert report.progress[-1] == "persisted"
