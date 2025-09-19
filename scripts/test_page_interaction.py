#!/usr/bin/env python3
"""Test script for basic page interaction automation from Story 2.4.

This script tests the Page Interaction Automation implementation,
including form interaction, scrolling, hover/focus, and modal handling.

Usage:
    python scripts/test_page_interaction.py [command]

Commands:
    all         - Run all page interaction tests
    form        - Test form interaction and submission
    scrolling   - Test page scrolling to reveal content
    hover       - Test hover and focus interactions
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.interaction import PageInteractionAutomator, InteractionConfig
from legacy_web_mcp.config.settings import MCPSettings

def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{ '='*60}")

def print_test(test_name: str) -> None:
    """Print a test header."""
    print(f"\n🔍 Testing: {test_name}")
    print("-" * 40)

def print_result(success: bool, message: str) -> None:
    """Print a test result."""
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")

async def test_form_interaction():
    """Test form interaction and submission."""
    print_test("Form Interaction")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-form-interaction"
    url = "https://httpbin.org/forms/post"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        await page.goto(url)

        interaction_config = InteractionConfig(enable_form_interactions=True, max_interactions_per_page=10)
        automator = PageInteractionAutomator(interaction_config)
        
        results = await automator.discover_and_interact(page, url)
        
        print_result(results["successful_interactions"] > 0, f"Successful interactions: {results['successful_interactions']}")
        print_result(len(automator.interaction_logs) > 0, f"Interaction logs created: {len(automator.interaction_logs)}")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_scrolling():
    """Test page scrolling to reveal lazy-loaded content."""
    print_test("Page Scrolling")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-scrolling"
    # This page has a lot of content to scroll through
    url = "https://www.google.com/search?q=playwright"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        await page.goto(url)

        interaction_config = InteractionConfig(enable_scrolling=True, max_scroll_attempts=3)
        automator = PageInteractionAutomator(interaction_config)
        
        results = await automator.discover_and_interact(page, url)
        
        scroll_logs = [log for log in automator.interaction_logs if log.interaction_type.value == "scroll"]
        print_result(len(scroll_logs) > 0, "Scrolling interactions were logged")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_hover_and_focus():
    """Test hover and focus interactions."""
    print_test("Hover and Focus Interactions")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-hover-focus"
    url = "file://" + str(Path(__file__).parent / "test_hover.html")

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        await page.goto(url)

        interaction_config = InteractionConfig(max_interactions_per_page=5)
        automator = PageInteractionAutomator(interaction_config)

        results = await automator.discover_and_interact(page, url)

        hover_logs = [log for log in automator.interaction_logs if log.interaction_type.value == "hover"]
        print_result(len(hover_logs) > 0, "Hover interactions were logged")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()


async def run_all_tests():
    """Run all tests in sequence."""
    print_section("Page Interaction Automation Test Suite")
    await test_form_interaction()
    await test_scrolling()
    await test_hover_and_focus()
    print("\n🎉 All page interaction tests completed!")

async def main():
    """Main entry point for the test script."""
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        await run_all_tests()
        return

    command = sys.argv[1].lower()
    
    if command == "form":
        await test_form_interaction()
    elif command == "scrolling":
        await test_scrolling()
    elif command == "hover":
        await test_hover_and_focus()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
