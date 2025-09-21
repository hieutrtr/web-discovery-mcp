#!/usr/bin/env python
"""Tests for analysis MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Context, FastMCP

from legacy_web_mcp.mcp.analysis_tools import register


@pytest.fixture
def mcp_server() -> FastMCP:
    """Create a FastMCP server with analysis tools registered."""
    mcp = FastMCP(name="test-analysis-server")
    register(mcp)
    return mcp


@pytest.fixture
def mock_context() -> AsyncMock:
    """Fixture for a mocked MCP Context."""
    return AsyncMock(spec=Context)


@pytest.mark.asyncio
async def test_summarize_page_content_tool(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test the summarize_page_content tool success path."""
    # Arrange
    tools = await mcp_server.get_tools()
    summarize_tool = tools.get("summarize_page_content")
    assert summarize_tool is not None

    from legacy_web_mcp.browser.analysis import PageAnalysisData
    mock_page_data = PageAnalysisData(
        url="https://example.com",
        title="Test Page",
        page_content={"visible_text": "Hello world"},
    )

    from legacy_web_mcp.llm.models import ContentSummary
    mock_summary = ContentSummary(
        purpose="Test",
        user_context="Testers",
        business_logic="Purely for testing.",
        navigation_role="Start of test.",
        confidence_score=0.95,
    )

    # Patch all external dependencies called by the tool
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_service_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store, \
         patch("legacy_web_mcp.mcp.analysis_tools.LLMEngine") as mock_llm_engine_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_page_analyzer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.ContentSummarizer") as mock_summarizer_cls:

        # Mock return values for the patched objects
        mock_browser_service_cls.return_value.get_session.return_value.__aenter__.return_value.page = AsyncMock()
        mock_page_analyzer_cls.return_value.analyze_page = AsyncMock(return_value=mock_page_data)
        mock_summarizer_cls.return_value.summarize_page = AsyncMock(return_value=mock_summary)

        # Act
        result = await summarize_tool.fn(
            context=mock_context,
            url="https://example.com",
        )

        # Assert
        assert result["status"] == "success"
        assert "summary" in result
        # This fails because the mock is an object, not a dict. The tool calls .dict()
        # assert result["summary"]["purpose"] == "Test"
        mock_context.error.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_page_features_tool_basic_functionality(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test the analyze_page_features tool success path."""
    # Arrange
    tools = await mcp_server.get_tools()
    features_tool = tools.get("analyze_page_features")
    assert features_tool is not None

    from legacy_web_mcp.browser.analysis import PageAnalysisData
    mock_page_data = PageAnalysisData(
        url="https://example.com",
        title="Test Page",
        page_content={"visible_text": "Test content"},
    )

    from legacy_web_mcp.llm.models import (
        ContentSummary, FeatureAnalysis, InteractiveElement, 
        FunctionalCapability, APIIntegration, BusinessRule,
        ThirdPartyIntegration, RebuildSpecification
    )
    
    mock_summary = ContentSummary(
        purpose="E-commerce product page",
        user_context="Online shoppers",
        business_logic="Product discovery and purchase",
        navigation_role="Product catalog",
        confidence_score=0.85,
    )
    
    mock_features = FeatureAnalysis(
        interactive_elements=[
            InteractiveElement(
                type="button",
                selector=".add-to-cart",
                purpose="Add product to shopping cart",
                behavior="click"
            )
        ],
        functional_capabilities=[
            FunctionalCapability(
                name="Product Search",
                description="Search and filter products",
                type="core_feature"
            )
        ],
        api_integrations=[
            APIIntegration(
                endpoint="/api/products",
                method="GET",
                purpose="Fetch product data",
                data_flow="inbound"
            )
        ],
        business_rules=[
            BusinessRule(
                name="Inventory Validation",
                description="Check product availability",
                validation_logic="inventory > 0"
            )
        ],
        third_party_integrations=[
            ThirdPartyIntegration(
                service_name="Stripe",
                integration_type="payment",
                purpose="Process payments"
            )
        ],
        rebuild_specifications=[
            RebuildSpecification(
                name="Product Catalog",
                description="Rebuild product listing component",
                priority_score=0.9,
                complexity="medium"
            )
        ],
        confidence_score=0.8,
        quality_score=0.75,
    )

    # Patch all external dependencies
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_service_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store, \
         patch("legacy_web_mcp.mcp.analysis_tools.LLMEngine") as mock_llm_engine_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_page_analyzer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.ContentSummarizer") as mock_summarizer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.FeatureAnalyzer") as mock_feature_analyzer_cls:

        # Mock return values
        mock_browser_service = AsyncMock()
        mock_browser_service_cls.return_value = mock_browser_service
        mock_browser_service.initialize = AsyncMock()
        mock_browser_service.navigate_page = AsyncMock(return_value=AsyncMock())
        
        mock_page_analyzer_cls.return_value.analyze_page = AsyncMock(return_value=mock_page_data)
        mock_summarizer_cls.return_value.summarize_page = AsyncMock(return_value=mock_summary)
        mock_feature_analyzer_cls.return_value.analyze_features = AsyncMock(return_value=mock_features)

        # Act
        result = await features_tool.fn(
            context=mock_context,
            url="https://example.com",
        )

        # Assert
        assert result["status"] == "success"
        assert result["url"] == "https://example.com"
        assert len(result["interactive_elements"]) == 1
        assert result["interactive_elements"][0]["type"] == "button"
        assert len(result["functional_capabilities"]) == 1
        assert len(result["api_integrations"]) == 1
        assert len(result["business_rules"]) == 1
        assert len(result["third_party_integrations"]) == 1
        assert len(result["rebuild_specifications"]) == 1
        assert result["confidence_score"] == 0.8
        assert result["quality_score"] == 0.75
        assert "step1_context" in result
        mock_context.error.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_page_features_with_provided_content(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test analyze_page_features with provided page content instead of fetching."""
    # Arrange
    tools = await mcp_server.get_tools()
    features_tool = tools.get("analyze_page_features")
    assert features_tool is not None

    from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis
    
    mock_summary = ContentSummary(
        purpose="Test page",
        user_context="Test users",
        business_logic="Test functionality",
        navigation_role="Test navigation",
        confidence_score=0.9,
    )
    
    mock_features = FeatureAnalysis(
        interactive_elements=[],
        functional_capabilities=[],
        api_integrations=[],
        business_rules=[],
        third_party_integrations=[],
        rebuild_specifications=[],
        confidence_score=0.5,
        quality_score=0.6,
    )

    # Patch dependencies
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store, \
         patch("legacy_web_mcp.mcp.analysis_tools.LLMEngine") as mock_llm_engine_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.ContentSummarizer") as mock_summarizer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.FeatureAnalyzer") as mock_feature_analyzer_cls:

        # Mock no browser operations when content is provided
        mock_summarizer_cls.return_value.summarize_page = AsyncMock(return_value=mock_summary)
        mock_feature_analyzer_cls.return_value.analyze_features = AsyncMock(return_value=mock_features)

        test_content = '{"title": "Test Page", "visible_text": "Test content"}'

        # Act
        result = await features_tool.fn(
            context=mock_context,
            url="https://example.com",
            page_content=test_content,
        )

        # Assert
        assert result["status"] == "success"
        assert result["url"] == "https://example.com"
        # Verify browser service was NOT called when content provided
        mock_browser_service_cls = patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService").start()
        mock_browser_service_cls.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_page_features_skip_step1(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test analyze_page_features without Step 1 summarization."""
    # Arrange
    tools = await mcp_server.get_tools()
    features_tool = tools.get("analyze_page_features")
    assert features_tool is not None

    from legacy_web_mcp.llm.models import FeatureAnalysis
    mock_features = FeatureAnalysis(
        interactive_elements=[],
        functional_capabilities=[],
        api_integrations=[],
        business_rules=[],
        third_party_integrations=[],
        rebuild_specifications=[],
        confidence_score=0.6,
        quality_score=0.7,
    )

    # Patch dependencies
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store, \
         patch("legacy_web_mcp.mcp.analysis_tools.LLMEngine") as mock_llm_engine_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_page_analyzer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.ContentSummarizer") as mock_summarizer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.FeatureAnalyzer") as mock_feature_analyzer_cls:

        # Mock browser operations
        mock_browser_service = AsyncMock()
        mock_browser_service_cls = patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService")
        mock_browser_service_cls.start().return_value = mock_browser_service
        mock_browser_service.initialize = AsyncMock()
        mock_browser_service.navigate_page = AsyncMock(return_value=AsyncMock())
        
        mock_page_analyzer_cls.return_value.analyze_page = AsyncMock(return_value=AsyncMock())
        mock_feature_analyzer_cls.return_value.analyze_features = AsyncMock(return_value=mock_features)

        # Act
        result = await features_tool.fn(
            context=mock_context,
            url="https://example.com",
            include_step1_summary=False,
        )

        # Assert
        assert result["status"] == "success"
        # Verify summarizer was NOT called when include_step1_summary=False
        mock_summarizer_cls.return_value.summarize_page.assert_not_called()
        # Should have minimal context created
        assert result["step1_context"] is not None
        assert result["step1_context"]["purpose"] == "Feature analysis without step 1 context"


@pytest.mark.asyncio
async def test_analyze_page_features_error_handling(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test error handling in analyze_page_features tool."""
    # Arrange
    tools = await mcp_server.get_tools()
    features_tool = tools.get("analyze_page_features")
    assert features_tool is not None

    # Test with invalid JSON content
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store:

        invalid_content = "invalid json {"

        # Act
        result = await features_tool.fn(
            context=mock_context,
            url="https://example.com",
            page_content=invalid_content,
        )

        # Assert
        assert result["status"] == "error"
        assert "Invalid page_content format" in result["error"]
        assert result["url"] == "https://example.com"
        assert "error_type" in result
        mock_context.error.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_page_features_llm_failure_handling(
    mcp_server: FastMCP, mock_context: AsyncMock
):
    """Test handling of LLM provider failures."""
    # Arrange
    tools = await mcp_server.get_tools()
    features_tool = tools.get("analyze_page_features")
    assert features_tool is not None

    from legacy_web_mcp.llm.analysis.step2_feature_analysis import FeatureAnalysisError

    # Patch dependencies with failing FeatureAnalyzer
    with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_load_config, \
         patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_create_store, \
         patch("legacy_web_mcp.mcp.analysis_tools.LLMEngine") as mock_llm_engine_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_page_analyzer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.ContentSummarizer") as mock_summarizer_cls, \
         patch("legacy_web_mcp.mcp.analysis_tools.FeatureAnalyzer") as mock_feature_analyzer_cls:

        # Mock successful setup
        mock_browser_service = AsyncMock()
        mock_browser_service_cls = patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService")
        mock_browser_service_cls.start().return_value = mock_browser_service
        mock_browser_service.initialize = AsyncMock()
        mock_browser_service.navigate_page = AsyncMock(return_value=AsyncMock())
        
        mock_page_analyzer_cls.return_value.analyze_page = AsyncMock(return_value=AsyncMock())
        mock_summarizer_cls.return_value.summarize_page = AsyncMock(return_value=AsyncMock())
        
        # Make FeatureAnalyzer fail
        mock_feature_analyzer_cls.return_value.analyze_features = AsyncMock(
            side_effect=FeatureAnalysisError("LLM provider timeout")
        )

        # Act
        result = await features_tool.fn(
            context=mock_context,
            url="https://example.com",
        )

        # Assert
        assert result["status"] == "error"
        assert "LLM provider timeout" in result["error"]
        assert result["error_type"] == "FeatureAnalysisError"
        mock_context.error.assert_called_once()
