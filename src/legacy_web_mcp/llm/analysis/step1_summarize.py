#!/usr/bin/env python
"""Core logic for Step 1: Content Summarization Analysis."""

from __future__ import annotations

import json
from typing import Any

import structlog

from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.llm.models import ContentSummary, LLMMessage, LLMRequest, LLMRequestType, LLMRole
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
        """Performs content summarization analysis for a single page with quality validation.

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
            # Create a structured LLM request for JSON parsing
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=CONTENT_SUMMARY_SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=prompt),
            ]
            
            request = LLMRequest(
                messages=messages,
                request_type=LLMRequestType.CONTENT_SUMMARY,
                metadata={"step": "step1", "model_config_key": "step1_model"}
            )
            
            # Use validation-enabled chat completion for quality assurance
            response, validation_result, quality_metrics = await self.llm_engine.chat_completion_with_validation(
                request=request,
                analysis_type="step1",
                page_url=page_analysis_data.url,
                quality_threshold=0.6  # Minimum acceptable quality
            )
            
            # Parse the validated JSON response
            try:
                content = response.content.strip()
                
                # Extract JSON from response (handles markdown formatting)
                if "```json" in content and "```" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    if json_end == -1:
                        json_end = len(content)
                    json_str = content[json_start:json_end].strip()
                elif content.startswith("{") and content.endswith("}"):
                    json_str = content
                else:
                    # Try to find JSON object in the content
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = content[json_start:json_end]
                    else:
                        raise ValueError("No valid JSON found in response")
                
                summary_json = json.loads(json_str)
                
                # Validate and create ContentSummary instance
                content_summary = ContentSummary(**summary_json)
                
                # Override confidence score with quality-adjusted value
                content_summary.confidence_score = min(
                    content_summary.confidence_score,
                    quality_metrics.overall_quality_score
                )
                
                # Log quality metrics for monitoring
                _logger.info(
                    "content_summarization_successful",
                    url=page_analysis_data.url,
                    quality_score=quality_metrics.overall_quality_score,
                    completeness_score=quality_metrics.completeness_score,
                    needs_manual_review=quality_metrics.needs_manual_review,
                    validation_errors=len(validation_result.errors),
                    validation_warnings=len(validation_result.warnings)
                )
                
                # Store quality metrics in metadata for later use
                if hasattr(content_summary, 'metadata'):
                    content_summary.metadata = content_summary.metadata or {}
                else:
                    content_summary.metadata = {}
                    
                content_summary.metadata.update({
                    'quality_metrics': quality_metrics.model_dump(),
                    'validation_result': validation_result.model_dump()
                })
                
                return content_summary

            except json.JSONDecodeError as e:
                _logger.error(
                    "content_summary_json_parse_failed",
                    url=page_analysis_data.url,
                    error=str(e),
                    response_content=response.content[:500] if response.content else None
                )
                raise ContentSummarizationError(
                    f"Failed to parse JSON response for {page_analysis_data.url}: {str(e)}"
                ) from e

        except Exception as e:
            _logger.error(
                "content_summarization_failed",
                url=page_analysis_data.url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ContentSummarizationError(
                f"Failed to summarize content for {page_analysis_data.url}: {str(e)}"
            ) from e

    def _calculate_confidence(self, summary: ContentSummary) -> float:
        """Calculates a confidence score based on the completeness of the summary.

        Args:
            summary: The ContentSummary object.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        score = 1.0
        
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
