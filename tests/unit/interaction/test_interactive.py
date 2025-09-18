import asyncio
from collections import deque
from pathlib import Path
from typing import Any, Sequence

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
from legacy_web_mcp.interaction import (
    InteractiveAnalysisSession,
    InteractiveConfig,
    InteractivePageContext,
)
from legacy_web_mcp.interaction.interactive import InteractiveIO
from legacy_web_mcp.interaction.actions import InteractionAction
from legacy_web_mcp.llm.client import LLMClient
from legacy_web_mcp.llm.feature_analysis import FeatureAnalysis, InteractiveElement, RebuildRequirement
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.progress import CheckpointManager, ProgressTracker
from legacy_web_mcp.storage import initialize_project


class StubIO(InteractiveIO):
    def __init__(
        self,
        *,
        choices: Sequence[int],
        confirmations: Sequence[bool],
        inputs: Sequence[str] | None = None,
    ) -> None:
        self._choices = deque(choices)
        self._confirmations = deque(confirmations)
        self._inputs = deque(inputs or [])
        self.messages: list[str] = []

    async def choose(self, prompt: str, options: Sequence[str]) -> int:
        return self._choices.popleft()

    async def confirm(self, prompt: str) -> bool:
        return self._confirmations.popleft()

    async def input_text(self, prompt: str, *, default: str = "") -> str:
        return self._inputs.popleft() if self._inputs else default

    async def notify(self, message: str) -> None:
        self.messages.append(message)


async def _page_loader(_: str, page: PageAnalysis) -> InteractivePageContext:
    return InteractivePageContext(page=page, interactions=[], network_report=_NetworkReport())


class _NetworkReport:
    events: list[Any] = []


def _build_page(tmp_path: Path, url: str) -> PageAnalysis:
    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text("{}", encoding="utf-8")
    return PageAnalysis(
        url=url,
        title="Example",
        text_length=500,
        element_summary=ElementSummary(total=50, forms=1, inputs=3, buttons=2, links=5),
        functionality=FunctionalitySummary(categories=["form", "navigation"]),
        accessibility_outline=[AccessibilityNode(role="heading", label="title", level=1)],
        frameworks=FrameworkDetection(react=True),
        css=CssSummary(stylesheets=1, inline_styles=0, has_media_queries=True, responsive_meta=True),
        performance=PerformanceSummary(load_seconds=1.1, network_events=2, total_transfer_bytes=1024),
        generated_at="2025-01-01T00:00:00Z",
        analysis_path=analysis_path,
    )


async def _summary_runner(page: PageAnalysis, client: LLMClient, model_alias: str) -> ContentSummary:
    return ContentSummary(
        page_url=page.url,
        purpose=f"Purpose via {model_alias}",
        target_users="Users",
        business_context="Context",
        user_journey="Journey",
        navigation_role="Role",
        business_logic="Logic",
        confidence=0.8,
        processing_seconds=0.5,
        quality_score=0.9,
        validation_issues=(),
        context_highlights=("Purpose",),
    )


async def _feature_runner(
    page: PageAnalysis,
    summary: ContentSummary,
    interactions: Sequence[InteractionAction],
    network_report: Any,
    client: LLMClient,
    model_alias: str,
) -> FeatureAnalysis:
    return FeatureAnalysis(
        page_url=page.url,
        interactive_elements=[
            InteractiveElement(selector="button#submit", purpose="submit", details="details")
        ],
        functional_capabilities=["Capture"],
        api_integrations=[],
        business_rules=["Validate"],
        rebuild_requirements=[
            RebuildRequirement(priority="high", requirement="Implement", dependencies=[], score=0.8, rationale="Aligned")
        ],
        integration_points=[],
        processing_seconds=1.0,
        quality_score=0.95,
        consistency_warnings=(),
        context_links=(summary.purpose,),
        debug=None,
    )


def test_interactive_session_executes_and_updates_docs(tmp_path: Path) -> None:
    settings = Settings(analysis_output_root=str(tmp_path))
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    tracker = ProgressTracker(project)
    checkpoints = CheckpointManager(project)
    documentation = DocumentationGenerator(project)
    client = LLMClient(settings=settings)
    page = _build_page(tmp_path, "https://example.com/")

    async def loader(url: str) -> InteractivePageContext:
        return await _page_loader(url, page)

    io = StubIO(choices=[0, 0, 0, 1], confirmations=[True])
    # choices: analyze now, approve summary, approve feature, skip second page
    session = InteractiveAnalysisSession(
        project=project,
        urls=["https://example.com/", "https://example.com/about"],
        page_loader=loader,
        summary_runner=_summary_runner,
        feature_runner=_feature_runner,
        llm_client=client,
        io=io,
        checkpoints=checkpoints,
        progress=tracker,
        documentation=documentation,
        config=InteractiveConfig(step1_model="step1", step2_model="step2", timeout_seconds=45.0),
    )

    result = asyncio.run(session.run())

    assert "https://example.com/" in result.completed
    assert "https://example.com/about" in result.skipped
    assert result.snapshot.completed == 1
    assert result.checkpoint_path is not None
    assert Path(result.checkpoint_path).exists()

    page_md = project.docs_pages_dir / "page-example.com.md"
    assert page_md.exists()
    report_md = project.docs_master_report
    assert "Legacy Web Analysis Report" in report_md.read_text(encoding="utf-8")

    # ensure cost notification executed
    assert any("Estimated cost" in message for message in io.messages)
