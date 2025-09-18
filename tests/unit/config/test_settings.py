import asyncio
from pathlib import Path

import pytest

from legacy_web_mcp.config import load_settings, show_config, validate_settings


def test_load_settings_applies_env_overrides(tmp_path: Path) -> None:
    config_file = tmp_path / "config.json"
    config_file.write_text(
        '{"step1_model": "config-model", "max_concurrent_browsers": 5, "analysis_output_root": "./custom", "monthly_budget_usd": 25.5}'
    )
    env = {
        "OPENAI_API_KEY": "env-openai",
        "STEP1_MODEL": "env-model",
        "HEADLESS": "false",
        "MCP_CONFIG_FILE": str(config_file),
        "MONTHLY_BUDGET_USD": "30",
    }
    settings = load_settings(env=env)
    assert settings.openai_api_key == "env-openai"
    assert settings.step1_model == "env-model"
    assert settings.max_concurrent_browsers == 5
    assert settings.headless is False
    assert settings.analysis_output_root == "./custom"
    assert settings.config_file == config_file
    assert settings.monthly_budget_usd == 30.0


def test_validate_settings_reports_missing_keys() -> None:
    settings = load_settings(env={})
    validation = validate_settings(settings)
    assert not validation["valid"]
    assert validation["errors"][0]["code"] == "CONFIG_MISSING"


def test_show_config_redacts_secrets(tmp_path: Path) -> None:
    env = {
        "OPENAI_API_KEY": "super-secret",
        "ANTHROPIC_API_KEY": "secret",
        "GEMINI_API_KEY": "secret",
        "STEP1_MODEL": "model-a",
        "STEP2_MODEL": "model-b",
        "FALLBACK_MODEL": "model-c",
    }
    # Use JSON config to avoid PyYAML dependency in tests
    report = tmp_path / "config.json"
    report.write_text(
        '{"step1_model": "config-model", "analysis_output_root": "./reports"}'
    )
    result = load_settings(env=env, config_path=report)
    safe = result.sanitized()
    assert safe["openai_api_key"] == "***redacted***"
    config_report = asyncio.run(show_config(env=env, config_path=report))
    assert config_report["settings"]["anthropic_api_key"] == "***redacted***"
    assert config_report["settings"]["headless"] in {True, False}
    assert config_report["validation"]["valid"]


def test_yaml_config_requires_pyyaml_dependency(tmp_path: Path) -> None:
    """Test that YAML config files properly handle missing PyYAML dependency."""
    yaml_config = tmp_path / "config.yaml"
    yaml_config.write_text("step1_model: yaml-model\nheadless: true\n")

    # This should raise a clear error about missing PyYAML
    with pytest.raises(RuntimeError, match="PyYAML is required to parse YAML configuration files"):
        load_settings(env={}, config_path=yaml_config)
