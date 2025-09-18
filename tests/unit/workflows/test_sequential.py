import asyncio
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.storage import initialize_project
from legacy_web_mcp.workflows import SequentialNavigationWorkflow


class StubEnvironment:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    async def fetch(self, url: str) -> str:
        return self.mapping[url]


def test_sequential_workflow_persists_checkpoint(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path), headless=True)
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    mapping = {
        "https://example.com/": "<html><head><title>Home</title></head><body><p>Hello</p></body></html>",
        "https://example.com/about": "<html><head><title>About</title></head><body></body></html>",
    }
    env = StubEnvironment(mapping)
    workflow = SequentialNavigationWorkflow(project, list(mapping.keys()), settings=settings, fetch_html=env.fetch)

    asyncio.run(workflow.run())

    assert len(workflow._queue) == 0
    assert workflow._progress.completed == list(mapping.keys())
    assert workflow._progress.checkpoint_path is not None
    assert workflow._progress.checkpoint_path.exists()
    checkpoint = workflow._progress.checkpoint_path.read_text()
    assert '"completed"' in checkpoint


def test_workflow_skip(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path), headless=True)
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    env = StubEnvironment({"https://example.com/": "<html><head><title>Home</title></head><body></body></html>"})
    workflow = SequentialNavigationWorkflow(project, ["https://example.com/"], settings=settings, fetch_html=env.fetch)
    workflow.skip("https://example.com/")
    asyncio.run(workflow.run())
    assert workflow._progress.skipped == ["https://example.com/"]
