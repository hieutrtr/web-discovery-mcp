from __future__ import annotations

import pytest
from typing import cast

from fastmcp import Context
from fastmcp.tools.tool import FunctionTool

from legacy_web_mcp.mcp import server


@pytest.fixture
def required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {
        "OPENAI_API_KEY": "openai-key",
        "ANTHROPIC_API_KEY": "anthropic-key",
        "GEMINI_API_KEY": "gemini-key",
        "STEP1_MODEL": "gpt-step1",
        "STEP2_MODEL": "gpt-step2",
        "FALLBACK_MODEL": "gpt-fallback",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)


@pytest.mark.asyncio
async def test_show_config_tool_redacts_sensitive_fields(required_env: None) -> None:
    mcp = server.create_mcp()
    tools = await mcp.get_tools()
    show_config = cast(FunctionTool, tools["show_config"])

    payload = await show_config.fn(Context(mcp))

    assert payload["OPENAI_API_KEY"] == "***"
    assert payload["ANTHROPIC_API_KEY"] == "***"
    assert payload["GEMINI_API_KEY"] == "***"
    assert payload["STEP1_MODEL"] == "gpt-step1"
    assert payload["STEP2_MODEL"] == "gpt-step2"
    assert payload["FALLBACK_MODEL"] == "gpt-fallback"
    assert payload["BROWSER_ENGINE"] == "chromium"
    assert payload["MAX_CONCURRENT_PAGES"] == 3
    assert isinstance(payload["OUTPUT_ROOT"], str)
    assert payload["OUTPUT_ROOT"].endswith("docs/web_discovery")
