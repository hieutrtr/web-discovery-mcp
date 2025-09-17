from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.discovery.models import DiscoveryReport, DiscoveredUrl
from legacy_web_mcp.storage import (
    cleanup_project,
    initialize_project,
    list_projects,
    save_url_inventory,
)


def _build_report(root: str) -> DiscoveryReport:
    report = DiscoveryReport(root_url=root)
    report.pages.append(
        DiscoveredUrl(url=f"{root}/", source="crawl", depth=0, url_type="page", title="Home")
    )
    report.assets.append(
        DiscoveredUrl(url=f"{root}/style.css", source="crawl", depth=0, url_type="asset")
    )
    return report


def test_initialize_project_creates_structure(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    assert project.discovery_dir.exists()
    assert project.analysis_dir.exists()
    assert project.reports_dir.exists()
    metadata = (project.root_path / "metadata.json").read_text()
    assert "example.com" in metadata


def test_save_url_inventory_updates_metadata(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    report = _build_report("https://example.com")
    path = save_url_inventory(project, report)
    assert Path(path).exists()
    metadata = (project.metadata_file).read_text()
    assert '"pages": 1' in metadata


def test_list_projects_and_cleanup(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    save_url_inventory(project, _build_report("https://example.com"))
    summaries = list_projects(tmp_path)
    assert len(summaries) == 1
    assert summaries[0].pages == 1
    archive_path = cleanup_project(project.root_path, archive=True)
    assert archive_path is not None
    assert archive_path.exists()
    cleanup_project(archive_path)
    assert not archive_path.exists()
