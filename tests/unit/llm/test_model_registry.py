"""Tests for LLM model registry."""
import pytest

from legacy_web_mcp.llm.model_registry import ModelRegistry, get_model_registry
from legacy_web_mcp.llm.models import LLMProvider, LLMRequestType


class TestModelRegistry:
    """Test model registry functionality."""

    def test_singleton_registry(self):
        """Test that get_model_registry returns the same instance."""
        registry1 = get_model_registry()
        registry2 = get_model_registry()
        assert registry1 is registry2

    def test_resolve_logical_model(self):
        """Test resolving logical model names."""
        registry = ModelRegistry()

        # Test logical mappings
        provider, model_id = registry.resolve_model("fast")
        assert provider == LLMProvider.OPENAI
        assert model_id == "gpt-3.5-turbo"

        provider, model_id = registry.resolve_model("accurate")
        assert provider == LLMProvider.OPENAI
        assert model_id == "gpt-4-turbo"

    def test_resolve_actual_model(self):
        """Test resolving actual model IDs."""
        registry = ModelRegistry()

        provider, model_id = registry.resolve_model("gpt-4")
        assert provider == LLMProvider.OPENAI
        assert model_id == "gpt-4"

        provider, model_id = registry.resolve_model("claude-3-haiku-20240307")
        assert provider == LLMProvider.ANTHROPIC
        assert model_id == "claude-3-haiku-20240307"

    def test_resolve_invalid_model(self):
        """Test error handling for invalid model names."""
        registry = ModelRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.resolve_model("nonexistent-model")

        assert "not found" in str(exc_info.value)
        assert "Available models" in str(exc_info.value)

    def test_resolve_empty_model(self):
        """Test error handling for empty model name."""
        registry = ModelRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.resolve_model("")

        assert "cannot be empty" in str(exc_info.value)

    def test_get_model_info(self):
        """Test getting model information."""
        registry = ModelRegistry()

        model_info = registry.get_model_info("gpt-4")
        assert model_info is not None
        assert model_info.provider == LLMProvider.OPENAI
        assert model_info.model_id == "gpt-4"
        assert model_info.context_length == 8192
        assert model_info.cost_per_1k_prompt > 0

        # Test non-existent model
        model_info = registry.get_model_info("nonexistent")
        assert model_info is None

    def test_get_models_for_provider(self):
        """Test getting models for specific providers."""
        registry = ModelRegistry()

        openai_models = registry.get_models_for_provider(LLMProvider.OPENAI)
        assert len(openai_models) > 0
        assert "gpt-4" in openai_models
        assert "gpt-3.5-turbo" in openai_models

        anthropic_models = registry.get_models_for_provider(LLMProvider.ANTHROPIC)
        assert len(anthropic_models) > 0
        assert "claude-3-haiku-20240307" in anthropic_models

        gemini_models = registry.get_models_for_provider(LLMProvider.GEMINI)
        assert len(gemini_models) > 0
        assert "gemini-pro" in gemini_models

    def test_get_recommended_model(self):
        """Test getting recommended models for request types."""
        registry = ModelRegistry()

        # Test without provider constraint
        model = registry.get_recommended_model(LLMRequestType.CONTENT_SUMMARY)
        assert model in registry.get_all_model_ids()

        # Test with provider constraint
        model = registry.get_recommended_model(
            LLMRequestType.FEATURE_ANALYSIS,
            provider=LLMProvider.OPENAI
        )
        openai_models = registry.get_models_for_provider(LLMProvider.OPENAI)
        assert model in openai_models

        # Test budget conscious recommendation
        budget_model = registry.get_recommended_model(
            LLMRequestType.CONTENT_SUMMARY,
            budget_conscious=True
        )
        expensive_model = registry.get_recommended_model(
            LLMRequestType.CONTENT_SUMMARY,
            budget_conscious=False
        )
        # Budget model should be different from expensive model in most cases
        assert budget_model in registry.get_all_model_ids()
        assert expensive_model in registry.get_all_model_ids()

    def test_validate_model_exists(self):
        """Test model existence validation."""
        registry = ModelRegistry()

        # Test valid models
        assert registry.validate_model_exists("gpt-4")
        assert registry.validate_model_exists("fast")  # logical name
        assert registry.validate_model_exists("claude-3-haiku-20240307")

        # Test invalid models
        assert not registry.validate_model_exists("nonexistent-model")
        assert not registry.validate_model_exists("")

    def test_get_all_logical_names(self):
        """Test getting all logical model names."""
        registry = ModelRegistry()

        logical_names = registry.get_all_logical_names()
        assert len(logical_names) > 0
        assert "fast" in logical_names
        assert "accurate" in logical_names
        assert "cheapest" in logical_names

    def test_get_all_model_ids(self):
        """Test getting all model IDs."""
        registry = ModelRegistry()

        model_ids = registry.get_all_model_ids()
        assert len(model_ids) > 0
        assert "gpt-4" in model_ids
        assert "claude-3-haiku-20240307" in model_ids
        assert "gemini-pro" in model_ids

    def test_get_model_cost_info(self):
        """Test getting model cost information."""
        registry = ModelRegistry()

        prompt_cost, completion_cost = registry.get_model_cost_info("gpt-4")
        assert prompt_cost > 0
        assert completion_cost > 0

        # Test non-existent model
        prompt_cost, completion_cost = registry.get_model_cost_info("nonexistent")
        assert prompt_cost == 0.0
        assert completion_cost == 0.0

    def test_calculate_cost(self):
        """Test cost calculation."""
        registry = ModelRegistry()

        # Test with known model
        cost = registry.calculate_cost("gpt-4", 1000, 500)
        assert cost > 0

        # Cost should be proportional to token count
        double_cost = registry.calculate_cost("gpt-4", 2000, 1000)
        assert abs(double_cost - (cost * 2)) < 0.001

        # Test with unknown model
        unknown_cost = registry.calculate_cost("nonexistent", 1000, 500)
        assert unknown_cost == 0.0

    def test_provider_specific_shortcuts(self):
        """Test provider-specific logical shortcuts."""
        registry = ModelRegistry()

        # Test OpenAI shortcuts
        provider, model = registry.resolve_model("openai-fast")
        assert provider == LLMProvider.OPENAI

        provider, model = registry.resolve_model("openai-best")
        assert provider == LLMProvider.OPENAI

        # Test Anthropic shortcuts
        provider, model = registry.resolve_model("anthropic-fast")
        assert provider == LLMProvider.ANTHROPIC

        provider, model = registry.resolve_model("anthropic-best")
        assert provider == LLMProvider.ANTHROPIC

        # Test Gemini shortcuts
        provider, model = registry.resolve_model("gemini-fast")
        assert provider == LLMProvider.GEMINI

        provider, model = registry.resolve_model("gemini-best")
        assert provider == LLMProvider.GEMINI

    def test_cost_tier_mappings(self):
        """Test cost-based model mappings."""
        registry = ModelRegistry()

        # Test cost mappings
        provider, model = registry.resolve_model("cheapest")
        cheapest_info = registry.get_model_info(model)

        provider, model = registry.resolve_model("expensive")
        expensive_info = registry.get_model_info(model)

        # Expensive model should cost more than cheapest
        cheapest_cost = cheapest_info.cost_per_1k_prompt + cheapest_info.cost_per_1k_completion
        expensive_cost = expensive_info.cost_per_1k_prompt + expensive_info.cost_per_1k_completion
        assert expensive_cost > cheapest_cost