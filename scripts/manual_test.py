#!/usr/bin/env python3
"""Manual testing script for the Legacy Web MCP Server.

This script helps you manually test the MCP server functionality including:
- Health checks and diagnostics
- Configuration management
- Website discovery
- Project organization

Usage:
    python scripts/manual_test.py [command]

Commands:
    health      - Run health checks and diagnostics
    config      - Test configuration management
    discover    - Test website discovery (requires URL)
    projects    - List and manage projects
    all         - Run all tests (interactive)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context
from mcp.server.lowlevel.server import request_ctx
from mcp.shared.context import RequestContext

from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.mcp.server import create_mcp
from legacy_web_mcp.storage import create_project_store


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


class MCPTester:
    """Helper class for manual MCP server testing."""

    def __init__(self):
        self.mcp = create_mcp()
        self.context = Context(self.mcp)
        self.mock_request_context = create_mock_request_context()
        self.settings = load_configuration()
        self.project_store = create_project_store(self.settings)

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
            import inspect
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

    async def test_health_checks(self) -> None:
        """Test health check and diagnostic tools."""
        print("🔍 Testing Health Checks and Diagnostics")
        print("=" * 50)

        tools_to_test = ["health_check", "validate_dependencies", "test_llm_connectivity"]

        for tool_name in tools_to_test:
            print(f"\n📊 Running {tool_name}...")
            try:
                result = await self.call_tool(tool_name, {{}})
                print(f"✅ {tool_name} passed: {result}")
            except Exception as e:
                print(f"❌ {tool_name} failed: {e}")

    async def test_configuration(self) -> None:
        """Test configuration management."""
        print("⚙️  Testing Configuration Management")
        print("=" * 50)

        print("\n📋 Running show_config...")
        try:
            result = await self.call_tool("show_config", {{}})
            config_data = result
            print("✅ Configuration retrieved:")
            print(json.dumps(config_data, indent=2))
        except Exception as e:
            print(f"❌ Configuration retrieval failed: {e}")

        # Show current settings
        print(f"\n📁 Output root: {self.settings.OUTPUT_ROOT}")
        print(f"🌐 Discovery timeout: {self.settings.DISCOVERY_TIMEOUT}s")
        print(f"📊 Discovery max depth: {self.settings.DISCOVERY_MAX_DEPTH}")

    async def test_website_discovery(self, url: str = "https://example.com") -> None:
        """Test website discovery functionality."""
        print(f"🕸️  Testing Website Discovery for: {url}")
        print("=" * 50)

        print(f"\n🔍 Discovering website: {url}")
        try:
            result = await self.call_tool("discover_website", {{"url": url}})
            discovery_data = result

            print("✅ Website discovery completed!")
            print(f"📊 Project ID: {discovery_data['project_id']}")
            print(f"🌐 Domain: {discovery_data['domain']}")
            print(f"📈 Total URLs: {discovery_data['summary']['total']}")
            print(f"📄 Internal pages: {discovery_data['summary']['internal_pages']}")
            print(f"🔗 External pages: {discovery_data['summary']['external_pages']}")
            print(f"📎 Assets: {discovery_data['summary']['assets']}")

            print("\n📋 Discovery sources:")
            sources = discovery_data['sources']
            print(f"  📄 Sitemap: {'✅' if sources['sitemap'] else '❌'}")
            print(f"  🤖 Robots.txt: {'✅' if sources['robots'] else '❌'}")
            print(f"  🕷️  Crawling: {'✅' if sources['crawl'] else '❌'}")

            print("\n📁 Project files:")
            paths = discovery_data['paths']
            print(f"  📂 Root: {paths['root']}")
            print(f"  📄 JSON: {paths['inventory_json']}")
            print(f"  📄 YAML: {paths['inventory_yaml']}")

        except Exception as e:
            print(f"❌ Website discovery failed: {e}")
            import traceback
            traceback.print_exc()

    async def test_project_management(self) -> None:
        """Test project organization and management."""
        print("📁 Testing Project Management")
        print("=" * 50)

        # List existing projects
        print("\n📋 Listing existing projects...")
        try:
            projects = self.project_store.list_projects()
            if projects:
                print(f"✅ Found {len(projects)} projects:")
                for project in projects[:5]:  # Show first 5
                    print(f"  📁 {project.project_id} ({project.domain}) - {project.discovered_url_count} URLs")
                if len(projects) > 5:
                    print(f"  ... and {len(projects) - 5} more")
            else:
                print("📭 No projects found")
        except Exception as e:
            print(f"❌ Project listing failed: {e}")

        # Show storage configuration
        print(f"\n📂 Storage root: {self.project_store.root}")
        print(f"📊 Total projects in storage: {len(self.project_store.list_projects())}")

    async def run_all_tests(self) -> None:
        """Run all tests interactively."""
        print("🚀 Legacy Web MCP Server - Manual Testing Suite")
        print("=" * 60)

        # Test health checks
        await self.test_health_checks()
        input("\nPress Enter to continue to configuration tests...")

        # Test configuration
        await self.test_configuration()
        input("\nPress Enter to continue to project management tests...")

        # Test project management
        await self.test_project_management()

        # Test website discovery
        url = input("\nEnter a website URL to test discovery (or press Enter for example.com): ").strip()
        if not url:
            url = "https://example.com"

        await self.test_website_discovery(url)

        print("\n🎉 All tests completed!")


async def main():
    """Main entry point for manual testing."""
    tester = MCPTester()

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "health":
            await tester.test_health_checks()
        elif command == "config":
            await tester.test_configuration()
        elif command == "discover":
            url = sys.argv[2] if len(sys.argv) > 2 else "https://example.com"
            await tester.test_website_discovery(url)
        elif command == "projects":
            await tester.test_project_management()
        elif command == "all":
            await tester.run_all_tests()
        else:
            print(f"❌ Unknown command: {command}")
            print(__doc__)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())