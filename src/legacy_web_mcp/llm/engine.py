"""Unified LLM engine with multi-provider support and failover."""
from __future__ import annotations

from typing import Any

import structlog

from legacy_web_mcp.config.settings import MCPSettings

from .config_manager import LLMConfigurationManager
from .models import (
    AuthenticationError,
    CostTracking,
    LLMError,
    LLMProvider,
    LLMProviderInterface,
    LLMRequest,
    LLMResponse,
    ProviderConfig,
    ProviderHealth,
)
from .providers import AnthropicProvider, GeminiProvider, OpenAIProvider
from .utils import HealthMonitor

_logger = structlog.get_logger("legacy_web_mcp.llm.engine")


class LLMEngine:
    """Unified LLM engine with multi-provider support and automatic failover."""

    def __init__(self, settings: MCPSettings):
        self.settings = settings
        self.providers: dict[LLMProvider, LLMProviderInterface] = {}
        self.provider_configs: dict[LLMProvider, ProviderConfig] = {}
        self.health_monitor = HealthMonitor()
        self.cost_tracking: list[CostTracking] = []
        self.config_manager = LLMConfigurationManager(settings)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all configured providers."""
        if self._initialized:
            return

        # Initialize OpenAI if API key is provided
        if self.settings.OPENAI_API_KEY:
            try:
                provider = OpenAIProvider()
                # Use environment variable for model, with error if not set
                if not self.settings.OPENAI_CHAT_MODEL:
                    raise ValueError("OPENAI_CHAT_MODEL environment variable must be set when OpenAI API key is provided")
                
                config = ProviderConfig(
                    provider=LLMProvider.OPENAI,
                    api_key=self.settings.OPENAI_API_KEY.get_secret_value(),
                    model=self.settings.OPENAI_CHAT_MODEL,
                )
                await provider.initialize(config)
                self.providers[LLMProvider.OPENAI] = provider
                self.provider_configs[LLMProvider.OPENAI] = config
                _logger.info("openai_provider_initialized", model=self.settings.OPENAI_CHAT_MODEL)
            except Exception as e:
                _logger.warning("openai_provider_init_failed", error=str(e))

        # Initialize Anthropic if API key is provided
        if self.settings.ANTHROPIC_API_KEY:
            try:
                provider = AnthropicProvider()
                # Use environment variable for model, with error if not set
                if not self.settings.ANTHROPIC_CHAT_MODEL:
                    raise ValueError("ANTHROPIC_CHAT_MODEL environment variable must be set when Anthropic API key is provided")
                
                config = ProviderConfig(
                    provider=LLMProvider.ANTHROPIC,
                    api_key=self.settings.ANTHROPIC_API_KEY.get_secret_value(),
                    model=self.settings.ANTHROPIC_CHAT_MODEL,
                )
                await provider.initialize(config)
                self.providers[LLMProvider.ANTHROPIC] = provider
                self.provider_configs[LLMProvider.ANTHROPIC] = config
                _logger.info("anthropic_provider_initialized", model=self.settings.ANTHROPIC_CHAT_MODEL)
            except Exception as e:
                _logger.warning("anthropic_provider_init_failed", error=str(e))

        # Initialize Gemini if API key is provided
        if self.settings.GEMINI_API_KEY:
            try:
                provider = GeminiProvider()
                # Use environment variable for model, with error if not set
                if not self.settings.GEMINI_CHAT_MODEL:
                    raise ValueError("GEMINI_CHAT_MODEL environment variable must be set when Gemini API key is provided")
                
                config = ProviderConfig(
                    provider=LLMProvider.GEMINI,
                    api_key=self.settings.GEMINI_API_KEY.get_secret_value(),
                    model=self.settings.GEMINI_CHAT_MODEL,
                )
                await provider.initialize(config)
                self.providers[LLMProvider.GEMINI] = provider
                self.provider_configs[LLMProvider.GEMINI] = config
                _logger.info("gemini_provider_initialized", model=self.settings.GEMINI_CHAT_MODEL)
            except Exception as e:
                _logger.warning("gemini_provider_init_failed", error=str(e))

        if not self.providers:
            raise LLMError("No LLM providers were successfully initialized")

        self._initialized = True
        _logger.info("llm_engine_initialized", providers=list(self.providers.keys()))

    async def chat_completion(
        self,
        request: LLMRequest,
        preferred_provider: LLMProvider | None = None,
        page_url: str | None = None,
        project_id: str | None = None,
    ) -> LLMResponse:
        """Execute a chat completion with configuration-based model selection and fallback."""
        if not self._initialized:
            await self.initialize()

        # Get fallback chain based on request type
        fallback_chain = self.config_manager.get_fallback_chain(request.request_type)

        # Override with preferred provider if specified
        if preferred_provider:
            fallback_chain = self._modify_chain_for_preferred_provider(fallback_chain, preferred_provider)

        last_error = None
        for provider_type, model_id in fallback_chain:
            if provider_type not in self.providers:
                _logger.debug(
                    "provider_not_available",
                    provider=provider_type.value,
                    model=model_id,
                )
                continue

            provider = self.providers[provider_type]

            try:
                # Create request with specific model
                configured_request = LLMRequest(
                    messages=request.messages,
                    model=model_id,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    request_type=request.request_type,
                    metadata=request.metadata,
                )

                _logger.debug(
                    "llm_request_attempt",
                    provider=provider_type.value,
                    model=model_id,
                    request_type=request.request_type.value,
                )

                response = await provider.chat_completion(configured_request)

                # Record usage in configuration manager
                self.config_manager.record_usage(
                    request_type=request.request_type,
                    provider=provider_type,
                    model_id=response.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    cost=response.cost_estimate or 0.0,
                    page_url=page_url,
                    project_id=project_id,
                )

                # Track cost (legacy tracking)
                if response.cost_estimate:
                    cost_record = CostTracking(
                        provider=provider_type,
                        model=response.model,
                        prompt_tokens=response.usage.prompt_tokens,
                        completion_tokens=response.usage.completion_tokens,
                        cost_per_prompt_token=response.cost_estimate / response.usage.total_tokens if response.usage.total_tokens > 0 else 0,
                        cost_per_completion_token=response.cost_estimate / response.usage.total_tokens if response.usage.total_tokens > 0 else 0,
                        total_cost=response.cost_estimate,
                    )
                    self.cost_tracking.append(cost_record)

                _logger.info(
                    "llm_request_completed",
                    provider=provider_type.value,
                    model=response.model,
                    tokens=response.usage.total_tokens,
                    cost=response.cost_estimate,
                    fallback_used=fallback_chain.index((provider_type, model_id)) > 0,
                )

                return response

            except AuthenticationError as e:
                _logger.error(
                    "llm_provider_auth_failed",
                    provider=provider_type.value,
                    model=model_id,
                    error=str(e),
                )
                last_error = e
                continue

            except LLMError as e:
                _logger.warning(
                    "llm_provider_failed",
                    provider=provider_type.value,
                    model=model_id,
                    error=str(e),
                    retryable=e.retryable,
                )
                last_error = e
                if not e.retryable:
                    continue

            except Exception as e:
                _logger.warning(
                    "llm_provider_unexpected_error",
                    provider=provider_type.value,
                    model=model_id,
                    error=str(e),
                )
                last_error = LLMError(f"Unexpected error: {e}", provider_type)
                continue

        # All providers in chain failed
        if last_error:
            raise last_error
        else:
            raise LLMError("All LLM providers in fallback chain failed")

    def _modify_chain_for_preferred_provider(
        self,
        fallback_chain: list[tuple[LLMProvider, str]],
        preferred_provider: LLMProvider,
    ) -> list[tuple[LLMProvider, str]]:
        """Modify fallback chain to prioritize preferred provider."""
        # Find models for preferred provider in the chain
        preferred_models = [
            (provider, model) for provider, model in fallback_chain
            if provider == preferred_provider
        ]

        # Find other models
        other_models = [
            (provider, model) for provider, model in fallback_chain
            if provider != preferred_provider
        ]

        # Put preferred provider models first
        return preferred_models + other_models

    def _get_provider_order(self, preferred_provider: LLMProvider | None = None) -> list[LLMProvider]:
        """Get the order of providers to try, with preferred provider first."""
        available_providers = list(self.providers.keys())

        if not available_providers:
            return []

        # Start with preferred provider if specified and available
        if preferred_provider and preferred_provider in available_providers:
            provider_order = [preferred_provider]
            # Add remaining providers sorted by health
            remaining = [p for p in available_providers if p != preferred_provider]
        else:
            remaining = available_providers

        # Sort remaining providers by health status
        remaining.sort(key=lambda p: self._get_provider_priority(p))

        return provider_order + remaining if preferred_provider else remaining

    def _get_provider_priority(self, provider: LLMProvider) -> int:
        """Get priority score for provider (lower is better)."""
        error_rate = self.health_monitor.get_error_rate(provider)

        # Priority based on error rate
        if error_rate > 0.5:
            return 3  # Lowest priority
        elif error_rate > 0.2:
            return 2  # Medium priority
        else:
            return 1  # High priority

    async def get_provider_health(self, provider: LLMProvider) -> ProviderHealth | None:
        """Get health status for a specific provider."""
        if provider not in self.providers:
            return None

        return await self.providers[provider].check_health()

    async def get_all_provider_health(self) -> dict[LLMProvider, ProviderHealth]:
        """Get health status for all providers."""
        health_status = {}

        for provider_type, provider in self.providers.items():
            try:
                health = await provider.check_health()
                health_status[provider_type] = health
            except Exception as e:
                _logger.warning(
                    "health_check_failed",
                    provider=provider_type.value,
                    error=str(e),
                )

        return health_status

    async def validate_all_providers(self) -> dict[LLMProvider, bool]:
        """Validate API keys for all configured providers."""
        validation_results = {}

        for provider_type, provider in self.providers.items():
            try:
                is_valid = await provider.validate_api_key()
                validation_results[provider_type] = is_valid
                _logger.info(
                    "provider_validation",
                    provider=provider_type.value,
                    valid=is_valid,
                )
            except Exception as e:
                validation_results[provider_type] = False
                _logger.warning(
                    "provider_validation_failed",
                    provider=provider_type.value,
                    error=str(e),
                )

        return validation_results

    def get_total_cost(self, provider: LLMProvider | None = None) -> float:
        """Get total cost for all requests or specific provider."""
        if provider:
            return sum(
                record.total_cost
                for record in self.cost_tracking
                if record.provider == provider
            )
        else:
            return sum(record.total_cost for record in self.cost_tracking)

    def get_cost_breakdown(self) -> dict[LLMProvider, float]:
        """Get cost breakdown by provider."""
        breakdown = {}
        for provider in LLMProvider:
            breakdown[provider] = self.get_total_cost(provider)
        return breakdown

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        # Get stats from both legacy tracking and configuration manager
        config_stats = self.config_manager.get_configuration_summary()

        total_requests = len(self.cost_tracking)
        total_cost = self.get_total_cost()

        provider_stats = {}
        for provider in LLMProvider:
            provider_records = [r for r in self.cost_tracking if r.provider == provider]
            provider_stats[provider.value] = {
                "requests": len(provider_records),
                "total_cost": sum(r.total_cost for r in provider_records),
                "total_tokens": sum(r.prompt_tokens + r.completion_tokens for r in provider_records),
            }

        # Merge with configuration manager data
        return {
            "total_requests": total_requests,
            "total_cost": total_cost,
            "providers": provider_stats,
            "configured_providers": [p.value for p in self.providers.keys()],
            "configuration": config_stats,
            "model_usage": self.config_manager.get_usage_by_model(),
            "recent_alerts": [alert.dict() for alert in self.config_manager.get_recent_alerts()],
        }

    async def validate_configuration(self) -> dict[str, Any]:
        """Validate the current LLM configuration."""
        return {
            "model_validation": self.config_manager.validate_configuration(),
            "provider_validation": await self.validate_all_providers(),
            "configuration_summary": self.config_manager.get_configuration_summary(),
        }

    def get_model_for_request_type(self, request_type: LLMRequestType) -> tuple[LLMProvider, str]:
        """Get the configured model for a specific request type."""
        return self.config_manager.get_model_for_request_type(request_type)

    def get_fallback_chain(self, request_type: LLMRequestType) -> list[tuple[LLMProvider, str]]:
        """Get the fallback chain for a request type."""
        return self.config_manager.get_fallback_chain(request_type)

    async def close(self) -> None:
        """Close all providers and clean up resources."""
        for provider in self.providers.values():
            try:
                await provider.close()
            except Exception as e:
                _logger.warning("provider_close_failed", error=str(e))

        self.providers.clear()
        self.provider_configs.clear()
        self._initialized = False

        _logger.info("llm_engine_closed")


__all__ = ["LLMEngine"]