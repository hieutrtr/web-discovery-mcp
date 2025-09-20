#!/usr/bin/env python3
"""Test script for browser session management features from Story 2.1.

This script tests the Playwright Browser Session Management implementation
following the patterns established in the existing scripts folder.

Features tested:
- Multi-engine browser support (Chromium, Firefox, WebKit)
- Session lifecycle management with proper cleanup
- Concurrency control with configurable limits
- Crash detection and recovery
- Headless/headed mode configuration
- Performance metrics collection

Usage:
    python scripts/test_browser_session.py [command]

Commands:
    all         - Run all browser session tests
    engines     - Test multi-engine support
    concurrency - Test concurrent session limits
    lifecycle   - Test session lifecycle management
    recovery    - Test crash detection and recovery
    metrics     - Test performance metrics collection
    install     - Validate browser installation
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import (
    BrowserAutomationService,
    BrowserEngine,
    SessionLimitExceededError,
)
from legacy_web_mcp.config.settings import MCPSettings


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")


def print_test(test_name: str) -> None:
    """Print a test header."""
    print(f"\n🔍 Testing: {test_name}")
    print("-" * 40)


def print_result(success: bool, message: str) -> None:
    """Print a test result."""
    emoji = "✅" if success else "❌"
    print(f"{emoji} {message}")


def print_metrics(metrics: dict[str, Any], prefix: str = "  ") -> None:
    """Print metrics in a formatted way."""
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(f"{prefix}📊 {key}:")
            print_metrics(value, prefix + "  ")
        else:
            print(f"{prefix}📊 {key}: {value}")


async def test_browser_installation() -> dict[str, Any]:
    """Test browser installation validation."""
    print_test("Browser Installation Validation")

    settings = MCPSettings()
    service = BrowserAutomationService(settings)

    try:
        results = await service.validate_browser_installation()

        for engine, result in results.items():
            success = result["status"] == "available"
            print_result(success, f"{engine.capitalize()}: {result['status']}")

            if not success and "remediation" in result.get("details", {}):
                print(f"    💡 Fix: {result['details']['remediation']}")

        available_engines = [k for k, v in results.items() if v["status"] == "available"]
        print(f"\n📊 Summary: {len(available_engines)}/3 engines available")

        return results

    finally:
        await service.shutdown()


async def test_multi_engine_support() -> dict[str, Any]:
    """Test multi-engine browser support."""
    print_test("Multi-Engine Browser Support")

    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    results = {}
    test_url = "https://httpbin.org/get"

    try:
        for engine in [BrowserEngine.CHROMIUM, BrowserEngine.FIREFOX, BrowserEngine.WEBKIT]:
            print(f"\n  🌐 Testing {engine.value}...")

            try:
                # Create session with specific engine
                session = await service.create_session(
                    project_id=f"engine-test-{engine.value}",
                    engine=engine,
                    headless=True
                )

                # Navigate to test URL
                page = await service.navigate_page(f"engine-test-{engine.value}", test_url)
                title = await page.title()
                url = page.url

                # Collect metrics
                metrics = session.metrics

                results[engine.value] = {
                    "status": "success",
                    "session_id": session.session_id,
                    "page_title": title,
                    "final_url": url,
                    "pages_loaded": metrics.pages_loaded,
                    "session_duration": metrics.session_duration,
                }

                print_result(True, f"{engine.value}: Session created, page loaded")
                print(f"    📄 Title: {title}")
                print(f"    🔗 URL: {url}")

                # Clean up
                await page.close()
                await service.close_session(f"engine-test-{engine.value}")

            except Exception as e:
                results[engine.value] = {
                    "status": "failed",
                    "error": str(e)
                }
                print_result(False, f"{engine.value}: {str(e)}")

        successful_engines = [k for k, v in results.items() if v["status"] == "success"]
        print(f"\n📊 Summary: {len(successful_engines)}/{len(results)} engines working")

        return results

    finally:
        await service.shutdown()


async def test_concurrency_control() -> dict[str, Any]:
    """Test concurrency control and session limits."""
    print_test("Concurrency Control and Session Limits")

    # Set low limit for testing
    max_concurrent = 2
    settings = MCPSettings(MAX_CONCURRENT_PAGES=max_concurrent)
    service = BrowserAutomationService(settings)

    try:
        sessions = []

        # Create sessions up to limit
        print(f"  🔄 Creating {max_concurrent} concurrent sessions...")
        for i in range(max_concurrent):
            session = await service.create_session(
                project_id=f"concurrent-{i}",
                headless=True
            )
            sessions.append((f"concurrent-{i}", session))
            print_result(True, f"Session {i+1}/{max_concurrent} created: {session.session_id}")

        # Check service metrics
        metrics = await service.get_service_metrics()
        print_metrics({
            "Active sessions": metrics['active_sessions'],
            "Max concurrent": metrics['max_concurrent'],
            "Available slots": metrics['available_slots']
        })

        # Try to exceed limit
        print("\n  🚫 Attempting to exceed limit...")
        try:
            await service.create_session(
                project_id="concurrent-overflow",
                headless=True
            )
            print_result(False, "Expected SessionLimitExceededError but session was created")
            limit_enforced = False
        except SessionLimitExceededError as e:
            print_result(True, f"Limit correctly enforced: {e}")
            limit_enforced = True

        # Test navigation with concurrent sessions
        print("\n  🌐 Testing navigation with concurrent sessions...")
        for i, (project_id, session) in enumerate(sessions):
            try:
                page = await service.navigate_page(project_id, f"https://httpbin.org/delay/{i+1}")
                print_result(True, f"Session {i+1} navigated successfully")
                await page.close()
            except Exception as e:
                print_result(False, f"Session {i+1} navigation failed: {e}")

        # Clean up sessions one by one and verify slot release
        print("\n  🧹 Cleaning up sessions...")
        for project_id, session in sessions:
            await service.close_session(project_id)
            current_metrics = await service.get_service_metrics()
            print_result(True, f"Session closed: {project_id} (Active: {current_metrics['active_sessions']})")

        # Verify all slots are available
        final_metrics = await service.get_service_metrics()
        cleanup_successful = final_metrics['active_sessions'] == 0

        return {
            "max_concurrent": max_concurrent,
            "sessions_created": len(sessions),
            "limit_enforced": limit_enforced,
            "cleanup_successful": cleanup_successful,
            "final_active_sessions": final_metrics['active_sessions']
        }

    finally:
        await service.shutdown()


async def test_session_lifecycle() -> dict[str, Any]:
    """Test session lifecycle management."""
    print_test("Session Lifecycle Management")

    settings = MCPSettings()
    service = BrowserAutomationService(settings)

    try:
        project_id = "lifecycle-test"

        # Create session
        print("  🚀 Creating browser session...")
        session = await service.create_session(project_id, headless=True)
        print_result(True, f"Session created: {session.session_id}")
        print_metrics({
            "Status": session.metrics.status.value,
            "Engine": session.metrics.engine.value,
            "Created": session.metrics.created_at.isoformat()
        })

        # Navigate to multiple pages
        test_urls = [
            ("Basic GET", "https://httpbin.org/get"),
            ("Headers", "https://httpbin.org/headers"),
            ("User Agent", "https://httpbin.org/user-agent"),
            ("Delayed Response", "https://httpbin.org/delay/1")
        ]

        print(f"\n  🌐 Testing navigation to {len(test_urls)} pages...")
        for i, (desc, url) in enumerate(test_urls):
            start_time = time.time()
            page = await service.navigate_page(project_id, url, create_new_page=True)
            load_time = time.time() - start_time

            title = await page.title()
            page_url = page.url

            print_result(True, f"{desc}: {title} ({load_time:.2f}s)")
            print(f"    🔗 URL: {page_url}")

            await page.close()

        # Check session metrics
        print("\n  📊 Session metrics after navigation:")
        metrics = session.metrics
        print_metrics({
            "Pages loaded": metrics.pages_loaded,
            "Total load time": f"{metrics.total_load_time:.2f}s",
            "Average load time": f"{metrics.average_load_time:.2f}s",
            "Session duration": f"{metrics.session_duration:.2f}s",
            "Crash count": metrics.crash_count
        })

        # Test session retrieval
        print("\n  🔍 Testing session retrieval...")
        retrieved_session = await service.get_session(project_id)
        session_found = retrieved_session is not None and retrieved_session.session_id == session.session_id
        print_result(session_found, f"Session retrieval: {session_found}")

        # Test context and pages
        print("\n  📄 Testing context and pages...")
        context_pages = len(session.context.pages)
        print_result(True, f"Context has {context_pages} pages")

        # Close session
        print("\n  🔚 Closing session...")
        await service.close_session(project_id)
        print_result(True, "Session closed")

        # Verify session cleanup
        closed_session = await service.get_session(project_id)
        cleanup_verified = closed_session is None
        print_result(cleanup_verified, f"Session cleanup verified: {cleanup_verified}")

        return {
            "session_id": session.session_id,
            "pages_loaded": metrics.pages_loaded,
            "average_load_time": metrics.average_load_time,
            "session_duration": metrics.session_duration,
            "crash_count": metrics.crash_count,
            "cleanup_successful": cleanup_verified
        }

    finally:
        await service.shutdown()


async def test_crash_detection_recovery() -> dict[str, Any]:
    """Test crash detection and recovery mechanisms."""
    print_test("Crash Detection and Recovery")

    settings = MCPSettings()
    service = BrowserAutomationService(settings)

    try:
        project_id = "recovery-test"

        # Create initial session
        print("  🚀 Creating initial session...")
        session = await service.create_session(project_id, headless=True)
        print_result(True, f"Initial session created: {session.session_id}")

        # Navigate to test page
        print("  🌐 Initial navigation...")
        page = await service.navigate_page(project_id, "https://httpbin.org/get")
        initial_title = await page.title()
        print_result(True, f"Initial navigation successful: {initial_title}")
        await page.close()

        # Force close browser context to simulate crash
        print("  💥 Simulating browser crash...")
        await session.context.close()
        print_result(True, "Browser context forcibly closed")

        # Test recovery mechanism
        print("  🔄 Testing recovery mechanism...")
        try:
            # This should trigger recovery
            recovery_page = await service.navigate_page(project_id, "https://httpbin.org/headers")
            recovery_title = await recovery_page.title()
            print_result(True, f"Recovery successful: {recovery_title}")

            # Verify new session was created
            recovered_session = await service.get_session(project_id)
            session_recreated = recovered_session.session_id != session.session_id
            print_result(session_recreated, f"New session created: {session_recreated}")

            await recovery_page.close()
            recovery_successful = True

        except Exception as e:
            print_result(False, f"Recovery failed: {e}")
            recovery_successful = False

        # Test navigation error handling
        print("  🚫 Testing invalid URL handling...")
        try:
            invalid_page = await service.navigate_page(project_id, "invalid://malformed-url")
            print_result(False, "Expected navigation error but succeeded")
            error_handled = False
        except Exception as e:
            print_result(True, f"Navigation error handled: {type(e).__name__}")
            error_handled = True

        # Get final metrics
        final_session = await service.get_session(project_id)
        if final_session:
            final_metrics = final_session.metrics
            print_metrics({
                "Final session ID": final_metrics.session_id,
                "Status": final_metrics.status.value,
                "Pages loaded": final_metrics.pages_loaded,
                "Crash count": final_metrics.crash_count
            })

        await service.close_session(project_id)

        return {
            "initial_session_id": session.session_id,
            "recovery_successful": recovery_successful,
            "error_handling": error_handled,
            "session_recreated": session_recreated if 'session_recreated' in locals() else False
        }

    finally:
        await service.shutdown()


async def test_performance_metrics() -> dict[str, Any]:
    """Test performance metrics collection."""
    print_test("Performance Metrics Collection")

    settings = MCPSettings()
    service = BrowserAutomationService(settings)

    try:
        project_id = "metrics-test"

        # Create session
        session = await service.create_session(project_id, headless=True)
        print_result(True, f"Session created for metrics testing: {session.session_id}")

        # Load pages with different timing characteristics
        test_scenarios = [
            ("Fast response", "https://httpbin.org/get"),
            ("1 second delay", "https://httpbin.org/delay/1"),
            ("2 second delay", "https://httpbin.org/delay/2"),
            ("JSON response", "https://httpbin.org/json"),
            ("Large response", "https://httpbin.org/html")
        ]

        print(f"\n  🌐 Loading {len(test_scenarios)} test pages...")
        individual_times = []

        for desc, url in test_scenarios:
            start_time = time.time()
            page = await service.navigate_page(project_id, url, create_new_page=True)
            load_time = time.time() - start_time
            individual_times.append(load_time)

            title = await page.title()
            print_result(True, f"{desc}: {title} ({load_time:.2f}s)")
            await page.close()

        # Get session metrics
        session_metrics = session.metrics
        print("\n  📊 Session-level metrics:")
        print_metrics({
            "Session ID": session_metrics.session_id,
            "Engine": session_metrics.engine.value,
            "Status": session_metrics.status.value,
            "Pages loaded": session_metrics.pages_loaded,
            "Total load time": f"{session_metrics.total_load_time:.2f}s",
            "Average load time": f"{session_metrics.average_load_time:.2f}s",
            "Session duration": f"{session_metrics.session_duration:.2f}s",
            "Crash count": session_metrics.crash_count,
            "Memory usage": f"{session_metrics.memory_usage_mb or 'N/A'} MB"
        })

        # Get service-level metrics
        service_metrics = await service.get_service_metrics()
        print("\n  📊 Service-level metrics:")
        print_metrics({
            "Active sessions": service_metrics['active_sessions'],
            "Max concurrent": service_metrics['max_concurrent'],
            "Available slots": service_metrics['available_slots'],
            "Total pages loaded": service_metrics['total_pages_loaded'],
            "Total crashes": service_metrics['total_crashes']
        })

        # Verify metrics accuracy
        print("\n  🔍 Metrics verification:")
        expected_pages = len(test_scenarios)
        actual_pages = session_metrics.pages_loaded
        pages_accurate = expected_pages == actual_pages
        print_result(pages_accurate, f"Page count accurate: {actual_pages}/{expected_pages}")

        timing_reasonable = 0 < session_metrics.average_load_time < 10
        print_result(timing_reasonable, f"Timing reasonable: {session_metrics.average_load_time:.2f}s avg")

        await service.close_session(project_id)

        return {
            "session_metrics": {
                "session_id": session_metrics.session_id,
                "pages_loaded": session_metrics.pages_loaded,
                "total_load_time": session_metrics.total_load_time,
                "average_load_time": session_metrics.average_load_time,
                "session_duration": session_metrics.session_duration,
                "crash_count": session_metrics.crash_count
            },
            "service_metrics": service_metrics,
            "individual_load_times": individual_times,
            "metrics_accuracy": {
                "pages_accurate": pages_accurate,
                "timing_reasonable": timing_reasonable
            }
        }

    finally:
        await service.shutdown()


async def run_all_tests() -> dict[str, Any]:
    """Run all browser session tests."""
    print_section("Browser Session Management Test Suite")
    print("Testing all features from Story 2.1: Playwright Browser Session Management")

    all_results = {}

    test_suite = [
        ("Browser Installation", test_browser_installation),
        ("Multi-Engine Support", test_multi_engine_support),
        ("Concurrency Control", test_concurrency_control),
        ("Session Lifecycle", test_session_lifecycle),
        ("Crash Detection & Recovery", test_crash_detection_recovery),
        ("Performance Metrics", test_performance_metrics),
    ]

    passed_tests = 0

    for test_name, test_func in test_suite:
        try:
            print_section(test_name)
            result = await test_func()
            all_results[test_name.lower().replace(" ", "_").replace("&", "and")] = {
                "status": "passed",
                "result": result
            }
            print_result(True, f"{test_name} completed successfully")
            passed_tests += 1

        except Exception as e:
            all_results[test_name.lower().replace(" ", "_").replace("&", "and")] = {
                "status": "failed",
                "error": str(e)
            }
            print_result(False, f"{test_name} failed: {e}")

    # Final summary
    print_section("Test Suite Summary")
    print(f"📊 Tests passed: {passed_tests}/{len(test_suite)}")

    for test_name, result in all_results.items():
        status_emoji = "✅" if result["status"] == "passed" else "❌"
        print(f"{status_emoji} {test_name.replace('_', ' ').title()}")

    # Save results
    results_file = Path("browser_session_test_results.json")
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n📄 Detailed results saved to: {results_file}")

    return all_results


def print_usage():
    """Print usage information."""
    print(__doc__)


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        command = "all"
    else:
        command = sys.argv[1].lower()

    commands = {
        "all": run_all_tests,
        "engines": test_multi_engine_support,
        "concurrency": test_concurrency_control,
        "lifecycle": test_session_lifecycle,
        "recovery": test_crash_detection_recovery,
        "metrics": test_performance_metrics,
        "install": test_browser_installation,
    }

    if command == "help" or command not in commands:
        print_usage()
        return

    try:
        await commands[command]()
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())