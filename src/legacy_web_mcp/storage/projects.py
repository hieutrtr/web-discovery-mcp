from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.discovery.models import DiscoveryReport

PROJECT_METADATA_FILE = "metadata.json"
DISCOVERY_DIR = "discovery"
ANALYSIS_DIR = "analysis"
REPORTS_DIR = "reports"
ARCHIVE_DIR = "archive"


@dataclass(slots=True)
class ProjectPaths:
    project_id: str
    root_path: Path
    discovery_dir: Path
    analysis_dir: Path
    reports_dir: Path
    metadata_file: Path
    checkpoints_dir: Path
    docs_root: Path
    docs_web_dir: Path
    docs_progress_dir: Path
    docs_pages_dir: Path
    docs_reports_dir: Path
    docs_metadata_file: Path
    docs_master_report: Path


@dataclass(slots=True)
class ProjectSummary:
    project_id: str
    root_url: str
    created_at: str
    path: Path
    pages: int = 0
    assets: int = 0


def _slugify_host(root_url: str) -> str:
    parsed = urlparse(root_url)
    host = parsed.netloc or parsed.path
    cleaned = host.lower().strip()
    cleaned = cleaned.replace(":", "-").replace("/", "-")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in {"-", "_", "."})
    return cleaned or "project"


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def initialize_project(
    root_url: str,
    *,
    base_path: Path | None = None,
    settings: Settings | None = None,
) -> ProjectPaths:
    parsed = load_settings() if settings is None else settings
    base = base_path or Path(parsed.analysis_output_root)
    base.mkdir(parents=True, exist_ok=True)
    host = _slugify_host(root_url)
    project_id = f"{host}-{_timestamp()}"
    project_path = base / project_id
    discovery = project_path / DISCOVERY_DIR
    analysis = project_path / ANALYSIS_DIR
    reports = project_path / REPORTS_DIR
    checkpoints = project_path / "checkpoints"
    docs_root = project_path / "docs"
    docs_web = docs_root / "web_discovery"
    docs_progress = docs_web / "progress"
    docs_pages = docs_web / "pages"
    docs_reports = docs_web / "reports"
    for directory in (
        project_path,
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

    metadata = {
        "project_id": project_id,
        "root_url": root_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_output_root": str(base),
        "settings": parsed.sanitized(),
    }
    metadata_file = project_path / PROJECT_METADATA_FILE
    metadata_file.write_text(json.dumps(metadata, indent=2))
    docs_metadata_file = docs_web / "analysis-metadata.json"
    docs_metadata_file.write_text(
        json.dumps(
            {
                "project_id": project_id,
                "root_url": root_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "completed_pages": 0,
                "total_pages": 0,
                "status": "pending",
            },
            indent=2,
        )
    )
    docs_master_report = docs_web / "analysis-report.md"
    if not docs_master_report.exists():
        docs_master_report.write_text("# Legacy Web Analysis Report\n\n", encoding="utf-8")
    return ProjectPaths(
        project_id,
        project_path,
        discovery,
        analysis,
        reports,
        metadata_file,
        checkpoints,
        docs_root,
        docs_web,
        docs_progress,
        docs_pages,
        docs_reports,
        docs_metadata_file,
        docs_master_report,
    )


def save_url_inventory(project: ProjectPaths, report: DiscoveryReport) -> Path:
    inventory = {
        "root_url": report.root_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": [asdict(page) for page in report.pages],
        "assets": [asdict(asset) for asset in report.assets],
    }
    file_path = project.discovery_dir / "urls.json"
    file_path.write_text(json.dumps(inventory, indent=2))
    report.metadata_path = str(file_path)
    _update_metadata_counts(project, len(report.pages), len(report.assets))
    return file_path


def list_projects(base_path: Path | None = None) -> List[ProjectSummary]:
    base = base_path or Path(load_settings().analysis_output_root)
    summaries: list[ProjectSummary] = []
    if not base.exists():
        return summaries
    for path in sorted(base.iterdir()):
        metadata_file = path / PROJECT_METADATA_FILE
        if not metadata_file.exists():
            continue
        data = json.loads(metadata_file.read_text())
        summaries.append(
            ProjectSummary(
                project_id=data.get("project_id", path.name),
                root_url=data.get("root_url", ""),
                created_at=data.get("created_at", ""),
                path=path,
                pages=data.get("url_inventory", {}).get("pages", 0),
                assets=data.get("url_inventory", {}).get("assets", 0),
            )
        )
    return summaries


def cleanup_project(project_path: Path, *, archive: bool = False) -> Path | None:
    if not project_path.exists():
        return None
    if archive:
        archive_dir = project_path.parent / ARCHIVE_DIR
        archive_dir.mkdir(exist_ok=True)
        destination = archive_dir / project_path.name
        shutil.move(str(project_path), destination)
        return destination
    shutil.rmtree(project_path)
    return None


def _update_metadata_counts(project: ProjectPaths, pages: int, assets: int) -> None:
    metadata_file = project.metadata_file
    data = json.loads(metadata_file.read_text())
    data.setdefault("url_inventory", {})
    data["url_inventory"].update({"pages": pages, "assets": assets})
    metadata_file.write_text(json.dumps(data, indent=2))
