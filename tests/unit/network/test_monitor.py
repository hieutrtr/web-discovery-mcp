from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.network import NetworkTrafficRecorder, save_network_report
from legacy_web_mcp.storage import initialize_project


def test_network_recorder_classifies_and_saves(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)

    recorder = NetworkTrafficRecorder("https://example.com/")
    recorder.record(url="https://example.com/api/items", method="GET", status=200)
    recorder.record(url="https://example.com/static/app.js", method="GET", status=200)

    report = recorder.export()
    path = save_network_report(project, report)
    written = Path(path)
    assert written.exists()
    content = written.read_text()
    assert '"by_type"' in content
    assert '"api"' in content
    assert '"asset"' in content
