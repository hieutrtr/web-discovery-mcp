#!/usr/bin/env python
"""Tests for the Step 1 Content Summarizer."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from legacy_web_mcp.browser.analysis import DOMStructureAnalysis, PageAnalysisData
from legacy_web_mcp.llm.analysis.step1_summarize import (
    ContentSummarizationError,
    ContentSummarizer,
)
from legacy_web_mcp.llm.models import ContentSummary


@pytest.fixture
def mock_llm_engine() -> AsyncMock:
    """Fixture for a mocked LLMEngine."""
    return AsyncMock()


@pytest.fixture
def sample_page_analysis_data() -> PageAnalysisData:
    """Fixture for sample PageAnalysisData."""
    return PageAnalysisData(
        url="https://example.com",
        title="Test Page",
        html_content="<html><body><h1>Welcome</h1></body></html>",
        visible_text="Welcome",
        dom_structure=DOMStructureAnalysis(
            total_elements=10,
            interactive_elements_count=2,
            form_count=1,
            link_count=5,
        ),
        analysis_duration=1.0
    )


@pytest.mark.asyncio
async def test_summarize_page_success(
    mock_llm_engine: AsyncMock, sample_page_analysis_data: PageAnalysisData
):
    """Test successful page summarization."""
    # Arrange
    summarizer = ContentSummarizer(llm_engine=mock_llm_engine)
    mock_response = AsyncMock()
    mock_response.content = """{
        "purpose": "User Login",
        "user_context": "Registered users",
        "business_logic": "Allows users to authenticate.",
        "navigation_role": "Entry point for secure area."
    }"""
    mock_llm_engine.chat_completion.return_value = mock_response

    # Act
    result = await summarizer.summarize_page(sample_page_analysis_data)

    # Assert
    assert isinstance(result, ContentSummary)
    assert result.purpose == "User Login"
    assert result.confidence_score > 0.6 # Should be high for a complete response
    mock_llm_engine.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_summarize_page_llm_failure(
    mock_llm_engine: AsyncMock, sample_page_analysis_data: PageAnalysisData
):
    """Test that a failure in the LLM engine propagates correctly."""
    # Arrange
    summarizer = ContentSummarizer(llm_engine=mock_llm_engine)
    mock_llm_engine.chat_completion.side_effect = Exception("LLM API Error")

    # Act & Assert
    with pytest.raises(ContentSummarizationError, match="Failed to summarize content"):
        await summarizer.summarize_page(sample_page_analysis_data)


@pytest.mark.asyncio
async def test_summarize_page_bad_response_type(
    mock_llm_engine: AsyncMock, sample_page_analysis_data: PageAnalysisData
):
    """Test handling of an unexpected response type from the LLM engine."""
    # Arrange
    summarizer = ContentSummarizer(llm_engine=mock_llm_engine)
    mock_response = AsyncMock()
    mock_response.content = "just a string, not JSON"
    mock_llm_engine.chat_completion.return_value = mock_response

    # Act & Assert
    with pytest.raises(ContentSummarizationError):
        await summarizer.summarize_page(sample_page_analysis_data)


@pytest.mark.asyncio
async def test_summarize_page_with_different_field_names(
    mock_llm_engine: AsyncMock, sample_page_analysis_data: PageAnalysisData
):
    """Test handling of LLM responses with different field naming conventions."""
    # Arrange
    summarizer = ContentSummarizer(llm_engine=mock_llm_engine)
    mock_response = AsyncMock()
    
    # Test with alternative field names that the normalization should handle
    mock_response.content = """{
        "Primary Purpose": "Developer Tools Hub",
        "Target Users": "Software developers",
        "Business Logic": "Aggregates AI tools for developers",
        "Page Role": "Navigation and access point",
        "confidence_score": 0.9
    }"""
    mock_llm_engine.chat_completion.return_value = mock_response

    # Act
    result = await summarizer.summarize_page(sample_page_analysis_data)

    assert isinstance(result, ContentSummary)
    assert result.purpose == "Developer Tools Hub"
    assert result.user_context == "Software developers"
    assert result.business_logic == "Aggregates AI tools for developers"
    assert result.navigation_role == "Navigation and access point"
    # Note: confidence_score is recalculated by _calculate_confidence, should be high for complete response
    assert result.confidence_score > 0.8


    """Test the confidence score calculation logic."""
    summarizer = ContentSummarizer(llm_engine=AsyncMock())

    # High confidence case
    summary_good = ContentSummary(
        purpose="This is a very clear and well-defined purpose.",
        user_context="The target users are clearly identified.",
        business_logic="The business logic is explained in great detail with many words.",
        navigation_role="This is a critical step in the user journey.",
        confidence_score=0.0
    )
    assert summarizer._calculate_confidence(summary_good) == 1.0

    # Low confidence case
    summary_bad = ContentSummary(
        purpose="",
        user_context="",
        business_logic="",
        navigation_role="",
        confidence_score=0.0
    )
    assert summarizer._calculate_confidence(summary_bad) <= 0.21

    # Medium confidence case
    summary_medium = ContentSummary(
        purpose="A good purpose.",
        user_context="Users.", # too short
        business_logic="Some logic here.",
        navigation_role="", # empty
        confidence_score=0.0
    )
    score = summarizer._calculate_confidence(summary_medium)
    assert 0.3 < score < 0.7
