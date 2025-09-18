from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from legacy_web_mcp.config.settings import MCPSettings
from legacy_web_mcp.config.validator import (
    MANDATORY_ENV_KEYS,
    summarize_env_validation,
    validate_env_vars,
)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("OPENAI_API_KEY", "***"),
        ("STEP1_MODEL", "gpt-test"),
        ("OUTPUT_ROOT", str(Path("docs/web_discovery").resolve())),
    ],
)
def test_display_dict_redacts_sensitive_values(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    expected: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("STEP1_MODEL", "gpt-test")

    config = MCPSettings()
    display = config.display_dict()
    assert display[key] == expected


def test_missing_env_vars_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in MANDATORY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    issues = validate_env_vars()
    assert {issue.key for issue in issues} == set(MANDATORY_ENV_KEYS)

    summary = summarize_env_validation()
    assert summary["status"] == "warning"
    details = cast(list[dict[str, str]], summary["details"])
    assert len(details) == len(MANDATORY_ENV_KEYS)
