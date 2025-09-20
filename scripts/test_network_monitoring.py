#!/usr/bin/env python3
"""Test script for network traffic monitoring from Story 2.3.

This script tests the Network Traffic Monitoring implementation,
including summary generation, API endpoint analysis, third-party service
detection, and filtering.

Usage:
    python scripts/test_network_monitoring.py [command]

Commands:
    all         - Run all network monitoring tests
    summary     - Test network traffic summary generation
    api         - Test API endpoint analysis
    third-party - Test third-party service detection
    filtering   - Test static asset filtering
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.network import NetworkMonitor, NetworkMonitorConfig
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

async def test_network_summary():
    """Test network traffic summary generation."""
    print_test("Network Traffic Summary")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-network-summary"
    url = "https://httpbin.org/html"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        monitor_config = NetworkMonitorConfig(filter_static_assets=False)
        base_domain = urlparse(url).netloc
        monitor = NetworkMonitor(monitor_config, base_domain)
        
        await monitor.start_monitoring(page)
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await monitor.stop_monitoring(page)
        
        summary = monitor.get_summary()
        
        print_result(summary.total_requests > 0, f"Total requests: {summary.total_requests}")
        print_result(summary.total_bytes > 0, f"Total bytes: {summary.total_bytes}")
        print_result(len(summary.unique_domains) > 0, f"Unique domains: {len(summary.unique_domains)}")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_api_endpoint_analysis():
    """Test API endpoint analysis."""
    print_test("API Endpoint Analysis")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-api-analysis"
    url = "https://httpbin.org/get"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        monitor_config = NetworkMonitorConfig()
        base_domain = urlparse(url).netloc
        monitor = NetworkMonitor(monitor_config, base_domain)
        
        await monitor.start_monitoring(page)
        await page.goto(url)
        # Make a fetch call to an API endpoint
        await page.evaluate("() => fetch('/json')")
        await page.wait_for_load_state("networkidle")
        await monitor.stop_monitoring(page)
        
        summary = monitor.get_summary()
        
        print_result(summary.api_requests > 0, f"API requests: {summary.api_requests}")
        print_result(len(summary.api_endpoints) > 0, f"API endpoints: {summary.api_endpoints}")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_third_party_service_detection():
    """Test third-party service detection."""
    print_test("Third-Party Service Detection")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-third-party"
    # A page with known third-party requests (e.g., Google Fonts)
    url = "https://fonts.google.com/"
    
    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()
        
        monitor_config = NetworkMonitorConfig(filter_static_assets=False)
        base_domain = urlparse(url).netloc
        monitor = NetworkMonitor(monitor_config, base_domain)
        
        await monitor.start_monitoring(page)
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await monitor.stop_monitoring(page)
        
        summary = monitor.get_summary()
        
        print_result(summary.third_party_requests > 0, f"Third-party requests: {summary.third_party_requests}")
        print_result(len(summary.third_party_domains) > 0, f"Third-party domains: {summary.third_party_domains}")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_static_asset_filtering():
    """Test static asset filtering."""
    print_test("Static Asset Filtering")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-filtering"
    url = "file://" + str(Path(__file__).parent / "test.html")
    
    try:
        await service.initialize()
        
        # Run with filtering disabled
        session_no_filter = await service.create_session(f"{project_id}-no-filter", engine=BrowserEngine.CHROMIUM)
        page_no_filter = await session_no_filter.create_page()
        monitor_config_no_filter = NetworkMonitorConfig(filter_static_assets=False)
        base_domain = urlparse(url).netloc
        monitor_no_filter = NetworkMonitor(monitor_config_no_filter, base_domain)
        await monitor_no_filter.start_monitoring(page_no_filter)
        await page_no_filter.goto(url)
        await page_no_filter.wait_for_load_state("networkidle")
        await monitor_no_filter.stop_monitoring(page_no_filter)
        summary_no_filter = monitor_no_filter.get_summary()
        await service.close_session(f"{project_id}-no-filter")

        # Run with filtering enabled
        session_filter = await service.create_session(f"{project_id}-filter", engine=BrowserEngine.CHROMIUM)
        page_filter = await session_filter.create_page()
        monitor_config_filter = NetworkMonitorConfig(filter_static_assets=True)
        monitor_filter = NetworkMonitor(monitor_config_filter, base_domain)
        await monitor_filter.start_monitoring(page_filter)
        await page_filter.goto(url)
        await page_filter.wait_for_load_state("networkidle")
        await monitor_filter.stop_monitoring(page_filter)
        summary_filter = monitor_filter.get_summary()
        await service.close_session(f"{project_id}-filter")

        print(f"Requests without filtering: {summary_no_filter.total_requests}")
        print(f"Requests with filtering: {summary_filter.total_requests}")
        print_result(summary_no_filter.total_requests > summary_filter.total_requests, "Filtering reduces request count")
        
    except Exception as e:
        print_result(False, f"Test failed: {e}")
    finally:
        await service.shutdown()

async def run_all_tests():
    """Run all tests in sequence."""
    print_section("Network Traffic Monitoring Test Suite")
    await test_network_summary()
    await test_api_endpoint_analysis()
    await test_third_party_service_detection()
    await test_static_asset_filtering()
    print("\n🎉 All network monitoring tests completed!")

async def main():
    """Main entry point for the test script."""
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        await run_all_tests()
        return

    command = sys.argv[1].lower()
    
    if command == "summary":
        await test_network_summary()
    elif command == "api":
        await test_api_endpoint_analysis()
    elif command == "third-party":
        await test_third_party_service_detection()
    elif command == "filtering":
        await test_static_asset_filtering()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
