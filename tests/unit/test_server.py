from __future__ import annotations

import pytest

from legacy_web_mcp.mcp import server


@pytest.mark.asyncio
async def test_ping_returns_status() -> None:
    result = await server.ping()

    assert result["status"] == "ok"
    assert result["server_name"]
    assert result["server_version"]
    assert result["python_version"]


@pytest.mark.asyncio
async def test_create_mcp_registers_ping_tool() -> None:
    mcp = server.create_mcp()

    tool_names = set((await mcp.get_tools()).keys())
    expected_tools = {
        "ping",
        "health_check",
        "validate_dependencies",
        "test_llm_connectivity",
        "show_config",
    }
    assert expected_tools.issubset(tool_names)

    templates = set((await mcp.get_resource_templates()).keys())
    assert "/system/status/{scope}" in templates
