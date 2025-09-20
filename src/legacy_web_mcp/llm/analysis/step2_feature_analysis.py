#!/usr/bin/env python
"""Core logic for Step 2: Detailed Feature Analysis."""

from __future__ import annotations

import json
from typing import Any

import structlog

from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis
from legacy_web_mcp.llm.prompts.step2_feature_analysis import (
    FEATURE_ANALYSIS_SYSTEM_PROMPT,
    create_feature_analysis_prompt,
)

_logger = structlog.get_logger(__name__)


class FeatureAnalysisError(Exception):
    """Custom exception for feature analysis failures."""


class FeatureAnalyzer:
    """Orchestrates the Step 2 Feature Analysis analysis."""

    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine

    async def analyze_features(
        self, page_analysis_data: PageAnalysisData, step1_context: ContentSummary
    ) -> FeatureAnalysis:
        """Performs comprehensive feature analysis for a page.

        Args:
            page_analysis_data: The comprehensive analysis data collected from the page.
            step1_context: Results from Step 1 analysis providing business context.

        Returns:
            A FeatureAnalysis object with detailed technical findings.

        Raises:
            FeatureAnalysisError: If the analysis fails after all retries.
        """
        _logger.info("Starting feature analysis for page", url=page_analysis_data.url)

        # Extract interactive elements from the page data
        interactive_elements = self._extract_interactive_elements(page_analysis_data)

        # Extract network requests from network monitoring
        network_requests = self._extract_network_requests(page_analysis_data)

        prompt = create_feature_analysis_prompt(
            page_content=page_analysis_data.page_content,
            step1_context=step1_context,
            interactive_elements=interactive_elements,
            network_requests=network_requests,
            url=page_analysis_data.url,
        )

        try:
            # Create a structured LLM request for JSON parsing
            from legacy_web_mcp.llm.models import LLMMessage, LLMRequest, LLMRequestType, LLMRole

            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=FEATURE_ANALYSIS_SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=prompt),
            ]

            request = LLMRequest(
                messages=messages,
                request_type=LLMRequestType.FEATURE_ANALYSIS,
                metadata={"step": "step2", "model_config_key": "step2_model"},
            )

            # Use the LLM engine to get a structured JSON response via chat completion
            response = await self.llm_engine.chat_completion(
                request=request, page_url=page_analysis_data.url
            )

            # Parse the JSON response content
            analysis_json = self._parse_json_response(response.content)

            # Convert JSON to FeatureAnalysis model
            feature_analysis = self._json_to_feature_analysis(analysis_json)

            # Calculate confidence and quality scores
            feature_analysis.confidence_score = self._calculate_confidence(feature_analysis)
            feature_analysis.quality_score = self._calculate_quality(
                feature_analysis, step1_context
            )

            _logger.info("Feature analysis successful", url=page_analysis_data.url)
            return feature_analysis

        except Exception as e:
            _logger.error(
                "Feature analysis failed",
                url=page_analysis_data.url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FeatureAnalysisError(
                f"Failed to analyze features for {page_analysis_data.url}: {str(e)}"
            ) from e

    def _extract_interactive_elements(self, page_analysis_data: PageAnalysisData) -> list:
        """Extract interactive elements from page analysis data."""
        elements = []

        # Extract from buttons array in DOM analysis if available
        if page_analysis_data.dom_analysis and page_analysis_data.dom_analysis.buttons:
            for btn in page_analysis_data.dom_analysis.buttons:
                elements.append(
                    {
                        "type": "button",
                        "selector": btn.get("type", "button"),
                        "purpose": btn.get("text", "button interaction"),
                        "behavior": "click",
                    }
                )

        # Extract from forms array in DOM analysis if available
        if page_analysis_data.dom_analysis and page_analysis_data.dom_analysis.forms:
            for form in page_analysis_data.dom_analysis.forms:
                elements.append(
                    {
                        "type": "form",
                        "selector": f"form[action='{form.get('action', '')}']",
                        "purpose": form.get("action", "form submission"),
                        "behavior": form.get("method", "POST"),
                    }
                )

        # Extract from page content interactive elements
        page_content = page_analysis_data.page_content
        if "interactive_elements" in page_content:
            for elem in page_content["interactive_elements"]:
                elements.append(
                    {
                        "type": elem.get("type", "button"),
                        "selector": elem.get("selector", "unknown"),
                        "purpose": elem.get("purpose", f"{elem.get('type', 'button')} interaction"),
                        "behavior": elem.get("action", "click"),
                    }
                )

        return elements

    def _extract_network_requests(self, page_analysis_data: PageAnalysisData) -> list:
        """Extract network requests from page analysis data."""
        requests = []

        # Extract from network monitoring data
        if "network_requests" in page_analysis_data.page_content:
            for req in page_analysis_data.page_content["network_requests"]:
                requests.append(
                    {
                        "url": req.get("url", "unknown"),
                        "method": req.get("method", "GET"),
                        "status_code": req.get("status", 200),
                        "purpose": req.get("purpose", "data loading"),
                    }
                )

        return requests

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON response from LLM, handling various formats."""
        _logger.debug(
            "Parsing JSON response",
            content=content[:200] + "..." if len(content) > 200 else content,
        )

        try:
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

            return json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            _logger.warning("Failed to parse JSON response, using minimal structure", error=str(e))
            # Return minimal valid structure
            return {
                "interactive_elements": [],
                "functional_capabilities": [],
                "api_integrations": [],
                "business_rules": [],
                "third_party_integrations": [],
                "rebuild_specifications": [],
                "confidence_score": 0.0,
                "quality_score": 0.0,
            }

    def _json_to_feature_analysis(self, json_data: dict[str, Any]) -> FeatureAnalysis:
        """Convert parsed JSON to FeatureAnalysis model."""
        # Convert lists of dictionaries to model instances
        interactive_elements = [
            {
                "type": elem.get("type", "unknown"),
                "selector": elem.get("selector", "unknown"),
                "purpose": elem.get("purpose", "unknown"),
                "behavior": elem.get("behavior", "unknown"),
            }
            for elem in json_data.get("interactive_elements", [])
        ]

        functional_capabilities = [
            {
                "name": cap.get("name", "unknown"),
                "description": cap.get("description", ""),
                "type": cap.get("type", "unknown"),
                "complexity_score": cap.get("complexity_score"),
            }
            for cap in json_data.get("functional_capabilities", [])
        ]

        api_integrations = [
            {
                "endpoint": api.get("endpoint", "unknown"),
                "method": api.get("method", "GET"),
                "purpose": api.get("purpose", "unknown"),
                "data_flow": api.get("data_flow", "unknown"),
                "auth_type": api.get("auth_type"),
            }
            for api in json_data.get("api_integrations", [])
        ]

        business_rules = [
            {
                "name": rule.get("name", "unknown"),
                "description": rule.get("description", ""),
                "validation_logic": rule.get("validation_logic", ""),
                "error_handling": rule.get("error_handling"),
            }
            for rule in json_data.get("business_rules", [])
        ]

        third_party_integrations = [
            {
                "service_name": integration.get("service_name", "unknown"),
                "integration_type": integration.get("integration_type", "unknown"),
                "purpose": integration.get("purpose", "unknown"),
                "auth_method": integration.get("auth_method"),
            }
            for integration in json_data.get("third_party_integrations", [])
        ]

        rebuild_specifications = [
            {
                "name": spec.get("name", "unknown"),
                "description": spec.get("description", ""),
                "priority_score": float(spec.get("priority_score", 0.0)),
                "complexity": spec.get("complexity", "medium"),
                "dependencies": spec.get("dependencies", []),
            }
            for spec in json_data.get("rebuild_specifications", [])
        ]

        feature_analysis = FeatureAnalysis(
            interactive_elements=interactive_elements,
            functional_capabilities=functional_capabilities,
            api_integrations=api_integrations,
            business_rules=business_rules,
            third_party_integrations=third_party_integrations,
            rebuild_specifications=rebuild_specifications,
            confidence_score=float(json_data.get("confidence_score", 0.0)),
            quality_score=float(json_data.get("quality_score", 0.0)),
        )

        return feature_analysis

    def _calculate_confidence(self, analysis: FeatureAnalysis) -> float:
        """Calculates a confidence score based on analysis completeness."""
        score = 1.0

        # Penalize for empty or minimal data
        if not analysis.interactive_elements:
            score -= 0.3
        if not analysis.functional_capabilities:
            score -= 0.3
        if not analysis.api_integrations:
            score -= 0.2
        if not analysis.business_rules:
            score -= 0.2
        if not analysis.rebuild_specifications:
            score -= 0.3

        # Penalize for minimal rebuild items
        if analysis.rebuild_specifications and len(analysis.rebuild_specifications) < 3:
            score -= 0.2

        return max(0.1, score)  # Ensure a minimum score

    def _calculate_quality(self, analysis: FeatureAnalysis, step1_context: ContentSummary) -> float:
        """Calculates a quality score based on analysis completeness and business relevance."""
        score = 1.0

        # Base quality from completeness
        quality_factors = [
            len(analysis.interactive_elements) > 0,
            len(analysis.functional_capabilities) > 0,
            len(analysis.api_integrations) > 0,
            len(analysis.business_rules) > 0,
            len(analysis.rebuild_specifications) > 0,
        ]

        completeness_ratio = sum(quality_factors) / len(quality_factors)
        score *= completeness_ratio

        # Boost quality for rebuild specifications with valid priorities
        if analysis.rebuild_specifications:
            valid_priorities = [
                0.3 <= spec.priority_score <= 1.0 for spec in analysis.rebuild_specifications
            ]
            if valid_priorities:
                priority_ratio = sum(valid_priorities) / len(valid_priorities)
                score *= 0.7 + 0.3 * priority_ratio

        # Factor in Step 1 confidence
        score *= step1_context.confidence_score

        return max(0.1, min(1.0, score))  # Bound between 0.1 and 1.0
