#!/usr/bin/env python
"""Core logic for Step 1: Content Summarization Analysis."""

from __future__ import annotations

import json
from typing import Any

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
            # Create a structured LLM request for JSON parsing
            from legacy_web_mcp.llm.models import LLMMessage, LLMRequest, LLMRequestType, LLMRole
            
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=CONTENT_SUMMARY_SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=prompt),
            ]
            
            request = LLMRequest(
                messages=messages,
                request_type=LLMRequestType.CONTENT_SUMMARY,
                metadata={"step": "step1", "model_config_key": "step1_model"}
            )
            
            # Use the LLM engine to get a structured JSON response via chat completion
            response = await self.llm_engine.chat_completion(
                request=request,
                page_url=page_analysis_data.url
            )
            
            # Parse the JSON response content
            try:
                # Try to extract JSON from the response content
                content = response.content.strip()
                
                # Log the raw content for debugging
                _logger.debug("Raw LLM response content", 
                            content=content[:200] + "..." if len(content) > 200 else content)
                
                # Look for JSON block (handles cases where response might have markdown)
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
                _logger.debug("Parsed JSON summary", summary_json=summary_json)
                
                # Normalize field names from LLM response to match ContentSummary model
                def normalize_field(json_data: dict[str, Any]) -> dict[str, Any]:
                    """Normalize field names from various LLM response formats."""
                    normalized = {}
                    
                    # Convert all keys to lowercase for case-insensitive matching
                    lowercase_data = {k.lower(): v for k, v in json_data.items()}
                    
                    # Map common variations in field names - using lowercase versions
                    field_mappings = {
                        'purpose': ['purpose', 'primary_purpose', 'primary purpose',
                                   'main_purpose', 'main purpose'],
                        'user_context': ['user_context', 'user context', 'target_users',
                                         'target users', 'user_type', 'user type'],
                        'business_logic': ['business_logic', 'business logic', 'core_logic',
                                          'core logic', 'business_rules', 'business rules',
                                          'functionality'],
                        'navigation_role': ['navigation_role', 'navigation role', 'site_role',
                                           'site role', 'page_role', 'page role']
                    }
                    
                    for target_field, possible_sources in field_mappings.items():
                        for source in possible_sources:
                            if source in lowercase_data:
                                normalized[target_field] = lowercase_data[source]
                                break
                        else:
                            # If none of the sources found, use field name directly if present
                            if target_field in json_data:
                                normalized[target_field] = json_data[target_field]
                            elif target_field in lowercase_data:
                                normalized[target_field] = lowercase_data[target_field]
                    
                    # Copy other fields if they exist
                    if 'confidence_score' in json_data:
                        normalized['confidence_score'] = json_data['confidence_score']
                    elif 'confidence_score' in lowercase_data:
                        normalized['confidence_score'] = lowercase_data['confidence_score']
                    
                    return normalized
                
                # Normalize the JSON response
                normalized_json = normalize_field(summary_json)
                summary_json = normalized_json
                
                # Ensure confidence_score is present, default to 0.0
                if "confidence_score" not in summary_json:
                    summary_json["confidence_score"] = 0.0
            except json.JSONDecodeError as e:
                _logger.warning("Failed to parse JSON response, trying raw content", error=str(e))
                summary_json = {"purpose": content, "user_context": "", 
                                "business_logic": "", "navigation_role": content,
                                "confidence_score": 0.0}

            # Validate and create ContentSummary instance
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
