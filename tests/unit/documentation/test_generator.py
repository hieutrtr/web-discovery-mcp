import json
from pathlib import Path

from legacy_web_mcp.analysis.page_analysis import (
    AccessibilityNode,
    CssSummary,
    ElementSummary,
    FunctionalitySummary,
    FrameworkDetection,
    PageAnalysis,
    PerformanceSummary,
)
from legacy_web_mcp.config import Settings
from legacy_web_mcp.documentation import DocumentationGenerator
from legacy_web_mcp.llm.feature_analysis import (
    APIIntegration,
    FeatureAnalysis,
    InteractiveElement,
    RebuildRequirement,
)
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.progress import ProgressTracker
from legacy_web_mcp.storage import initialize_project


def _page(tmp_path: Path) -> PageAnalysis:
    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text("{}", encoding="utf-8")
    return PageAnalysis(
        url="https://example.com/",
        title="Example",
        text_length=800,
        element_summary=ElementSummary(total=80, forms=2, inputs=5, buttons=3, links=15),
        functionality=FunctionalitySummary(categories=["form", "search"]),
        accessibility_outline=[AccessibilityNode(role="heading", label="title", level=1)],
        frameworks=FrameworkDetection(react=True),
        css=CssSummary(stylesheets=2, inline_styles=1, has_media_queries=True, responsive_meta=True),
        performance=PerformanceSummary(load_seconds=1.0, network_events=3, total_transfer_bytes=2048),
        generated_at="2025-01-01T00:00:00Z",
        analysis_path=analysis_path,
    )


def test_documentation_generator_creates_report(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    generator = DocumentationGenerator(project)

    page = _page(tmp_path)
    summary = ContentSummary(
        page_url=page.url,
        purpose="Capture leads",
        target_users="Customers",
        business_context="Marketing",
        user_journey="Landing -> Form",
        navigation_role="entry",
        business_logic="Validates inputs",
        confidence=0.8,
        processing_seconds=0.5,
        quality_score=0.9,
        validation_issues=(),
        context_highlights=("Capture leads",),
    )
    feature = FeatureAnalysis(
        page_url=page.url,
        interactive_elements=[
            InteractiveElement(selector="form#lead", purpose="capture", details="Collect lead data")
        ],
        functional_capabilities=["Lead capture"],
        api_integrations=[
            APIIntegration(url="https://example.com/api/leads", method="POST", description="Submit leads")
        ],
        business_rules=["Validate email format"],
        rebuild_requirements=[
            RebuildRequirement(
                priority="high",
                requirement="Implement email validation",
                dependencies=["auth"],
                score=0.9,
                rationale="Aligned with Step 1 context",
            )
        ],
        integration_points=["CRM"],
        processing_seconds=1.2,
        quality_score=0.92,
        consistency_warnings=("Requires CRM integration",),
        context_links=("Lead capture",),
        debug=None,
    )

    tracker = ProgressTracker(project)
    tracker.register_urls([page.url])
    tracker.mark_analyzing(page.url)
    tracker.mark_completed(page.url, duration_seconds=1.0)
    progress_snapshot = tracker.snapshot()

    generator.update_page(
        page=page,
        summary=summary,
        feature=feature,
        progress=progress_snapshot,
    )

    page_file = project.docs_pages_dir / "page-example.com.md"
    assert page_file.exists()
    contents = page_file.read_text(encoding="utf-8")
    assert "Page Analysis" in contents
    assert "API Integrations" in contents

    report_contents = project.docs_master_report.read_text(encoding="utf-8")
    assert "Legacy Web Analysis Report" in report_contents
    assert "Lead capture" in report_contents

    data_file = project.docs_web_dir / DocumentationGenerator.DATA_FILE
    data = json.loads(data_file.read_text(encoding="utf-8"))
    assert data["totals"]["pages"] == 1
