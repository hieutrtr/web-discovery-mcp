"""Configuration manager for LLM model selection and budget monitoring."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, Field

from legacy_web_mcp.config.settings import MCPSettings

from .model_registry import get_model_registry
from .models import LLMProvider, LLMRequestType

_logger = structlog.get_logger("legacy_web_mcp.llm.config_manager")


class ModelConfiguration(BaseModel):
    """Configuration for model selection."""

    step1_model: str = Field(default="summary")
    step2_model: str = Field(default="analysis")
    fallback_model: str = Field(default="fast")

    step1_provider: LLMProvider | None = None
    step2_provider: LLMProvider | None = None
    fallback_provider: LLMProvider | None = None


class BudgetConfiguration(BaseModel):
    """Configuration for budget monitoring."""

    monthly_limit: float = Field(default=100.0)
    alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    warning_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class UsageRecord(BaseModel):
    """Record of model usage for a specific request."""

    timestamp: datetime
    request_type: LLMRequestType
    provider: LLMProvider
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    page_url: str | None = None
    project_id: str | None = None


class BudgetAlert(BaseModel):
    """Budget alert notification."""

    alert_type: str  # "warning" or "alert"
    current_usage: float
    budget_limit: float
    percentage_used: float
    period_start: datetime
    triggered_at: datetime


class LLMConfigurationManager:
    """Manages LLM model configuration and budget monitoring."""

    def __init__(self, settings: MCPSettings):
        self.settings = settings
        self.model_registry = get_model_registry()
        self.usage_records: list[UsageRecord] = []
        self.budget_alerts: list[BudgetAlert] = []

        # Initialize configuration
        self.model_config = self._initialize_model_config()
        self.budget_config = self._initialize_budget_config()

    def _initialize_model_config(self) -> ModelConfiguration:
        """Initialize model configuration from settings."""
        config = ModelConfiguration()

        # Set initial values from environment variables
        config.step1_model = self.settings.STEP1_MODEL or ""  # No default - must be set
        config.step2_model = self.settings.STEP2_MODEL or ""  # No default - must be set
        config.fallback_model = self.settings.FALLBACK_MODEL or ""  # No default - must be set

        # Ensure at least initial models are provided
        if not config.step1_model:
            raise ValueError("STEP1_MODEL environment variable must be set - no default available")
        if not config.step2_model:
            raise ValueError("STEP2_MODEL environment variable must be set - no default available")
        if not config.fallback_model:
            raise ValueError("FALLBACK_MODEL environment variable must be set - no default available")

        # Resolve providers for each model
        try:
            config.step1_provider, config.step1_model = self.model_registry.resolve_model(config.step1_model)
            config.step2_provider, config.step2_model = self.model_registry.resolve_model(config.step2_model)
            config.fallback_provider, config.fallback_model = self.model_registry.resolve_model(config.fallback_model)
        except ValueError as e:
            _logger.error("model_resolution_failed", error=str(e))
            raise ValueError(
                f"Failed to resolve configured models. Please check your model configuration: {e}"
            ) from e

        _logger.info(
            "model_configuration_initialized",
            step1=f"{config.step1_provider.value}:{config.step1_model}",
            step2=f"{config.step2_provider.value}:{config.step2_model}",
            fallback=f"{config.fallback_provider.value}:{config.fallback_model}",
        )

        return config

    def _initialize_budget_config(self) -> BudgetConfiguration:
        """Initialize budget configuration from settings."""
        return BudgetConfiguration(
            monthly_limit=self.settings.MONTHLY_BUDGET_LIMIT,
            alert_threshold=self.settings.BUDGET_ALERT_THRESHOLD,
            warning_threshold=self.settings.BUDGET_WARNING_THRESHOLD,
        )

    def get_model_for_request_type(self, request_type: LLMRequestType) -> tuple[LLMProvider, str]:
        """Get the configured model for a specific request type."""
        if request_type == LLMRequestType.CONTENT_SUMMARY:
            if self.model_config.step1_provider is None:
                raise ValueError("step1_provider is not configured")
            return self.model_config.step1_provider, self.model_config.step1_model
        elif request_type == LLMRequestType.FEATURE_ANALYSIS:
            if self.model_config.step2_provider is None:
                raise ValueError("step2_provider is not configured")
            return self.model_config.step2_provider, self.model_config.step2_model
        else:
            # Use fallback for diagnostics and other types
            if self.model_config.fallback_provider is None:
                raise ValueError("fallback_provider is not configured")
            return self.model_config.fallback_provider, self.model_config.fallback_model

    def get_fallback_chain(self, request_type: LLMRequestType) -> list[tuple[LLMProvider, str]]:
        """Get the fallback chain for a request type."""
        primary_provider, primary_model = self.get_model_for_request_type(request_type)
        fallback_provider, fallback_model = (
            self.model_config.fallback_provider,
            self.model_config.fallback_model,
        )

        # Create fallback chain
        if primary_provider is None or fallback_provider is None:
            raise ValueError("Providers must be configured before creating fallback chain")
        chain = [(primary_provider, primary_model)]
        
        # Add fallback if it's different from primary
        if (fallback_provider, fallback_model) != (primary_provider, primary_model):
            chain.append((fallback_provider, fallback_model))

        # Add additional fallbacks based on available providers
        additional_fallbacks = self._get_additional_fallbacks(request_type, chain)
        chain.extend(additional_fallbacks)

        return chain

    def _get_additional_fallbacks(
        self,
        request_type: LLMRequestType,
        existing_chain: list[tuple[LLMProvider, str]],
    ) -> list[tuple[LLMProvider, str]]:
        """Get additional fallback models for redundancy."""
        used_combinations = set(existing_chain)
        additional = []

        # Get recommended models for each provider
        for provider in LLMProvider:
            recommended = self.model_registry.get_recommended_model(
                request_type, provider, budget_conscious=True
            )
            combination = (provider, recommended)

            if combination not in used_combinations:
                additional.append(combination)
                if len(additional) >= 2:  # Limit additional fallbacks
                    break

        return additional

    def validate_configuration(self) -> dict[str, bool]:
        """Validate that all configured models are available."""
        validation_results = {}

        models_to_check = [
            ("step1_model", self.model_config.step1_model),
            ("step2_model", self.model_config.step2_model),
            ("fallback_model", self.model_config.fallback_model),
        ]

        for model_name, model_id in models_to_check:
            is_valid = self.model_registry.validate_model_exists(model_id)
            validation_results[model_name] = is_valid

            if not is_valid:
                _logger.warning(
                    "invalid_model_configuration",
                    model_name=model_name,
                    model_id=model_id,
                    available_models=self.model_registry.get_all_model_ids(),
                )

        return validation_results

    def record_usage(
        self,
        request_type: LLMRequestType,
        provider: LLMProvider,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        page_url: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Record model usage for budget tracking."""
        usage_record = UsageRecord(
            timestamp=datetime.now(UTC),
            request_type=request_type,
            provider=provider,
            model_id=model_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost,
            page_url=page_url,
            project_id=project_id,
        )

        self.usage_records.append(usage_record)

        _logger.info(
            "usage_recorded",
            provider=provider.value,
            model=model_id,
            cost=cost,
            tokens=prompt_tokens + completion_tokens,
        )

        # Check budget after recording
        self._check_budget_thresholds()

    def get_current_month_usage(self) -> float:
        """Get total usage for the current month."""
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        current_month_records = [
            record for record in self.usage_records
            if record.timestamp >= month_start
        ]

        return sum(record.cost for record in current_month_records)

    def get_usage_by_model(self, days: int = 30) -> dict[str, dict[str, float]]:
        """Get usage breakdown by model for the last N days."""
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days) if cutoff.day > days else cutoff.replace(month=cutoff.month - 1)

        recent_records = [
            record for record in self.usage_records
            if record.timestamp >= cutoff
        ]

        usage_by_model = {}
        for record in recent_records:
            model_key = f"{record.provider.value}:{record.model_id}"
            if model_key not in usage_by_model:
                usage_by_model[model_key] = {
                    "requests": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                }

            usage_by_model[model_key]["requests"] += 1
            usage_by_model[model_key]["total_cost"] += record.cost
            usage_by_model[model_key]["total_tokens"] += record.prompt_tokens + record.completion_tokens

        return usage_by_model

    def _check_budget_thresholds(self) -> None:
        """Check if budget thresholds have been crossed."""
        current_usage = self.get_current_month_usage()
        budget_limit = self.budget_config.monthly_limit
        usage_percentage = current_usage / budget_limit

        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Check for alerts
        if usage_percentage >= self.budget_config.alert_threshold:
            # Check if we've already alerted this month
            existing_alerts = [
                alert for alert in self.budget_alerts
                if alert.alert_type == "alert" and alert.period_start >= month_start
            ]

            if not existing_alerts:
                alert = BudgetAlert(
                    alert_type="alert",
                    current_usage=current_usage,
                    budget_limit=budget_limit,
                    percentage_used=usage_percentage,
                    period_start=month_start,
                    triggered_at=now,
                )
                self.budget_alerts.append(alert)

                _logger.warning(
                    "budget_alert_triggered",
                    current_usage=current_usage,
                    budget_limit=budget_limit,
                    percentage=usage_percentage * 100,
                )

        elif usage_percentage >= self.budget_config.warning_threshold:
            # Check if we've already warned this month
            existing_warnings = [
                alert for alert in self.budget_alerts
                if alert.alert_type == "warning" and alert.period_start >= month_start
            ]

            if not existing_warnings:
                warning = BudgetAlert(
                    alert_type="warning",
                    current_usage=current_usage,
                    budget_limit=budget_limit,
                    percentage_used=usage_percentage,
                    period_start=month_start,
                    triggered_at=now,
                )
                self.budget_alerts.append(warning)

                _logger.info(
                    "budget_warning_triggered",
                    current_usage=current_usage,
                    budget_limit=budget_limit,
                    percentage=usage_percentage * 100,
                )

    def get_configuration_summary(self) -> dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            "model_configuration": {
                "step1": f"{self.model_config.step1_provider.value if self.model_config.step1_provider else 'unknown'}:{self.model_config.step1_model}",
                "step2": f"{self.model_config.step2_provider.value if self.model_config.step2_provider else 'unknown'}:{self.model_config.step2_model}",
                "fallback": f"{self.model_config.fallback_provider.value if self.model_config.fallback_provider else 'unknown'}:{self.model_config.fallback_model}",
            },
            "budget_configuration": {
                "monthly_limit": self.budget_config.monthly_limit,
                "alert_threshold": self.budget_config.alert_threshold,
                "warning_threshold": self.budget_config.warning_threshold,
            },
            "current_usage": {
                "monthly_spend": self.get_current_month_usage(),
                "percentage_used": (self.get_current_month_usage() / self.budget_config.monthly_limit) * 100,
                "total_requests": len(self.usage_records),
            },
        }

    def get_recent_alerts(self, days: int = 30) -> list[BudgetAlert]:
        """Get recent budget alerts."""
        cutoff = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days) if cutoff.day > days else cutoff.replace(month=cutoff.month - 1)

        return [alert for alert in self.budget_alerts if alert.triggered_at >= cutoff]


__all__ = [
    "LLMConfigurationManager",
    "ModelConfiguration",
    "BudgetConfiguration",
    "UsageRecord",
    "BudgetAlert",
]