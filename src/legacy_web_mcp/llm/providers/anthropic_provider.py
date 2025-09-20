"""Anthropic provider implementation."""
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

_logger = structlog.get_logger("legacy_web_mcp.llm.providers.anthropic")


class AnthropicProvider(LLMProviderInterface):
    """Anthropic API provider implementation."""

    def __init__(self):
        self.config: ProviderConfig | None = None
        self.base_url: str = "https://api.anthropic.com/v1"
        self.session: aiohttp.ClientSession | None = None
        self.health_monitor = HealthMonitor()
        self.retry_config = RetryConfig()

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the Anthropic provider."""
        if not validate_api_key_format(config.api_key, LLMProvider.ANTHROPIC):
            raise ValidationError(
                "Invalid Anthropic API key format. Must start with 'sk-ant-'",
                LLMProvider.ANTHROPIC
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
            "anthropic_provider_initialized",
            base_url=self.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""
        if not self.config or not self.session:
            raise ValidationError("Provider not initialized", LLMProvider.ANTHROPIC)

        start_time = time.time()

        try:
            response = await retry_with_exponential_backoff(
                self._make_chat_request,
                self.retry_config,
                LLMProvider.ANTHROPIC,
                request,
            )

            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.record_success(LLMProvider.ANTHROPIC, response_time_ms)

            return response

        except Exception as e:
            self.health_monitor.record_failure(LLMProvider.ANTHROPIC, str(e))
            raise

    async def _make_chat_request(self, request: LLMRequest) -> LLMResponse:
        """Make the actual HTTP request to Anthropic API."""
        # Convert to Anthropic format
        anthropic_messages = []
        system_message = None

        for msg in request.messages:
            if msg.role.value == "system":
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

        payload = {
            "model": request.model or self.config.model,
            "messages": anthropic_messages,
            "max_tokens": request.max_tokens or 4096,
        }

        if system_message:
            payload["system"] = system_message
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        try:
            async with self.session.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers
            ) as response:
                response_data = await response.json()

                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid Anthropic API key",
                        LLMProvider.ANTHROPIC,
                        "authentication_failed"
                    )
                elif response.status == 429:
                    retry_after = response.headers.get("retry-after")
                    raise RateLimitError(
                        "Anthropic rate limit exceeded",
                        LLMProvider.ANTHROPIC,
                        retry_after=int(retry_after) if retry_after else None
                    )
                elif response.status >= 400:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise ValidationError(
                        f"Anthropic API error: {error_msg}",
                        LLMProvider.ANTHROPIC,
                        str(response.status)
                    )

                return self._parse_response(response_data, request)

        except aiohttp.ClientTimeout:
            raise TimeoutError("Anthropic API request timed out", LLMProvider.ANTHROPIC)
        except aiohttp.ClientError as e:
            raise TimeoutError(f"Anthropic API connection error: {e}", LLMProvider.ANTHROPIC)

    def _parse_response(self, response_data: dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Parse Anthropic API response into unified format."""
        try:
            content = ""
            if "content" in response_data and response_data["content"]:
                # Anthropic returns content as an array of content blocks
                for block in response_data["content"]:
                    if block.get("type") == "text":
                        content += block.get("text", "")

            model = response_data["model"]

            usage_data = response_data.get("usage", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
            )

            request_id = generate_request_id(content, LLMProvider.ANTHROPIC)
            cost_estimate = calculate_token_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                LLMProvider.ANTHROPIC,
                model,
            )

            return LLMResponse(
                content=content,
                model=model,
                provider=LLMProvider.ANTHROPIC,
                usage=usage,
                request_id=request_id,
                cost_estimate=cost_estimate,
                metadata={
                    "stop_reason": response_data.get("stop_reason"),
                    "stop_sequence": response_data.get("stop_sequence"),
                    "request_type": request.request_type.value,
                }
            )

        except (KeyError, IndexError, TypeError) as e:
            raise ParseError(
                f"Failed to parse Anthropic response: {e}",
                LLMProvider.ANTHROPIC
            )

    async def validate_api_key(self) -> bool:
        """Validate the API key and test connectivity."""
        if not self.config or not self.session:
            return False

        try:
            # Anthropic doesn't have a simple endpoint to test keys,
            # so we make a minimal request
            payload = {
                "model": self.config.model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1,
            }

            headers = {
                "x-api-key": self.config.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }

            async with self.session.post(
                f"{self.base_url}/messages",
                json=payload,
                headers=headers
            ) as response:
                return response.status in [200, 429]  # 429 means rate limited but key is valid

        except Exception as e:
            _logger.warning(
                "anthropic_api_key_validation_failed",
                error=sanitize_error_message(str(e))
            )
            return False

    async def check_health(self) -> ProviderHealth:
        """Check provider health status."""
        error_rate = self.health_monitor.get_error_rate(LLMProvider.ANTHROPIC)
        avg_response_time = self.health_monitor.get_average_response_time(LLMProvider.ANTHROPIC)

        # Determine health status based on error rate and connectivity
        if error_rate > 0.5:
            status = ProviderHealthStatus.UNHEALTHY
        elif error_rate > 0.2:
            status = ProviderHealthStatus.DEGRADED
        else:
            # Test connectivity
            is_healthy = await self.validate_api_key()
            status = ProviderHealthStatus.HEALTHY if is_healthy else ProviderHealthStatus.UNHEALTHY

        metrics = self.health_monitor.metrics.get(LLMProvider.ANTHROPIC, {})

        return ProviderHealth(
            provider=LLMProvider.ANTHROPIC,
            status=status,
            last_check=self.health_monitor.last_health_check.get(
                LLMProvider.ANTHROPIC,
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
            LLMProvider.ANTHROPIC,
            model,
        )

    def get_supported_models(self) -> list[str]:
        """Get list of supported Anthropic models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2",
        ]

    async def close(self) -> None:
        """Close the provider and clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

        _logger.info("anthropic_provider_closed")


__all__ = ["AnthropicProvider"]