"""Quality validation and error handling for LLM analysis responses.

This module provides comprehensive validation, quality scoring, and error handling
for both Step 1 (Content Summarization) and Step 2 (Feature Analysis) results.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple
from pydantic import BaseModel, Field, ValidationError

from legacy_web_mcp.llm.models import (
    ContentSummary,
    FeatureAnalysis,
    InteractiveElement,
    FunctionalCapability,
    APIIntegration,
    BusinessRule,
    RebuildSpecification
)

_logger = structlog.get_logger(__name__)


class ErrorCode(str, Enum):
    """Error codes following architecture error handling strategy."""

    # Validation Errors (VAL-xxx)
    VAL_001 = "VAL-001"  # Invalid JSON syntax
    VAL_002 = "VAL-002"  # Missing required fields
    VAL_003 = "VAL-003"  # Invalid field types
    VAL_004 = "VAL-004"  # Incomplete analysis
    VAL_005 = "VAL-005"  # Schema validation failure

    # LLM Provider Errors (LLM-xxx)
    LLM_001 = "LLM-001"  # Provider connection failure
    LLM_002 = "LLM-002"  # Rate limiting exceeded
    LLM_003 = "LLM-003"  # Authentication failure
    LLM_004 = "LLM-004"  # Model not available
    LLM_005 = "LLM-005"  # Response timeout

    # Analysis Quality Errors (AQL-xxx)
    AQL_001 = "AQL-001"  # Low completeness score
    AQL_002 = "AQL-002"  # Insufficient technical detail
    AQL_003 = "AQL-003"  # Low confidence indicators
    AQL_004 = "AQL-004"  # Context integration failure
    AQL_005 = "AQL-005"  # Business alignment issues


class ValidationResult(BaseModel):
    """Result of schema and quality validation."""

    is_valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    error_code: Optional[ErrorCode] = Field(default=None, description="Primary error code if validation failed")
    completeness_score: float = Field(default=0.0, description="Analysis completeness score (0.0-1.0)", ge=0.0, le=1.0)
    quality_score: float = Field(default=0.0, description="Overall quality score (0.0-1.0)", ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, description="Analysis confidence score (0.0-1.0)", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional validation metadata")


class QualityMetrics(BaseModel):
    """Comprehensive quality metrics for analysis results."""

    completeness_score: float = Field(description="Completeness of analysis (0.0-1.0)", ge=0.0, le=1.0)
    specificity_score: float = Field(description="Level of specific detail (0.0-1.0)", ge=0.0, le=1.0)
    technical_depth_score: float = Field(description="Technical implementation detail (0.0-1.0)", ge=0.0, le=1.0)
    llm_confidence_score: float = Field(description="LLM confidence in response (0.0-1.0)", ge=0.0, le=1.0)
    overall_quality_score: float = Field(description="Combined quality score (0.0-1.0)", ge=0.0, le=1.0)

    # Quality indicators for user guidance
    needs_manual_review: bool = Field(default=False, description="Whether manual review is recommended")
    review_reasons: List[str] = Field(default_factory=list, description="Reasons for manual review")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")

    # Detailed scoring breakdown
    field_completeness: Dict[str, float] = Field(default_factory=dict, description="Per-field completeness scores")
    detail_scores: Dict[str, float] = Field(default_factory=dict, description="Detail level scores by category")

    timestamp: datetime = Field(default_factory=datetime.now, description="When metrics were calculated")


class AnalysisError(Exception):
    """Structured error information for analysis failures."""

    def __init__(
        self,
        error_code: ErrorCode,
        error_message: str,
        error_context: Dict[str, Any] = None,
        category: str = "analysis",
        severity: str = "medium",
        recoverable: bool = True,
        llm_input: Optional[str] = None,
        llm_output: Optional[str] = None,
        stack_trace: Optional[str] = None
    ):
        super().__init__(error_message)
        self.error_code = error_code
        self.error_message = error_message
        self.error_context = error_context or {}
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.llm_input = llm_input
        self.llm_output = llm_output
        self.stack_trace = stack_trace
        self.timestamp = datetime.now()


class ResponseValidator:
    """Validates LLM responses against expected schemas and quality standards."""

    def __init__(self):
        self.step1_required_fields = {
            'purpose', 'user_context', 'business_logic', 'navigation_role', 'confidence_score'
        }
        self.step1_enhanced_fields = {
            'key_workflows', 'user_journey_stage', 'content_hierarchy',
            'business_importance', 'entry_exit_points', 'contextual_keywords'
        }

        self.step2_required_fields = {
            'interactive_elements', 'functional_capabilities', 'api_integrations',
            'business_rules', 'rebuild_specifications', 'confidence_score', 'quality_score'
        }

    def validate_step1_response(self, response_data: Dict[str, Any]) -> ValidationResult:
        """Validate Step 1 Content Summarization response."""
        try:
            # Parse as ContentSummary to leverage Pydantic validation
            content_summary = ContentSummary(**response_data)

            # Calculate quality metrics
            completeness = self._calculate_step1_completeness(response_data)
            quality = self._calculate_step1_quality(response_data)
            confidence = response_data.get('confidence_score', 0.0)

            # Check for quality issues
            errors = []
            warnings = []

            if confidence < 0.6:
                warnings.append(f"Low confidence score: {confidence:.2f}")

            if completeness < 0.7:
                errors.append(f"Incomplete analysis: {completeness:.2f} completeness")

            if not response_data.get('purpose', '').strip():
                errors.append("Missing or empty purpose field")

            # Enhanced field validation
            if len(response_data.get('key_workflows', [])) == 0:
                warnings.append("No key workflows identified")

            if not response_data.get('user_journey_stage', '').strip():
                warnings.append("User journey stage not specified")

            validation_result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                error_code=ErrorCode.AQL_001 if len(errors) > 0 else None,
                completeness_score=completeness,
                quality_score=quality,
                confidence_score=confidence,
                metadata={
                    'analysis_type': 'step1_content_summary',
                    'required_fields_present': len(self.step1_required_fields.intersection(response_data.keys())),
                    'enhanced_fields_present': len(self.step1_enhanced_fields.intersection(response_data.keys())),
                    'total_fields': len(response_data.keys())
                }
            )

            if validation_result.is_valid:
                _logger.info(
                    "step1_validation_success",
                    completeness_score=completeness,
                    quality_score=quality,
                    confidence_score=confidence
                )
            else:
                _logger.warning(
                    "step1_validation_failed",
                    errors=errors,
                    warnings=warnings,
                    completeness_score=completeness
                )

            return validation_result

        except ValidationError as e:
            errors = [f"Schema validation error: {error['msg']}" for error in e.errors()]
            _logger.error(
                "step1_schema_validation_failed",
                validation_errors=errors,
                error_code=ErrorCode.VAL_005
            )

            return ValidationResult(
                is_valid=False,
                errors=errors,
                error_code=ErrorCode.VAL_005,
                metadata={'validation_exception': str(e)}
            )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax: {str(e)}"
            _logger.error(
                "step1_json_parse_failed",
                error=error_msg,
                error_code=ErrorCode.VAL_001
            )

            return ValidationResult(
                is_valid=False,
                errors=[error_msg],
                error_code=ErrorCode.VAL_001,
                metadata={'json_error': str(e)}
            )

        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            _logger.error(
                "step1_validation_unexpected_error",
                error=error_msg,
                error_code=ErrorCode.VAL_005
            )

            return ValidationResult(
                is_valid=False,
                errors=[error_msg],
                error_code=ErrorCode.VAL_005,
                metadata={'unexpected_error': str(e)}
            )

    def validate_step2_response(self, response_data: Dict[str, Any]) -> ValidationResult:
        """Validate Step 2 Feature Analysis response."""
        try:
            # Parse as FeatureAnalysis to leverage Pydantic validation
            feature_analysis = FeatureAnalysis(**response_data)

            # Calculate quality metrics
            completeness = self._calculate_step2_completeness(response_data)
            quality = self._calculate_step2_quality(response_data)
            confidence = response_data.get('confidence_score', 0.0)

            # Check for quality issues
            errors = []
            warnings = []

            if confidence < 0.6:
                warnings.append(f"Low confidence score: {confidence:.2f}")

            if completeness < 0.7:
                errors.append(f"Incomplete analysis: {completeness:.2f} completeness")

            # Validate interactive elements
            interactive_elements = response_data.get('interactive_elements', [])
            if len(interactive_elements) == 0:
                warnings.append("No interactive elements identified")
            elif len(interactive_elements) < 3:
                warnings.append(f"Few interactive elements found: {len(interactive_elements)}")

            # Validate functional capabilities
            capabilities = response_data.get('functional_capabilities', [])
            if len(capabilities) == 0:
                errors.append("No functional capabilities identified")
            elif len(capabilities) < 2:
                warnings.append(f"Limited functional capabilities: {len(capabilities)}")

            # Check technical detail level
            tech_detail_score = self._calculate_technical_detail_score(response_data)
            if tech_detail_score < 0.5:
                warnings.append(f"Low technical detail level: {tech_detail_score:.2f}")

            validation_result = ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                error_code=ErrorCode.AQL_002 if len(errors) > 0 else None,
                completeness_score=completeness,
                quality_score=quality,
                confidence_score=confidence,
                metadata={
                    'analysis_type': 'step2_feature_analysis',
                    'interactive_elements_count': len(interactive_elements),
                    'functional_capabilities_count': len(capabilities),
                    'api_integrations_count': len(response_data.get('api_integrations', [])),
                    'business_rules_count': len(response_data.get('business_rules', [])),
                    'technical_detail_score': tech_detail_score
                }
            )

            if validation_result.is_valid:
                _logger.info(
                    "step2_validation_success",
                    completeness_score=completeness,
                    quality_score=quality,
                    confidence_score=confidence,
                    features_count=len(capabilities)
                )
            else:
                _logger.warning(
                    "step2_validation_failed",
                    errors=errors,
                    warnings=warnings,
                    completeness_score=completeness
                )

            return validation_result

        except ValidationError as e:
            errors = [f"Schema validation error: {error['msg']}" for error in e.errors()]
            _logger.error(
                "step2_schema_validation_failed",
                validation_errors=errors,
                error_code=ErrorCode.VAL_005
            )

            return ValidationResult(
                is_valid=False,
                errors=errors,
                error_code=ErrorCode.VAL_005,
                metadata={'validation_exception': str(e)}
            )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax: {str(e)}"
            _logger.error(
                "step2_json_parse_failed",
                error=error_msg,
                error_code=ErrorCode.VAL_001
            )

            return ValidationResult(
                is_valid=False,
                errors=[error_msg],
                error_code=ErrorCode.VAL_001,
                metadata={'json_error': str(e)}
            )

        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            _logger.error(
                "step2_validation_unexpected_error",
                error=error_msg,
                error_code=ErrorCode.VAL_005
            )

            return ValidationResult(
                is_valid=False,
                errors=[error_msg],
                error_code=ErrorCode.VAL_005,
                metadata={'unexpected_error': str(e)}
            )

    def _calculate_step1_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score for Step 1 analysis."""
        required_score = sum(
            1 for field in self.step1_required_fields
            if data.get(field) is not None and str(data.get(field)).strip()
        ) / len(self.step1_required_fields)

        enhanced_score = sum(
            1 for field in self.step1_enhanced_fields
            if data.get(field) is not None and (
                isinstance(data.get(field), (list, dict)) and data.get(field) or
                isinstance(data.get(field), str) and data.get(field).strip()
            )
        ) / len(self.step1_enhanced_fields)

        return (required_score * 0.8) + (enhanced_score * 0.2)

    def _calculate_step1_quality(self, data: Dict[str, Any]) -> float:
        """Calculate quality score for Step 1 analysis."""
        quality_factors = []

        # Purpose clarity (length and specificity)
        purpose = data.get('purpose', '')
        if len(purpose) > 10 and len(purpose) < 200:
            quality_factors.append(0.8)
        elif len(purpose) > 5:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.2)

        # Business logic detail
        business_logic = data.get('business_logic', '')
        if len(business_logic) > 50:
            quality_factors.append(0.8)
        elif len(business_logic) > 20:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.3)

        # Workflow identification
        workflows = data.get('key_workflows', [])
        workflow_score = min(len(workflows) / 3, 1.0) if workflows else 0.0
        quality_factors.append(workflow_score)

        # Context richness
        context_fields = ['user_journey_stage', 'contextual_keywords', 'content_hierarchy']
        context_score = sum(1 for field in context_fields if data.get(field)) / len(context_fields)
        quality_factors.append(context_score)

        return sum(quality_factors) / len(quality_factors)

    def _calculate_step2_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness score for Step 2 analysis."""
        section_scores = []

        # Interactive elements completeness
        ie_count = len(data.get('interactive_elements', []))
        ie_score = min(ie_count / 5, 1.0)  # Expect at least 5 interactive elements
        section_scores.append(ie_score)

        # Functional capabilities completeness
        fc_count = len(data.get('functional_capabilities', []))
        fc_score = min(fc_count / 3, 1.0)  # Expect at least 3 capabilities
        section_scores.append(fc_score)

        # API integrations (optional but valuable)
        api_count = len(data.get('api_integrations', []))
        api_score = min(api_count / 2, 1.0) if api_count > 0 else 0.5
        section_scores.append(api_score)

        # Business rules (optional but important)
        br_count = len(data.get('business_rules', []))
        br_score = min(br_count / 2, 1.0) if br_count > 0 else 0.5
        section_scores.append(br_score)

        return sum(section_scores) / len(section_scores)

    def _calculate_step2_quality(self, data: Dict[str, Any]) -> float:
        """Calculate quality score for Step 2 analysis."""
        quality_factors = []

        # Technical detail in capabilities
        capabilities = data.get('functional_capabilities', [])
        detail_score = self._calculate_technical_detail_score(data)
        quality_factors.append(detail_score)

        # Interactive elements specificity
        elements = data.get('interactive_elements', [])
        if elements:
            specificity_score = sum(
                1 for elem in elements
                if elem.get('selector') and elem.get('purpose') and elem.get('behavior')
            ) / len(elements)
            quality_factors.append(specificity_score)
        else:
            quality_factors.append(0.0)

        # API integration detail
        apis = data.get('api_integrations', [])
        if apis:
            api_detail_score = sum(
                1 for api in apis
                if api.get('endpoint') and api.get('method') and api.get('purpose')
            ) / len(apis)
            quality_factors.append(api_detail_score)
        else:
            quality_factors.append(0.5)  # Neutral if no APIs

        # Rebuild specifications usefulness
        specs = data.get('rebuild_specifications', [])
        if specs:
            spec_score = sum(
                1 for spec in specs
                if spec.get('priority_score', 0) > 0 and spec.get('dependencies')
            ) / len(specs)
            quality_factors.append(spec_score)
        else:
            quality_factors.append(0.3)

        return sum(quality_factors) / len(quality_factors)

    def _calculate_technical_detail_score(self, data: Dict[str, Any]) -> float:
        """Calculate technical detail level score."""
        capabilities = data.get('functional_capabilities', [])
        if not capabilities:
            return 0.0

        detail_scores = []
        for cap in capabilities:
            description = cap.get('description', '')

            # Check for technical indicators
            tech_indicators = [
                'api', 'endpoint', 'database', 'query', 'validation',
                'authentication', 'authorization', 'session', 'cookie',
                'ajax', 'fetch', 'post', 'get', 'json', 'xml', 'form'
            ]

            tech_score = sum(1 for indicator in tech_indicators if indicator in description.lower())
            detail_scores.append(min(tech_score / 3, 1.0))  # Normalize to 0-1

        return sum(detail_scores) / len(detail_scores)


class QualityAnalyzer:
    """Analyzes and scores quality of analysis results."""

    def __init__(self):
        self.validator = ResponseValidator()

    def calculate_quality_metrics(
        self,
        analysis_data: Union[ContentSummary, FeatureAnalysis, Dict[str, Any]],
        analysis_type: str
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics for analysis results."""

        if isinstance(analysis_data, (ContentSummary, FeatureAnalysis)):
            data_dict = analysis_data.model_dump()
        else:
            data_dict = analysis_data

        if analysis_type == "step1":
            return self._calculate_step1_metrics(data_dict)
        elif analysis_type == "step2":
            return self._calculate_step2_metrics(data_dict)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

    def _calculate_step1_metrics(self, data: Dict[str, Any]) -> QualityMetrics:
        """Calculate quality metrics for Step 1 analysis."""
        validation_result = self.validator.validate_step1_response(data)

        # Calculate specificity based on detail level
        specificity_score = self._calculate_step1_specificity(data)

        # Technical depth is not applicable for Step 1
        technical_depth_score = 0.5  # Neutral score

        # LLM confidence from the analysis
        llm_confidence = data.get('confidence_score', 0.0)

        # Overall quality combining all factors
        overall_quality = (
            validation_result.completeness_score * 0.4 +
            specificity_score * 0.3 +
            validation_result.quality_score * 0.2 +
            llm_confidence * 0.1
        )

        # Determine if manual review is needed
        needs_review = (
            overall_quality < 0.7 or
            llm_confidence < 0.6 or
            len(validation_result.errors) > 0
        )

        review_reasons = []
        if overall_quality < 0.7:
            review_reasons.append(f"Low overall quality: {overall_quality:.2f}")
        if llm_confidence < 0.6:
            review_reasons.append(f"Low LLM confidence: {llm_confidence:.2f}")
        if validation_result.errors:
            review_reasons.extend(validation_result.errors)

        return QualityMetrics(
            completeness_score=validation_result.completeness_score,
            specificity_score=specificity_score,
            technical_depth_score=technical_depth_score,
            llm_confidence_score=llm_confidence,
            overall_quality_score=overall_quality,
            needs_manual_review=needs_review,
            review_reasons=review_reasons,
            quality_issues=validation_result.errors + validation_result.warnings,
            field_completeness=self._calculate_field_completeness_step1(data),
            detail_scores={
                'purpose_detail': len(data.get('purpose', '')) / 100,  # Normalize to ~0-1
                'business_logic_detail': len(data.get('business_logic', '')) / 200,
                'workflow_identification': len(data.get('key_workflows', [])) / 5
            }
        )

    def _calculate_step2_metrics(self, data: Dict[str, Any]) -> QualityMetrics:
        """Calculate quality metrics for Step 2 analysis."""
        validation_result = self.validator.validate_step2_response(data)

        # Calculate specificity based on detail level
        specificity_score = self._calculate_step2_specificity(data)

        # Technical depth score
        technical_depth_score = self.validator._calculate_technical_detail_score(data)

        # LLM confidence from the analysis
        llm_confidence = data.get('confidence_score', 0.0)

        # Overall quality combining all factors
        overall_quality = (
            validation_result.completeness_score * 0.3 +
            specificity_score * 0.3 +
            technical_depth_score * 0.3 +
            llm_confidence * 0.1
        )

        # Determine if manual review is needed
        needs_review = (
            overall_quality < 0.7 or
            llm_confidence < 0.6 or
            technical_depth_score < 0.5 or
            len(validation_result.errors) > 0
        )

        review_reasons = []
        if overall_quality < 0.7:
            review_reasons.append(f"Low overall quality: {overall_quality:.2f}")
        if llm_confidence < 0.6:
            review_reasons.append(f"Low LLM confidence: {llm_confidence:.2f}")
        if technical_depth_score < 0.5:
            review_reasons.append(f"Insufficient technical detail: {technical_depth_score:.2f}")
        if validation_result.errors:
            review_reasons.extend(validation_result.errors)

        return QualityMetrics(
            completeness_score=validation_result.completeness_score,
            specificity_score=specificity_score,
            technical_depth_score=technical_depth_score,
            llm_confidence_score=llm_confidence,
            overall_quality_score=overall_quality,
            needs_manual_review=needs_review,
            review_reasons=review_reasons,
            quality_issues=validation_result.errors + validation_result.warnings,
            field_completeness=self._calculate_field_completeness_step2(data),
            detail_scores={
                'interactive_elements_detail': self._score_interactive_elements_detail(data),
                'functional_capabilities_detail': self._score_capabilities_detail(data),
                'api_integrations_detail': self._score_api_detail(data),
                'technical_implementation_detail': technical_depth_score
            }
        )

    def _calculate_step1_specificity(self, data: Dict[str, Any]) -> float:
        """Calculate specificity score for Step 1 analysis."""
        factors = []

        # Purpose specificity (avoid generic terms)
        purpose = data.get('purpose', '').lower()
        generic_terms = ['page', 'website', 'application', 'content', 'information']
        specificity = 1.0 - (sum(1 for term in generic_terms if term in purpose) / len(generic_terms))
        factors.append(specificity)

        # User context specificity
        user_context = data.get('user_context', '').lower()
        if 'specific' in user_context or 'targeted' in user_context:
            factors.append(0.8)
        elif len(user_context) > 20:
            factors.append(0.6)
        else:
            factors.append(0.3)

        # Business logic detail
        business_logic = data.get('business_logic', '')
        if len(business_logic) > 100:
            factors.append(0.9)
        elif len(business_logic) > 50:
            factors.append(0.7)
        else:
            factors.append(0.4)

        return sum(factors) / len(factors)

    def _calculate_step2_specificity(self, data: Dict[str, Any]) -> float:
        """Calculate specificity score for Step 2 analysis."""
        factors = []

        # Interactive elements specificity
        elements = data.get('interactive_elements', [])
        if elements:
            specificity = sum(
                1 for elem in elements
                if elem.get('selector') and elem.get('purpose') and len(elem.get('purpose', '')) > 10
            ) / len(elements)
            factors.append(specificity)
        else:
            factors.append(0.0)

        # Functional capabilities specificity
        capabilities = data.get('functional_capabilities', [])
        if capabilities:
            specificity = sum(
                1 for cap in capabilities
                if len(cap.get('description', '')) > 20 and cap.get('type')
            ) / len(capabilities)
            factors.append(specificity)
        else:
            factors.append(0.0)

        # API integrations specificity
        apis = data.get('api_integrations', [])
        if apis:
            specificity = sum(
                1 for api in apis
                if api.get('endpoint') and api.get('method') and api.get('data_flow')
            ) / len(apis)
            factors.append(specificity)
        else:
            factors.append(0.5)  # Neutral if no APIs

        return sum(factors) / len(factors)

    def _calculate_field_completeness_step1(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate per-field completeness for Step 1."""
        completeness = {}

        # Required fields
        for field in self.validator.step1_required_fields:
            value = data.get(field)
            if value is None:
                completeness[field] = 0.0
            elif isinstance(value, str):
                completeness[field] = 1.0 if value.strip() else 0.0
            elif isinstance(value, (int, float)):
                completeness[field] = 1.0
            else:
                completeness[field] = 0.5

        # Enhanced fields
        for field in self.validator.step1_enhanced_fields:
            value = data.get(field)
            if value is None:
                completeness[field] = 0.0
            elif isinstance(value, list):
                completeness[field] = 1.0 if len(value) > 0 else 0.0
            elif isinstance(value, dict):
                completeness[field] = 1.0 if value else 0.0
            elif isinstance(value, str):
                completeness[field] = 1.0 if value.strip() else 0.0
            else:
                completeness[field] = 0.5

        return completeness

    def _calculate_field_completeness_step2(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate per-field completeness for Step 2."""
        completeness = {}

        # Array fields
        array_fields = ['interactive_elements', 'functional_capabilities', 'api_integrations', 'business_rules']
        for field in array_fields:
            items = data.get(field, [])
            if not items:
                completeness[field] = 0.0
            else:
                # Score based on item count and quality
                expected_counts = {
                    'interactive_elements': 5,
                    'functional_capabilities': 3,
                    'api_integrations': 2,
                    'business_rules': 2
                }
                expected = expected_counts.get(field, 3)
                completeness[field] = min(len(items) / expected, 1.0)

        # Scalar fields
        scalar_fields = ['confidence_score', 'quality_score']
        for field in scalar_fields:
            value = data.get(field)
            completeness[field] = 1.0 if value is not None else 0.0

        return completeness

    def _score_interactive_elements_detail(self, data: Dict[str, Any]) -> float:
        """Score detail level of interactive elements."""
        elements = data.get('interactive_elements', [])
        if not elements:
            return 0.0

        detail_scores = []
        for elem in elements:
            score = 0.0
            if elem.get('type'):
                score += 0.25
            if elem.get('selector'):
                score += 0.25
            if elem.get('purpose') and len(elem.get('purpose', '')) > 10:
                score += 0.25
            if elem.get('behavior') and len(elem.get('behavior', '')) > 10:
                score += 0.25
            detail_scores.append(score)

        return sum(detail_scores) / len(detail_scores)

    def _score_capabilities_detail(self, data: Dict[str, Any]) -> float:
        """Score detail level of functional capabilities."""
        capabilities = data.get('functional_capabilities', [])
        if not capabilities:
            return 0.0

        detail_scores = []
        for cap in capabilities:
            score = 0.0
            if cap.get('name'):
                score += 0.2
            if cap.get('description') and len(cap.get('description', '')) > 20:
                score += 0.3
            if cap.get('type'):
                score += 0.2
            if cap.get('complexity_score', 0) > 0:
                score += 0.15
            if cap.get('priority_score'):
                score += 0.15
            detail_scores.append(score)

        return sum(detail_scores) / len(detail_scores)

    def _score_api_detail(self, data: Dict[str, Any]) -> float:
        """Score detail level of API integrations."""
        apis = data.get('api_integrations', [])
        if not apis:
            return 0.5  # Neutral score if no APIs

        detail_scores = []
        for api in apis:
            score = 0.0
            if api.get('endpoint'):
                score += 0.3
            if api.get('method'):
                score += 0.2
            if api.get('purpose'):
                score += 0.2
            if api.get('data_flow'):
                score += 0.2
            if api.get('auth_type'):
                score += 0.1
            detail_scores.append(score)

        return sum(detail_scores) / len(detail_scores)