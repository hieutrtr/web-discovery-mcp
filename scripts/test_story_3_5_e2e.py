import asyncio
from legacy_web_mcp.mcp.orchestration_tools import LegacyAnalysisOrchestrator, AnalysisMode, CostPriority
from legacy_web_mcp.config.loader import load_configuration
from unittest.mock import AsyncMock

async def main():
    """Run the analysis."""
    config = load_configuration()
    orchestrator = LegacyAnalysisOrchestrator(config, "httpbin-test")
    mock_context = AsyncMock()

    result = await orchestrator.discover_and_analyze_site(
        context=mock_context,
        url="https://httpbin.org",
        analysis_mode=AnalysisMode.RECOMMENDED,
        max_pages=5,
        include_step2=True,
        cost_priority=CostPriority.BALANCED,
    )

    print(result)

if __name__ == "__main__":
    asyncio.run(main())
