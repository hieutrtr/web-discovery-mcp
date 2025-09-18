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
    workflow = SequentialNavigationWorkflow(
        project,
        list(mapping.keys()),
        settings=settings,
        fetch_html=env.fetch,
        resume=False,
    )

    result = asyncio.run(workflow.run())

    assert len(workflow._queue) == 0
    snapshot = result.snapshot
    assert snapshot.completed == len(mapping)
    assert snapshot.percentage == 100.0
    assert result.checkpoint_path is not None
    assert result.checkpoint_path.exists()
    checkpoint = result.checkpoint_path.read_text(encoding="utf-8")
    assert '"queue": []' in checkpoint
    page_file = project.docs_pages_dir / "page-example.com.md"
    assert page_file.exists()
    report_contents = project.docs_master_report.read_text(encoding="utf-8")
    assert "Legacy Web Analysis Report" in report_contents
    manual_checkpoint = workflow.manual_checkpoint()
    assert manual_checkpoint.exists()
    workflow.cleanup_checkpoints(retain=1)
    retained = list(project.checkpoints_dir.glob("checkpoint-*.json"))
    assert len(retained) == 1


def test_workflow_skip(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path), headless=True)
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    env = StubEnvironment({"https://example.com/": "<html><head><title>Home</title></head><body></body></html>"})
    workflow = SequentialNavigationWorkflow(
        project,
        ["https://example.com/"],
        settings=settings,
        fetch_html=env.fetch,
        resume=False,
    )
    workflow.skip("https://example.com/")
    asyncio.run(workflow.run())
    snapshot = workflow.progress_tracker.snapshot()
    assert snapshot.skipped == 1
