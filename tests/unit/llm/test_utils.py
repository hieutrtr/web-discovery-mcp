"""Tests for LLM utilities."""
import pytest
from unittest.mock import AsyncMock, Mock
import asyncio

from legacy_web_mcp.llm.models import (
    AuthenticationError,
    LLMError,
    LLMProvider,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from legacy_web_mcp.llm.utils import (
    HealthMonitor,
    RetryConfig,
    calculate_token_cost,
    generate_request_id,
    retry_with_exponential_backoff,
    sanitize_error_message,
    validate_api_key_format,
)


class TestApiKeyValidation:
    """Test API key format validation."""

    def test_valid_openai_key(self):
        """Test valid OpenAI API key."""
        assert validate_api_key_format("sk-1234567890abcdef1234567890abcdef1234567890", LLMProvider.OPENAI)
        assert validate_api_key_format("sk-abc123", LLMProvider.OPENAI)

    def test_invalid_openai_key(self):
        """Test invalid OpenAI API key."""
        assert not validate_api_key_format("invalid-key", LLMProvider.OPENAI)
        assert not validate_api_key_format("pk-1234567890", LLMProvider.OPENAI)
        assert not validate_api_key_format("sk-", LLMProvider.OPENAI)
        assert not validate_api_key_format("", LLMProvider.OPENAI)

    def test_valid_anthropic_key(self):
        """Test valid Anthropic API key."""
        assert validate_api_key_format("sk-ant-1234567890abcdef", LLMProvider.ANTHROPIC)
        assert validate_api_key_format("sk-ant-api03-1234567890abcdef", LLMProvider.ANTHROPIC)

    def test_invalid_anthropic_key(self):
        """Test invalid Anthropic API key."""
        assert not validate_api_key_format("sk-1234567890", LLMProvider.ANTHROPIC)
        assert not validate_api_key_format("ant-1234567890", LLMProvider.ANTHROPIC)
        assert not validate_api_key_format("sk-ant-", LLMProvider.ANTHROPIC)
        assert not validate_api_key_format("", LLMProvider.ANTHROPIC)

    def test_valid_gemini_key(self):
        """Test valid Gemini API key."""
        assert validate_api_key_format("AIzaSyAbc123def456ghi789jkl012mno345pqr", LLMProvider.GEMINI)
        assert validate_api_key_format("1234567890abcdef1234567890abcdef12345678", LLMProvider.GEMINI)

    def test_invalid_gemini_key(self):
        """Test invalid Gemini API key."""
        assert not validate_api_key_format("too_short", LLMProvider.GEMINI)
        assert not validate_api_key_format("invalid@characters!", LLMProvider.GEMINI)
        assert not validate_api_key_format("", LLMProvider.GEMINI)

    def test_none_or_empty_keys(self):
        """Test None or empty keys."""
        for provider in LLMProvider:
            assert not validate_api_key_format(None, provider)
            assert not validate_api_key_format("", provider)
            assert not validate_api_key_format("   ", provider)


class TestRequestIdGeneration:
    """Test request ID generation."""

    def test_generate_request_id(self):
        """Test generating request IDs."""
        content = "Hello, world!"
        request_id = generate_request_id(content, LLMProvider.OPENAI)

        assert request_id.startswith("openai-")
        assert len(request_id.split("-")) >= 3

    def test_different_content_different_ids(self):
        """Test that different content generates different IDs."""
        id1 = generate_request_id("content1", LLMProvider.OPENAI)
        id2 = generate_request_id("content2", LLMProvider.OPENAI)

        assert id1 != id2

    def test_same_content_different_timestamps(self):
        """Test same content at different times generates different IDs."""
        content = "same content"
        id1 = generate_request_id(content, LLMProvider.OPENAI)
        # Small delay to ensure different timestamp
        import time
        time.sleep(0.001)
        id2 = generate_request_id(content, LLMProvider.OPENAI)

        assert id1 != id2


class TestErrorMessageSanitization:
    """Test error message sanitization."""

    def test_sanitize_openai_key(self):
        """Test sanitizing OpenAI API keys from error messages."""
        error_msg = "Authentication failed with key sk-1234567890abcdef"
        sanitized = sanitize_error_message(error_msg)

        assert "sk-1234567890abcdef" not in sanitized
        assert "[API_KEY_REDACTED]" in sanitized

    def test_sanitize_anthropic_key(self):
        """Test sanitizing Anthropic API keys."""
        error_msg = "Invalid key: sk-ant-api03-1234567890abcdef"
        sanitized = sanitize_error_message(error_msg)

        assert "sk-ant-api03-1234567890abcdef" not in sanitized
        assert "[API_KEY_REDACTED]" in sanitized

    def test_sanitize_bearer_token(self):
        """Test sanitizing Bearer tokens."""
        error_msg = "Authorization: Bearer abc123def456"
        sanitized = sanitize_error_message(error_msg)

        assert "abc123def456" not in sanitized
        assert "[TOKEN_REDACTED]" in sanitized

    def test_sanitize_api_key_assignment(self):
        """Test sanitizing API key assignments."""
        error_msg = 'Configuration error: api_key="sk-1234567890abcdef"'
        sanitized = sanitize_error_message(error_msg)

        assert "sk-1234567890abcdef" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_no_sensitive_data(self):
        """Test message with no sensitive data."""
        error_msg = "Network timeout occurred"
        sanitized = sanitize_error_message(error_msg)

        assert sanitized == error_msg


class TestTokenCostCalculation:
    """Test token cost calculation."""

    def test_openai_gpt4_cost(self):
        """Test OpenAI GPT-4 cost calculation."""
        cost = calculate_token_cost(1000, 500, LLMProvider.OPENAI, "gpt-4")

        # GPT-4: $0.03 per 1K prompt tokens, $0.06 per 1K completion tokens
        expected = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        assert cost == expected

    def test_anthropic_claude_cost(self):
        """Test Anthropic Claude cost calculation."""
        cost = calculate_token_cost(1000, 500, LLMProvider.ANTHROPIC, "claude-3-haiku")

        # Claude-3-haiku: $0.00025 per 1K prompt tokens, $0.00125 per 1K completion tokens
        expected = (1000 / 1000) * 0.00025 + (500 / 1000) * 0.00125
        assert cost == expected

    def test_gemini_cost(self):
        """Test Gemini cost calculation."""
        cost = calculate_token_cost(1000, 500, LLMProvider.GEMINI, "gemini-pro")

        # Gemini Pro: $0.000125 per 1K prompt tokens, $0.000375 per 1K completion tokens
        expected = (1000 / 1000) * 0.000125 + (500 / 1000) * 0.000375
        assert cost == expected

    def test_unknown_provider(self):
        """Test cost calculation for unknown provider."""
        # This should return 0.0 for unknown providers
        cost = calculate_token_cost(1000, 500, "unknown_provider", "unknown_model")
        assert cost == 0.0

    def test_unknown_model(self):
        """Test cost calculation for unknown model."""
        # Should use default pricing for the provider
        cost = calculate_token_cost(1000, 500, LLMProvider.OPENAI, "unknown_model")
        assert cost > 0.0  # Should still calculate some cost


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_retry(self):
        """Test successful execution without retry."""
        mock_func = AsyncMock(return_value="success")
        config = RetryConfig(max_attempts=3)

        result = await retry_with_exponential_backoff(
            mock_func,
            config,
            LLMProvider.OPENAI,
        )

        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry on timeout error."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            TimeoutError("timeout", LLMProvider.OPENAI),
            "success"
        ]
        config = RetryConfig(max_attempts=3, min_wait=0.001, max_wait=0.002)

        result = await retry_with_exponential_backoff(
            mock_func,
            config,
            LLMProvider.OPENAI,
        )

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self):
        """Test no retry on authentication error."""
        mock_func = AsyncMock()
        mock_func.side_effect = AuthenticationError("auth failed", LLMProvider.OPENAI)
        config = RetryConfig(max_attempts=3)

        with pytest.raises(AuthenticationError):
            await retry_with_exponential_backoff(
                mock_func,
                config,
                LLMProvider.OPENAI,
            )

        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        """Test max attempts exceeded."""
        mock_func = AsyncMock()
        mock_func.side_effect = TimeoutError("timeout", LLMProvider.OPENAI)
        config = RetryConfig(max_attempts=2, min_wait=0.001, max_wait=0.002)

        with pytest.raises(TimeoutError):
            await retry_with_exponential_backoff(
                mock_func,
                config,
                LLMProvider.OPENAI,
            )

        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry_after(self):
        """Test rate limit error with retry-after header."""
        mock_func = AsyncMock()
        rate_limit_error = RateLimitError("rate limited", LLMProvider.OPENAI, retry_after=1)
        mock_func.side_effect = [rate_limit_error, "success"]
        config = RetryConfig(max_attempts=3, min_wait=0.001, max_wait=0.002)

        # Mock asyncio.sleep to avoid actual delays in tests
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()

        try:
            result = await retry_with_exponential_backoff(
                mock_func,
                config,
                LLMProvider.OPENAI,
            )

            assert result == "success"
            assert mock_func.call_count == 2
            # Should have called sleep with retry_after value
            asyncio.sleep.assert_called_with(1)
        finally:
            asyncio.sleep = original_sleep


class TestHealthMonitor:
    """Test health monitoring functionality."""

    def test_record_success(self):
        """Test recording successful requests."""
        monitor = HealthMonitor()

        monitor.record_success(LLMProvider.OPENAI, 150.5)

        assert LLMProvider.OPENAI in monitor.metrics
        metrics = monitor.metrics[LLMProvider.OPENAI]
        assert metrics["success_count"] == 1
        assert metrics["failure_count"] == 0
        assert metrics["total_response_time"] == 150.5

    def test_record_failure(self):
        """Test recording failed requests."""
        monitor = HealthMonitor()

        monitor.record_failure(LLMProvider.OPENAI, "Connection timeout")

        assert LLMProvider.OPENAI in monitor.metrics
        metrics = monitor.metrics[LLMProvider.OPENAI]
        assert metrics["success_count"] == 0
        assert metrics["failure_count"] == 1
        assert "timeout" in metrics["last_error"].lower()

    def test_error_rate_calculation(self):
        """Test error rate calculation."""
        monitor = HealthMonitor()

        # Record some successes and failures
        monitor.record_success(LLMProvider.OPENAI, 100.0)
        monitor.record_success(LLMProvider.OPENAI, 150.0)
        monitor.record_failure(LLMProvider.OPENAI, "Error")

        error_rate = monitor.get_error_rate(LLMProvider.OPENAI)
        assert error_rate == 1/3  # 1 failure out of 3 total requests

    def test_average_response_time(self):
        """Test average response time calculation."""
        monitor = HealthMonitor()

        monitor.record_success(LLMProvider.OPENAI, 100.0)
        monitor.record_success(LLMProvider.OPENAI, 200.0)

        avg_time = monitor.get_average_response_time(LLMProvider.OPENAI)
        assert avg_time == 150.0

    def test_metrics_for_unknown_provider(self):
        """Test metrics for provider with no data."""
        monitor = HealthMonitor()

        error_rate = monitor.get_error_rate(LLMProvider.GEMINI)
        avg_time = monitor.get_average_response_time(LLMProvider.GEMINI)

        assert error_rate == 0.0
        assert avg_time == 0.0

    def test_reset_metrics(self):
        """Test resetting metrics for a provider."""
        monitor = HealthMonitor()

        monitor.record_success(LLMProvider.OPENAI, 100.0)
        monitor.record_failure(LLMProvider.OPENAI, "Error")

        monitor.reset_metrics(LLMProvider.OPENAI)

        error_rate = monitor.get_error_rate(LLMProvider.OPENAI)
        avg_time = monitor.get_average_response_time(LLMProvider.OPENAI)

        assert error_rate == 0.0
        assert avg_time == 0.0


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.min_wait == 1.0
        assert config.max_wait == 60.0
        assert config.multiplier == 2.0

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            min_wait=0.5,
            max_wait=30.0,
            multiplier=1.5,
        )

        assert config.max_attempts == 5
        assert config.min_wait == 0.5
        assert config.max_wait == 30.0
        assert config.multiplier == 1.5