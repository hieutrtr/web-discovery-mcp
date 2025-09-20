"""OpenAI provider implementation."""
from __future__ import annotations

import time
from typing import Any

import aiohttp
import structlog

from ..models import (
    AuthenticationError,
    LLMProvider,
    LLMProviderInterface,
    LLMRequest,
    LLMResponse,
    ParseError,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
    RateLimitError,
    TimeoutError,
    TokenUsage,
    ValidationError,
)
from ..utils import (
    HealthMonitor,
    RetryConfig,
    calculate_token_cost,
    generate_request_id,
    retry_with_exponential_backoff,
    sanitize_error_message,
    validate_api_key_format,
)

_logger = structlog.get_logger("legacy_web_mcp.llm.providers.openai")


class OpenAIProvider(LLMProviderInterface):
    """OpenAI API provider implementation."""

    def __init__(self):
        self.config: ProviderConfig | None = None
        self.base_url: str = "https://api.openai.com/v1"
        self.session: aiohttp.ClientSession | None = None
        self.health_monitor = HealthMonitor()
        self.retry_config = RetryConfig()

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the OpenAI provider."""
        if not validate_api_key_format(config.api_key, LLMProvider.OPENAI):
            raise ValidationError(
                "Invalid OpenAI API key format. Must start with 'sk-'",
                LLMProvider.OPENAI
            )

        self.config = config
        if config.base_url:
            self.base_url = config.base_url.rstrip("/")

        # Create HTTP session with timeout configuration
        timeout = aiohttp.ClientTimeout(total=config.timeout)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": "LegacyWebMCP/1.0"}
        )

        _logger.info(
            "openai_provider_initialized",
            base_url=self.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""
        if not self.config or not self.session:
            raise ValidationError("Provider not initialized", LLMProvider.OPENAI)

        start_time = time.time()

        try:
            response = await retry_with_exponential_backoff(
                self._make_chat_request,
                self.retry_config,
                LLMProvider.OPENAI,
                request,
            )

            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.record_success(LLMProvider.OPENAI, response_time_ms)

            return response

        except Exception as e:
            self.health_monitor.record_failure(LLMProvider.OPENAI, str(e))
            raise

    async def _make_chat_request(self, request: LLMRequest) -> LLMResponse:
        """Make the actual HTTP request to OpenAI API."""
        # Convert to OpenAI format
        openai_messages = []
        for msg in request.messages:
            openai_messages.append({
                "role": msg.role.value,
                "content": msg.content,
            })

        payload = {
            "model": request.model or self.config.model,
            "messages": openai_messages,
        }

        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                response_data = await response.json()

                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid OpenAI API key",
                        LLMProvider.OPENAI,
                        "authentication_failed"
                    )
                elif response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise RateLimitError(
                        "OpenAI rate limit exceeded",
                        LLMProvider.OPENAI,
                        retry_after=int(retry_after) if retry_after else None
                    )
                elif response.status >= 400:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise ValidationError(
                        f"OpenAI API error: {error_msg}",
                        LLMProvider.OPENAI,
                        str(response.status)
                    )

                return self._parse_response(response_data, request)

        except aiohttp.ClientTimeout:
            raise TimeoutError("OpenAI API request timed out", LLMProvider.OPENAI)
        except aiohttp.ClientError as e:
            raise TimeoutError(f"OpenAI API connection error: {e}", LLMProvider.OPENAI)

    def _parse_response(self, response_data: dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Parse OpenAI API response into unified format."""
        try:
            choice = response_data["choices"][0]
            content = choice["message"]["content"]
            model = response_data["model"]

            usage_data = response_data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            request_id = generate_request_id(content, LLMProvider.OPENAI)
            cost_estimate = calculate_token_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                LLMProvider.OPENAI,
                model,
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=LLMProvider.OPENAI,
                usage=usage,
                request_id=request_id,
                cost_estimate=cost_estimate,
                metadata={
                    "finish_reason": choice.get("finish_reason"),
                    "request_type": request.request_type.value,
                }
            )

        except (KeyError, IndexError, TypeError) as e:
            raise ParseError(
                f"Failed to parse OpenAI response: {e}",
                LLMProvider.OPENAI
            )

    async def validate_api_key(self) -> bool:
        """Validate the API key and test connectivity."""
        if not self.config or not self.session:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
            }

            async with self.session.get(
                f"{self.base_url}/models",
                headers=headers
            ) as response:
                return response.status == 200

        except Exception as e:
            _logger.warning(
                "openai_api_key_validation_failed",
                error=sanitize_error_message(str(e))
            )
            return False

    async def check_health(self) -> ProviderHealth:
        """Check provider health status."""
        error_rate = self.health_monitor.get_error_rate(LLMProvider.OPENAI)
        avg_response_time = self.health_monitor.get_average_response_time(LLMProvider.OPENAI)

        # Determine health status based on error rate and connectivity
        if error_rate > 0.5:
            status = ProviderHealthStatus.UNHEALTHY
        elif error_rate > 0.2:
            status = ProviderHealthStatus.DEGRADED
        else:
            # Test connectivity
            is_healthy = await self.validate_api_key()
            status = ProviderHealthStatus.HEALTHY if is_healthy else ProviderHealthStatus.UNHEALTHY

        metrics = self.health_monitor.metrics.get(LLMProvider.OPENAI, {})

        return ProviderHealth(
            provider=LLMProvider.OPENAI,
            status=status,
            last_check=self.health_monitor.last_health_check.get(
                LLMProvider.OPENAI,
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
            LLMProvider.OPENAI,
            model,
        )

    def get_supported_models(self) -> list[str]:
        """Get list of supported OpenAI models."""
        return [
            "gpt-4.1-mini"
        ]

    async def close(self) -> None:
        """Close the provider and clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

        _logger.info("openai_provider_closed")


__all__ = ["OpenAIProvider"]