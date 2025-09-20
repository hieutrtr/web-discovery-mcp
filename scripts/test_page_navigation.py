#!/usr/bin/env python3
"""Test script for page navigation and content extraction from Story 2.2.

This script tests the Page Navigation and Content Extraction implementation,
including successful navigation, content extraction, screenshot capture,
and error handling for timeouts and HTTP errors.

Usage:
    python scripts/test_page_navigation.py [command]

Commands:
    all         - Run all navigation and extraction tests
    navigation  - Test successful navigation and content extraction
    screenshot  - Test screenshot capture functionality
    errors      - Test handling of HTTP 404 and 403 errors
    timeout     - Test navigation timeout handling
"""

import asyncio
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.navigation import PageNavigationError, PageNavigator
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

async def test_successful_navigation():
    """Test successful navigation and content extraction."""
    print_test("Successful Navigation and Content Extraction")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    navigator = PageNavigator()
    project_id = "test-nav-success"
    url = "https://httpbin.org/html"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        content_data = await navigator.navigate_and_extract(page, url)
        
        print_result(content_data.status_code == 200, f"Status code: {content_data.status_code}")
        # httpbin.org/html has an empty title
        print_result(content_data.title == "", "Title is empty as expected.")
        html_content_extracted = "<h1>Herman Melville - Moby-Dick</h1>" in content_data.html_content
        print_result(html_content_extracted, "HTML content extracted")
        print_result(len(content_data.visible_text) > 100, "Visible text extracted")
        print_result(content_data.load_time > 0, f"Load time: {content_data.load_time:.2f}s")
        print_result(content_data.content_size > 0, f"Content size: {content_data.content_size} bytes")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_screenshot_capture():
    """Test screenshot capture functionality."""
    print_test("Screenshot Capture")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    navigator = PageNavigator(enable_screenshots=True)
    project_id = "test-screenshot"
    url = "https://httpbin.org/image/png"
    project_root = Path(settings.OUTPUT_ROOT) / project_id
    
    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        content_data = await navigator.navigate_and_extract(page, url, project_root)
        
        print_result(content_data.screenshot_path is not None, "Screenshot path is present")
        if content_data.screenshot_path:
            screenshot_full_path = project_root / content_data.screenshot_path
            print_result(screenshot_full_path.exists(), f"Screenshot file created at: {screenshot_full_path}")
            print(f"Screenshot saved to: {screenshot_full_path}")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_404_error_handling():
    """Test handling of HTTP 404 Not Found errors."""
    print_test("HTTP 404 Error Handling")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    navigator = PageNavigator(max_retries=1)
    project_id = "test-404"
    url = "https://httpbin.org/status/404"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        try:
            await navigator.navigate_and_extract(page, url)
            print_result(False, "Expected PageNavigationError but none was raised.")
        except PageNavigationError as e:
            print_result(e.status_code == 404, f"Correctly caught PageNavigationError with status 404. Message: {e}")
            
    except Exception as e:
        print_result(False, f"Test failed with unexpected error: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_403_error_handling():
    """Test handling of HTTP 403 Forbidden errors."""
    print_test("HTTP 403 Error Handling")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    navigator = PageNavigator(max_retries=1)
    project_id = "test-403"
    url = "https://httpbin.org/status/403"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        try:
            await navigator.navigate_and_extract(page, url)
            print_result(False, "Expected PageNavigationError but none was raised.")
        except PageNavigationError as e:
            print_result(e.status_code == 403, f"Correctly caught PageNavigationError with status 403. Message: {e}")
            
    except Exception as e:
        print_result(False, f"Test failed with unexpected error: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_navigation_timeout():
    """Test navigation timeout handling."""
    print_test("Navigation Timeout Handling")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    # Use a short timeout for testing
    navigator = PageNavigator(timeout=2.0, max_retries=1)
    project_id = "test-timeout"
    url = "https://httpbin.org/delay/5" # 5 second delay will trigger timeout
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        try:
            await navigator.navigate_and_extract(page, url)
            print_result(False, "Expected PageNavigationError for timeout but none was raised.")
        except PageNavigationError as e:
            print_result("timeout" in str(e).lower(), f"Correctly caught PageNavigationError for timeout. Message: {e}")
            
    except Exception as e:
        print_result(False, f"Test failed with unexpected error: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def run_all_tests():
    """Run all tests in sequence."""
    print_section("Page Navigation and Content Extraction Test Suite")
    await test_successful_navigation()
    await test_screenshot_capture()
    await test_404_error_handling()
    await test_403_error_handling()
    await test_navigation_timeout()
    print("\n🎉 All navigation tests completed!")

async def main():
    """Main entry point for the test script."""
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        await run_all_tests()
        return

    command = sys.argv[1].lower()
    
    if command == "navigation":
        await test_successful_navigation()
    elif command == "screenshot":
        await test_screenshot_capture()
    elif command == "errors":
        await test_404_error_handling()
        await test_403_error_handling()
    elif command == "timeout":
        await test_navigation_timeout()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())