#!/usr/bin/env python
"""Core logic for Step 2: Detailed Feature Analysis."""

from __future__ import annotations

import json
from typing import Any

import structlog

from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis, ContextPayload, PriorityScore, ConsistencyValidation, LLMMessage, LLMRequest, LLMRequestType, LLMRole
from legacy_web_mcp.llm.prompts.step2_feature_analysis import (
    FEATURE_ANALYSIS_SYSTEM_PROMPT,
    create_feature_analysis_prompt,
    create_context_aware_feature_analysis_prompt,
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
        """Performs comprehensive feature analysis for a page with quality validation.

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
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=FEATURE_ANALYSIS_SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=prompt),
            ]

            request = LLMRequest(
                messages=messages,
                request_type=LLMRequestType.FEATURE_ANALYSIS,
                metadata={"step": "step2", "model_config_key": "step2_model"},
            )

            # Use validation-enabled chat completion for quality assurance
            response, validation_result, quality_metrics = await self.llm_engine.chat_completion_with_validation(
                request=request,
                analysis_type="step2",
                page_url=page_analysis_data.url,
                quality_threshold=0.6  # Minimum acceptable quality
            )

            # Parse the validated JSON response
            analysis_json = self._parse_json_response(response.content)

            # Convert JSON to FeatureAnalysis model
            feature_analysis = self._json_to_feature_analysis(analysis_json)

            # Override confidence and quality scores with validated metrics
            feature_analysis.confidence_score = min(
                feature_analysis.confidence_score,
                quality_metrics.llm_confidence_score
            )
            feature_analysis.quality_score = quality_metrics.overall_quality_score

            # Store quality metrics and validation results for debugging
            if hasattr(feature_analysis, 'metadata'):
                feature_analysis.metadata = feature_analysis.metadata or {}
            else:
                feature_analysis.metadata = {}
                
            feature_analysis.metadata.update({
                'quality_metrics': quality_metrics.model_dump(),
                'validation_result': validation_result.model_dump(),
                'step1_context_confidence': step1_context.confidence_score
            })

            # Log comprehensive quality information
            _logger.info(
                "feature_analysis_successful",
                url=page_analysis_data.url,
                quality_score=quality_metrics.overall_quality_score,
                completeness_score=quality_metrics.completeness_score,
                technical_depth_score=quality_metrics.technical_depth_score,
                needs_manual_review=quality_metrics.needs_manual_review,
                interactive_elements_count=len(feature_analysis.interactive_elements),
                functional_capabilities_count=len(feature_analysis.functional_capabilities),
                validation_errors=len(validation_result.errors),
                validation_warnings=len(validation_result.warnings)
            )

            return feature_analysis

        except Exception as e:
            _logger.error(
                "feature_analysis_failed",
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

    async def analyze_features_with_context(
        self, page_analysis_data: PageAnalysisData, context_payload: ContextPayload
    ) -> FeatureAnalysis:
        """Performs context-aware feature analysis using rich Step 1 context.

        Args:
            page_analysis_data: The comprehensive analysis data collected from the page.
            context_payload: Rich context data from Step 1 analysis.

        Returns:
            A FeatureAnalysis object with context-aware insights and priority scoring.

        Raises:
            FeatureAnalysisError: If the analysis fails after all retries.
        """
        _logger.info("Starting context-aware feature analysis", url=page_analysis_data.url)

        # Extract interactive elements and network requests
        interactive_elements = self._extract_interactive_elements(page_analysis_data)
        network_requests = self._extract_network_requests(page_analysis_data)

        # Create context-aware prompt
        prompt = create_context_aware_feature_analysis_prompt(
            page_content=page_analysis_data.page_content,
            context_payload=context_payload,
            interactive_elements=interactive_elements,
            network_requests=network_requests,
            url=page_analysis_data.url,
        )

        try:
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=FEATURE_ANALYSIS_SYSTEM_PROMPT),
                LLMMessage(role=LLMRole.USER, content=prompt),
            ]

            request = LLMRequest(
                messages=messages,
                request_type=LLMRequestType.FEATURE_ANALYSIS,
            )

            response = await self.llm_engine.chat_completion(
                request=request,
                page_url=page_analysis_data.url
            )

            # Parse the JSON response into FeatureAnalysis
            analysis_json = self._parse_json_response(response.content)
            feature_analysis = self._json_to_feature_analysis(analysis_json)

            # Enhanced context-aware processing
            feature_analysis = self._enhance_with_context(feature_analysis, context_payload)

            # Calculate priority scores for features
            self._calculate_priority_scores(feature_analysis, context_payload)

            # Perform consistency validation
            feature_analysis.context_validation = self._validate_consistency(
                feature_analysis, context_payload
            )

            # Calculate context integration score
            feature_analysis.context_integration_score = self._calculate_context_integration_score(
                feature_analysis, context_payload
            )

            # Calculate confidence and quality scores
            feature_analysis.confidence_score = self._calculate_confidence(feature_analysis)
            feature_analysis.quality_score = self._calculate_quality(
                feature_analysis, context_payload.content_summary
            )

            _logger.info("Context-aware feature analysis successful", url=page_analysis_data.url)
            return feature_analysis

        except Exception as e:
            _logger.error(
                "Context-aware feature analysis failed",
                url=page_analysis_data.url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise FeatureAnalysisError(
                f"Failed to analyze features with context for {page_analysis_data.url}: {str(e)}"
            ) from e

    def _enhance_with_context(
        self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload
    ) -> FeatureAnalysis:
        """Enhance feature analysis with contextual information."""
        # Add business context relevance to interactive elements
        for element in feature_analysis.interactive_elements:
            element.business_context_relevance = self._determine_business_relevance(
                element, context_payload
            )
            element.workflow_role = self._determine_workflow_role(element, context_payload)

        # Add business alignment to functional capabilities
        for capability in feature_analysis.functional_capabilities:
            capability.business_alignment = self._determine_business_alignment(
                capability, context_payload
            )
            capability.user_journey_impact = self._determine_user_journey_impact(
                capability, context_payload
            )

        # Generate business alignment summary
        feature_analysis.business_alignment_summary = self._generate_business_alignment_summary(
            feature_analysis, context_payload
        )

        # Map workflow dependencies
        feature_analysis.workflow_dependencies = self._map_workflow_dependencies(
            feature_analysis, context_payload
        )

        return feature_analysis

    def _calculate_priority_scores(
        self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload
    ) -> None:
        """Calculate priority scores for features based on business and technical factors."""
        business_importance = context_payload.content_summary.business_importance

        # Calculate priority scores for interactive elements
        for element in feature_analysis.interactive_elements:
            element.priority_score = self._calculate_element_priority(
                element, business_importance, context_payload
            )

        # Calculate priority scores for functional capabilities
        for capability in feature_analysis.functional_capabilities:
            capability.priority_score = self._calculate_capability_priority(
                capability, business_importance, context_payload
            )

    def _validate_consistency(
        self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload
    ) -> ConsistencyValidation:
        """Validate consistency between Step 1 context and Step 2 findings."""
        inconsistencies = []

        # Check if features align with business purpose
        purpose_alignment = self._check_purpose_alignment(feature_analysis, context_payload)
        if not purpose_alignment['aligned']:
            inconsistencies.extend(purpose_alignment['issues'])

        # Check if features support identified workflows
        workflow_support = self._check_workflow_support(feature_analysis, context_payload)
        if not workflow_support['supported']:
            inconsistencies.extend(workflow_support['issues'])

        # Check user context consistency
        user_context_consistency = self._check_user_context_consistency(feature_analysis, context_payload)
        if not user_context_consistency['consistent']:
            inconsistencies.extend(user_context_consistency['issues'])

        # Calculate consistency score
        total_checks = 3
        passed_checks = sum([
            purpose_alignment['aligned'],
            workflow_support['supported'],
            user_context_consistency['consistent']
        ])
        consistency_score = passed_checks / total_checks

        return ConsistencyValidation(
            is_consistent=len(inconsistencies) == 0,
            inconsistencies=inconsistencies,
            consistency_score=consistency_score,
            action_required=consistency_score < 0.7,
            validation_details={
                'purpose_alignment': purpose_alignment,
                'workflow_support': workflow_support,
                'user_context_consistency': user_context_consistency
            }
        )

    def _calculate_context_integration_score(
        self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload
    ) -> float:
        """Calculate how well Step 1 context was integrated into Step 2 analysis."""
        integration_factors = []

        # Check if business context is reflected in features
        if feature_analysis.business_alignment_summary:
            integration_factors.append(1.0)
        else:
            integration_factors.append(0.0)

        # Check if workflow dependencies are mapped
        if feature_analysis.workflow_dependencies:
            integration_factors.append(1.0)
        else:
            integration_factors.append(0.5)

        # Check if elements have context relevance
        elements_with_context = sum(
            1 for el in feature_analysis.interactive_elements
            if el.business_context_relevance
        )
        if feature_analysis.interactive_elements:
            element_context_ratio = elements_with_context / len(feature_analysis.interactive_elements)
            integration_factors.append(element_context_ratio)
        else:
            integration_factors.append(0.5)

        # Check if capabilities have business alignment
        capabilities_with_alignment = sum(
            1 for cap in feature_analysis.functional_capabilities
            if cap.business_alignment
        )
        if feature_analysis.functional_capabilities:
            capability_alignment_ratio = capabilities_with_alignment / len(feature_analysis.functional_capabilities)
            integration_factors.append(capability_alignment_ratio)
        else:
            integration_factors.append(0.5)

        return sum(integration_factors) / len(integration_factors)

    # Helper methods for context analysis
    def _determine_business_relevance(self, element, context_payload: ContextPayload) -> str:
        """Determine how an element relates to business context."""
        keywords = context_payload.get_contextual_keywords()
        purpose = context_payload.content_summary.purpose.lower()

        # Simple keyword matching for business relevance
        element_purpose = element.purpose.lower()

        for keyword in keywords:
            if keyword.lower() in element_purpose:
                return f"Related to {keyword} as part of {purpose}"

        return f"Supports general {purpose} functionality"

    def _determine_workflow_role(self, element, context_payload: ContextPayload) -> str:
        """Determine an element's role in identified workflows."""
        workflows = context_payload.content_summary.key_workflows
        journey_stage = context_payload.content_summary.user_journey_stage

        # Map element types to likely workflow roles
        if element.type in ['form', 'input']:
            return f"Data collection for {', '.join(workflows)} at {journey_stage} stage"
        elif element.type == 'button':
            return f"Action trigger for {', '.join(workflows)}"
        else:
            return f"Interface element supporting {journey_stage} stage workflows"

    def _determine_business_alignment(self, capability, context_payload: ContextPayload) -> str:
        """Determine how a capability aligns with business purpose."""
        purpose = context_payload.content_summary.purpose
        business_logic = context_payload.content_summary.business_logic

        return f"Enables {capability.name} to support {purpose}: {business_logic}"

    def _determine_user_journey_impact(self, capability, context_payload: ContextPayload) -> str:
        """Determine a capability's impact on user journey."""
        journey_stage = context_payload.content_summary.user_journey_stage
        user_context = context_payload.content_summary.user_context

        return f"Impacts {user_context} experience during {journey_stage} stage"

    def _generate_business_alignment_summary(self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload) -> str:
        """Generate summary of how features align with business context."""
        purpose = context_payload.content_summary.purpose
        workflows = context_payload.content_summary.key_workflows

        return f"Features support {purpose} through {len(feature_analysis.interactive_elements)} interactive elements and {len(feature_analysis.functional_capabilities)} capabilities, enabling {', '.join(workflows)} workflows."

    def _map_workflow_dependencies(self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload) -> dict:
        """Map workflow dependencies between features."""
        workflows = context_payload.content_summary.key_workflows

        return {
            workflow: [cap.name for cap in feature_analysis.functional_capabilities]
            for workflow in workflows
        }

    def _check_purpose_alignment(self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload) -> dict:
        """Check if features align with stated purpose."""
        # Simplified alignment check - in production, this would be more sophisticated
        has_relevant_features = len(feature_analysis.interactive_elements) > 0 or len(feature_analysis.functional_capabilities) > 0

        return {
            'aligned': has_relevant_features,
            'issues': [] if has_relevant_features else ['No relevant features found for stated purpose']
        }

    def _check_workflow_support(self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload) -> dict:
        """Check if features support identified workflows."""
        workflows = context_payload.content_summary.key_workflows
        supported_workflows = len(workflows) > 0 and len(feature_analysis.functional_capabilities) > 0

        return {
            'supported': supported_workflows,
            'issues': [] if supported_workflows else ['Features do not clearly support identified workflows']
        }

    def _check_user_context_consistency(self, feature_analysis: FeatureAnalysis, context_payload: ContextPayload) -> dict:
        """Check if features are consistent with user context."""
        # Simplified consistency check
        user_context = context_payload.content_summary.user_context
        has_user_appropriate_features = len(feature_analysis.interactive_elements) > 0

        return {
            'consistent': has_user_appropriate_features,
            'issues': [] if has_user_appropriate_features else [f'Features may not be appropriate for {user_context}']
        }

    def _calculate_element_priority(
        self, element, business_importance: float, context_payload: ContextPayload
    ) -> PriorityScore:
        """Calculate priority score for an interactive element."""
        # Determine technical complexity based on element type
        complexity_map = {
            "form": 0.7,
            "button": 0.3,
            "input": 0.4,
            "select": 0.5,
            "textarea": 0.4,
        }
        technical_complexity = complexity_map.get(element.type, 0.5)

        # Determine user impact based on workflow role
        user_impact = 0.8 if element.workflow_role else 0.5

        # Determine implementation effort
        implementation_effort = technical_complexity * 0.8

        priority_score = PriorityScore(
            business_importance=business_importance,
            technical_complexity=technical_complexity,
            user_impact=user_impact,
            implementation_effort=implementation_effort
        )

        priority_score.calculate_priority()
        return priority_score

    def _calculate_capability_priority(
        self, capability, business_importance: float, context_payload: ContextPayload
    ) -> PriorityScore:
        """Calculate priority score for a functional capability."""
        # Use existing complexity score if available
        technical_complexity = capability.complexity_score or 0.5

        # Determine user impact based on business alignment
        user_impact = 0.9 if capability.business_alignment else 0.6

        # Estimate implementation effort based on complexity and type
        effort_map = {
            "feature": 0.6,
            "service": 0.8,
            "integration": 0.9,
        }
        implementation_effort = effort_map.get(capability.type, 0.7)

        priority_score = PriorityScore(
            business_importance=business_importance,
            technical_complexity=technical_complexity,
            user_impact=user_impact,
            implementation_effort=implementation_effort
        )

        priority_score.calculate_priority()
        return priority_score
