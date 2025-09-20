"""Tests for LLM models and data structures."""
import pytest
from datetime import UTC, datetime

from legacy_web_mcp.llm.models import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMRequestType,
    LLMResponse,
    LLMRole,
    ProviderConfig,
    ProviderHealth,
    ProviderHealthStatus,
    TokenUsage,
)


class TestLLMMessage:
    """Test LLM message model."""

    def test_create_message(self):
        """Test creating a basic LLM message."""
        message = LLMMessage(
            role=LLMRole.USER,
            content="Hello, world!",
        )

        assert message.role == LLMRole.USER
        assert message.content == "Hello, world!"
        assert message.metadata == {}

    def test_message_with_metadata(self):
        """Test creating message with metadata."""
        metadata = {"timestamp": "2023-01-01", "source": "test"}
        message = LLMMessage(
            role=LLMRole.SYSTEM,
            content="System prompt",
            metadata=metadata,
        )

        assert message.metadata == metadata


class TestLLMRequest:
    """Test LLM request model."""

    def test_create_basic_request(self):
        """Test creating a basic LLM request."""
        messages = [
            LLMMessage(role=LLMRole.USER, content="Hello"),
        ]
        request = LLMRequest(messages=messages)

        assert len(request.messages) == 1
        assert request.messages[0].content == "Hello"
        assert request.request_type == LLMRequestType.CONTENT_SUMMARY
        assert request.model is None
        assert request.max_tokens is None
        assert request.temperature is None

    def test_create_detailed_request(self):
        """Test creating request with all parameters."""
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="You are a helpful assistant"),
            LLMMessage(role=LLMRole.USER, content="Analyze this page"),
        ]
        request = LLMRequest(
            messages=messages,
            model="gpt-4",
            max_tokens=1000,
            temperature=0.7,
            request_type=LLMRequestType.FEATURE_ANALYSIS,
            metadata={"page_url": "https://example.com"},
        )

        assert len(request.messages) == 2
        assert request.model == "gpt-4"
        assert request.max_tokens == 1000
        assert request.temperature == 0.7
        assert request.request_type == LLMRequestType.FEATURE_ANALYSIS
        assert request.metadata["page_url"] == "https://example.com"


class TestTokenUsage:
    """Test token usage model."""

    def test_create_token_usage(self):
        """Test creating token usage."""
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_token_usage_defaults(self):
        """Test token usage with defaults."""
        usage = TokenUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestLLMResponse:
    """Test LLM response model."""

    def test_create_response(self):
        """Test creating LLM response."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        response = LLMResponse(
            content="Generated response",
            model="gpt-3.5-turbo",
            provider=LLMProvider.OPENAI,
            usage=usage,
            request_id="test-123",
            cost_estimate=0.002,
        )

        assert response.content == "Generated response"
        assert response.model == "gpt-3.5-turbo"
        assert response.provider == LLMProvider.OPENAI
        assert response.usage.total_tokens == 150
        assert response.request_id == "test-123"
        assert response.cost_estimate == 0.002
        assert isinstance(response.timestamp, datetime)

    def test_response_with_metadata(self):
        """Test response with metadata."""
        usage = TokenUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75)
        metadata = {"finish_reason": "stop", "model_version": "20240101"}

        response = LLMResponse(
            content="Response",
            model="claude-3-haiku",
            provider=LLMProvider.ANTHROPIC,
            usage=usage,
            request_id="test-456",
            metadata=metadata,
        )

        assert response.metadata == metadata


class TestProviderConfig:
    """Test provider configuration model."""

    def test_create_config(self):
        """Test creating provider config."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test123",
            model="gpt-4",
            timeout=30.0,
        )

        assert config.provider == LLMProvider.OPENAI
        assert config.api_key == "sk-test123"
        assert config.model == "gpt-4"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.enabled is True

    def test_config_defaults(self):
        """Test config with defaults."""
        config = ProviderConfig(
            provider=LLMProvider.ANTHROPIC,
            api_key="sk-ant-test",
        )

        assert config.base_url is None
        assert config.model is None
        assert config.max_retries == 3
        assert config.timeout == 30.0
        assert config.rate_limit_rpm is None
        assert config.enabled is True


class TestProviderHealth:
    """Test provider health model."""

    def test_create_health_status(self):
        """Test creating provider health status."""
        last_check = datetime.now(UTC)
        health = ProviderHealth(
            provider=LLMProvider.GEMINI,
            status=ProviderHealthStatus.HEALTHY,
            last_check=last_check,
            response_time_ms=250.5,
            error_rate=0.05,
            success_count=95,
            failure_count=5,
        )

        assert health.provider == LLMProvider.GEMINI
        assert health.status == ProviderHealthStatus.HEALTHY
        assert health.last_check == last_check
        assert health.response_time_ms == 250.5
        assert health.error_rate == 0.05
        assert health.success_count == 95
        assert health.failure_count == 5

    def test_health_defaults(self):
        """Test health status with defaults."""
        health = ProviderHealth(
            provider=LLMProvider.OPENAI,
            status=ProviderHealthStatus.UNKNOWN,
            last_check=datetime.now(UTC),
        )

        assert health.response_time_ms is None
        assert health.error_rate == 0.0
        assert health.success_count == 0
        assert health.failure_count == 0
        assert health.last_error is None


class TestEnums:
    """Test enum values."""

    def test_llm_provider_values(self):
        """Test LLM provider enum values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.GEMINI == "gemini"

    def test_llm_role_values(self):
        """Test LLM role enum values."""
        assert LLMRole.SYSTEM == "system"
        assert LLMRole.USER == "user"
        assert LLMRole.ASSISTANT == "assistant"

    def test_request_type_values(self):
        """Test request type enum values."""
        assert LLMRequestType.CONTENT_SUMMARY == "content_summary"
        assert LLMRequestType.FEATURE_ANALYSIS == "feature_analysis"
        assert LLMRequestType.DIAGNOSTIC == "diagnostic"

    def test_health_status_values(self):
        """Test health status enum values."""
        assert ProviderHealthStatus.HEALTHY == "healthy"
        assert ProviderHealthStatus.DEGRADED == "degraded"
        assert ProviderHealthStatus.UNHEALTHY == "unhealthy"
        assert ProviderHealthStatus.UNKNOWN == "unknown"