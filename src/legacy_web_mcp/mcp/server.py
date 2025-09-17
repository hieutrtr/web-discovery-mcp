"""FastMCP server bootstrap utilities.

The implementation is designed to work with the FastMCP framework when it is
available. During development environments where FastMCP is not installed, the
module falls back to a lightweight shim so that unit tests can still exercise
the ping tool without importing the real dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

SERVER_NAME = "legacy-web-analysis"


class PingTool(Protocol):
    async def __call__(self) -> dict[str, str]:
        """Ping the server."""


@dataclass
class SimpleMCPServer:
    """Minimal asynchronous server used as a fallback during local testing."""

    name: str = SERVER_NAME
    ping_tool: PingTool | None = None

    def __post_init__(self) -> None:
        if self.ping_tool is None:
            self.ping_tool = _default_ping

    async def ping(self) -> dict[str, str]:
        return await self.ping_tool()

    def run(self) -> None:
        raise RuntimeError(
            "FastMCP is not installed. Install 'fastmcp' to run the production server."
        )


async def _default_ping() -> dict[str, str]:
    return {"status": "ok"}


def create_mcp_server() -> Any:
    """Create the MCP server instance.

    Returns a FastMCP :class:`MCPServer` when the dependency is available,
    otherwise returns :class:`SimpleMCPServer` so the remainder of the
    application can operate in a degraded but testable mode.
    """
    try:
        from fastmcp import MCPServer, tool  # type: ignore
    except ModuleNotFoundError:
        return SimpleMCPServer()

    server = MCPServer(name=SERVER_NAME)

    @tool()
    async def ping() -> dict[str, str]:
        return await _default_ping()

    server.add_tool(ping)
    return server


__all__ = ["create_mcp_server", "SimpleMCPServer", "SERVER_NAME"]
