"""Data models for LLM provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMRole(str, Enum):
    """Message roles in LLM conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMRequestType(str, Enum):
    """Types of LLM analysis requests."""

    CONTENT_SUMMARY = "content_summary"
    FEATURE_ANALYSIS = "feature_analysis"
    DIAGNOSTIC = "diagnostic"


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: LLMRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(BaseModel):
    """Unified request format for all LLM providers."""

    messages: list[LLMMessage]
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    request_type: LLMRequestType = LLMRequestType.CONTENT_SUMMARY
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Token usage information from LLM response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Unified response format from all LLM providers."""

    content: str
    model: str
    provider: LLMProvider
    usage: TokenUsage
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    cost_estimate: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: LLMProvider | None = None,
        error_code: str | None = None,
        retryable: bool = False
    ):
        super().__init__(message)
        self.provider = provider
        self.error_code = error_code
        self.retryable = retryable


class AuthenticationError(LLMError):
    """Raised when API authentication fails."""
    pass


class RateLimitError(LLMError):
    """Raised when API rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        provider: LLMProvider | None = None,
        retry_after: int | None = None
    ):
        super().__init__(message, provider, retryable=True)
        self.retry_after = retry_after


class ValidationError(LLMError):
    """Raised when request validation fails."""
    pass


class TimeoutError(LLMError):
    """Raised when request times out."""

    def __init__(self, message: str, provider: LLMProvider | None = None):
        super().__init__(message, provider, retryable=True)


class ParseError(LLMError):
    """Raised when response parsing fails."""
    pass


class ProviderHealthStatus(str, Enum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ProviderHealth(BaseModel):
    """Health status information for a provider."""

    provider: LLMProvider
    status: ProviderHealthStatus
    last_check: datetime
    response_time_ms: float | None = None
    error_rate: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    last_error: str | None = None


class ProviderConfig(BaseModel):
    """Configuration for an LLM provider."""

    provider: LLMProvider
    api_key: str
    base_url: str | None = None
    model: str | None = None
    max_retries: int = 3
    timeout: float = 30.0
    rate_limit_rpm: int | None = None
    enabled: bool = True


class CostTracking(BaseModel):
    """Cost tracking information."""

    provider: LLMProvider
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_per_prompt_token: float
    cost_per_completion_token: float
    total_cost: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMProviderInterface(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration."""
        pass

    @abstractmethod
    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""
        pass

    @abstractmethod
    async def validate_api_key(self) -> bool:
        """Validate the API key and test connectivity."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Check provider health status."""
        pass

    @abstractmethod
    def calculate_cost(self, usage: TokenUsage, model: str) -> float:
        """Calculate cost for token usage."""
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """Get list of supported models for this provider."""
        pass


class ContentSummary(BaseModel):
    """Step 1 LLM analysis output capturing page purpose and context."""

    purpose: str = Field(description="Primary page purpose and business function")
    user_context: str = Field(description="Target users and user journey context")
    business_logic: str = Field(description="Core business rules and workflows")
    navigation_role: str = Field(description="Page's role in overall site navigation")
    confidence_score: float = Field(
        description="Analysis confidence level (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Enhanced context data for Step 2 passing
    key_workflows: list[str] = Field(
        default_factory=list,
        description="Key business workflows this page supports"
    )
    user_journey_stage: str = Field(
        default="",
        description="Stage in user journey (entry, middle, exit, conversion, etc.)"
    )
    content_hierarchy: dict[str, Any] = Field(
        default_factory=dict,
        description="Content organization and hierarchy analysis"
    )
    business_importance: float = Field(
        default=0.5,
        description="Business importance score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    entry_exit_points: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Entry and exit points identified on the page"
    )
    contextual_keywords: list[str] = Field(
        default_factory=list,
        description="Key terms and concepts that define page context"
    )


class ContextPayload(BaseModel):
    """Context data structure passed from Step 1 to Step 2 analysis."""

    content_summary: ContentSummary = Field(description="Complete Step 1 analysis results")
    filtered_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Filtered context data relevant for Step 2"
    )
    analysis_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the analysis process"
    )

    def get_business_context(self) -> str:
        """Extract business context for Step 2 prompts."""
        return f"""
Business Purpose: {self.content_summary.purpose}
Target Users: {self.content_summary.user_context}
Key Workflows: {', '.join(self.content_summary.key_workflows)}
Journey Stage: {self.content_summary.user_journey_stage}
Business Importance: {self.content_summary.business_importance:.2f}
Navigation Role: {self.content_summary.navigation_role}
"""

    def get_contextual_keywords(self) -> list[str]:
        """Get contextual keywords for enhanced analysis."""
        return self.content_summary.contextual_keywords

    def get_workflow_dependencies(self) -> dict[str, Any]:
        """Extract workflow dependency information."""
        return {
            "workflows": self.content_summary.key_workflows,
            "entry_points": self.content_summary.entry_exit_points.get("entry", []),
            "exit_points": self.content_summary.entry_exit_points.get("exit", []),
            "journey_stage": self.content_summary.user_journey_stage
        }


class PriorityScore(BaseModel):
    """Priority scoring combining business importance and technical complexity."""

    business_importance: float = Field(description="Business importance (0.0-1.0)", ge=0.0, le=1.0)
    technical_complexity: float = Field(description="Technical complexity (0.0-1.0)", ge=0.0, le=1.0)
    user_impact: float = Field(description="User experience impact (0.0-1.0)", ge=0.0, le=1.0)
    implementation_effort: float = Field(description="Implementation effort (0.0-1.0)", ge=0.0, le=1.0)
    overall_priority: float = Field(default=0.0, description="Calculated overall priority (0.0-1.0)", ge=0.0, le=1.0)

    def calculate_priority(self) -> float:
        """Calculate overall priority score using weighted algorithm."""
        # Weighted algorithm: business importance (40%), user impact (30%),
        # complexity penalty (20%), effort penalty (10%)
        score = (
            self.business_importance * 0.4 +
            self.user_impact * 0.3 +
            (1.0 - self.technical_complexity) * 0.2 +  # Lower complexity = higher priority
            (1.0 - self.implementation_effort) * 0.1   # Lower effort = higher priority
        )
        self.overall_priority = max(0.0, min(1.0, score))
        return self.overall_priority


class ConsistencyValidation(BaseModel):
    """Validation results for consistency between Step 1 and Step 2."""

    is_consistent: bool = Field(description="Whether analysis steps are consistent")
    inconsistencies: list[str] = Field(
        default_factory=list,
        description="List of identified inconsistencies"
    )
    consistency_score: float = Field(
        description="Overall consistency score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    validation_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed validation results"
    )
    action_required: bool = Field(
        default=False,
        description="Whether manual review is required"
    )


class InteractiveElement(BaseModel):
    """Interactive element found on a page."""

    type: str = Field(description="Element type (button, form, input, etc.)")
    selector: str = Field(description="CSS selector or element identifier")
    purpose: str = Field(description="What the element does")
    behavior: str = Field(description="How the element behaves (click, submit, etc.)")

    # Context-aware enhancements
    business_context_relevance: str = Field(
        default="",
        description="How this element relates to business context from Step 1"
    )
    workflow_role: str = Field(
        default="",
        description="Role in identified workflows"
    )
    priority_score: PriorityScore | None = Field(
        default=None,
        description="Priority scoring based on business and technical factors"
    )


class FunctionalCapability(BaseModel):
    """Functional capability identified on a page."""

    name: str = Field(description="Capability name")
    description: str = Field(description="What the capability does")
    type: str = Field(description="Type of capability (feature, service, etc.)")
    complexity_score: float | None = Field(None, description="Complexity rating 0.0-1.0")

    # Context-aware enhancements
    business_alignment: str = Field(
        default="",
        description="How this capability aligns with business purpose"
    )
    user_journey_impact: str = Field(
        default="",
        description="Impact on user journey from Step 1 context"
    )
    priority_score: PriorityScore | None = Field(
        default=None,
        description="Priority scoring based on business and technical factors"
    )


class APIIntegration(BaseModel):
    """API integration found on a page."""
    
    endpoint: str = Field(description="API endpoint URL")
    method: str = Field(default="GET", description="HTTP method")
    purpose: str = Field(description="What the API does")
    data_flow: str = Field(description="Data flow direction")
    auth_type: str | None = Field(None, description="Authentication type")


class BusinessRule(BaseModel):
    """Business rule identified on a page."""
    
    name: str = Field(description="Rule name")
    description: str = Field(description="What the rule does")
    validation_logic: str = Field(description="How the rule works")
    error_handling: str | None = Field(None, description="Error handling approach")


class ThirdPartyIntegration(BaseModel):
    """Third-party service integration."""
    
    service_name: str = Field(description="Service name")
    integration_type: str = Field(description="Type of integration")
    purpose: str = Field(description="What the integration does")
    auth_method: str | None = Field(None, description="Authentication method")


class RebuildSpecification(BaseModel):
    """Specification for rebuilding a component or feature."""
    
    name: str = Field(description="Specification name")
    description: str = Field(description="What needs to be built")
    priority_score: float = Field(description="Priority 0.0-1.0")
    complexity: str = Field(default="medium", description="Complexity level")
    dependencies: list[str] = Field(default_factory=list, description="Dependencies")


class FeatureAnalysis(BaseModel):
    """Step 2 LLM analysis output with detailed feature breakdown."""

    interactive_elements: list[InteractiveElement] = Field(default_factory=list)
    functional_capabilities: list[FunctionalCapability] = Field(default_factory=list)
    api_integrations: list[APIIntegration] = Field(default_factory=list)
    business_rules: list[BusinessRule] = Field(default_factory=list)
    third_party_integrations: list[ThirdPartyIntegration] = Field(default_factory=list)
    rebuild_specifications: list[RebuildSpecification] = Field(default_factory=list)
    confidence_score: float = Field(
        default=0.0,
        description="Analysis confidence level (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    quality_score: float = Field(
        default=0.0,
        description="Analysis quality score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Context-aware enhancements
    context_integration_score: float = Field(
        default=0.0,
        description="How well Step 1 context was integrated (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    workflow_dependencies: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Identified workflow dependencies between features"
    )
    business_alignment_summary: str = Field(
        default="",
        description="Summary of how features align with business context"
    )
    context_validation: ConsistencyValidation | None = Field(
        default=None,
        description="Validation results against Step 1 context"
    )


class CombinedAnalysisResult(BaseModel):
    """Combined analysis result merging Step 1 and Step 2 with context passing."""

    content_summary: ContentSummary = Field(description="Step 1 analysis results")
    feature_analysis: FeatureAnalysis = Field(description="Step 2 analysis results")
    context_payload: ContextPayload = Field(description="Context data used for integration")

    # Analysis quality metrics
    overall_quality_score: float = Field(
        default=0.0,
        description="Combined quality score from both steps (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    analysis_completeness: float = Field(
        default=0.0,
        description="Completeness of the analysis (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Integration metrics
    context_utilization_score: float = Field(
        default=0.0,
        description="How effectively context was utilized (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    cross_reference_score: float = Field(
        default=0.0,
        description="Quality of cross-referencing between steps (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

    # Priority and workflow insights
    prioritized_features: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Features prioritized by business importance and complexity"
    )
    workflow_insights: dict[str, Any] = Field(
        default_factory=dict,
        description="Insights about workflow dependencies and user journeys"
    )

    # Validation and consistency
    consistency_validation: ConsistencyValidation = Field(
        default_factory=lambda: ConsistencyValidation(
            is_consistent=True,
            consistency_score=1.0
        ),
        description="Overall consistency validation between steps"
    )

    # Documentation and export data
    documentation_ready: bool = Field(
        default=False,
        description="Whether the analysis is ready for documentation generation"
    )
    export_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata for documentation and export pipelines"
    )

    def calculate_overall_metrics(self) -> None:
        """Calculate overall quality and completeness metrics."""
        # Overall quality is weighted average of step scores
        step1_weight = 0.3
        step2_weight = 0.5
        context_weight = 0.2

        self.overall_quality_score = (
            self.content_summary.confidence_score * step1_weight +
            self.feature_analysis.quality_score * step2_weight +
            self.feature_analysis.context_integration_score * context_weight
        )

        # Completeness based on data richness
        step1_completeness = self._calculate_step1_completeness()
        step2_completeness = self._calculate_step2_completeness()

        self.analysis_completeness = (step1_completeness + step2_completeness) / 2

        # Context utilization
        self.context_utilization_score = self.feature_analysis.context_integration_score

        # Cross-reference quality
        self.cross_reference_score = self.consistency_validation.consistency_score

    def _calculate_step1_completeness(self) -> float:
        """Calculate Step 1 analysis completeness."""
        required_fields = [
            self.content_summary.purpose,
            self.content_summary.user_context,
            self.content_summary.business_logic,
            self.content_summary.navigation_role
        ]

        optional_fields = [
            self.content_summary.key_workflows,
            self.content_summary.user_journey_stage,
            self.content_summary.contextual_keywords
        ]

        required_score = sum(1 for field in required_fields if field and field.strip()) / len(required_fields)
        optional_score = sum(1 for field in optional_fields if field) / len(optional_fields)

        return (required_score * 0.8) + (optional_score * 0.2)

    def _calculate_step2_completeness(self) -> float:
        """Calculate Step 2 analysis completeness."""
        feature_counts = [
            len(self.feature_analysis.interactive_elements),
            len(self.feature_analysis.functional_capabilities),
            len(self.feature_analysis.business_rules),
            len(self.feature_analysis.rebuild_specifications)
        ]

        # Score based on having features identified
        has_features = sum(1 for count in feature_counts if count > 0) / len(feature_counts)

        # Quality scores
        quality_score = (
            self.feature_analysis.confidence_score +
            self.feature_analysis.quality_score
        ) / 2

        return (has_features * 0.6) + (quality_score * 0.4)


__all__ = [
    # Enums
    "LLMProvider",
    "LLMRole",
    "LLMRequestType",
    "ProviderHealthStatus",
    # Data Models
    "LLMMessage",
    "LLMRequest",
    "TokenUsage",
    "LLMResponse",
    "ProviderHealth",
    "ProviderConfig",
    "CostTracking",
    "ContentSummary",
    "ContextPayload",
    "PriorityScore",
    "ConsistencyValidation",
    "InteractiveElement",
    "FunctionalCapability",
    "APIIntegration",
    "BusinessRule",
    "ThirdPartyIntegration",
    "RebuildSpecification",
    "FeatureAnalysis",
    "CombinedAnalysisResult",
    # Exceptions
    "LLMError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "TimeoutError",
    "ParseError",
    # Interface
    "LLMProviderInterface",
]