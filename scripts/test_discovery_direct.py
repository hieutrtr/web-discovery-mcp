#!/usr/bin/env python3
"""Direct testing of the discovery pipeline without MCP layer.

This script tests the website discovery functionality directly by calling
the underlying services, bypassing the MCP context requirements.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.discovery.pipeline import WebsiteDiscoveryService
from legacy_web_mcp.storage import create_project_store


class DummyContext:
    """Mock context for testing purposes."""

    def __init__(self):
        self.messages = []

    async def info(self, message: str) -> None:
        print(f"ℹ️  {message}")
        self.messages.append(message)

    async def error(self, message: str) -> None:
        print(f"❌ {message}")
        self.messages.append(f"error:{message}")


async def test_discovery(url: str) -> None:
    """Test website discovery directly."""
    print(f"🕸️  Testing Website Discovery for: {url}")
    print("=" * 60)

    try:
        # Load configuration
        print("📋 Loading configuration...")
        settings = load_configuration()
        print(f"✅ Configuration loaded. Output root: {settings.OUTPUT_ROOT}")

        # Create project store
        print("📁 Initializing project store...")
        project_store = create_project_store(settings)
        print(f"✅ Project store initialized at: {project_store.root}")

        # Create discovery service
        print("🔧 Creating discovery service...")
        service = WebsiteDiscoveryService(settings, project_store=project_store)
        print("✅ Discovery service created")

        # Create dummy context
        context = DummyContext()

        # Run discovery
        print(f"\n🔍 Starting discovery for: {url}")
        print("-" * 40)

        result = await service.discover(context, url)

        print("-" * 40)
        print("✅ Discovery completed successfully!")
        print()

        # Display results
        print("📊 Discovery Results:")
        print(f"  🆔 Project ID: {result['project_id']}")
        print(f"  🌐 Domain: {result['domain']}")

        summary = result['summary']
        print(f"  📈 Total URLs: {summary['total']}")
        print(f"  📄 Internal pages: {summary['internal_pages']}")
        print(f"  🔗 External pages: {summary['external_pages']}")
        print(f"  📎 Assets: {summary['assets']}")

        sources = result['sources']
        print(f"\n📋 Discovery Sources:")
        print(f"  📄 Sitemap: {'✅ Used' if sources['sitemap'] else '❌ Not found/used'}")
        print(f"  🤖 Robots.txt: {'✅ Used' if sources['robots'] else '❌ Not found/used'}")
        print(f"  🕷️  Crawling: {'✅ Used' if sources['crawl'] else '❌ Not used'}")

        paths = result['paths']
        print(f"\n📁 Generated Files:")
        print(f"  📂 Project root: {paths['root']}")
        print(f"  📄 JSON inventory: {paths['inventory_json']}")
        print(f"  📄 YAML inventory: {paths['inventory_yaml']}")

        # Check if files exist
        json_path = Path(paths['inventory_json'])
        yaml_path = Path(paths['inventory_yaml'])

        print(f"\n📋 File Status:")
        print(f"  📄 JSON exists: {'✅' if json_path.exists() else '❌'}")
        print(f"  📄 YAML exists: {'✅' if yaml_path.exists() else '❌'}")

        if json_path.exists():
            print(f"  📊 JSON size: {json_path.stat().st_size} bytes")

        # Show some sample URLs if available
        if 'inventory' in result and 'urls' in result['inventory']:
            urls_data = result['inventory']['urls']

            print(f"\n🔗 Sample URLs Found:")
            for category, urls in urls_data.items():
                if urls:
                    print(f"  📁 {category.replace('_', ' ').title()}: {len(urls)} URLs")
                    # Show first 3 URLs as examples
                    for i, url_info in enumerate(urls[:3]):
                        url_str = url_info.get('url', 'Unknown URL')
                        print(f"    {i+1}. {url_str}")
                    if len(urls) > 3:
                        print(f"    ... and {len(urls) - 3} more")

        print(f"\n📝 Total log messages: {len(context.messages)}")

        # Show any errors in discovery
        if 'errors' in result:
            errors = result['errors']
            if any(errors.values()):
                print(f"\n⚠️  Errors encountered:")
                for error_type, error_list in errors.items():
                    if error_list:
                        print(f"  {error_type}: {error_list}")

        print(f"\n🎉 Discovery test completed successfully!")

    except Exception as e:
        print(f"\n❌ Discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_discovery_direct.py <URL>")
        print("Example: python scripts/test_discovery_direct.py https://github.com")
        sys.exit(1)

    url = sys.argv[1]

    try:
        success = await test_discovery(url)
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Discovery test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())