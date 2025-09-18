"""Configuration utilities for the Legacy Web MCP server."""
from __future__ import annotations

from .settings import MCPSettings, load_settings
from .validator import summarize_env_validation, validate_env_vars

__all__ = [
    "MCPSettings",
    "load_settings",
    "summarize_env_validation",
    "validate_env_vars",
]
