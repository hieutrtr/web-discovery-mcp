from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from legacy_web_mcp.storage.projects import ProjectStore


@pytest.fixture()
def store(tmp_path: Path) -> ProjectStore:
    return ProjectStore(tmp_path)


def _fixed_now() -> datetime:
    return datetime(2025, 2, 14, 12, 0, 0, tzinfo=UTC)


def test_initialize_project_creates_expected_structure(store: ProjectStore) -> None:
    record = store.initialize_project(
        "https://Example.com/path",
        configuration_snapshot={"browser": "chromium"},
        created_at=_fixed_now(),
    )

    assert record.paths.root.exists()
    assert record.paths.discovery_dir.exists()
    assert record.paths.analysis_dir.exists()
    assert record.paths.reports_dir.exists()
    assert record.paths.metadata_path.exists()
    assert record.metadata.project_id == "example-com_20250214-120000"
    assert record.metadata.domain == "example-com"

    with record.paths.metadata_path.open() as handle:
        metadata = json.load(handle)
    assert metadata["configuration"] == {"browser": "chromium"}
    assert metadata["discovered_url_count"] == 0


def test_write_url_inventory_updates_metadata_and_files(store: ProjectStore) -> None:
    record = store.initialize_project(
        "example.org",
        configuration_snapshot={},
        created_at=_fixed_now(),
    )

    inventory = {
        "summary": {"total_urls": 2},
        "entries": [
            {"url": "https://example.org/", "classification": "internal_page"},
            {"url": "https://example.org/assets/app.js", "classification": "asset"},
        ],
    }
    updated = store.write_url_inventory(record, inventory, discovered_count=2)

    with updated.paths.inventory_json_path.open() as handle:
        assert json.load(handle)["summary"]["total_urls"] == 2
    with updated.paths.inventory_yaml_path.open() as handle:
        data = yaml.safe_load(handle)
    assert data["entries"][0]["classification"] == "internal_page"
    assert updated.metadata.discovered_url_count == 2


def test_list_projects_returns_metadata_sorted(store: ProjectStore, tmp_path: Path) -> None:
    earlier = store.initialize_project(
        "earlier.test",
        configuration_snapshot={},
        created_at=datetime(2025, 2, 14, 10, 0, tzinfo=UTC),
    )
    later = store.initialize_project(
        "later.test",
        configuration_snapshot={},
        created_at=datetime(2025, 2, 14, 12, 0, tzinfo=UTC),
    )

    metadata_list = store.list_projects()
    assert [item.project_id for item in metadata_list] == [later.paths.project_id, earlier.paths.project_id]


def test_cleanup_requires_confirmation(store: ProjectStore) -> None:
    record = store.initialize_project("confirm.test", configuration_snapshot={}, created_at=_fixed_now())

    with pytest.raises(PermissionError):
        store.cleanup_project(record.paths.project_id)


def test_cleanup_archives_project(store: ProjectStore, tmp_path: Path) -> None:
    record = store.initialize_project("archive.test", configuration_snapshot={}, created_at=_fixed_now())

    destination = store.cleanup_project(record.paths.project_id, confirm=True)
    archive_root = tmp_path / "archive"
    assert destination == archive_root / record.paths.project_id
    assert destination.exists()
    assert not record.paths.root.exists()


def test_cleanup_deletes_project(store: ProjectStore) -> None:
    record = store.initialize_project("delete.test", configuration_snapshot={}, created_at=_fixed_now())

    destination = store.cleanup_project(record.paths.project_id, delete=True, confirm=True)
    assert destination == record.paths.root
    assert not record.paths.root.exists()
