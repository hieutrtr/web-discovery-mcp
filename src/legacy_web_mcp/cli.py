"""Command-line entrypoint for running the Legacy Web MCP server."""

from __future__ import annotations

from legacy_web_mcp.mcp.server import run


def main() -> None:
    """Run the MCP server."""
    run()


__all__ = ["main"]
