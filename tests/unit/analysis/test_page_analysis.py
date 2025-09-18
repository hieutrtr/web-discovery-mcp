from pathlib import Path

from legacy_web_mcp.analysis import collect_page_analysis
from legacy_web_mcp.config import Settings
from legacy_web_mcp.network import NetworkTrafficRecorder
from legacy_web_mcp.storage import initialize_project


def test_collect_page_analysis_outputs_json(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    html = """
    <html>
      <head><title>Example</title><link rel='stylesheet' href='style.css'><meta name='viewport' content='width=device-width'></head>
      <body>
        <nav><a href='/'>Home</a><a href='/docs'>Docs</a></nav>
        <form id='contact'><input type='text' name='name'><button type='submit'>Send</button></form>
        <script>window.ReactDOM.render()</script>
      </body>
    </html>
    """
    text = "Example form page"
    nav_meta = {"title": "Example", "load_seconds": 1.23}
    recorder = NetworkTrafficRecorder("https://example.com/")
    recorder.record(url="https://example.com/api", method="GET", status=200, body_size=512)
    report = recorder.export()

    analysis = collect_page_analysis(
        project=project,
        page_url="https://example.com/",
        html=html,
        text_content=text,
        navigation_metadata=nav_meta,
        network_report=report,
    )

    assert analysis.analysis_path.exists()
    content = analysis.analysis_path.read_text()
    assert '"frameworks"' in content
    assert analysis.element_summary.forms == 1
    assert analysis.performance.network_events == 1
    assert analysis.performance.total_transfer_bytes == 512
    assert '"form"' in content
