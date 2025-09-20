#!/usr/bin/env python
"""Core logic for Step 1: Content Summarization Analysis."""

from __future__ import annotations

import structlog

from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.llm.models import ContentSummary
from legacy_web_mcp.llm.prompts.step1_summarize import (
    CONTENT_SUMMARY_SYSTEM_PROMPT,
    create_content_summary_prompt,
)

_logger = structlog.get_logger(__name__)


class ContentSummarizationError(Exception):
    """Custom exception for content summarization failures."""


class ContentSummarizer:
    """Orchestrates the Step 1 Content Summarization analysis."""

    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine

    async def summarize_page(
        self, page_analysis_data: PageAnalysisData
    ) -> ContentSummary:
        """Performs content summarization analysis for a single page.

        Args:
            page_analysis_data: The comprehensive analysis data collected from the page.

        Returns:
            A ContentSummary object with the analysis results.

        Raises:
            ContentSummarizationError: If the analysis fails after all retries.
        """
        _logger.info("Starting content summarization for page", url=page_analysis_data.url)

        # For Step 1, we primarily need the visible text and a summary of the DOM.
        dom_analysis = page_analysis_data.dom_analysis
        dom_summary = {
            "total_elements": dom_analysis.total_elements,
            "interactive_elements": dom_analysis.interactive_elements,
            "form_count": dom_analysis.form_elements,
            "link_count": dom_analysis.link_elements,
        }

        # Extract visible text from page_content
        page_content = page_analysis_data.page_content
        visible_text = page_content.get("visible_text", page_content.get("text_content", ""))

        prompt = create_content_summary_prompt(
            page_content=visible_text,
            dom_structure=dom_summary,
            url=page_analysis_data.url,
        )

        try:
            # Use the LLM engine to get a structured JSON response.
            # The engine is expected to handle model selection, retries, and validation.
            summary_json = await self.llm_engine.generate_json_response(
                system_prompt=CONTENT_SUMMARY_SYSTEM_PROMPT,
                user_prompt=prompt,
                model_config_key="step1_model",
                response_model=ContentSummary,
            )

            if not isinstance(summary_json, dict):
                 raise TypeError(f"Expected a dict from LLM engine, but got {type(summary_json)}")

            # The engine should have already validated against the Pydantic model,
            # but we can instantiate it here.
            content_summary = ContentSummary(**summary_json)

            # Compute confidence score
            content_summary.confidence_score = self._calculate_confidence(content_summary)

            _logger.info("Content summarization successful", url=page_analysis_data.url)
            return content_summary

        except Exception as e:
            _logger.error(
                "Content summarization failed",
                url=page_analysis_data.url,
                error=str(e),
            )
            raise ContentSummarizationError(
                f"Failed to summarize content for {page_analysis_data.url}"
            ) from e

    def _calculate_confidence(self, summary: ContentSummary) -> float:
        """Calculates a confidence score based on the completeness of the summary.

        Args:
            summary: The ContentSummary object.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        score = 1.0
        num_fields = 5
        
        # Penalize for empty or placeholder-like fields
        if not summary.purpose or len(summary.purpose.split()) < 2:
            score -= 0.2
        if not summary.user_context or len(summary.user_context.split()) < 2:
            score -= 0.2
        if not summary.business_logic or len(summary.business_logic.split()) < 3:
            score -= 0.2
        if not summary.navigation_role:
            score -= 0.2

        return max(0.1, score) # Ensure a minimum score
