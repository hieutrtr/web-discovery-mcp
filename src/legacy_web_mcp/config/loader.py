"""Configuration loading facade integrating settings, env, and file overrides."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .settings import MCPSettings

_DEFAULT_CONFIG_CANDIDATES = (
    Path("config/default.yaml"),
    Path("config/default.yml"),
    Path("config/default.json"),
)


def _load_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(path.read_text()) or {}
        if not isinstance(data, dict):
            msg = f"Configuration file {path} must contain a mapping"
            raise ValueError(msg)
        return data
    if path.suffix == ".json":
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            msg = f"Configuration file {path} must contain a JSON object"
            raise ValueError(msg)
        return data
    msg = f"Unsupported config file format: {path.suffix}"
    raise ValueError(msg)


def _resolve_config_path(config_path: Path | None) -> Path | None:
    if config_path:
        return config_path
    for candidate in _DEFAULT_CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def load_configuration(config_path: Path | None = None) -> MCPSettings:
    """Load MCP settings applying config file overrides when available."""

    settings = MCPSettings()
    selected_path = _resolve_config_path(config_path)
    if selected_path:
        overrides = _load_file(selected_path)
        settings = settings.model_copy(update=overrides)
    return settings


__all__ = ["load_configuration"]
