"""Command-line entrypoint for running the Legacy Web MCP server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from legacy_web_mcp.mcp.server import run


def main() -> NoReturn:
    """Run the MCP server with command-line argument support."""
    parser = argparse.ArgumentParser(
        description="Legacy Web MCP Server - AI-powered legacy web application analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  legacy-web-mcp                 # Start MCP server (stdio mode)
  legacy-web-mcp --version       # Show version information
  legacy-web-mcp --help          # Show this help message

For more information, visit: https://github.com/your-username/web-discovery-mcp-claude-1
""",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="legacy-web-mcp 0.1.0",
        help="Show version information and exit",
    )

    parser.add_argument(
        "--config-check",
        action="store_true",
        help="Validate configuration and exit",
    )

    # Parse arguments
    args = parser.parse_args()

    if args.config_check:
        print("✅ Configuration validation not yet implemented")
        sys.exit(0)

    # Default action: run the MCP server
    try:
        print("🚀 Starting Legacy Web MCP Server...")
        print("📖 For usage help: legacy-web-mcp --help")
        print("🔗 MCP stdio transport active")
        run()
    except KeyboardInterrupt:
        print("\n👋 Legacy Web MCP Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


__all__ = ["main"]
