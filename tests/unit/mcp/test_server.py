import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from legacy_web_mcp.config import Settings
from legacy_web_mcp.mcp.server import (
    SERVER_NAME,
    SimpleMCPServer,
    _load_progress_snapshot,
    create_mcp_server,
)
from legacy_web_mcp.progress import CheckpointManager, ProgressSnapshot, ProgressTracker
from legacy_web_mcp.storage import initialize_project
from legacy_web_mcp.workflows.yolo import YoloAnalysisResult


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


def test_simple_server_yolo_analysis_invokes_entrypoint(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_entrypoint(project_id: str, urls: list[str] | None, *, config_overrides=None) -> dict[str, Any]:
        captured["project_id"] = project_id
        captured["urls"] = urls
        captured["config_overrides"] = config_overrides
        return {"project_id": project_id, "status": "ok"}

    monkeypatch.setattr("legacy_web_mcp.mcp.server._yolo_entrypoint", fake_entrypoint)
    server = SimpleMCPServer()
    result = asyncio.run(server.yolo_analysis("proj-123", ["https://example.com/"]))

    assert result["status"] == "ok"
    assert captured["project_id"] == "proj-123"
    assert captured["urls"] == ["https://example.com/"]
    assert captured["config_overrides"] is None


def test_start_analysis_lists_modes(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        analysis_output_root=str(tmp_path),
        step1_model="model-a",
        step2_model="model-b",
        fallback_model="model-c",
    )
    loader = lambda env=None, config_path=None: settings
    monkeypatch.setattr("legacy_web_mcp.config.load_settings", loader)
    monkeypatch.setattr("legacy_web_mcp.mcp.server.load_settings", loader)

    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    server = SimpleMCPServer()
    result = asyncio.run(server.start_analysis(project.project_id))

    assert result["status"] == "awaiting_selection"
    assert any(mode["id"] == "interactive" for mode in result["modes"])
    defaults = result["defaults"]
    assert defaults["interactive"]["suggested_models"]["step1"] == settings.step1_model
    assert defaults["yolo"]["max_concurrency"] == settings.max_concurrent_browsers


def test_start_analysis_yolo_delegates_config(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    loader = lambda env=None, config_path=None: settings
    monkeypatch.setattr("legacy_web_mcp.config.load_settings", loader)
    monkeypatch.setattr("legacy_web_mcp.mcp.server.load_settings", loader)
    project = initialize_project("https://example.org", base_path=tmp_path, settings=settings)

    captured: dict[str, Any] = {}

    async def fake_entrypoint(project_id: str, urls: list[str] | None, *, config_overrides=None) -> dict[str, Any]:
        captured["project_id"] = project_id
        captured["urls"] = urls
        captured["config_overrides"] = config_overrides
        return {"project_id": project_id, "status": "scheduled"}

    monkeypatch.setattr("legacy_web_mcp.mcp.server._yolo_entrypoint", fake_entrypoint)
    server = SimpleMCPServer()
    result = asyncio.run(
        server.start_analysis(
            project.project_id,
            mode="yolo",
            config={"yolo": {"max_concurrency": 5}},
        )
    )

    assert result["status"] == "scheduled"
    assert captured["config_overrides"] == {"max_concurrency": 5}


def test_start_analysis_switches_to_yolo(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    loader = lambda env=None, config_path=None: settings
    monkeypatch.setattr("legacy_web_mcp.config.load_settings", loader)
    monkeypatch.setattr("legacy_web_mcp.mcp.server.load_settings", loader)

    project = initialize_project("https://example.net", base_path=tmp_path, settings=settings)
    tracker = ProgressTracker(project)
    urls = ["https://example.net/a", "https://example.net/b"]
    tracker.register_urls(urls)
    state = tracker.to_state()
    state["interactive"] = {
        "config": {"step1_model": "alt-step1", "step2_model": "alt-step2"},
        "queue": [urls[1]],
    }
    manager = CheckpointManager(project)
    checkpoint_path = manager.write(queue=[urls[1]], tracker_state=state, current_url=urls[0])

    snapshot = ProgressSnapshot(
        project_id=project.project_id,
        total_pages=2,
        pending=1,
        analyzing=0,
        completed=1,
        failed=0,
        skipped=0,
        percentage=50.0,
        average_seconds=None,
        eta_seconds=None,
        current_url=None,
        started_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        pages=state.get("pages", {}),
    )

    async def fake_run_yolo_analysis(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return YoloAnalysisResult(
            project_id=project.project_id,
            snapshot=snapshot,
            completed=[urls[0]],
            failed=[],
            errors={},
            duration_seconds=0.5,
            checkpoint_path=None,
            artifacts={},
            budget={},
        )

    captured_kwargs: dict[str, Any] = {}
    monkeypatch.setattr("legacy_web_mcp.mcp.server.run_yolo_analysis", fake_run_yolo_analysis)

    server = SimpleMCPServer()
    result = asyncio.run(
        server.start_analysis(
            project.project_id,
            mode="switch_to_yolo",
            checkpoint_path=str(checkpoint_path),
            urls=["https://example.net/c"],
        )
    )

    assert result["mode"] == "yolo"
    assert result["source_checkpoint"] == str(checkpoint_path)
    assert "pending_urls" in result and result["pending_urls"][0] == urls[0]
    assert captured_kwargs["config_overrides"]["step1_model"] == "alt-step1"
    assert captured_kwargs["progress"].snapshot().project_id == project.project_id
