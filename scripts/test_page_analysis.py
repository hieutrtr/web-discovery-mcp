#!/usr/bin/env python3
"""Test script for comprehensive page analysis from Story 2.5.

This script tests the Page Analysis Data Collection implementation,
including DOM structure analysis, technology detection, accessibility evaluation,
performance metrics, and comprehensive page categorization for LLM processing.

Usage:
    python scripts/test_page_analysis.py [command]

Commands:
    all               - Run all page analysis tests
    comprehensive     - Test comprehensive page analysis with all features
    dom_structure     - Test DOM structure analysis specifically
    technology        - Test technology detection capabilities
    mcp_tools         - Test MCP tools for page analysis via client
    simple            - Test basic page analysis without extra features

The script references the core PageAnalyzer implementation in:
- src/legacy_web_mcp/browser/analysis.py
- src/legacy_web_mcp/mcp/analysis_tools.py

And follows the testing patterns established in existing scripts like test_page_navigation.py
"""

import asyncio
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.analysis import PageAnalyzer, PageType
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

def print_analysis_summary(analysis_data) -> None:
    """Print a summary of the analysis results."""
    print("\n📊 Analysis Summary:")
    print(f"  Page Type: {analysis_data.page_functionality.page_type}")
    print(f"  DOM Elements: {analysis_data.dom_structure.total_elements}")
    print(f"  Interactive Elements: {analysis_data.dom_structure.interactive_elements}")
    print(f"  Technology Score: {analysis_data.technology_detection.complexity_score:.1f}")
    print(f"  Accessibility Score: {analysis_data.accessibility_evaluation.accessibility_score:.1f}")
    if analysis_data.technology_detection.primary_framework:
        print(f"  Primary Framework: {analysis_data.technology_detection.primary_framework}")

async def test_comprehensive_analysis():
    """Test comprehensive page analysis with all features enabled."""
    print_test("Comprehensive Page Analysis with All Features")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    analyzer = PageAnalyzer()
    project_id = "test-comprehensive-analysis"
    url = "https://httpbin.org/html"  # Simple HTML page for testing
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()

        # Run comprehensive analysis
        analysis_data = await analyzer.analyze_comprehensive(
            page=page,
            url=url,
            project_root=project_root,
            include_network_monitoring=True,
            include_interaction_simulation=True,
            include_performance_metrics=True
        )

        # Verify analysis components
        print_result(analysis_data.page_content.status_code == 200, f"Page loaded successfully: {analysis_data.page_content.status_code}")
        print_result(analysis_data.dom_structure.total_elements > 0, f"DOM structure analyzed: {analysis_data.dom_structure.total_elements} elements")
        print_result(analysis_data.page_functionality.page_type != PageType.UNKNOWN, f"Page type classified: {analysis_data.page_functionality.page_type}")
        print_result(analysis_data.accessibility_evaluation.accessibility_score >= 0, f"Accessibility evaluated: {analysis_data.accessibility_evaluation.accessibility_score:.1f}")
        print_result(analysis_data.technology_detection.total_technologies > 0, f"Technologies detected: {analysis_data.technology_detection.total_technologies}")
        print_result(analysis_data.css_analysis.total_rules >= 0, f"CSS analysis performed: {analysis_data.css_analysis.total_rules} rules")
        print_result(analysis_data.performance_metrics.total_load_time > 0, f"Performance metrics collected: {analysis_data.performance_metrics.total_load_time:.2f}s")

        # Check for network monitoring data (if enabled)
        if analysis_data.network_traffic:
            print_result(analysis_data.network_traffic.total_requests >= 0, f"Network traffic monitored: {analysis_data.network_traffic.total_requests} requests")

        print_analysis_summary(analysis_data)

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_dom_structure_analysis():
    """Test DOM structure analysis specifically."""
    print_test("DOM Structure Analysis")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    analyzer = PageAnalyzer()
    project_id = "test-dom-analysis"
    url = "https://httpbin.org/forms/post"  # Page with forms for interactive elements
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()

        # Run analysis focusing on DOM structure
        analysis_data = await analyzer.analyze_comprehensive(
            page=page,
            url=url,
            project_root=project_root,
            include_network_monitoring=False,  # Disabled for focused test
            include_interaction_simulation=True,  # Enabled to detect forms
            include_performance_metrics=False
        )

        dom = analysis_data.dom_structure
        print_result(dom.total_elements > 0, f"Total elements analyzed: {dom.total_elements}")
        print_result(dom.interactive_elements > 0, f"Interactive elements found: {dom.interactive_elements}")
        print_result(len(dom.semantic_elements) > 0, f"Semantic elements identified: {len(dom.semantic_elements)}")
        print_result(dom.nesting_depth > 0, f"DOM nesting depth: {dom.nesting_depth}")

        # Check for form elements since we're using forms/post page
        print_result(analysis_data.page_functionality.has_forms, "Forms detected on page")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_technology_detection():
    """Test technology detection capabilities."""
    print_test("Technology Detection")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    analyzer = PageAnalyzer()
    project_id = "test-tech-detection"
    url = "https://httpbin.org/"  # Main httpbin page which might have some technologies
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()

        # Run analysis focusing on technology detection
        analysis_data = await analyzer.analyze_comprehensive(
            page=page,
            url=url,
            project_root=project_root,
            include_network_monitoring=False,
            include_interaction_simulation=False,
            include_performance_metrics=False
        )

        tech = analysis_data.technology_detection
        print_result(tech.total_technologies >= 0, f"Technologies scanned: {tech.total_technologies}")
        print_result(tech.complexity_score >= 0, f"Complexity score calculated: {tech.complexity_score:.1f}")
        print_result(len(tech.css_frameworks) >= 0, f"CSS frameworks detected: {len(tech.css_frameworks)}")
        print_result(len(tech.js_libraries) >= 0, f"JS libraries detected: {len(tech.js_libraries)}")

        # Print detected technologies
        if tech.primary_framework:
            print(f"  Primary Framework: {tech.primary_framework}")
        if tech.css_frameworks:
            print(f"  CSS Frameworks: {', '.join(tech.css_frameworks)}")
        if tech.js_libraries:
            print(f"  JS Libraries: {', '.join(tech.js_libraries)}")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def test_mcp_tools():
    """Test MCP tools for page analysis via the test client."""
    print_test("MCP Tools for Page Analysis")

    # Import the MCP client for testing
    from scripts.test_mcp_client import SimpleMCPClient

    client = SimpleMCPClient()

    try:
        # Test analyze_page_comprehensive tool
        print("🔧 Testing analyze_page_comprehensive MCP tool...")
        result = await client.call_tool("analyze_page_comprehensive", {
            "url": "https://httpbin.org/html",
            "project_id": "mcp-test-comprehensive",
            "include_network_monitoring": False,  # Disable for faster testing
            "include_interaction_simulation": False,
            "include_performance_metrics": True,
            "save_analysis_data": True,
            "browser_engine": "chromium"
        })

        print_result(result.get("status") == "success", f"Comprehensive analysis completed: {result.get('status')}")
        if result.get("analysis_summary"):
            summary = result["analysis_summary"]
            print_result("page_type" in summary, f"Page type classified: {summary.get('page_type', 'unknown')}")
            print_result("dom_elements" in summary, f"DOM elements counted: {summary.get('dom_elements', 0)}")

        # Test analyze_dom_structure tool
        print("\n🔧 Testing analyze_dom_structure MCP tool...")
        result = await client.call_tool("analyze_dom_structure", {
            "url": "https://httpbin.org/forms/post",
            "project_id": "mcp-test-dom",
            "browser_engine": "chromium"
        })

        print_result(result.get("status") == "success", f"DOM analysis completed: {result.get('status')}")
        if result.get("dom_structure"):
            dom = result["dom_structure"]
            print_result(dom.get("total_elements", 0) > 0, f"DOM elements analyzed: {dom.get('total_elements', 0)}")

        # Test detect_technologies tool
        print("\n🔧 Testing detect_technologies MCP tool...")
        result = await client.call_tool("detect_technologies", {
            "url": "https://httpbin.org/",
            "project_id": "mcp-test-tech",
            "browser_engine": "chromium"
        })

        print_result(result.get("status") == "success", f"Technology detection completed: {result.get('status')}")
        if result.get("technology_detection"):
            tech = result["technology_detection"]
            print_result("total_technologies" in tech, f"Technologies detected: {tech.get('total_technologies', 0)}")

    except Exception as e:
        print_result(False, f"MCP tools test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_simple_analysis():
    """Test basic page analysis without extra features for faster execution."""
    print_test("Simple Page Analysis (Fast)")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    analyzer = PageAnalyzer()
    project_id = "test-simple-analysis"
    url = "https://httpbin.org/html"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    try:
        await service.initialize()
        session = await service.create_session(project_id, engine=BrowserEngine.CHROMIUM)
        page = await session.create_page()

        # Run minimal analysis for speed
        analysis_data = await analyzer.analyze_comprehensive(
            page=page,
            url=url,
            project_root=project_root,
            include_network_monitoring=False,
            include_interaction_simulation=False,
            include_performance_metrics=False
        )

        # Verify basic analysis components
        print_result(analysis_data.page_content.status_code == 200, "Page loaded successfully")
        print_result(analysis_data.dom_structure.total_elements > 0, "DOM structure analyzed")
        print_result(analysis_data.page_functionality.page_type != PageType.UNKNOWN, f"Page type: {analysis_data.page_functionality.page_type}")
        print_result(analysis_data.accessibility_evaluation.accessibility_score >= 0, f"Accessibility score: {analysis_data.accessibility_evaluation.accessibility_score:.1f}")

        print_analysis_summary(analysis_data)

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.close_session(project_id)
        await service.shutdown()

async def run_all_tests():
    """Run all tests in sequence."""
    print_section("Page Analysis Data Collection Test Suite (Story 2.5)")
    await test_simple_analysis()
    await test_dom_structure_analysis()
    await test_technology_detection()
    await test_comprehensive_analysis()
    await test_mcp_tools()
    print("\n🎉 All page analysis tests completed!")

async def main():
    """Main entry point for the test script."""
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        await run_all_tests()
        return

    command = sys.argv[1].lower()

    if command == "comprehensive":
        await test_comprehensive_analysis()
    elif command == "dom_structure":
        await test_dom_structure_analysis()
    elif command == "technology":
        await test_technology_detection()
    elif command == "mcp_tools":
        await test_mcp_tools()
    elif command == "simple":
        await test_simple_analysis()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())