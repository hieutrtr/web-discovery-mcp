"""Pydantic-based configuration management for the MCP server."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_OUTPUT_ROOT = Path("docs/web_discovery").resolve()
_DEFAULT_BROWSER = "chromium"
_DEFAULT_MAX_CONCURRENCY = 3


class MCPSettings(BaseSettings):
    """Typed settings object loaded from environment and optional files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM providers
    OPENAI_API_KEY: SecretStr | None = Field(default=None, repr=False)
    ANTHROPIC_API_KEY: SecretStr | None = Field(default=None, repr=False)
    GEMINI_API_KEY: SecretStr | None = Field(default=None, repr=False)

    # Model selection configuration
    STEP1_MODEL: str | None = None
    STEP2_MODEL: str | None = None
    FALLBACK_MODEL: str | None = None
    
    # Provider-specific model configuration (no defaults - must be set)
    OPENAI_CHAT_MODEL: str | None = None
    ANTHROPIC_CHAT_MODEL: str | None = None
    GEMINI_CHAT_MODEL: str | None = None

    # Budget monitoring configuration
    MONTHLY_BUDGET_LIMIT: float = Field(default=100.0)  # USD per month
    BUDGET_ALERT_THRESHOLD: float = Field(default=0.8)  # Alert at 80% of budget
    BUDGET_WARNING_THRESHOLD: float = Field(default=0.5)  # Warn at 50% of budget

    # Browser defaults
    BROWSER_ENGINE: str = Field(default=_DEFAULT_BROWSER)
    MAX_CONCURRENT_PAGES: int = Field(default=_DEFAULT_MAX_CONCURRENCY)
    BROWSER_HEADLESS: bool = Field(default=True)
    BROWSER_VIEWPORT_WIDTH: int = Field(default=1280)
    BROWSER_VIEWPORT_HEIGHT: int = Field(default=720)
    BROWSER_TIMEOUT: float = Field(default=30.0)
    BROWSER_USER_AGENT: str | None = Field(default=None)

    # Storage paths
    OUTPUT_ROOT: Path = Field(default=_DEFAULT_OUTPUT_ROOT)

    # Misc toggles
    YOLO_MODE_ENABLED: bool = False
    INTERACTIVE_MODE_ENABLED: bool = True

    # Timeout configuration (seconds)
    DISCOVERY_TIMEOUT: float = 60.0
    ANALYSIS_TIMEOUT: float = 120.0
    DISCOVERY_MAX_DEPTH: int = 1

    @property
    def sensitive_fields(self) -> set[str]:
        return {
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
        }

    def display_dict(self) -> dict[str, Any]:
        """Return a redacted dictionary representation suitable for display."""

        data: dict[str, Any] = {}
        for field_name, _model_field in type(self).model_fields.items():
            value = getattr(self, field_name)
            if field_name in self.sensitive_fields:
                data[field_name] = "***"
            elif isinstance(value, SecretStr):
                data[field_name] = "***"
            elif isinstance(value, Path):
                data[field_name] = str(value.resolve())
            else:
                data[field_name] = value
        return data


def load_settings() -> MCPSettings:
    """Load configuration using default environment and .env overrides."""

    return MCPSettings()


__all__ = ["MCPSettings", "load_settings"]
