from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

try:  # pragma: no cover - optional dependency
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    yaml = None  # type: ignore

CONFIG_ENV_VAR = "MCP_CONFIG_FILE"


@dataclass
class Settings:
    """Application configuration."""

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    step1_model: str = "gpt-4o-mini"
    step2_model: str = "claude-3-haiku"
    fallback_model: str = "gemini-1.5-pro"
    default_browser_engine: str = "chromium"
    max_concurrent_browsers: int = 3
    analysis_output_root: str = "./analysis-output"
    headless: bool = True
    monthly_budget_usd: float | None = None
    config_file: Path | None = None

    def sanitized(self) -> Dict[str, Any]:
        data = asdict(self)
        for key in ("openai_api_key", "anthropic_api_key", "gemini_api_key"):
            if data.get(key):
                data[key] = "***redacted***"
        if self.config_file is not None:
            data["config_file"] = str(self.config_file)
        return data


def _load_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file '{path}' does not exist")
    if path.suffix in {".json"}:
        return json.loads(path.read_text())
    if path.suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to parse YAML configuration files. Install 'pyyaml'."
            )
        return yaml.safe_load(path.read_text())  # type: ignore[arg-type]
    raise ValueError(f"Unsupported configuration format: '{path.suffix}'")


def _collect_sources(
    *, env: Mapping[str, str] | None = None, config_path: str | Path | None = None
) -> Dict[str, Any]:
    env = dict(os.environ if env is None else env)
    data: Dict[str, Any] = {}

    resolved_path: Path | None = None
    candidate = config_path or env.get(CONFIG_ENV_VAR)
    if candidate:
        resolved_path = Path(candidate).expanduser()
        file_data = _load_file(resolved_path)
        if not isinstance(file_data, dict):
            raise ValueError("Configuration file must contain a top-level object")
        data.update(file_data)

    env_overrides = {
        "openai_api_key": env.get("OPENAI_API_KEY"),
        "anthropic_api_key": env.get("ANTHROPIC_API_KEY"),
        "gemini_api_key": env.get("GEMINI_API_KEY"),
        "step1_model": env.get("STEP1_MODEL"),
        "step2_model": env.get("STEP2_MODEL"),
        "fallback_model": env.get("FALLBACK_MODEL"),
        "default_browser_engine": env.get("DEFAULT_BROWSER_ENGINE"),
        "max_concurrent_browsers": env.get("MAX_CONCURRENT_BROWSERS"),
        "analysis_output_root": env.get("ANALYSIS_OUTPUT_ROOT"),
        "headless": env.get("HEADLESS"),
        "monthly_budget_usd": env.get("MONTHLY_BUDGET_USD"),
    }
    for key, value in env_overrides.items():
        if value is not None and value != "":
            if key == "max_concurrent_browsers":
                data[key] = int(value)
            elif key == "headless":
                data[key] = str(value).lower() not in {"false", "0", "no"}
            elif key == "monthly_budget_usd":
                data[key] = float(value)
            else:
                data[key] = value
    if "max_concurrent_browsers" in data:
        data["max_concurrent_browsers"] = int(data["max_concurrent_browsers"])
    if "headless" in data and not isinstance(data["headless"], bool):
        data["headless"] = str(data["headless"]).lower() not in {"false", "0", "no"}
    if "monthly_budget_usd" in data and not isinstance(data["monthly_budget_usd"], (float, int)):
        data["monthly_budget_usd"] = float(data["monthly_budget_usd"])
    return data, resolved_path


def load_settings(
    *, env: Mapping[str, str] | None = None, config_path: str | Path | None = None
) -> Settings:
    data, resolved_path = _collect_sources(env=env, config_path=config_path)
    settings = Settings(**{k: v for k, v in data.items() if k in Settings.__annotations__})
    settings.config_file = resolved_path
    return settings


def validate_settings(settings: Settings) -> Dict[str, Any]:
    missing_keys = [
        key
        for key in [
            "openai_api_key",
            "anthropic_api_key",
            "gemini_api_key",
            "step1_model",
            "step2_model",
            "fallback_model",
        ]
        if not getattr(settings, key)
    ]
    errors = []
    if missing_keys:
        errors.append(
            {
                "code": "CONFIG_MISSING",
                "message": "Missing required configuration values",
                "fields": missing_keys,
                "remediation": "Populate the missing values in .env or the configuration file.",
            }
        )
    if settings.max_concurrent_browsers <= 0:
        errors.append(
            {
                "code": "INVALID_CONCURRENCY",
                "message": "max_concurrent_browsers must be greater than zero",
                "remediation": "Update configuration to use a positive integer.",
            }
        )
    return {"valid": not errors, "errors": errors}


async def show_config(
    *, env: Mapping[str, str] | None = None, config_path: str | Path | None = None
) -> Dict[str, Any]:
    settings = load_settings(env=env, config_path=config_path)
    report = validate_settings(settings)
    return {
        "settings": settings.sanitized(),
        "validation": report,
    }
