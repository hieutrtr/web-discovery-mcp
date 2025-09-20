"""Tests for LLM configuration manager."""
import pytest
from datetime import UTC, datetime
from unittest.mock import Mock

from legacy_web_mcp.config.settings import MCPSettings
from legacy_web_mcp.llm.config_manager import LLMConfigurationManager
from legacy_web_mcp.llm.models import LLMProvider, LLMRequestType


class TestLLMConfigurationManager:
    """Test LLM configuration manager functionality."""

    def test_initialization_with_defaults(self):
        """Test initialization with default settings."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        assert manager.model_config is not None
        assert manager.budget_config is not None
        assert manager.usage_records == []
        assert manager.budget_alerts == []

    def test_initialization_with_custom_models(self):
        """Test initialization with custom model settings."""
        settings = MCPSettings(
            STEP1_MODEL="fast",
            STEP2_MODEL="accurate",
            FALLBACK_MODEL="cheapest",
        )
        manager = LLMConfigurationManager(settings)

        # Should resolve logical names to actual models
        assert manager.model_config.step1_provider == LLMProvider.OPENAI
        assert manager.model_config.step1_model == "gpt-3.5-turbo"

    def test_get_model_for_request_type(self):
        """Test getting models for different request types."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        # Test different request types
        provider, model = manager.get_model_for_request_type(LLMRequestType.CONTENT_SUMMARY)
        assert provider in LLMProvider
        assert isinstance(model, str)

        provider, model = manager.get_model_for_request_type(LLMRequestType.FEATURE_ANALYSIS)
        assert provider in LLMProvider
        assert isinstance(model, str)

        provider, model = manager.get_model_for_request_type(LLMRequestType.DIAGNOSTIC)
        assert provider in LLMProvider
        assert isinstance(model, str)

    def test_get_fallback_chain(self):
        """Test getting fallback chains for request types."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        chain = manager.get_fallback_chain(LLMRequestType.CONTENT_SUMMARY)

        # Should have at least primary and fallback
        assert len(chain) >= 2

        # Each item should be a tuple of (provider, model)
        for provider, model in chain:
            assert provider in LLMProvider
            assert isinstance(model, str)

        # Should include additional fallbacks for redundancy
        providers_in_chain = [provider for provider, _ in chain]
        assert len(set(providers_in_chain)) >= 2  # Should have multiple providers

    def test_validate_configuration(self):
        """Test configuration validation."""
        settings = MCPSettings(
            STEP1_MODEL="gpt-3.5-turbo",
            STEP2_MODEL="gpt-4",
            FALLBACK_MODEL="claude-3-haiku-20240307",
        )
        manager = LLMConfigurationManager(settings)

        validation = manager.validate_configuration()

        assert "step1_model" in validation
        assert "step2_model" in validation
        assert "fallback_model" in validation

        # All should be valid models
        for model_name, is_valid in validation.items():
            assert is_valid is True

    def test_validate_configuration_with_invalid_models(self):
        """Test configuration validation with invalid models."""
        settings = MCPSettings(
            STEP1_MODEL="nonexistent-model",
            STEP2_MODEL="gpt-4",
            FALLBACK_MODEL="claude-3-haiku-20240307",
        )
        manager = LLMConfigurationManager(settings)

        validation = manager.validate_configuration()

        # step1_model should be invalid, others valid
        assert validation["step1_model"] is False
        assert validation["step2_model"] is True
        assert validation["fallback_model"] is True

    def test_record_usage(self):
        """Test recording usage for budget tracking."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        # Record some usage
        manager.record_usage(
            request_type=LLMRequestType.CONTENT_SUMMARY,
            provider=LLMProvider.OPENAI,
            model_id="gpt-3.5-turbo",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.002,
            page_url="https://example.com",
            project_id="test-project",
        )

        assert len(manager.usage_records) == 1
        record = manager.usage_records[0]

        assert record.request_type == LLMRequestType.CONTENT_SUMMARY
        assert record.provider == LLMProvider.OPENAI
        assert record.model_id == "gpt-3.5-turbo"
        assert record.prompt_tokens == 100
        assert record.completion_tokens == 50
        assert record.cost == 0.002
        assert record.page_url == "https://example.com"
        assert record.project_id == "test-project"

    def test_get_current_month_usage(self):
        """Test getting current month usage."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        # Add some usage records
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-3.5-turbo",
            100, 50, 0.002
        )
        manager.record_usage(
            LLMRequestType.FEATURE_ANALYSIS,
            LLMProvider.OPENAI,
            "gpt-4",
            200, 100, 0.01
        )

        usage = manager.get_current_month_usage()
        assert usage == 0.012  # 0.002 + 0.01

    def test_get_usage_by_model(self):
        """Test getting usage breakdown by model."""
        settings = MCPSettings()
        manager = LLMConfigurationManager(settings)

        # Add usage for different models
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-3.5-turbo",
            100, 50, 0.002
        )
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-3.5-turbo",
            150, 75, 0.003
        )
        manager.record_usage(
            LLMRequestType.FEATURE_ANALYSIS,
            LLMProvider.ANTHROPIC,
            "claude-3-haiku-20240307",
            200, 100, 0.005
        )

        usage_by_model = manager.get_usage_by_model()

        # Should have two models
        assert len(usage_by_model) == 2

        openai_key = "openai:gpt-3.5-turbo"
        anthropic_key = "anthropic:claude-3-haiku-20240307"

        assert openai_key in usage_by_model
        assert anthropic_key in usage_by_model

        # Check OpenAI model stats
        openai_stats = usage_by_model[openai_key]
        assert openai_stats["requests"] == 2
        assert openai_stats["total_cost"] == 0.005
        assert openai_stats["total_tokens"] == 375  # (100+50) + (150+75)

        # Check Anthropic model stats
        anthropic_stats = usage_by_model[anthropic_key]
        assert anthropic_stats["requests"] == 1
        assert anthropic_stats["total_cost"] == 0.005
        assert anthropic_stats["total_tokens"] == 300  # 200+100

    def test_budget_warning_threshold(self):
        """Test budget warning threshold triggers."""
        settings = MCPSettings(
            MONTHLY_BUDGET_LIMIT=10.0,
            BUDGET_WARNING_THRESHOLD=0.5,
        )
        manager = LLMConfigurationManager(settings)

        # Add usage that exceeds warning threshold
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-4",
            1000, 500, 6.0  # 60% of budget
        )

        # Should trigger warning
        assert len(manager.budget_alerts) == 1
        alert = manager.budget_alerts[0]
        assert alert.alert_type == "warning"
        assert alert.current_usage == 6.0
        assert alert.budget_limit == 10.0

    def test_budget_alert_threshold(self):
        """Test budget alert threshold triggers."""
        settings = MCPSettings(
            MONTHLY_BUDGET_LIMIT=10.0,
            BUDGET_ALERT_THRESHOLD=0.8,
        )
        manager = LLMConfigurationManager(settings)

        # Add usage that exceeds alert threshold
        manager.record_usage(
            LLMRequestType.FEATURE_ANALYSIS,
            LLMProvider.OPENAI,
            "gpt-4",
            2000, 1000, 9.0  # 90% of budget
        )

        # Should trigger alert
        assert len(manager.budget_alerts) == 1
        alert = manager.budget_alerts[0]
        assert alert.alert_type == "alert"
        assert alert.current_usage == 9.0
        assert alert.budget_limit == 10.0

    def test_no_duplicate_alerts(self):
        """Test that duplicate alerts aren't created in the same month."""
        settings = MCPSettings(
            MONTHLY_BUDGET_LIMIT=10.0,
            BUDGET_WARNING_THRESHOLD=0.5,
        )
        manager = LLMConfigurationManager(settings)

        # Add usage that exceeds warning threshold twice
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-4",
            1000, 500, 6.0
        )
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-4",
            500, 250, 1.0
        )

        # Should only have one warning alert
        warning_alerts = [a for a in manager.budget_alerts if a.alert_type == "warning"]
        assert len(warning_alerts) == 1

    def test_get_configuration_summary(self):
        """Test getting configuration summary."""
        settings = MCPSettings(
            STEP1_MODEL="fast",
            STEP2_MODEL="accurate",
            FALLBACK_MODEL="cheapest",
            MONTHLY_BUDGET_LIMIT=50.0,
        )
        manager = LLMConfigurationManager(settings)

        # Add some usage
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-3.5-turbo",
            100, 50, 0.002
        )

        summary = manager.get_configuration_summary()

        assert "model_configuration" in summary
        assert "budget_configuration" in summary
        assert "current_usage" in summary

        # Check model configuration
        model_config = summary["model_configuration"]
        assert "step1" in model_config
        assert "step2" in model_config
        assert "fallback" in model_config

        # Check budget configuration
        budget_config = summary["budget_configuration"]
        assert budget_config["monthly_limit"] == 50.0

        # Check current usage
        current_usage = summary["current_usage"]
        assert current_usage["monthly_spend"] == 0.002
        assert current_usage["total_requests"] == 1

    def test_get_recent_alerts(self):
        """Test getting recent budget alerts."""
        settings = MCPSettings(
            MONTHLY_BUDGET_LIMIT=10.0,
            BUDGET_WARNING_THRESHOLD=0.5,
        )
        manager = LLMConfigurationManager(settings)

        # Trigger a warning
        manager.record_usage(
            LLMRequestType.CONTENT_SUMMARY,
            LLMProvider.OPENAI,
            "gpt-4",
            1000, 500, 6.0
        )

        recent_alerts = manager.get_recent_alerts(days=30)
        assert len(recent_alerts) == 1
        assert recent_alerts[0].alert_type == "warning"

        # Test with shorter time range
        recent_alerts = manager.get_recent_alerts(days=0)
        assert len(recent_alerts) == 0