"""FastMCP server bootstrap for the Legacy Web MCP project."""

from __future__ import annotations

import platform
from datetime import UTC, datetime
from typing import Final

import structlog
from fastmcp import FastMCP

from legacy_web_mcp.shared.logging import configure_logging

_SERVER_NAME: Final[str] = "Legacy Web MCP Server"
_SERVER_VERSION: Final[str] = "0.1.0"
_logger = structlog.get_logger("legacy_web_mcp.mcp.server")


def _build_base_payload() -> dict[str, str]:
    """Collect baseline metadata for ping responses and startup logs."""
    return {
        "server_name": _SERVER_NAME,
        "server_version": _SERVER_VERSION,
        "python_version": platform.python_version(),
    }


async def ping() -> dict[str, str]:
    """Report the MCP server status and runtime metadata."""
    payload = {
        **_build_base_payload(),
        "status": "ok",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    _logger.info("ping", **payload)
    return payload


def create_mcp() -> FastMCP:
    """Factory for a configured FastMCP instance with core tools registered."""
    configure_logging()

    mcp = FastMCP(name=_SERVER_NAME)
    mcp.tool(ping)
    return mcp


_APP: Final[FastMCP] = create_mcp()


def run() -> None:
    """Start the FastMCP server using stdio transport by default."""
    _logger.info("server_start", **_build_base_payload())
    _APP.run()


__all__ = ["create_mcp", "run", "ping"]
