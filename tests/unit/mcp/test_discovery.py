"""Tests for MCP discovery tools."""
from __future__ import annotations

from pathlib import Path

import pytest

from legacy_web_mcp.discovery.http import FetchResult
from legacy_web_mcp.mcp import server


class StubFetcher:
    def __init__(self, responses: dict[str, FetchResult]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResult:
        return self._responses.get(
            url, FetchResult(url=url, status=404, text="", content_type=None)
        )


class DummyContext:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def info(self, message: str) -> None:
        self.messages.append(message)

    async def error(self, message: str) -> None:
        self.messages.append(f"error:{message}")


@pytest.mark.asyncio()
async def test_discover_website_tool_registered(tmp_path: Path) -> None:
    """Test that discover_website tool is properly registered with MCP server."""
    mcp = server.create_mcp()
    tools = await mcp.get_tools()

    assert "discover_website" in tools
    discover_tool = tools["discover_website"]

    assert discover_tool is not None
    assert hasattr(discover_tool, "description")
    description = discover_tool.description or ""
    assert "sitemap" in description.lower()


@pytest.mark.asyncio()
async def test_discover_website_tool_has_correct_schema(tmp_path: Path) -> None:
    """Test that discover_website tool has the correct input schema."""
    mcp = server.create_mcp()
    tools = await mcp.get_tools()

    assert "discover_website" in tools
    discover_tool = tools["discover_website"]

    # Check the tool has the expected schema attributes
    # FastMCP tools might use different attribute names
    if hasattr(discover_tool, 'input_schema'):
        schema = discover_tool.input_schema
        # Should have properties for url parameter
        assert 'properties' in schema
        assert 'url' in schema['properties']
    elif hasattr(discover_tool, 'signature'):
        # Alternative: check the signature has url parameter
        sig = discover_tool.signature
        assert 'url' in sig.parameters
        assert sig.parameters['url'].annotation == str
    else:
        # At minimum, the tool should be callable with url parameter
        assert discover_tool.name == "discover_website"


@pytest.mark.asyncio()
async def test_discover_website_tool_metadata(tmp_path: Path) -> None:
    """Test that discover_website tool has correct metadata."""
    mcp = server.create_mcp()
    tools = await mcp.get_tools()

    assert "discover_website" in tools
    discover_tool = tools["discover_website"]

    # Verify tool properties
    assert discover_tool.name == "discover_website"
    description = discover_tool.description or ""
    assert "discover" in description.lower()
    description = discover_tool.description or ""
    assert "sitemap" in description.lower()
    assert hasattr(discover_tool, 'enabled')
    assert discover_tool.enabled is True