import asyncio
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.storage import initialize_project
from legacy_web_mcp.navigation import navigate_to_page


class StubFetcher:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    async def __call__(self, url: str) -> str:
        return self.mapping[url]


def test_navigate_to_page_persists_artifacts(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    fetcher = StubFetcher(
        {
            "https://example.com/": "<html><head><title>Example</title></head><body><p>Hello</p></body></html>",
        }
    )
    capture = asyncio.run(
        navigate_to_page("https://example.com/", project, fetch=fetcher.__call__)
    )

    assert capture.html_path.exists()
    assert capture.text_path.exists()
    assert capture.screenshot_path.exists()
    assert capture.metadata["title"] == "Example"
    assert capture.metadata["text_length"] > 0


def test_navigate_to_page_records_errors(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)

    async def failing_fetch(url: str) -> str:
        raise RuntimeError("boom")

    capture = asyncio.run(
        navigate_to_page("https://example.com/", project, fetch=failing_fetch)
    )

    assert capture.errors
    assert capture.html_path.exists()
