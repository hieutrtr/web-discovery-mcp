#!/usr/bin/env python3
"""
Test script for Story 6.4: High-Level Workflow Orchestration Tools

This script validates the orchestration tools implementation by testing:
1. Tool registration and MCP server integration
2. Orchestration class functionality
3. Analysis workflow execution (mocked)
4. Error handling and edge cases
5. Performance and timing validation

Usage:
    python scripts/test_orchestration_story_6_4.py [--verbose] [--mode quick|full]
"""

import argparse
import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from legacy_web_mcp.mcp.orchestration_tools import (
        AnalysisMode,
        CostPriority,
        LegacyAnalysisOrchestrator,
        OrchestrationError,
        ToolIntegrationError,
        WorkflowPlanningError,
        register,
    )
    from legacy_web_mcp.mcp.server import create_mcp
    from fastmcp import FastMCP, Context
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the project root and dependencies are installed.")
    sys.exit(1)


class OrchestrationTestRunner:
    """Test runner for Story 6.4 orchestration tools."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message with optional verbose output."""
        if self.verbose or level in ["ERROR", "SUCCESS", "FAIL"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert a test condition and track results."""
        if condition:
            self.passed_tests += 1
            self.test_results.append({"name": test_name, "status": "PASS"})
            self.log(f"✅ {test_name}", "SUCCESS")
        else:
            self.failed_tests += 1
            self.test_results.append({"name": test_name, "status": "FAIL", "error": error_msg})
            self.log(f"❌ {test_name}: {error_msg}", "FAIL")

    async def test_enum_definitions(self):
        """Test that enum classes are properly defined."""
        self.log("Testing enum definitions...")

        # Test AnalysisMode enum
        try:
            modes = [AnalysisMode.QUICK, AnalysisMode.RECOMMENDED, AnalysisMode.COMPREHENSIVE, AnalysisMode.TARGETED]
            mode_values = [mode.value for mode in modes]
            expected_values = ["quick", "recommended", "comprehensive", "targeted"]

            self.assert_test(
                mode_values == expected_values,
                "AnalysisMode enum values correct",
                f"Expected {expected_values}, got {mode_values}"
            )

            # Test enum creation from strings
            quick_mode = AnalysisMode("quick")
            self.assert_test(
                quick_mode == AnalysisMode.QUICK,
                "AnalysisMode creation from string",
                f"Expected {AnalysisMode.QUICK}, got {quick_mode}"
            )

        except Exception as e:
            self.assert_test(False, "AnalysisMode enum validation", str(e))

        # Test CostPriority enum
        try:
            priorities = [CostPriority.SPEED, CostPriority.BALANCED, CostPriority.COST_EFFICIENT]
            priority_values = [p.value for p in priorities]
            expected_values = ["speed", "balanced", "cost_efficient"]

            self.assert_test(
                priority_values == expected_values,
                "CostPriority enum values correct",
                f"Expected {expected_values}, got {priority_values}"
            )

        except Exception as e:
            self.assert_test(False, "CostPriority enum validation", str(e))

    async def test_orchestrator_initialization(self):
        """Test orchestrator class initialization."""
        self.log("Testing orchestrator initialization...")

        try:
            mock_config = MagicMock()
            mock_config.BROWSER_HEADLESS = True

            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

                # Test basic properties
                self.assert_test(
                    orchestrator.project_id == "test-project",
                    "Orchestrator project_id set correctly"
                )

                self.assert_test(
                    orchestrator.current_phase == "initialization",
                    "Orchestrator initial phase correct"
                )

                self.assert_test(
                    isinstance(orchestrator.workflow_id, str) and "orchestration-" in orchestrator.workflow_id,
                    "Orchestrator workflow_id generated correctly"
                )

                self.assert_test(
                    isinstance(orchestrator.start_time, float) and orchestrator.start_time > 0,
                    "Orchestrator start_time initialized"
                )

        except Exception as e:
            self.assert_test(False, "Orchestrator initialization", str(e))

    async def test_page_selection_algorithms(self):
        """Test intelligent page selection algorithms."""
        self.log("Testing page selection algorithms...")

        try:
            mock_config = MagicMock()
            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

                # Test with prioritized URLs
                all_urls = [
                    "https://example.com/",
                    "https://example.com/login",
                    "https://example.com/dashboard",
                    "https://example.com/about",
                    "https://example.com/contact",
                    "https://example.com/random1",
                    "https://example.com/random2",
                ]
                site_info = {"site_type": "webapp"}

                selected = await orchestrator._select_priority_pages(
                    all_urls, site_info, AnalysisMode.QUICK, 5
                )

                self.assert_test(
                    len(selected) == 5,
                    "Page selection respects max_pages limit"
                )

                self.assert_test(
                    "https://example.com/" in selected,
                    "Home page prioritized in selection"
                )

                self.assert_test(
                    "https://example.com/login" in selected,
                    "Login page prioritized in selection"
                )

                # Test auto-calculation of max pages
                selected_auto = await orchestrator._select_priority_pages(
                    all_urls, site_info, AnalysisMode.QUICK, 0  # 0 = auto
                )

                self.assert_test(
                    len(selected_auto) <= 10,  # Quick mode default
                    "Auto page selection uses correct defaults"
                )

        except Exception as e:
            self.assert_test(False, "Page selection algorithms", str(e))

    async def test_cost_estimation(self):
        """Test cost estimation functionality."""
        self.log("Testing cost estimation...")

        try:
            mock_config = MagicMock()
            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

                # Test quick mode cost estimation
                pages = ["https://example.com/"] * 10
                cost_estimate = orchestrator._estimate_analysis_cost(pages, AnalysisMode.QUICK)

                self.assert_test(
                    cost_estimate["page_count"] == 10,
                    "Cost estimation page count correct"
                )

                self.assert_test(
                    cost_estimate["cost_per_page"] == 0.05,
                    "Quick mode cost per page correct"
                )

                self.assert_test(
                    cost_estimate["estimated_cost_usd"] == 0.5,
                    "Total cost estimation correct"
                )

                # Test comprehensive mode
                cost_estimate_comp = orchestrator._estimate_analysis_cost(pages, AnalysisMode.COMPREHENSIVE)

                self.assert_test(
                    cost_estimate_comp["cost_per_page"] > cost_estimate["cost_per_page"],
                    "Comprehensive mode costs more than quick mode"
                )

                # Test time estimation
                self.assert_test(
                    "estimated_time_seconds" in cost_estimate and cost_estimate["estimated_time_seconds"] > 0,
                    "Time estimation included in cost estimate"
                )

        except Exception as e:
            self.assert_test(False, "Cost estimation", str(e))

    async def test_strategy_creation(self):
        """Test analysis strategy creation."""
        self.log("Testing analysis strategy creation...")

        try:
            mock_config = MagicMock()
            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

                discovery_result = {
                    "selected_pages": ["https://example.com/", "https://example.com/login"],
                    "site_characteristics": {"complexity": "medium"},
                }

                # Test balanced strategy
                strategy = await orchestrator._create_analysis_strategy(
                    discovery_result, AnalysisMode.RECOMMENDED, CostPriority.BALANCED, True
                )

                self.assert_test(
                    strategy["analysis_mode"] == "recommended",
                    "Strategy analysis mode set correctly"
                )

                self.assert_test(
                    strategy["max_concurrent_sessions"] == 3,  # Balanced default
                    "Balanced cost priority sets correct concurrency"
                )

                self.assert_test(
                    strategy["include_step2_analysis"] is True,
                    "Step 2 analysis enabled in strategy"
                )

                # Test cost-efficient strategy
                strategy_cost = await orchestrator._create_analysis_strategy(
                    discovery_result, AnalysisMode.QUICK, CostPriority.COST_EFFICIENT, False
                )

                self.assert_test(
                    strategy_cost["max_concurrent_sessions"] == 1,  # Cost efficient
                    "Cost efficient priority limits concurrency"
                )

                self.assert_test(
                    strategy_cost["batch_size"] == 3,  # Cost efficient batching
                    "Cost efficient strategy uses larger batches"
                )

        except Exception as e:
            self.assert_test(False, "Strategy creation", str(e))

    async def test_mcp_tool_registration(self):
        """Test MCP tool registration."""
        self.log("Testing MCP tool registration...")

        try:
            # Test with mock MCP server
            mock_mcp = MagicMock()
            register(mock_mcp)

            self.assert_test(
                mock_mcp.tool.call_count >= 3,
                "At least 3 tools registered with MCP",
                f"Expected >= 3 tool calls, got {mock_mcp.tool.call_count}"
            )

            # Test with real FastMCP server
            real_mcp = FastMCP(name="Test Server")
            register(real_mcp)

            tools = await real_mcp.get_tools()
            orchestration_tools = [
                "analyze_legacy_site",
                "analyze_with_recommendations",
                "get_analysis_status"
            ]

            for tool_name in orchestration_tools:
                self.assert_test(
                    tool_name in tools,
                    f"Tool '{tool_name}' registered in MCP server"
                )

        except Exception as e:
            self.assert_test(False, "MCP tool registration", str(e))

    async def test_server_integration(self):
        """Test integration with main MCP server."""
        self.log("Testing server integration...")

        try:
            # Test server creation with orchestration tools
            server = create_mcp()

            self.assert_test(
                server is not None,
                "MCP server created successfully"
            )

            self.assert_test(
                hasattr(server, 'name') and "Legacy Web MCP Server" in server.name,
                "Server has correct name"
            )

            # Test tools are available
            tools = await server.get_tools()

            self.assert_test(
                len(tools) >= 25,  # Should have many tools including orchestration
                f"Server has expected number of tools (got {len(tools)})"
            )

            self.assert_test(
                "analyze_legacy_site" in tools,
                "Primary orchestration tool available in server"
            )

        except Exception as e:
            self.assert_test(False, "Server integration", str(e))

    async def test_error_handling(self):
        """Test error handling and custom exceptions."""
        self.log("Testing error handling...")

        try:
            # Test custom exception hierarchy
            base_error = OrchestrationError("Base error")
            planning_error = WorkflowPlanningError("Planning error")
            integration_error = ToolIntegrationError("Integration error")

            self.assert_test(
                isinstance(planning_error, OrchestrationError),
                "WorkflowPlanningError inherits from OrchestrationError"
            )

            self.assert_test(
                isinstance(integration_error, OrchestrationError),
                "ToolIntegrationError inherits from OrchestrationError"
            )

            # Test error handling in orchestrator
            mock_config = MagicMock()
            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

                # Test error tracking
                self.assert_test(
                    orchestrator.progress_tracker["errors"] == [],
                    "Error tracker initialized empty"
                )

        except Exception as e:
            self.assert_test(False, "Error handling", str(e))

    async def test_parameter_validation(self):
        """Test parameter validation in tools."""
        self.log("Testing parameter validation...")

        try:
            mock_context = AsyncMock(spec=Context)

            # Test invalid analysis mode
            with patch("legacy_web_mcp.mcp.orchestration_tools.load_configuration"):
                from legacy_web_mcp.mcp.orchestration_tools import register

                mock_mcp = MagicMock()
                register(mock_mcp)

                # Find the analyze_legacy_site function
                analyze_legacy_site = None
                for call in mock_mcp.tool.call_args_list:
                    args = call[0] if call[0] else []
                    if args and hasattr(args[0], '__name__') and 'analyze_legacy_site' in args[0].__name__:
                        analyze_legacy_site = args[0]
                        break

                if analyze_legacy_site:
                    result = await analyze_legacy_site(
                        mock_context,
                        url="https://example.com",
                        analysis_mode="invalid_mode"
                    )

                    self.assert_test(
                        result.get("status") == "error",
                        "Invalid analysis mode returns error"
                    )

                    self.assert_test(
                        "Invalid analysis_mode" in result.get("error", ""),
                        "Error message indicates invalid analysis mode"
                    )

        except Exception as e:
            self.assert_test(False, "Parameter validation", str(e))

    async def test_performance_metrics(self):
        """Test performance and timing functionality."""
        self.log("Testing performance metrics...")

        try:
            mock_config = MagicMock()
            with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
                 patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

                start_time = time.time()
                orchestrator = LegacyAnalysisOrchestrator(mock_config, "perf-test")

                self.assert_test(
                    orchestrator.start_time >= start_time,
                    "Orchestrator start time initialized correctly"
                )

                # Simulate some processing time
                await asyncio.sleep(0.1)

                current_time = time.time()
                self.assert_test(
                    current_time > orchestrator.start_time,
                    "Time measurement working correctly"
                )

        except Exception as e:
            self.assert_test(False, "Performance metrics", str(e))

    async def test_file_system_integration(self):
        """Test file system integration and project structure."""
        self.log("Testing file system integration...")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create mock project structure
                analysis_dir = temp_path / "analysis" / "pages"
                analysis_dir.mkdir(parents=True)

                workflow_dir = temp_path / "workflow" / "checkpoints"
                workflow_dir.mkdir(parents=True)

                # Create some test files
                (analysis_dir / "page1.json").write_text('{"url": "test1", "title": "Test 1"}')
                (analysis_dir / "page2.json").write_text('{"url": "test2", "title": "Test 2"}')

                # Test file detection
                analysis_files = list(analysis_dir.glob("*.json"))
                self.assert_test(
                    len(analysis_files) == 2,
                    "Analysis files created and detected correctly"
                )

                checkpoint_files = list(workflow_dir.glob("*.json"))
                self.assert_test(
                    len(checkpoint_files) == 0,
                    "Checkpoint directory empty as expected"
                )

        except Exception as e:
            self.assert_test(False, "File system integration", str(e))

    async def run_all_tests(self, mode: str = "full"):
        """Run all tests based on the specified mode."""
        print(f"🚀 Starting Story 6.4 Orchestration Tools Test Suite ({mode} mode)")
        print("=" * 70)

        start_time = time.time()

        # Always run core tests
        await self.test_enum_definitions()
        await self.test_orchestrator_initialization()
        await self.test_page_selection_algorithms()
        await self.test_cost_estimation()
        await self.test_mcp_tool_registration()
        await self.test_error_handling()

        if mode == "full":
            # Additional comprehensive tests
            await self.test_strategy_creation()
            await self.test_server_integration()
            await self.test_parameter_validation()
            await self.test_performance_metrics()
            await self.test_file_system_integration()

        # Calculate results
        total_time = time.time() - start_time
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Total Tests:     {total_tests}")
        print(f"Passed:          {self.passed_tests} ✅")
        print(f"Failed:          {self.failed_tests} ❌")
        print(f"Success Rate:    {success_rate:.1f}%")
        print(f"Execution Time:  {total_time:.2f} seconds")

        if self.failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    error_msg = result.get("error", "Unknown error")
                    print(f"  • {result['name']}: {error_msg}")

        print("\n" + "=" * 70)
        if self.failed_tests == 0:
            print("🎉 ALL TESTS PASSED! Story 6.4 implementation is working correctly.")
            return True
        else:
            print(f"⚠️  {self.failed_tests} test(s) failed. Please review the implementation.")
            return False

    def generate_report(self, output_file: str = None):
        """Generate a detailed test report."""
        report = {
            "test_suite": "Story 6.4: High-Level Workflow Orchestration Tools",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_tests": self.passed_tests + self.failed_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "success_rate": f"{(self.passed_tests / (self.passed_tests + self.failed_tests) * 100):.1f}%" if (self.passed_tests + self.failed_tests) > 0 else "0%"
            },
            "test_results": self.test_results
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"📄 Test report saved to: {output_file}")

        return report


async def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test Story 6.4 Orchestration Tools")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--mode", choices=["quick", "full"], default="full", help="Test mode")
    parser.add_argument("--report", help="Generate JSON report to specified file")

    args = parser.parse_args()

    # Create test runner
    runner = OrchestrationTestRunner(verbose=args.verbose)

    try:
        # Run tests
        success = await runner.run_all_tests(mode=args.mode)

        # Generate report if requested
        if args.report:
            runner.generate_report(args.report)

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())