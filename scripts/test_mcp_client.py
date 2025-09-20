#!/usr/bin/env python3
"""Simple MCP client for testing the Legacy Web MCP Server.

This script creates a direct MCP server context to test tools
without needing external MCP client tools.

Usage:
    python scripts/test_mcp_client.py [tool_name] [args...]

Examples:
    python scripts/test_mcp_client.py ping
    python scripts/test_mcp_client.py health_check
    python scripts/test_mcp_client.py show_config
    python scripts/test_mcp_client.py discover_website https://example.com
    python scripts/test_mcp_client.py validate_dependencies
"""

import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context

# Import the actual request context that FastMCP uses
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext

from legacy_web_mcp.mcp.server import create_mcp


class MockMCPSession:
    """Mock MCP session that mimics ServerSession interface."""

    def __init__(self):
        self.session_id = "test-session-123"

    async def send_log_message(self, level: str, data: Any, logger: str = None, related_request_id: str = None):
        """Mock log message sending - print to console with formatting."""
        prefix = f"[{level.upper()}]"
        if logger:
            prefix += f" {logger}:"
        print(f"{prefix} {data}")
        if related_request_id:
            print(f"  Request ID: {related_request_id}")


def create_mock_request_context():
    """Create a mock request context that works with FastMCP."""
    mock_session = MockMCPSession()
    # Create a proper RequestContext with all required parameters
    return RequestContext(
        request_id="test-request-123",
        meta=None,  # Optional metadata
        session=mock_session,
        lifespan_context=None,  # We don't need lifespan context for basic testing
        request=None  # We don't need the request for basic tool testing
    )


class SimpleMCPClient:
    """Simple MCP client for testing purposes."""

    def __init__(self):
        self.mcp = create_mcp()
        self.context = Context(self.mcp)
        self.mock_request_context = create_mock_request_context()

    async def list_tools(self) -> dict[str, Any]:
        """List all available tools."""
        tools = await self.mcp.get_tools()
        return {name: {
            "name": tool.name,
            "description": tool.description,
            "enabled": tool.enabled
        } for name, tool in tools.items()}

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Call a specific tool with given arguments."""
        tools = await self.mcp.get_tools()
        if tool_name not in tools:
            available_tools = ", ".join(tools.keys())
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {available_tools}")

        tool = tools[tool_name]
        if not tool.enabled:
            raise ValueError(f"Tool '{tool_name}' is disabled")

        # Call the tool function with context and arguments
        try:
            # Check if the function takes a context parameter
            sig = inspect.signature(tool.fn)
            params = list(sig.parameters.keys())

            if params and params[0] == 'context':
                # Function expects context as first parameter
                # Set up mock context for tools that need session
                token = request_ctx.set(self.mock_request_context)
                try:
                    return await tool.fn(self.context, **arguments)
                finally:
                    request_ctx.reset(token)
            else:
                # Function doesn't take context
                return await tool.fn(**arguments)
        except Exception as e:
            raise RuntimeError(f"Tool execution failed: {e}") from e

    async def test_tool(self, tool_name: str, args: dict[str, Any] = None) -> None:
        """Test a specific tool and print results."""
        if args is None:
            args = {}

        print(f"🔧 Testing tool: {tool_name}")
        print(f"📝 Arguments: {args}")
        print("-" * 50)

        try:
            result = await self.call_tool(tool_name, args)
            print("✅ Success!")
            print("📊 Result:")
            if isinstance(result, dict):
                print(json.dumps(result, indent=2, default=str))
            else:
                print(str(result))
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    async def interactive_mode(self) -> None:
        """Run in interactive mode."""
        print("🚀 Legacy Web MCP Server - Interactive Testing")
        print("=" * 50)

        # List available tools
        tools = await self.list_tools()
        print("📋 Available MCP tools:")
        for name, info in tools.items():
            status = "✅" if info["enabled"] else "❌"
            print(f"  {status} {name}: {info['description']}")

        print("\n" + "=" * 50)
        print("✅ MCP server context created - all tools can be called directly!")
        print("\n📋 All testable tools:")
        print("  python scripts/test_mcp_client.py ping")
        print("  python scripts/test_mcp_client.py health_check")
        print("  python scripts/test_mcp_client.py show_config")
        print("  python scripts/test_mcp_client.py validate_dependencies")
        print("  python scripts/test_mcp_client.py test_llm_connectivity")
        print("  python scripts/test_mcp_client.py discover_website https://example.com")
        print("  python scripts/test_mcp_client.py discover_website https://github.com")
        print("  python scripts/test_mcp_client.py discover_website https://context7.com")
        print("\n💡 Note: discover_website now works with mock MCP session context!")

        print("\nPress Enter to exit...")
        input()


async def main():
    """Main entry point."""
    client = SimpleMCPClient()

    if len(sys.argv) < 2:
        # Interactive mode
        await client.interactive_mode()
        return

    tool_name = sys.argv[1]

    # Parse arguments from command line
    args = {}
    for arg in sys.argv[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            args[key] = value
        else:
            # Handle common single-argument tools
            if tool_name == "discover_website":
                args["url"] = arg
            else:
                print(f"Unknown argument format: {arg}")
                sys.exit(1)

    try:
        await client.test_tool(tool_name, args)
    except Exception as e:
        print(f"❌ Failed to test tool: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())