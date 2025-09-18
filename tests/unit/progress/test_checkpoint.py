from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.progress import CheckpointManager
from legacy_web_mcp.storage import initialize_project


def test_checkpoint_manager_round_trip(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    manager = CheckpointManager(project, max_history=2)

    first = manager.write(["https://example.com/"], {"pages": {}}, None)
    assert first.exists()
    second = manager.write([], {"pages": {}}, None)
    assert second.exists()

    state = manager.load_latest()
    assert state is not None
    assert state.queue == []
    assert manager.latest_path is not None

    # Ensure max history enforcement
    third = manager.write([], {"pages": {}}, None)
    assert third.exists()
    retained = sorted(project.checkpoints_dir.glob("checkpoint-*.json"))
    assert len(retained) <= 2

    manager.prune(retain=1)
    retained_after_prune = sorted(project.checkpoints_dir.glob("checkpoint-*.json"))
    assert len(retained_after_prune) == 1
