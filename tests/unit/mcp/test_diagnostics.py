from __future__ import annotations

from typing import Any

import pytest
from fastmcp import FastMCP

from legacy_web_mcp.mcp import diagnostics


@pytest.fixture(autouse=True)
def reset_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(diagnostics, "_PLAYWRIGHT_CHECKER", None, raising=False)
    monkeypatch.setattr(diagnostics, "_LLM_PROBE", None, raising=False)


@pytest.mark.asyncio
async def test_perform_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_browsers() -> list[diagnostics.BrowserStatus]:
        return [
            diagnostics.BrowserStatus(
                name="chromium",
                status="ok",
                details={"executable": "/bin/chromium"},
            )
        ]

    async def fake_llm(provider: str, url: str, key: str) -> dict[str, Any]:
        return {"status": "ok", "provider": provider}

    for key in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "STEP1_MODEL",
        "STEP2_MODEL",
        "FALLBACK_MODEL",
    ):
        monkeypatch.setenv(key, "test")

    diagnostics._PLAYWRIGHT_CHECKER = fake_browsers
    diagnostics._LLM_PROBE = fake_llm

    mcp = FastMCP(name="test")
    result = await diagnostics.perform_health_check(mcp)

    assert result["server"]["name"] == "test"
    assert result["environment"]["status"] == "ok"
    assert result["playwright"][0]["name"] == "chromium"
    assert result["llm"]["openai"]["status"] == "ok"


@pytest.mark.asyncio
async def test_gather_dependency_report() -> None:
    async def fake_firefox() -> list[diagnostics.BrowserStatus]:
        return [
            diagnostics.BrowserStatus(
                name="firefox",
                status="missing",
                details={"remediation": "install"},
            )
        ]

    diagnostics._PLAYWRIGHT_CHECKER = fake_firefox

    result = await diagnostics.gather_dependency_report()

    assert result["browsers"][0]["name"] == "firefox"
    assert result["browsers"][0]["status"] == "missing"


@pytest.mark.asyncio
async def test_gather_llm_connectivity_handles_missing_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(key, raising=False)

    result = await diagnostics.gather_llm_connectivity()

    assert result["openai"]["status"] == "missing_key"
    assert "remediation" in result["openai"]


def test_collect_system_status_snapshot() -> None:
    snapshot = diagnostics._collect_system_status()
    assert "timestamp" in snapshot
    assert snapshot["active_tasks"] >= 0


@pytest.mark.asyncio
async def test_register_adds_tools_and_resource_templates() -> None:
    mcp = FastMCP(name="test")
    diagnostics.register(mcp)

    tool_names = set((await mcp.get_tools()).keys())
    template_names = set((await mcp.get_resource_templates()).keys())

    assert {"health_check", "validate_dependencies", "test_llm_connectivity"}.issubset(tool_names)
    assert "/system/status/{scope}" in template_names
