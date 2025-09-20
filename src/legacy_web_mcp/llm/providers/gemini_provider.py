"""Gemini provider implementation."""
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

_logger = structlog.get_logger("legacy_web_mcp.llm.providers.gemini")


class GeminiProvider(LLMProviderInterface):
    """Google Gemini API provider implementation."""

    def __init__(self):
        self.config: ProviderConfig | None = None
        self.base_url: str = "https://generativelanguage.googleapis.com/v1beta"
        self.session: aiohttp.ClientSession | None = None
        self.health_monitor = HealthMonitor()
        self.retry_config = RetryConfig()

    async def initialize(self, config: ProviderConfig) -> None:
        """Initialize the Gemini provider."""
        if not validate_api_key_format(config.api_key, LLMProvider.GEMINI):
            raise ValidationError(
                "Invalid Gemini API key format",
                LLMProvider.GEMINI
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
            "gemini_provider_initialized",
            base_url=self.base_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
        )

    async def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """Execute a chat completion request."""
        if not self.config or not self.session:
            raise ValidationError("Provider not initialized", LLMProvider.GEMINI)

        start_time = time.time()

        try:
            response = await retry_with_exponential_backoff(
                self._make_chat_request,
                self.retry_config,
                LLMProvider.GEMINI,
                request,
            )

            response_time_ms = (time.time() - start_time) * 1000
            self.health_monitor.record_success(LLMProvider.GEMINI, response_time_ms)

            return response

        except Exception as e:
            self.health_monitor.record_failure(LLMProvider.GEMINI, str(e))
            raise

    async def _make_chat_request(self, request: LLMRequest) -> LLMResponse:
        """Make the actual HTTP request to Gemini API."""
        # Convert to Gemini format
        gemini_contents = []

        for msg in request.messages:
            # Gemini uses "user" and "model" roles
            role = "user" if msg.role.value in ["user", "system"] else "model"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })

        model_name = request.model or self.config.model

        payload = {
            "contents": gemini_contents,
        }

        # Add generation config if specified
        generation_config = {}
        if request.max_tokens:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature

        if generation_config:
            payload["generationConfig"] = generation_config

        url = f"{self.base_url}/models/{model_name}:generateContent"
        params = {"key": self.config.api_key}

        try:
            async with self.session.post(
                url,
                json=payload,
                params=params
            ) as response:
                response_data = await response.json()

                if response.status == 400:
                    error_msg = response_data.get("error", {}).get("message", "Bad request")
                    if "API_KEY" in error_msg:
                        raise AuthenticationError(
                            "Invalid Gemini API key",
                            LLMProvider.GEMINI,
                            "authentication_failed"
                        )
                    else:
                        raise ValidationError(
                            f"Gemini API error: {error_msg}",
                            LLMProvider.GEMINI,
                            str(response.status)
                        )
                elif response.status == 429:
                    raise RateLimitError(
                        "Gemini rate limit exceeded",
                        LLMProvider.GEMINI,
                    )
                elif response.status >= 400:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise ValidationError(
                        f"Gemini API error: {error_msg}",
                        LLMProvider.GEMINI,
                        str(response.status)
                    )

                return self._parse_response(response_data, request, model_name)

        except aiohttp.ClientTimeout:
            raise TimeoutError("Gemini API request timed out", LLMProvider.GEMINI)
        except aiohttp.ClientError as e:
            raise TimeoutError(f"Gemini API connection error: {e}", LLMProvider.GEMINI)

    def _parse_response(self, response_data: dict[str, Any], request: LLMRequest, model: str) -> LLMResponse:
        """Parse Gemini API response into unified format."""
        try:
            content = ""

            if "candidates" in response_data and response_data["candidates"]:
                candidate = response_data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            content += part["text"]

            # Gemini doesn't always provide token usage in the response
            usage_data = response_data.get("usageMetadata", {})
            usage = TokenUsage(
                prompt_tokens=usage_data.get("promptTokenCount", 0),
                completion_tokens=usage_data.get("candidatesTokenCount", 0),
                total_tokens=usage_data.get("totalTokenCount", 0),
            )

            request_id = generate_request_id(content, LLMProvider.GEMINI)
            cost_estimate = calculate_token_cost(
                usage.prompt_tokens,
                usage.completion_tokens,
                LLMProvider.GEMINI,
                model,
            )

            # Extract safety ratings and finish reason
            metadata = {"request_type": request.request_type.value}

            if "candidates" in response_data and response_data["candidates"]:
                candidate = response_data["candidates"][0]
                metadata["finish_reason"] = candidate.get("finishReason")
                metadata["safety_ratings"] = candidate.get("safetyRatings", [])

            return LLMResponse(
                content=content,
                model=model,
                provider=LLMProvider.GEMINI,
                usage=usage,
                request_id=request_id,
                cost_estimate=cost_estimate,
                metadata=metadata
            )

        except (KeyError, IndexError, TypeError) as e:
            raise ParseError(
                f"Failed to parse Gemini response: {e}",
                LLMProvider.GEMINI
            )

    async def validate_api_key(self) -> bool:
        """Validate the API key and test connectivity."""
        if not self.config or not self.session:
            return False

        try:
            # Test with a simple request
            url = f"{self.base_url}/models"
            params = {"key": self.config.api_key}

            async with self.session.get(url, params=params) as response:
                return response.status == 200

        except Exception as e:
            _logger.warning(
                "gemini_api_key_validation_failed",
                error=sanitize_error_message(str(e))
            )
            return False

    async def check_health(self) -> ProviderHealth:
        """Check provider health status."""
        error_rate = self.health_monitor.get_error_rate(LLMProvider.GEMINI)
        avg_response_time = self.health_monitor.get_average_response_time(LLMProvider.GEMINI)

        # Determine health status based on error rate and connectivity
        if error_rate > 0.5:
            status = ProviderHealthStatus.UNHEALTHY
        elif error_rate > 0.2:
            status = ProviderHealthStatus.DEGRADED
        else:
            # Test connectivity
            is_healthy = await self.validate_api_key()
            status = ProviderHealthStatus.HEALTHY if is_healthy else ProviderHealthStatus.UNHEALTHY

        metrics = self.health_monitor.metrics.get(LLMProvider.GEMINI, {})

        return ProviderHealth(
            provider=LLMProvider.GEMINI,
            status=status,
            last_check=self.health_monitor.last_health_check.get(
                LLMProvider.GEMINI,
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
            LLMProvider.GEMINI,
            model,
        )

    def get_supported_models(self) -> list[str]:
        """Get list of supported Gemini models."""
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    async def close(self) -> None:
        """Close the provider and clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

        _logger.info("gemini_provider_closed")


__all__ = ["GeminiProvider"]