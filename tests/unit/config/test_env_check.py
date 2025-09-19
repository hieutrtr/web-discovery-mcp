from __future__ import annotations

import pytest

from legacy_web_mcp.config.env_check import (
    check_required_env,
    default_required_keys,
    format_report,
)
from legacy_web_mcp.config.validator import MANDATORY_ENV_KEYS


def test_check_required_env_succeeds_when_keys_present(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in MANDATORY_ENV_KEYS:
        monkeypatch.setenv(key, "value")

    ok, issues = check_required_env()
    assert ok
    assert issues == []


def test_check_required_env_reports_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in MANDATORY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    ok, issues = check_required_env()
    assert not ok
    messages = format_report(issues)
    assert any("OPENAI_API_KEY" in line for line in messages)


def test_default_required_keys_matches_constants() -> None:
    assert default_required_keys() == tuple(MANDATORY_ENV_KEYS)
