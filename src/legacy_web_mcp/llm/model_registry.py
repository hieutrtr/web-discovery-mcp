"""Model registry for provider-specific model mapping and configuration."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from .models import LLMProvider, LLMRequestType

_logger = structlog.get_logger("legacy_web_mcp.llm.model_registry")


@dataclass
class ModelInfo:
    """Information about a specific model."""

    provider: LLMProvider
    model_id: str
    display_name: str
    context_length: int
    cost_per_1k_prompt: float
    cost_per_1k_completion: float
    best_for: list[LLMRequestType]
    deprecated: bool = False


class ModelRegistry:
    """Registry for mapping logical model names to provider-specific models."""

    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        self._logical_mappings: dict[str, str] = {}
        self._provider_models: dict[LLMProvider, list[str]] = {}
        self._initialize_models()
        self._initialize_logical_mappings()

    def _initialize_models(self) -> None:
        """Initialize the model registry with updated cost-effective models."""
        models = [
            # OpenAI Models 2024-2025 (Cost-Optimized)
            ModelInfo(
                provider=LLMProvider.OPENAI,
                model_id="gpt-4.1",
                display_name="GPT-4.1 (Optimized)",
                context_length=1047576,  # ~1M
                cost_per_1k_prompt=0.002,  # $2/1M tokens
                cost_per_1k_completion=0.008,  # $8/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS],
            ),
            ModelInfo(
                provider=LLMProvider.OPENAI,
                model_id="gpt-4.1-mini",
                display_name="GPT-4.1 Mini",
                context_length=1047576,  # ~1M
                cost_per_1k_prompt=0.0004,  # $0.40/1M tokens
                cost_per_1k_completion=0.0016,  # $1.60/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS, LLMRequestType.CONTENT_SUMMARY],
            ),
            ModelInfo(
                provider=LLMProvider.OPENAI,
                model_id="gpt-4o-mini",
                display_name="GPT-4o Mini",
                context_length=128000,
                cost_per_1k_prompt=0.00015,  # $0.15/1M tokens
                cost_per_1k_completion=0.0006,  # $0.60/1M tokens
                best_for=[LLMRequestType.CONTENT_SUMMARY, LLMRequestType.DIAGNOSTIC],
            ),
            # Anthropic Models 2024-2025 (Cost-Optimized)
            ModelInfo(
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-3-5-sonnet-20241022",
                display_name="Claude 3.5 Sonnet (Oct 2024)",
                context_length=200000,
                cost_per_1k_prompt=0.003,  # $3/1M tokens
                cost_per_1k_completion=0.015,  # $15/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS],
            ),
            ModelInfo(
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-3-5-haiku-20241022",
                display_name="Claude 3.5 Haiku (Oct 2024)",
                context_length=200000,
                cost_per_1k_prompt=0.00025,  # $0.25/1M tokens
                cost_per_1k_completion=0.00125,  # $1.25/1M tokens
                best_for=[LLMRequestType.CONTENT_SUMMARY, LLMRequestType.DIAGNOSTIC],
            ),
            # Gemini Models 2024-2025 (Ultra Cost-Effective)
            ModelInfo(
                provider=LLMProvider.GEMINI,
                model_id="gemini-2.0-flash-lite",
                display_name="Gemini 2.0 Flash Lite",
                context_length=1000000,  # 1M
                cost_per_1k_prompt=0.000075,  # $0.075/1M tokens (CHEAPEST!)
                cost_per_1k_completion=0.0003,  # $0.30/1M tokens
                best_for=[LLMRequestType.CONTENT_SUMMARY, LLMRequestType.DIAGNOSTIC],
            ),
            ModelInfo(
                provider=LLMProvider.GEMINI,
                model_id="gemini-2.0-flash",
                display_name="Gemini 2.0 Flash",
                context_length=1000000,  # 1M
                cost_per_1k_prompt=0.0001,  # $0.10/1M tokens
                cost_per_1k_completion=0.0004,  # $0.40/1M tokens
                best_for=[LLMRequestType.CONTENT_SUMMARY, LLMRequestType.FEATURE_ANALYSIS],
            ),
            ModelInfo(
                provider=LLMProvider.GEMINI,
                model_id="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                context_length=1000000,  # 1M
                cost_per_1k_prompt=0.00015,  # $0.15/1M tokens
                cost_per_1k_completion=0.0006,  # $0.60/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS, LLMRequestType.CONTENT_SUMMARY],
            ),
            # Retain older models for compatibility & comparison
            ModelInfo(
                provider=LLMProvider.OPENAI,
                model_id="gpt-4o",
                display_name="GPT-4o",
                context_length=128000,
                cost_per_1k_prompt=0.0025,  # $2.50/1M tokens
                cost_per_1k_completion=0.01,  # $10/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS],
            ),
            ModelInfo(
                provider=LLMProvider.ANTHROPIC,
                model_id="claude-3-opus-20240229",
                display_name="Claude 3 Opus (Legacy)",
                context_length=200000,
                cost_per_1k_prompt=0.015,  # $15/1M tokens
                cost_per_1k_completion=0.075,  # $75/1M tokens
                best_for=[LLMRequestType.FEATURE_ANALYSIS],
                deprecated=True,
            ),
        ]

        # Register models
        for model in models:
            self._models[model.model_id] = model

            # Group by provider
            if model.provider not in self._provider_models:
                self._provider_models[model.provider] = []
            self._provider_models[model.provider].append(model.model_id)

    def _initialize_logical_mappings(self) -> None:
        """Initialize logical name mappings for easier configuration."""
        self._logical_mappings.update(
            {
                # Performance tiers (optimized 2024-2025)
                "fast": "gemini-2.0-flash-lite",  # Ultra-fast, cheapest
                "balanced": "gpt-4o-mini",  # Good balance of speed/cost
                "accurate": "gpt-4.1-mini",  # High accuracy, reasonable cost
                "premium": "claude-3-5-sonnet-20241022",  # Best overall performance
                # Use case optimized
                "summary": "gemini-2.0-flash-lite",  # Fast summaries, ultra-cheap
                "analysis": "gpt-4.1-mini",  # Detailed analysis, cost-effective
                "diagnostic": "claude-3-5-haiku-20241022",  # Quick diagnostics
                # Cost optimized (2024-2025)
                "cheapest": "gemini-2.0-flash-lite",  # $0.075/1M tokens
                "cost-effective": "gpt-4o-mini",  # $0.15/1M tokens, good quality
                "ultra-cheap": "gemini-2.0-flash-lite",
                "expensive": "claude-3-opus-20240229",  # Legacy high-end
                # Provider-specific shortcuts (updated 2024-2025)
                "openai-fast": "gpt-4o-mini",
                "openai-balanced": "gpt-4.1-mini",
                "openai-best": "gpt-4.1",
                "anthropic-fast": "claude-3-5-haiku-20241022",
                "anthropic-balanced": "claude-3-5-haiku-20241022",
                "anthropic-best": "claude-3-5-sonnet-20241022",
                "gemini-fast": "gemini-2.0-flash-lite",
                "gemini-balanced": "gemini-2.0-flash",
                "gemini-best": "gemini-2.5-flash",
            }
        )

    def resolve_model(self, model_name: str) -> tuple[LLMProvider, str]:
        """Resolve a logical or actual model name to provider and model ID."""
        if not model_name:
            raise ValueError("Model name cannot be empty")

        # Check if it's a logical mapping
        if model_name in self._logical_mappings:
            resolved_model_id = self._logical_mappings[model_name]
            _logger.debug(
                "model_logical_mapping_resolved",
                logical_name=model_name,
                resolved_model=resolved_model_id,
            )
        else:
            resolved_model_id = model_name

        # Find the provider for this model
        if resolved_model_id not in self._models:
            available_models = list(self._models.keys())
            available_logical = list(self._logical_mappings.keys())
            raise ValueError(
                f"Model '{model_name}' not found. "
                f"Available models: {available_models}. "
                f"Available logical names: {available_logical}"
            )

        model_info = self._models[resolved_model_id]
        return model_info.provider, resolved_model_id

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        """Get detailed information about a model."""
        return self._models.get(model_id)

    def get_models_for_provider(self, provider: LLMProvider) -> list[str]:
        """Get all available models for a specific provider."""
        return self._provider_models.get(provider, [])

    def get_recommended_model(
        self,
        request_type: LLMRequestType,
        provider: LLMProvider | None = None,
        budget_conscious: bool = True,  # Default to cost-effective
    ) -> str:
        """Get a recommended model for a specific request type and constraints."""
        candidates = []

        for model_id, model_info in self._models.items():
            # Filter by provider if specified
            if provider and model_info.provider != provider:
                continue

            # Check if model is good for this request type
            if request_type in model_info.best_for and not model_info.deprecated:
                candidates.append((model_id, model_info))

        if not candidates:
            # Fallback to any model from the provider
            if provider:
                provider_models = self.get_models_for_provider(provider)
                # Prefer non-deprecated models
                non_deprecated = [m for m in provider_models if not self._models[m].deprecated]
                return non_deprecated[0] if non_deprecated else "gpt-4o-mini"
            return "gemini-2.0-flash-lite"  # Ultra cheap fallback

        # Default cost-conscious optimization (2024-2025)
        if budget_conscious:
            candidates.sort(key=lambda x: x[1].cost_per_1k_prompt + x[1].cost_per_1k_completion)
        else:
            # Sort by performance (higher cost generally means better performance)
            candidates.sort(
                key=lambda x: x[1].cost_per_1k_prompt + x[1].cost_per_1k_completion, reverse=True
            )

        return candidates[0][0]

    def validate_model_exists(self, model_name: str) -> bool:
        """Check if a model name (logical or actual) exists in the registry."""
        try:
            self.resolve_model(model_name)
            return True
        except ValueError:
            return False

    def get_all_logical_names(self) -> list[str]:
        """Get all available logical model names."""
        return list(self._logical_mappings.keys())

    def get_all_model_ids(self) -> list[str]:
        """Get all available model IDs."""
        return list(self._models.keys())

    def get_model_cost_info(self, model_id: str) -> tuple[float, float]:
        """Get cost per 1K tokens for a model (prompt, completion)."""
        model_info = self.get_model_info(model_id)
        if not model_info:
            return 0.0, 0.0
        return model_info.cost_per_1k_prompt, model_info.cost_per_1k_completion

    def calculate_cost(self, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost for a specific model and token usage."""
        prompt_cost, completion_cost = self.get_model_cost_info(model_id)
        return (prompt_tokens / 1000) * prompt_cost + (completion_tokens / 1000) * completion_cost


# Global registry instance
_model_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    return _model_registry


__all__ = ["ModelRegistry", "ModelInfo", "get_model_registry"]
