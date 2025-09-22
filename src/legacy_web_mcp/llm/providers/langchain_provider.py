"""LangChain-based provider implementation."""
from __future__ import annotations

import time
import datetime
from typing import Any, Optional

import structlog
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from ..models import (
    AuthenticationError,
    LLMProvider,
    LLMProviderInterface,
    LLMRequest,
    LLMResponse,
    LLMRole,
    ParseError,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    TokenUsage,
    ValidationError,
)
from ..utils import (
    RetryConfig,
    calculate_token_cost,
    generate_request_id,
    retry_with_exponential_backoff,
    sanitize_error_message,
    validate_api_key_format,
    HealthMonitor,
)

_logger = structlog.get_logger("legacy_web_mcp.llm.providers.langchain")


class LangChainProvider(LLMProviderInterface):
    """LangChain-based universal provider for OpenAI, Anthropic, and Google."""

    def __init__(self, provider_type: LLMProvider):
        self.provider_type = provider_type
        self.config: Optional[ProviderConfig] = None
        self.model: Optional[BaseChatModel] = None
        self.health_monitor = HealthMonitor()
        self.retry_config = RetryConfig(max_attempts=3, min_wait=1.0, max_wait=60.0)

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the LangChain provider with configuration."""
        self.config = config

        # Validate API key format
        if not validate_api_key_format(config.api_key, self.provider_type):
            raise ValidationError(
                f"Invalid API key format for {self.provider_type.value}",
                self.provider_type
            )

        # Initialize the appropriate LangChain chat model
        try:
            if self.provider_type == LLMProvider.OPENAI:
                self.model = ChatOpenAI(
                    model=config.model,
                    openai_api_key=config.api_key,
                    temperature=0.0,
                    max_tokens=None,  # Let the model use its default
                )
            elif self.provider_type == LLMProvider.ANTHROPIC:
                self.model = ChatAnthropic(
                    model=config.model,
                    anthropic_api_key=config.api_key,
                    temperature=0.0,
                    max_tokens=4096,  # Anthropic requires max_tokens
                )
            elif self.provider_type == LLMProvider.GEMINI:
                self.model = ChatGoogleGenerativeAI(
                    model=config.model,
                    google_api_key=config.api_key,
                    temperature=0.0,
                )
            else:
                raise ValidationError(
                    f"Unsupported provider: {self.provider_type.value}",
                    self.provider_type
                )

            _logger.info(
                "langchain_provider_initialized",
                provider=self.provider_type.value,
                model=config.model
            )

        except Exception as e:
            _logger.error(
                "langchain_provider_init_failed",
                provider=self.provider_type.value,
                error=sanitize_error_message(str(e))
            )
            raise ValidationError(
                f"Failed to initialize {self.provider_type.value} provider: {str(e)}",
                self.provider_type
            ) from e

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute chat completion using LangChain."""
        if not self.model or not self.config:
            raise ValidationError(
                "Provider not initialized",
                self.provider_type
            )

        start_time = time.time()

        try:
            response = await retry_with_exponential_backoff(
                self._make_chat_request,
                self.retry_config,
                self.provider_type,
                request
            )

            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.record_success(self.provider_type, response_time_ms)

            return response

        except Exception as e:
            self.health_monitor.record_failure(self.provider_type, str(e))
            raise

    async def _make_chat_request(self, request: LLMRequest) -> LLMResponse:
        """Make the actual LangChain chat request."""
        # Convert LLMRequest messages to LangChain messages
        langchain_messages = []
        for msg in request.messages:
            if msg.role == LLMRole.SYSTEM:
                langchain_messages.append(SystemMessage(content=msg.content))
            elif msg.role == LLMRole.USER:
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == LLMRole.ASSISTANT:
                langchain_messages.append(AIMessage(content=msg.content))

        try:
            # Configure model parameters for this request
            model = self.model
            if request.temperature is not None:
                model = model.bind(temperature=request.temperature)
            if request.max_tokens and self.provider_type != LLMProvider.GEMINI:
                model = model.bind(max_tokens=request.max_tokens)

            # Invoke the model
            result = await model.ainvoke(langchain_messages)

            # Extract response content
            content = result.content if hasattr(result, 'content') else str(result)

            # Extract usage information if available
            usage_data = getattr(result, 'usage_metadata', {}) or {}
            prompt_tokens = usage_data.get('input_tokens', 0)
            completion_tokens = usage_data.get('output_tokens', 0)
            total_tokens = prompt_tokens + completion_tokens

            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )

            # Generate request ID and calculate cost
            request_id = generate_request_id(content, self.provider_type)
            cost_estimate = calculate_token_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                self.provider_type,
                self.config.model
            )

            # Extract additional metadata
            metadata = {
                "request_type": request.request_type.value,
                "provider": "langchain",
            }

            # Add provider-specific metadata
            if hasattr(result, 'response_metadata'):
                metadata.update(result.response_metadata)

            return LLMResponse(
                content=content,
                model=self.config.model,
                provider=self.provider_type,
                usage=usage,
                request_id=request_id,
                cost_estimate=cost_estimate,
                metadata=metadata
            )

        except Exception as e:
            error_message = str(e)

            # Map common LangChain/provider errors to our custom exceptions
            if "authentication" in error_message.lower() or "api key" in error_message.lower():
                raise AuthenticationError(
                    f"Authentication failed for {self.provider_type.value}: {error_message}",
                    self.provider_type
                ) from e
            elif "rate limit" in error_message.lower() or "quota" in error_message.lower():
                raise RateLimitError(
                    f"Rate limit exceeded for {self.provider_type.value}: {error_message}",
                    self.provider_type
                ) from e
            elif "timeout" in error_message.lower():
                raise LLMTimeoutError(
                    f"Request timeout for {self.provider_type.value}: {error_message}",
                    self.provider_type
                ) from e
            else:
                raise ValidationError(
                    f"LangChain request failed for {self.provider_type.value}: {error_message}",
                    self.provider_type
                ) from e

    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request."""
        if not self.model or not self.config:
            return False

        try:
            # Make a minimal test request
            test_message = [HumanMessage(content="Hi")]
            await self.model.ainvoke(test_message)
            return True
        except Exception as e:
            _logger.warning(
                "langchain_api_key_validation_failed",
                provider=self.provider_type.value,
                error=sanitize_error_message(str(e))
            )
            return False

    async def check_health(self) -> ProviderHealth:
        """Check provider health status."""
        error_rate = self.health_monitor.get_error_rate(self.provider_type)
        avg_response_time = self.health_monitor.get_average_response_time(self.provider_type)

        # Determine health status based on error rate and connectivity
        if error_rate > 0.5:
            status = ProviderHealthStatus.UNHEALTHY
        elif error_rate > 0.2:
            status = ProviderHealthStatus.DEGRADED
        else:
            # Test connectivity
            is_healthy = await self.validate_api_key()
            status = ProviderHealthStatus.HEALTHY if is_healthy else ProviderHealthStatus.UNHEALTHY

        metrics = self.health_monitor.metrics.get(self.provider_type, {})

        return ProviderHealth(
            provider=self.provider_type,
            status=status,
            last_check=self.health_monitor.last_health_check.get(
                self.provider_type,
                time.datetime.now(time.timezone.utc)
            ),
            response_time_ms=avg_response_time,
            error_rate=error_rate,
            success_count=metrics.get("success_count", 0),
            failure_count=metrics.get("failure_count", 0),
            last_error=metrics.get("last_error"),
        )

    def calculate_cost(self, usage: TokenUsage, model: str) -> float:
        """Calculate cost for token usage."""
        return calculate_token_cost(
            usage.prompt_tokens,
            usage.completion_tokens,
            self.provider_type,
            model,
        )

    def get_supported_models(self) -> list[str]:
        """Get list of supported models for this provider."""
        if self.provider_type == LLMProvider.OPENAI:
            return [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-4",
                "gpt-3.5-turbo"
            ]
        elif self.provider_type == LLMProvider.ANTHROPIC:
            return [
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ]
        elif self.provider_type == LLMProvider.GEMINI:
            return [
                "gemini-2.0-flash-exp",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-pro"
            ]
        else:
            return []

    async def close(self) -> None:
        """Close the provider and clean up resources."""
        # LangChain models don't typically need explicit cleanup
        self.model = None
        self.config = None

        _logger.info(
            "langchain_provider_closed",
            provider=self.provider_type.value
        )


__all__ = ["LangChainProvider"]