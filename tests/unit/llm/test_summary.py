import asyncio
from pathlib import Path

from legacy_web_mcp.analysis.page_analysis import PageAnalysis, ElementSummary, FunctionalitySummary, AccessibilityNode, FrameworkDetection, CssSummary, PerformanceSummary
from legacy_web_mcp.llm.client import LLMResponse, LLMRequest
from legacy_web_mcp.llm.summary import ContentSummary, summarize_content


class StubLLMClient:
    def __init__(self, content: str) -> None:
        self.content = content

    async def generate(self, request: LLMRequest, *, preferred=None):
        return LLMResponse(provider="stub", model=request.model, content=self.content, tokens_used=20, cost_usd=0.002)


def _page(tmp_path: Path) -> PageAnalysis:
    analysis_path = tmp_path / "analysis.json"
    analysis_path.write_text("{}")
    return PageAnalysis(
        url="https://example.com/",
        title="Example",
        text_length=600,
        element_summary=ElementSummary(total=50, forms=1, inputs=1, buttons=1, links=10),
        functionality=FunctionalitySummary(categories=["form", "content"]),
        accessibility_outline=[AccessibilityNode(role="heading", label="title", level=1)],
        frameworks=FrameworkDetection(react=True),
        css=CssSummary(stylesheets=1, inline_styles=0, has_media_queries=False, responsive_meta=True),
        performance=PerformanceSummary(load_seconds=1.2, network_events=2, total_transfer_bytes=1024),
        generated_at="2025-01-01T00:00:00Z",
        analysis_path=analysis_path,
    )


def test_summarize_content_parses_json(tmp_path: Path) -> None:
    client = StubLLMClient(
        "{\"purpose\": \"Collect leads\", \"target_users\": \"Customers\", \"business_context\": \"Marketing\", \"user_journey\": \"From landing to submit\", \"navigation_role\": \"entry\", \"business_logic\": \"Validates form\", \"confidence\": 0.8}"
    )
    summary = asyncio.run(summarize_content(_page(tmp_path), llm_client=client))
    assert isinstance(summary, ContentSummary)
    assert summary.purpose == "Collect leads"
    assert summary.confidence == 0.8
    assert summary.quality_score > 0.5
    assert "confidence" not in " ".join(summary.validation_issues)
    assert summary.debug is not None
    assert summary.context_highlights


def test_summarize_content_missing_confidence_uses_heuristic(tmp_path: Path) -> None:
    client = StubLLMClient(
        "{\"purpose\": \"Collect\", \"target_users\": \"Users\", \"business_context\": \"Biz\", \"user_journey\": \"Journey\", \"navigation_role\": \"nav\", \"business_logic\": \"Logic\"}"
    )
    summary = asyncio.run(summarize_content(_page(tmp_path), llm_client=client))
    assert 0.5 <= summary.confidence <= 0.9
    assert any("confidence" in issue for issue in summary.validation_issues)
    assert summary.quality_score > 0.0
