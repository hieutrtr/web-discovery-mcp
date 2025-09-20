"""Utilities for LLM provider interface."""
from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .models import (
    AuthenticationError,
    LLMError,
    LLMProvider,
    ParseError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

_logger = structlog.get_logger("legacy_web_mcp.llm.utils")

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry logic."""

    def __init__(
        self,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 60.0,
        multiplier: float = 2.0,
    ):
        self.max_attempts = max_attempts
        self.min_wait = min_wait
        self.max_wait = max_wait
        self.multiplier = multiplier


async def retry_with_exponential_backoff(
    func: Callable[..., T],
    config: RetryConfig,
    provider: LLMProvider | None = None,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Execute function with exponential backoff retry logic."""

    def is_retryable_error(exception: Exception) -> bool:
        """Determine if an exception is retryable."""
        if isinstance(exception, (RateLimitError, TimeoutError)):
            return True
        if isinstance(exception, (AuthenticationError, ValidationError, ParseError)):
            return False
        if isinstance(exception, LLMError):
            return exception.retryable
        # Network-related errors are typically retryable
        if isinstance(exception, (asyncio.TimeoutError, ConnectionError)):
            return True
        return False

    async for attempt in AsyncRetrying(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(
            multiplier=config.multiplier,
            min=config.min_wait,
            max=config.max_wait,
        ),
        reraise=True,
    ):
        with attempt:
            try:
                _logger.debug(
                    "llm_request_attempt",
                    provider=provider.value if provider else None,
                    attempt_number=attempt.retry_state.attempt_number,
                )
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                if not is_retryable_error(e):
                    _logger.error(
                        "llm_request_failed_permanently",
                        provider=provider.value if provider else None,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                _logger.warning(
                    "llm_request_failed_retrying",
                    provider=provider.value if provider else None,
                    attempt=attempt.retry_state.attempt_number,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                if isinstance(e, RateLimitError) and e.retry_after:
                    _logger.info(
                        "rate_limit_retry_delay",
                        provider=provider.value if provider else None,
                        retry_after=e.retry_after,
                    )
                    await asyncio.sleep(e.retry_after)

                raise


def validate_api_key_format(api_key: str, provider: LLMProvider) -> bool:
    """Validate API key format for each provider."""
    if not api_key or not isinstance(api_key, str):
        return False

    api_key = api_key.strip()

    if provider == LLMProvider.OPENAI:
        # OpenAI keys start with "sk-" and are typically 51 characters
        return api_key.startswith("sk-") and len(api_key) >= 20

    elif provider == LLMProvider.ANTHROPIC:
        # Anthropic keys start with "sk-ant-"
        return api_key.startswith("sk-ant-") and len(api_key) >= 20

    elif provider == LLMProvider.GEMINI:
        # Gemini API keys are typically 39 characters, alphanumeric + hyphens
        return len(api_key) >= 20 and re.match(r"^[A-Za-z0-9_-]+$", api_key)

    return False


def generate_request_id(content: str, provider: LLMProvider) -> str:
    """Generate a unique request ID based on content and provider."""
    timestamp = datetime.now(UTC).isoformat()
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"{provider.value}-{content_hash}-{timestamp}"


def sanitize_error_message(error_message: str) -> str:
    """Sanitize error messages to remove sensitive information."""
    # Remove API keys
    error_message = re.sub(r"sk-[A-Za-z0-9-_]{20,}", "[API_KEY_REDACTED]", error_message)
    error_message = re.sub(r"sk-ant-[A-Za-z0-9-_]{20,}", "[API_KEY_REDACTED]", error_message)

    # Remove other potential sensitive patterns
    error_message = re.sub(r"Bearer [A-Za-z0-9-_]{20,}", "[TOKEN_REDACTED]", error_message)
    error_message = re.sub(r"api[_-]?key[\"'\s]*[:=][\"'\s]*[A-Za-z0-9-_]{20,}", "api_key=[REDACTED]", error_message, flags=re.IGNORECASE)

    return error_message


def calculate_token_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: LLMProvider,
    model: str,
) -> float:
    """Calculate cost based on token usage and provider pricing."""

    # Pricing per 1K tokens (as of 2025) - these should be configurable
    pricing = {
        LLMProvider.OPENAI: {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4.1-mini": {"prompt": 0.0004, "completion": 0.002},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
        },
        LLMProvider.ANTHROPIC: {
            "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku": {"prompt": 0.00025, "completion": 0.00125},
        },
        LLMProvider.GEMINI: {
            "gemini-pro": {"prompt": 0.000125, "completion": 0.000375},
            "gemini-pro-vision": {"prompt": 0.00025, "completion": 0.0005},
        },
    }

    provider_pricing = pricing.get(provider)
    if not provider_pricing:
        return 0.0

    model_pricing = provider_pricing.get(model)
    if not model_pricing:
        # Try to find a default model or use the first available
        model_pricing = next(iter(provider_pricing.values()), {"prompt": 0.0, "completion": 0.0})

    prompt_cost = (prompt_tokens / 1000) * model_pricing["prompt"]
    completion_cost = (completion_tokens / 1000) * model_pricing["completion"]

    return prompt_cost + completion_cost


class HealthMonitor:
    """Monitors provider health and tracks metrics."""

    def __init__(self):
        self.metrics: dict[LLMProvider, dict[str, Any]] = {}
        self.last_health_check: dict[LLMProvider, datetime] = {}

    def record_success(self, provider: LLMProvider, response_time_ms: float) -> None:
        """Record a successful request."""
        if provider not in self.metrics:
            self.metrics[provider] = {
                "success_count": 0,
                "failure_count": 0,
                "total_response_time": 0.0,
                "last_error": None,
            }

        self.metrics[provider]["success_count"] += 1
        self.metrics[provider]["total_response_time"] += response_time_ms
        self.last_health_check[provider] = datetime.now(UTC)

    def record_failure(self, provider: LLMProvider, error: str) -> None:
        """Record a failed request."""
        if provider not in self.metrics:
            self.metrics[provider] = {
                "success_count": 0,
                "failure_count": 0,
                "total_response_time": 0.0,
                "last_error": None,
            }

        self.metrics[provider]["failure_count"] += 1
        self.metrics[provider]["last_error"] = sanitize_error_message(error)
        self.last_health_check[provider] = datetime.now(UTC)

    def get_error_rate(self, provider: LLMProvider) -> float:
        """Get error rate for a provider."""
        if provider not in self.metrics:
            return 0.0

        metrics = self.metrics[provider]
        total_requests = metrics["success_count"] + metrics["failure_count"]

        if total_requests == 0:
            return 0.0

        return metrics["failure_count"] / total_requests

    def get_average_response_time(self, provider: LLMProvider) -> float:
        """Get average response time for a provider."""
        if provider not in self.metrics:
            return 0.0

        metrics = self.metrics[provider]
        success_count = metrics["success_count"]

        if success_count == 0:
            return 0.0

        return metrics["total_response_time"] / success_count

    def reset_metrics(self, provider: LLMProvider) -> None:
        """Reset metrics for a provider."""
        if provider in self.metrics:
            self.metrics[provider] = {
                "success_count": 0,
                "failure_count": 0,
                "total_response_time": 0.0,
                "last_error": None,
            }


__all__ = [
    "RetryConfig",
    "retry_with_exponential_backoff",
    "validate_api_key_format",
    "generate_request_id",
    "sanitize_error_message",
    "calculate_token_cost",
    "HealthMonitor",
]