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
from typing import Any, Mapping, Optional, Protocol, Sequence

from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.llm.client import build_default_client
from legacy_web_mcp.interaction import InteractiveConfig
from legacy_web_mcp.progress import CheckpointManager, ProgressTracker
from legacy_web_mcp.storage import ProjectPaths
from legacy_web_mcp.workflows import (
    YoloAnalysisConfig,
    load_discovered_urls,
    run_yolo_analysis,
)

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

    async def yolo_analysis(self, project_id: str, urls: Sequence[str] | None = None, config_overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return await _yolo_entrypoint(project_id, urls, config_overrides=config_overrides)

    async def start_analysis(
        self,
        project_id: str,
        mode: str | None = None,
        urls: Sequence[str] | None = None,
        config: Mapping[str, Any] | None = None,
        checkpoint_path: str | None = None,
    ) -> dict[str, Any]:
        return await _start_analysis(
            project_id,
            mode=mode,
            urls=urls,
            config=config,
            checkpoint_path=checkpoint_path,
        )

    def run(self) -> None:
        raise RuntimeError(
            "FastMCP is not installed. Install 'fastmcp' to run the production server."
        )


async def _default_ping() -> dict[str, str]:
    return {"status": "ok"}


def create_mcp_server() -> Any:
    """Create the MCP server instance.

    Returns a FastMCP server when the dependency is available,
    otherwise returns :class:`SimpleMCPServer` so the remainder of the
    application can operate in a degraded but testable mode.
    """
    try:
        from fastmcp import FastMCP  # type: ignore
    except ModuleNotFoundError:
        return SimpleMCPServer()

    server = FastMCP(name=SERVER_NAME)

    @server.tool
    async def ping() -> dict[str, str]:
        return await _default_ping()

    @server.resource("analysis://progress")
    async def analysis_progress(project_id: Optional[str] = None) -> dict[str, Any]:
        return _load_progress_snapshot(project_id)

    @server.tool
    async def pause_analysis(project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "paused")

    @server.tool
    async def resume_analysis(project_id: str) -> dict[str, Any]:
        return _set_analysis_status(project_id, "running")

    @server.tool
    async def checkpoint_analysis(project_id: str) -> dict[str, Any]:
        return _create_manual_checkpoint(project_id)

    @server.tool
    async def yolo_analysis(project_id: str, urls: Sequence[str] | None = None, config_overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return await _yolo_entrypoint(project_id, urls, config_overrides=config_overrides)

    @server.tool
    async def start_analysis(
        project_id: str,
        mode: str | None = None,
        urls: Sequence[str] | None = None,
        config: Mapping[str, Any] | None = None,
        checkpoint_path: str | None = None,
    ) -> dict[str, Any]:
        return await _start_analysis(
            project_id,
            mode=mode,
            urls=urls,
            config=config,
            checkpoint_path=checkpoint_path,
        )

    return server


async def _yolo_entrypoint(
    project_id: str,
    urls: Sequence[str] | None,
    *,
    config_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    settings = load_settings()
    root = Path(settings.analysis_output_root)
    try:
        project = _build_project_paths(project_id, root)
    except FileNotFoundError:
        return {
            "project_id": project_id,
            "status": "missing_project",
            "detail": "Project directory not found. Run discovery before analysis.",
        }

    try:
        url_list = list(urls) if urls is not None else load_discovered_urls(project)
    except FileNotFoundError:
        url_list = []

    url_list = [url for url in url_list if url]
    if not url_list:
        return {
            "project_id": project_id,
            "status": "no_urls",
            "detail": "No URLs provided or discovered for analysis. Supply urls or rerun discovery.",
        }

    llm_client = build_default_client()
    try:
        result = await run_yolo_analysis(
            project=project,
            urls=url_list,
            settings=settings,
            llm_client=llm_client,
            config_overrides=config_overrides,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "project_id": project_id,
            "status": "error",
            "detail": str(exc),
        }
    payload = result.to_dict()
    payload.setdefault("project_id", project_id)
    payload.setdefault("urls_processed", len(url_list))
    return payload


async def _start_analysis(
    project_id: str,
    *,
    mode: str | None,
    urls: Sequence[str] | None,
    config: Mapping[str, Any] | None,
    checkpoint_path: str | None,
) -> dict[str, Any]:
    settings = load_settings()
    root = Path(settings.analysis_output_root)
    try:
        project = _build_project_paths(project_id, root)
    except FileNotFoundError:
        return {
            "project_id": project_id,
            "status": "missing_project",
            "detail": "Project directory not found. Run discovery before starting analysis.",
        }

    catalog = _analysis_mode_catalog(settings)
    configuration = dict(config or {})

    if mode is None:
        interactive_defaults = _interactive_defaults(settings, configuration.get("interactive"))
        yolo_defaults = _yolo_defaults(settings, configuration.get("yolo"))
        return {
            "project_id": project_id,
            "status": "awaiting_selection",
            "modes": catalog,
            "defaults": {
                "interactive": interactive_defaults,
                "yolo": yolo_defaults,
            },
            "instructions": "Invoke start_analysis with mode='interactive' or mode='yolo' to begin a workflow.",
        }

    normalized_mode = mode.lower()
    if normalized_mode == "interactive":
        interactive_overrides = configuration.get("interactive")
        interactive_config = _interactive_defaults(settings, interactive_overrides)
        pending_urls = _resolve_urls(project, urls)
        return {
            "project_id": project_id,
            "status": "interactive_ready",
            "mode": "interactive",
            "config": interactive_config,
            "pending_urls": pending_urls,
            "modes": catalog,
            "next_tool": "interactive_analysis",
            "instructions": "Call interactive_analysis with the provided configuration to begin the guided session.",
        }

    if normalized_mode == "yolo":
        yolo_overrides = configuration.get("yolo")
        return await _yolo_entrypoint(project_id, urls, config_overrides=yolo_overrides)

    if normalized_mode in {"switch", "switch_to_yolo", "interactive_to_yolo"}:
        if not checkpoint_path:
            return {
                "project_id": project_id,
                "status": "error",
                "detail": "checkpoint_path is required when switching from Interactive to YOLO.",
            }
        yolo_overrides = configuration.get("yolo")
        return await _switch_interactive_to_yolo(
            project=project,
            settings=settings,
            checkpoint_path=checkpoint_path,
            config_overrides=yolo_overrides,
            additional_urls=urls,
        )

    return {
        "project_id": project_id,
        "status": "unsupported_mode",
        "detail": f"Unknown analysis mode '{mode}'.",
        "modes": catalog,
    }


def _analysis_mode_catalog(settings: Settings) -> list[dict[str, Any]]:
    interactive = {
        "id": "interactive",
        "title": "Interactive Mode",
        "summary": "Human-in-the-loop review for each analysis step before results are committed.",
        "tradeoffs": {
            "speed": "Slower — pauses for approvals at every checkpoint.",
            "cost": "Higher — retries and edits may incur extra LLM usage.",
            "confidence": "Highest — manual validation on every page.",
        },
    }
    yolo = {
        "id": "yolo",
        "title": "YOLO Mode",
        "summary": "Fully automated batch analysis optimized for throughput.",
        "tradeoffs": {
            "speed": "Fastest — continuous automation with concurrency.",
            "cost": "Predictable — single pass through each page with retries on failure.",
            "confidence": "Moderate — relies on automated validation heuristics.",
        },
    }
    return [interactive, yolo]


def _interactive_defaults(settings: Settings, overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    overrides = dict(overrides or {})
    config = InteractiveConfig(
        step1_model=str(overrides.get("step1_model", "step1")),
        step2_model=str(overrides.get("step2_model", "step2")),
        timeout_seconds=float(overrides.get("timeout_seconds", InteractiveConfig().timeout_seconds)),
    )
    return {
        "step1_model": config.step1_model,
        "step2_model": config.step2_model,
        "timeout_seconds": config.timeout_seconds,
        "suggested_models": {
            "step1": settings.step1_model,
            "step2": settings.step2_model,
        },
    }


def _yolo_defaults(settings: Settings, overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    config = YoloAnalysisConfig.from_settings(settings, overrides=overrides)
    return {
        "step1_model": config.step1_model,
        "step2_model": config.step2_model,
        "max_concurrency": config.max_concurrency,
        "max_attempts": config.max_attempts,
    }


def _resolve_urls(project: ProjectPaths, urls: Sequence[str] | None) -> list[str]:
    if urls:
        return [url for url in urls if url]
    try:
        return load_discovered_urls(project)
    except FileNotFoundError:
        return []


def _merge_pending_urls(
    current_url: str | None,
    queue_urls: Sequence[str],
    additional_urls: Sequence[str] | None,
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    def _append(url: str | None) -> None:
        if url and url not in seen:
            seen.add(url)
            merged.append(url)

    _append(current_url)
    for url in queue_urls:
        _append(url)
    if additional_urls:
        for url in additional_urls:
            _append(url)
    return merged


async def _switch_interactive_to_yolo(
    *,
    project: ProjectPaths,
    settings: Settings,
    checkpoint_path: str,
    config_overrides: Mapping[str, Any] | None,
    additional_urls: Sequence[str] | None,
) -> dict[str, Any]:
    path = Path(checkpoint_path)
    if not path.is_absolute():
        path = project.checkpoints_dir / path
    if not path.exists():
        return {
            "project_id": project.project_id,
            "status": "missing_checkpoint",
            "detail": f"Checkpoint file '{path}' not found.",
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "project_id": project.project_id,
            "status": "invalid_checkpoint",
            "detail": f"Checkpoint could not be parsed: {exc}",
        }

    tracker_state = payload.get("tracker", {})
    interactive_state = tracker_state.get("interactive", {})
    queue = interactive_state.get("queue") or payload.get("queue", [])
    current_url = payload.get("current_url")
    pending_urls = _merge_pending_urls(current_url, queue, additional_urls)

    if not pending_urls:
        return {
            "project_id": project.project_id,
            "status": "nothing_to_process",
            "detail": "No remaining URLs found in checkpoint queue.",
        }

    progress = ProgressTracker(project)
    if tracker_state:
        progress.restore(tracker_state)
    progress.register_urls(pending_urls)

    overrides = dict(config_overrides or {})
    interactive_config = interactive_state.get("config", {})
    for key in ("step1_model", "step2_model"):
        if key in interactive_config and key not in overrides:
            overrides[key] = interactive_config[key]

    llm_client = build_default_client()
    checkpoints = CheckpointManager(project)
    result = await run_yolo_analysis(
        project=project,
        urls=pending_urls,
        settings=settings,
        llm_client=llm_client,
        config_overrides=overrides,
        progress=progress,
        checkpoints=checkpoints,
    )
    response = result.to_dict()
    response.update(
        {
            "mode": "yolo",
            "source_checkpoint": str(path),
            "pending_urls": pending_urls,
        }
    )
    return response


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
