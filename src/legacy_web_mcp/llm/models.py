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