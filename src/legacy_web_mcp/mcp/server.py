"""FastMCP server bootstrap utilities.

The implementation is designed to work with the FastMCP framework when it is
available. During development environments where FastMCP is not installed, the
module falls back to a lightweight shim so that unit tests can still exercise
the ping tool without importing the real dependency.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

from legacy_web_mcp.config import load_settings
from legacy_web_mcp.progress import CheckpointManager
from legacy_web_mcp.storage import ProjectPaths

SERVER_NAME = "legacy-web-analysis"


class PingTool(Protocol):
    async def __call__(self) -> dict[str, str]:
        """Ping the server."""


@dataclass
class SimpleMCPServer:
    """Minimal asynchronous server used as a fallback during local testing."""

    name: str = SERVER_NAME
    ping_tool: PingTool | None = None

    def __post_init__(self) -> None:
        if self.ping_tool is None:
            self.ping_tool = _default_ping

    async def ping(self) -> dict[str, str]:
        return await self.ping_tool()

    async def analysis_progress(self, project_id: str | None = None) -> dict[str, Any]:
        return _load_progress_snapshot(project_id)

    async def pause_analysis(self, project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "paused")

    async def resume_analysis(self, project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "running")

    async def checkpoint_analysis(self, project_id: str) -> dict[str, Any]:
        return _create_manual_checkpoint(project_id)

    def run(self) -> None:
        raise RuntimeError(
            "FastMCP is not installed. Install 'fastmcp' to run the production server."
        )


async def _default_ping() -> dict[str, str]:
    return {"status": "ok"}


def create_mcp_server() -> Any:
    """Create the MCP server instance.

    Returns a FastMCP :class:`MCPServer` when the dependency is available,
    otherwise returns :class:`SimpleMCPServer` so the remainder of the
    application can operate in a degraded but testable mode.
    """
    try:
        from fastmcp import MCPServer, resource, tool  # type: ignore
    except ModuleNotFoundError:
        return SimpleMCPServer()

    server = MCPServer(name=SERVER_NAME)

    @tool()
    async def ping() -> dict[str, str]:
        return await _default_ping()

    server.add_tool(ping)

    @resource()
    async def analysis_progress(project_id: Optional[str] = None) -> dict[str, Any]:
        return _load_progress_snapshot(project_id)

    server.add_resource(analysis_progress)

    @tool()
    async def pause_analysis(project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "paused")

    @tool()
    async def resume_analysis(project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "running")

    @tool()
    async def checkpoint_analysis(project_id: str) -> dict[str, Any]:
        return _create_manual_checkpoint(project_id)

    server.add_tool(pause_analysis)
    server.add_tool(resume_analysis)
    server.add_tool(checkpoint_analysis)
    return server


def _load_progress_snapshot(project_id: str | None) -> dict[str, Any]:
    settings = load_settings()
    root = Path(settings.analysis_output_root)
    if project_id:
        candidates = [
            root
            / project_id
            / "docs"
            / "web_discovery"
            / "progress"
            / "analysis-progress.json"
        ]
    else:
        candidates = sorted(
            root.glob("*/docs/web_discovery/progress/analysis-progress.json"),
            reverse=True,
        )
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        data.setdefault("project_id", project_id or path.parent.parent.parent.name)
        data.setdefault("status", "running")
        return data
    return {
        "project_id": project_id,
        "status": "unavailable",
        "detail": "No progress snapshot found.",
    }


def _set_analysis_status(project_id: str, status: str) -> dict[str, Any]:
    settings = load_settings()
    root = Path(settings.analysis_output_root)
    try:
        paths = _build_project_paths(project_id, root)
    except FileNotFoundError:
        return {"project_id": project_id, "status": "missing"}

    metadata_path = paths.docs_metadata_file
    metadata: dict[str, Any]
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    except json.JSONDecodeError:
        metadata = {}
    metadata.update(
        {
            "project_id": project_id,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if status == "paused":
        metadata["paused_at"] = datetime.now(timezone.utc).isoformat()
    else:
        metadata.pop("paused_at", None)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"project_id": project_id, "status": status}


def _create_manual_checkpoint(project_id: str) -> dict[str, Any]:
    settings = load_settings()
    root = Path(settings.analysis_output_root)
    try:
        paths = _build_project_paths(project_id, root)
    except FileNotFoundError:
        return {"project_id": project_id, "status": "missing"}

    manager = CheckpointManager(paths)
    state = manager.load_latest()
    if state is None:
        return {"project_id": project_id, "status": "no_checkpoint"}
    manual_path = manager.write(state.queue, state.tracker_state, state.current_url)
    return {
        "project_id": project_id,
        "status": "checkpoint_created",
        "path": str(manual_path),
    }


def _build_project_paths(project_id: str, root: Path) -> ProjectPaths:
    project_path = root / project_id
    if not project_path.exists():
        raise FileNotFoundError(project_id)

    discovery = project_path / "discovery"
    analysis = project_path / "analysis"
    reports = project_path / "reports"
    checkpoints = project_path / "checkpoints"
    docs_root = project_path / "docs"
    docs_web = docs_root / "web_discovery"
    docs_progress = docs_web / "progress"
    docs_pages = docs_web / "pages"
    docs_reports = docs_web / "reports"

    for directory in (
        discovery,
        analysis,
        reports,
        checkpoints,
        docs_root,
        docs_web,
        docs_progress,
        docs_pages,
        docs_reports,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    docs_metadata_file = docs_web / "analysis-metadata.json"
    if not docs_metadata_file.exists():
        docs_metadata_file.write_text(
            json.dumps(
                {
                    "project_id": project_id,
                    "status": "pending",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    docs_master_report = docs_web / "analysis-report.md"
    if not docs_master_report.exists():
        docs_master_report.write_text("# Legacy Web Analysis Report\n\n", encoding="utf-8")

    metadata_file = project_path / "metadata.json"
    return ProjectPaths(
        project_id=project_id,
        root_path=project_path,
        discovery_dir=discovery,
        analysis_dir=analysis,
        reports_dir=reports,
        metadata_file=metadata_file,
        checkpoints_dir=checkpoints,
        docs_root=docs_root,
        docs_web_dir=docs_web,
        docs_progress_dir=docs_progress,
        docs_pages_dir=docs_pages,
        docs_reports_dir=docs_reports,
        docs_metadata_file=docs_metadata_file,
        docs_master_report=docs_master_report,
    )


__all__ = ["create_mcp_server", "SimpleMCPServer", "SERVER_NAME"]
