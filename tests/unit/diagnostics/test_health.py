import asyncio
from datetime import datetime

from legacy_web_mcp import diagnostics


def test_validate_configuration_reports_missing_keys() -> None:
    report = diagnostics.validate_configuration(env={})
    assert not report["valid"]
    assert set(report["missing"]) == {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "STEP1_MODEL",
        "STEP2_MODEL",
        "FALLBACK_MODEL",
    }
    assert report["remediation"]


def test_validate_configuration_all_keys_present() -> None:
    report = diagnostics.validate_configuration(
        env={
            "OPENAI_API_KEY": "test",
            "ANTHROPIC_API_KEY": "test",
            "GEMINI_API_KEY": "test",
            "STEP1_MODEL": "gpt",
            "STEP2_MODEL": "claude",
            "FALLBACK_MODEL": "gemini",
        }
    )
    assert report["valid"]
    assert report["missing"] == []


def test_llm_connectivity_reflects_keys() -> None:
    env = {
        "OPENAI_API_KEY": "set",
        "ANTHROPIC_API_KEY": "",
        "GEMINI_API_KEY": "",
    }
    report = asyncio.run(diagnostics.test_llm_connectivity(env))
    assert report["openai"]["status"] == "configured"
    assert report["anthropic"]["status"] == "missing_key"


def test_health_check_reports_degraded_without_fastmcp() -> None:
    report = asyncio.run(diagnostics.health_check())
    assert report["server"]["status"] == "degraded"
    assert not report["configuration"]["valid"]


def test_validate_dependencies_reports_missing_playwright() -> None:
    report = asyncio.run(diagnostics.validate_dependencies())
    assert report["playwright"]["status"] in {"missing", "ok"}


def test_system_status_contains_expected_fields() -> None:
    status = asyncio.run(diagnostics.system_status())
    assert status["pid"] > 0
    datetime.fromisoformat(status["timestamp"])
    assert "memory_mb" in status
