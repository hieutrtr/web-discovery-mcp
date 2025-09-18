"""MCP tools exposing configuration state."""
from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from legacy_web_mcp.config.loader import load_configuration


def register(mcp: FastMCP) -> None:
    """Register configuration-related tools."""

    @mcp.tool(
        name="show_config",
        description="Display current configuration with sensitive fields redacted.",
    )
    async def show_config(context: Context) -> dict[str, Any]:
        settings = load_configuration()
        return settings.display_dict()


__all__ = ["register"]
