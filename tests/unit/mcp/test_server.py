import asyncio
import json
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.mcp.server import (
    SERVER_NAME,
    SimpleMCPServer,
    _load_progress_snapshot,
    create_mcp_server,
)
from legacy_web_mcp.progress import CheckpointManager, ProgressTracker
from legacy_web_mcp.storage import initialize_project


def test_simple_server_ping_returns_status_ok() -> None:
    server = SimpleMCPServer()
    result = asyncio.run(server.ping())
    assert result == {"status": "ok"}


def test_create_mcp_server_returns_fallback_without_fastmcp() -> None:
    server = create_mcp_server()
    assert isinstance(server, SimpleMCPServer)
    assert server.name == SERVER_NAME
    result = asyncio.run(server.ping())
    assert result["status"] == "ok"


def test_analysis_progress_uses_snapshot(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    loader = lambda env=None, config_path=None: settings
    monkeypatch.setattr("legacy_web_mcp.config.load_settings", loader)
    monkeypatch.setattr("legacy_web_mcp.mcp.server.load_settings", loader)

    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)

    tracker = ProgressTracker(project)
    tracker.register_urls(["https://example.com/"])
    tracker.mark_analyzing("https://example.com/")
    tracker.mark_completed("https://example.com/", 1.0)
    tracker_state = tracker.to_state()
    manager = CheckpointManager(project)
    manager.write(["https://example.com/"], tracker_state, "https://example.com/")

    data = _load_progress_snapshot(project.project_id)
    assert data["project_id"] == project.project_id

    server = SimpleMCPServer()
    result = asyncio.run(server.analysis_progress(project.project_id))
    assert result["project_id"] == project.project_id

    pause = asyncio.run(server.pause_analysis(project.project_id))
    assert pause["status"] == "paused"
    metadata = json.loads(project.docs_metadata_file.read_text())
    assert metadata["status"] == "paused"

    resume = asyncio.run(server.resume_analysis(project.project_id))
    assert resume["status"] == "running"
    metadata = json.loads(project.docs_metadata_file.read_text())
    assert metadata["status"] == "running"

    checkpoint = asyncio.run(server.checkpoint_analysis(project.project_id))
    assert checkpoint["status"] == "checkpoint_created"
    assert Path(checkpoint["path"]).exists()
