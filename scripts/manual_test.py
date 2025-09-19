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

from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.mcp.server import create_mcp
from legacy_web_mcp.storage import create_project_store


class MCPTester:
    """Helper class for manual MCP server testing."""

    def __init__(self):
        self.mcp = create_mcp()
        self.settings = load_configuration()
        self.project_store = create_project_store(self.settings)

    async def test_health_checks(self) -> None:
        """Test health check and diagnostic tools."""
        print("🔍 Testing Health Checks and Diagnostics")
        print("=" * 50)

        tools = await self.mcp.get_tools()

        # Test health_check tool
        if "health_check" in tools:
            print("\n📊 Running health_check...")
            try:
                result = await tools["health_check"].run({})
                print(f"✅ Health check passed: {result.content}")
            except Exception as e:
                print(f"❌ Health check failed: {e}")

        # Test validate_dependencies tool
        if "validate_dependencies" in tools:
            print("\n🔧 Running validate_dependencies...")
            try:
                result = await tools["validate_dependencies"].run({})
                print(f"✅ Dependencies validated: {result.content}")
            except Exception as e:
                print(f"❌ Dependencies validation failed: {e}")

        # Test test_llm_connectivity tool
        if "test_llm_connectivity" in tools:
            print("\n🌐 Running test_llm_connectivity...")
            try:
                result = await tools["test_llm_connectivity"].run({})
                print(f"✅ LLM connectivity tested: {result.content}")
            except Exception as e:
                print(f"❌ LLM connectivity test failed: {e}")

    async def test_configuration(self) -> None:
        """Test configuration management."""
        print("⚙️  Testing Configuration Management")
        print("=" * 50)

        tools = await self.mcp.get_tools()

        # Test show_config tool
        if "show_config" in tools:
            print("\n📋 Running show_config...")
            try:
                result = await tools["show_config"].run({})
                config_data = result.content
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

        tools = await self.mcp.get_tools()

        if "discover_website" in tools:
            print(f"\n🔍 Discovering website: {url}")
            try:
                result = await tools["discover_website"].run({"url": url})
                discovery_data = result.content

                print("✅ Website discovery completed!")
                print(f"📊 Project ID: {discovery_data['project_id']}")
                print(f"🌐 Domain: {discovery_data['domain']}")
                print(f"📈 Total URLs: {discovery_data['summary']['total']}")
                print(f"📄 Internal pages: {discovery_data['summary']['internal_pages']}")
                print(f"🔗 External pages: {discovery_data['summary']['external_pages']}")
                print(f"📎 Assets: {discovery_data['summary']['assets']}")

                print(f"\n📋 Discovery sources:")
                sources = discovery_data['sources']
                print(f"  📄 Sitemap: {'✅' if sources['sitemap'] else '❌'}")
                print(f"  🤖 Robots.txt: {'✅' if sources['robots'] else '❌'}")
                print(f"  🕷️  Crawling: {'✅' if sources['crawl'] else '❌'}")

                print(f"\n📁 Project files:")
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
        print(f"\n📂 Storage root: {self.project_store._root}")
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