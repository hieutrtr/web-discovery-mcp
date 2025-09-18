import json
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.progress import ProgressTracker
from legacy_web_mcp.storage import initialize_project


def test_progress_tracker_records_states(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    tracker = ProgressTracker(project)
    tracker.register_urls(["https://example.com/"])
    tracker.mark_analyzing("https://example.com/")
    tracker.mark_completed("https://example.com/", duration_seconds=1.25)

    snapshot = tracker.snapshot()
    assert snapshot.completed == 1
    assert snapshot.average_seconds is not None
    assert snapshot.percentage == 100.0

    snapshot_path = project.docs_progress_dir / ProgressTracker.SNAPSHOT_FILE
    assert snapshot_path.exists()
    snapshot_payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot_payload["completed"] == 1


def test_progress_tracker_restore(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    tracker = ProgressTracker(project)
    tracker.register_urls(["https://example.com/"])
    tracker.mark_analyzing("https://example.com/")
    tracker_state = tracker.to_state()

    restored = ProgressTracker(project)
    restored.register_urls(["https://example.com/"])
    restored.restore({"pages": tracker_state.get("pages", {}), "current_url": "https://example.com/"})
    snapshot = restored.snapshot()
    assert snapshot.analyzing == 1
