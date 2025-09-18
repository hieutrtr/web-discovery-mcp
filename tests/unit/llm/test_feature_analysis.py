import asyncio
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
from legacy_web_mcp.interaction import InteractionAction
from legacy_web_mcp.llm.client import LLMRequest, LLMResponse
from legacy_web_mcp.llm.feature_analysis import analyse_features
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.network import NetworkEvent, NetworkTrafficReport


class StubLLMClient:
    def __init__(self, content: str) -> None:
        self.content = content

    async def generate(self, request: LLMRequest, *, preferred=None) -> LLMResponse:
        return LLMResponse(
            provider="stub",
            model=request.model,
            content=self.content,
            tokens_used=30,
            cost_usd=0.003,
        )


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


def _summary() -> ContentSummary:
    return ContentSummary(
        page_url="https://example.com/",
        purpose="Capture leads",
        target_users="Customers",
        business_context="Marketing",
        user_journey="Landing -> Form",
        navigation_role="entry",
        business_logic="Validates inputs",
        confidence=0.8,
        processing_seconds=0.4,
    )


def _network() -> NetworkTrafficReport:
    report = NetworkTrafficReport(page_url="https://example.com/")
    report.add_event(
        NetworkEvent(
            url="https://example.com/api/leads",
            method="POST",
            status=200,
            resource_type="api",
        )
    )
    return report


def test_analyse_features_parses_response(tmp_path: Path) -> None:
    llm_content = (
        '{"interactive_elements": [{"selector": "form#lead", "purpose": "capture", "details": "collect"}],'
        ' "functional_capabilities": ["create"],'
        ' "api_integrations": [{"url": "https://example.com/api/leads", "method": "POST", "description": "submit"}],'
        ' "business_rules": ["Validate email"],'
        ' "rebuild_requirements": [{"priority": "high", "requirement": "Implement validations", "dependencies": ["auth"]}],'
        ' "integration_points": ["CRM"]}'
    )
    client = StubLLMClient(llm_content)
    interactions = [InteractionAction(action_type="click", selector="button#submit", description="Submit")]
    analysis = asyncio.run(
        analyse_features(
            _page(tmp_path),
            _summary(),
            interactions,
            _network(),
            llm_client=client,
        )
    )
    assert analysis.interactive_elements[0].selector == "form#lead"
    assert analysis.rebuild_requirements[0].priority == "high"
    assert analysis.api_integrations
