"""Project storage management for analysis sessions."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog
import yaml

from legacy_web_mcp.config.settings import MCPSettings

_LOGGER = structlog.get_logger(__name__)
_DOMAIN_PATTERN = re.compile(r"[^a-z0-9]+")
_DEFAULT_PROJECT_PREFIX = "project"
_ARCHIVE_FOLDER_NAME = "archive"
_METADATA_FILE_NAME = "metadata.json"


def _sanitize_domain(domain_or_url: str) -> str:
    """Return a filesystem-safe identifier derived from the input domain or URL."""

    parsed = urlparse(domain_or_url)
    candidate = parsed.netloc or parsed.path or domain_or_url
    candidate = candidate.lower()
    candidate = _DOMAIN_PATTERN.sub("-", candidate).strip("-")
    return candidate or _DEFAULT_PROJECT_PREFIX


def _generate_project_id(domain_or_url: str, created_at: datetime) -> str:
    timestamp = created_at.astimezone(UTC).strftime("%Y%m%d-%H%M%S")
    domain_slug = _sanitize_domain(domain_or_url)
    return f"{domain_slug}_{timestamp}"


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Materialized filesystem locations for a project."""

    project_id: str
    root: Path
    discovery_dir: Path
    analysis_dir: Path
    reports_dir: Path
    metadata_path: Path
    inventory_json_path: Path
    inventory_yaml_path: Path


@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Describes persisted metadata for a project."""

    project_id: str
    domain: str
    created_at: str
    last_updated: str
    configuration: dict[str, Any]
    discovered_url_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def with_discovered_count(
        self, count: int, *, updated_at: datetime | None = None
    ) -> ProjectMetadata:
        updated = updated_at or datetime.now(tz=UTC)
        return ProjectMetadata(
            project_id=self.project_id,
            domain=self.domain,
            created_at=self.created_at,
            last_updated=updated.astimezone(UTC).isoformat(),
            configuration=self.configuration,
            discovered_url_count=count,
        )

    @property
    def root_path(self) -> Path:
        """Get the root path for this project."""
        # This is a temporary implementation - in practice this should be calculated 
        # from a base directory and project_id
        return Path("docs/web_discovery") / self.project_id


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """Combined paths and metadata for a project."""

    paths: ProjectPaths
    metadata: ProjectMetadata


class ProjectStore:
    """Manage project directory lifecycle and metadata persistence."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / _ARCHIVE_FOLDER_NAME).mkdir(exist_ok=True)

    @classmethod
    def from_settings(cls, settings: MCPSettings) -> ProjectStore:
        return cls(Path(settings.OUTPUT_ROOT))

    @property
    def root(self) -> Path:
        return self._root

    def initialize_project(
        self,
        domain_or_url: str,
        *,
        configuration_snapshot: dict[str, Any],
        created_at: datetime | None = None,
    ) -> ProjectRecord:
        """Create a new project hierarchy and persist initial metadata."""

        now = created_at or datetime.now(tz=UTC)
        project_id = _generate_project_id(domain_or_url, now)
        root = self._root / project_id
        if root.exists():
            raise FileExistsError(f"Project directory '{project_id}' already exists")

        discovery_dir = root / "discovery"
        analysis_dir = root / "analysis"
        reports_dir = root / "reports"
        metadata_path = root / _METADATA_FILE_NAME
        inventory_json_path = discovery_dir / "inventory.json"
        inventory_yaml_path = discovery_dir / "inventory.yaml"

        for path in (root, discovery_dir, analysis_dir, reports_dir):
            path.mkdir(parents=True, exist_ok=False)

        metadata = ProjectMetadata(
            project_id=project_id,
            domain=_sanitize_domain(domain_or_url),
            created_at=now.astimezone(UTC).isoformat(),
            last_updated=now.astimezone(UTC).isoformat(),
            configuration=configuration_snapshot,
            discovered_url_count=0,
        )

        paths = ProjectPaths(
            project_id=project_id,
            root=root,
            discovery_dir=discovery_dir,
            analysis_dir=analysis_dir,
            reports_dir=reports_dir,
            metadata_path=metadata_path,
            inventory_json_path=inventory_json_path,
            inventory_yaml_path=inventory_yaml_path,
        )
        self._write_metadata(paths.metadata_path, metadata)
        _LOGGER.info("project_initialized", project_id=project_id, root=str(root))
        return ProjectRecord(paths=paths, metadata=metadata)

    def _write_metadata(self, path: Path, metadata: ProjectMetadata) -> None:
        _LOGGER.debug("write_metadata", path=str(path))
        with path.open("w", encoding="utf-8") as handle:
            json.dump(metadata.to_dict(), handle, indent=2)

    def load_project(self, project_id: str) -> ProjectRecord | None:
        root = self._root / project_id
        metadata_path = root / _METADATA_FILE_NAME
        if not metadata_path.exists():
            return None
        try:
            with metadata_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover - defended via tests
            _LOGGER.error("metadata_invalid", project_id=project_id, error=str(exc))
            return None

        metadata = ProjectMetadata(
            project_id=raw["project_id"],
            domain=raw["domain"],
            created_at=raw["created_at"],
            last_updated=raw["last_updated"],
            configuration=raw["configuration"],
            discovered_url_count=int(raw.get("discovered_url_count", 0)),
        )
        paths = ProjectPaths(
            project_id=project_id,
            root=root,
            discovery_dir=root / "discovery",
            analysis_dir=root / "analysis",
            reports_dir=root / "reports",
            metadata_path=metadata_path,
            inventory_json_path=root / "discovery" / "inventory.json",
            inventory_yaml_path=root / "discovery" / "inventory.yaml",
        )
        return ProjectRecord(paths=paths, metadata=metadata)

    def get_project_metadata(self, project_id: str) -> ProjectMetadata | None:
        """Get just the metadata for a project without loading the full project record."""
        project = self.load_project(project_id)
        return project.metadata if project else None

    def create_project(self, project_id: str, website_url: str, config: dict[str, Any]) -> ProjectMetadata:
        """Create a new project and return its metadata."""
        from urllib.parse import urlparse
        import time
        
        # Extract domain from URL
        domain = urlparse(website_url).netloc or "unknown-domain"
        
        # Create timestamps
        now = datetime.now(tz=UTC)
        
        # Initialize the project (this will create directories and persist metadata)
        project_record = self.initialize_project(
            domain_or_url=website_url,  # Fixed parameter name
            configuration_snapshot=config,
            created_at=now
        )
        
        return project_record.metadata

    def list_projects(self) -> list[ProjectMetadata]:
        """Return metadata for all discoverable projects."""

        records: list[ProjectMetadata] = []
        for directory in self._root.iterdir():
            if not directory.is_dir() or directory.name == _ARCHIVE_FOLDER_NAME:
                continue
            record = self.load_project(directory.name)
            if record is not None:
                records.append(record.metadata)
        return sorted(records, key=lambda item: item.created_at, reverse=True)

    def write_url_inventory(
        self,
        project: ProjectRecord,
        inventory: dict[str, Any],
        *,
        discovered_count: int,
    ) -> ProjectRecord:
        """Persist URL inventory as JSON and YAML, updating metadata counts."""

        project.paths.discovery_dir.mkdir(parents=True, exist_ok=True)
        with project.paths.inventory_json_path.open("w", encoding="utf-8") as handle:
            json.dump(inventory, handle, indent=2)
        with project.paths.inventory_yaml_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(inventory, handle, sort_keys=False, allow_unicode=False)

        updated_metadata = project.metadata.with_discovered_count(discovered_count)
        self._write_metadata(project.paths.metadata_path, updated_metadata)
        _LOGGER.info(
            "inventory_persisted",
            project_id=project.paths.project_id,
            entries=discovered_count,
        )
        return ProjectRecord(paths=project.paths, metadata=updated_metadata)

    def cleanup_project(
        self, project_id: str, *, delete: bool = False, confirm: bool = False
    ) -> Path:
        """Archive or delete a project directory after explicit confirmation."""

        if not confirm:
            raise PermissionError("Cleanup requires explicit confirmation (confirm=True).")
        record = self.load_project(project_id)
        if record is None:
            raise FileNotFoundError(f"Unknown project '{project_id}'")

        if delete:
            shutil.rmtree(record.paths.root)
            _LOGGER.info("project_deleted", project_id=project_id)
            return record.paths.root

        archive_root = self._root / _ARCHIVE_FOLDER_NAME
        destination = archive_root / project_id
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(record.paths.root), destination)
        _LOGGER.info("project_archived", project_id=project_id, destination=str(destination))
        return destination


def create_project_store(settings: MCPSettings) -> ProjectStore:
    """Convenience factory used by application wiring."""

    return ProjectStore.from_settings(settings)


__all__ = [
    "ProjectPaths",
    "ProjectMetadata",
    "ProjectRecord",
    "ProjectStore",
    "create_project_store",
]
