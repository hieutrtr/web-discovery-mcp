#!/usr/bin/env python3
"""Test script for sequential navigation workflow from Story 2.6.

This script tests the Sequential Navigation Workflow implementation,
including queue management, progress tracking, error recovery, checkpoint creation,
and resource management for processing multiple pages systematically.

Usage:
    python scripts/test_sequential_workflow.py [command]

Commands:
    all                - Run all workflow tests
    basic_workflow     - Test basic multi-page workflow execution
    queue_control      - Test pause, resume, stop, skip functionality
    error_recovery     - Test error handling and retry mechanisms
    checkpointing      - Test checkpoint creation and resumption
    mcp_tools          - Test MCP tools for workflow management
    performance        - Test workflow performance and resource management

The script references the core workflow implementation in:
- src/legacy_web_mcp/browser/workflow.py
- src/legacy_web_mcp/mcp/workflow_tools.py

And follows the testing patterns established in existing scripts like test_page_navigation.py
"""

import asyncio
import shutil
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legacy_web_mcp.browser import BrowserAutomationService
from legacy_web_mcp.browser.workflow import QueueStatus, SequentialNavigationWorkflow
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

def print_workflow_progress(progress) -> None:
    """Print workflow progress information."""
    print("\n📊 Workflow Progress:")
    print(f"  Status: {progress.queue_status}")
    print(f"  Pages Completed: {progress.pages_completed}/{progress.total_pages}")
    print(f"  Success Rate: {progress.success_rate:.1%}")
    if progress.estimated_time_remaining:
        print(f"  ETA: {progress.estimated_time_remaining:.1f}s")
    if progress.pages_per_minute > 0:
        print(f"  Processing Rate: {progress.pages_per_minute:.1f} pages/min")

async def test_basic_workflow():
    """Test basic multi-page workflow execution."""
    print_test("Basic Multi-Page Workflow Execution")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-basic-workflow"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    # Test URLs - using httpbin for reliable testing
    test_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml",
    ]

    try:
        await service.initialize()

        # Create workflow
        workflow = SequentialNavigationWorkflow(
            urls=test_urls,
            project_id=project_id,
            project_root=project_root,
            browser_service=service,
            max_retries_per_page=2,
            enable_checkpointing=True,
            checkpoint_interval=2
        )

        print(f"Created workflow with {len(test_urls)} pages")

        # Execute workflow
        result = await workflow.execute()

        print_result(result.final_status == QueueStatus.COMPLETED, f"Workflow completed: {result.final_status}")
        print_result(result.total_pages == len(test_urls), f"All pages processed: {result.total_pages}")
        print_result(result.successful_pages >= 0, f"Successful pages: {result.successful_pages}")
        print_result(result.failed_pages >= 0, f"Failed pages: {result.failed_pages}")
        print_result(result.execution_time > 0, f"Execution time: {result.execution_time:.2f}s")

        print_workflow_progress(result.final_progress)

        # Check that analysis files were created
        analysis_files = list(project_root.glob("**/page-analysis-*.json"))
        print_result(len(analysis_files) > 0, f"Analysis files created: {len(analysis_files)}")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.shutdown()

async def test_queue_control():
    """Test pause, resume, stop, skip functionality."""
    print_test("Queue Control Operations (Pause/Resume/Stop/Skip)")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-queue-control"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    # Test URLs with some delay to allow control operations
    test_urls = [
        "https://httpbin.org/delay/1",  # 1 second delay
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]

    try:
        await service.initialize()

        # Create workflow
        workflow = SequentialNavigationWorkflow(
            urls=test_urls,
            project_id=project_id,
            project_root=project_root,
            browser_service=service,
            max_retries_per_page=1,
            enable_checkpointing=True
        )

        # Start workflow in background
        workflow_task = asyncio.create_task(workflow.execute())

        # Allow workflow to start
        await asyncio.sleep(0.5)

        # Test pause
        await workflow.pause()
        progress = await workflow.get_progress()
        print_result(progress.queue_status == QueueStatus.PAUSED, f"Workflow paused: {progress.queue_status}")

        # Test resume
        await workflow.resume()
        await asyncio.sleep(0.5)
        progress = await workflow.get_progress()
        print_result(progress.queue_status == QueueStatus.RUNNING, f"Workflow resumed: {progress.queue_status}")

        # Test skip current page
        current_page_before = progress.current_page_index
        await workflow.skip_current_page()
        await asyncio.sleep(0.5)
        progress = await workflow.get_progress()
        print_result(progress.current_page_index > current_page_before, "Page skipped successfully")

        # Let workflow complete
        result = await workflow_task

        print_result(result.final_status in [QueueStatus.COMPLETED, QueueStatus.CANCELLED], f"Workflow finished: {result.final_status}")
        print_workflow_progress(result.final_progress)

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.shutdown()

async def test_error_recovery():
    """Test error handling and retry mechanisms."""
    print_test("Error Handling and Retry Mechanisms")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-error-recovery"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    # Test URLs including error cases
    test_urls = [
        "https://httpbin.org/html",          # Success
        "https://httpbin.org/status/404",    # 404 Error
        "https://httpbin.org/json",          # Success
        "https://httpbin.org/status/500",    # 500 Error
        "https://httpbin.org/xml",           # Success
    ]

    try:
        await service.initialize()

        # Create workflow with retry configuration
        workflow = SequentialNavigationWorkflow(
            urls=test_urls,
            project_id=project_id,
            project_root=project_root,
            browser_service=service,
            max_retries_per_page=2,  # Allow retries
            enable_checkpointing=True
        )

        # Execute workflow
        result = await workflow.execute()

        print_result(result.final_status == QueueStatus.COMPLETED, f"Workflow completed despite errors: {result.final_status}")
        print_result(result.failed_pages > 0, f"Error pages properly handled: {result.failed_pages} failed")
        print_result(result.successful_pages > 0, f"Success pages processed: {result.successful_pages} succeeded")

        # Check error details
        error_summary = result.error_summary
        print_result(len(error_summary.get("error_patterns", [])) > 0, "Error patterns analyzed")
        print_result(error_summary.get("total_retries", 0) > 0, f"Retries attempted: {error_summary.get('total_retries', 0)}")

        print_workflow_progress(result.final_progress)

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.shutdown()

async def test_checkpointing():
    """Test checkpoint creation and resumption."""
    print_test("Checkpoint Creation and Resumption")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-checkpointing"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    test_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml",
        "https://httpbin.org/user-agent",
    ]

    try:
        await service.initialize()

        # Create workflow with checkpointing
        workflow = SequentialNavigationWorkflow(
            urls=test_urls,
            project_id=project_id,
            project_root=project_root,
            browser_service=service,
            max_retries_per_page=1,
            enable_checkpointing=True,
            checkpoint_interval=2  # Checkpoint every 2 pages
        )

        # Start workflow and let it process some pages
        workflow_task = asyncio.create_task(workflow.execute())
        await asyncio.sleep(3)  # Let it process a few pages

        # Stop the workflow to simulate interruption
        await workflow.stop()
        result = await workflow_task

        print_result(result.final_status == QueueStatus.CANCELLED, f"Workflow stopped: {result.final_status}")

        # Check that checkpoint was created
        checkpoint_files = list(project_root.glob("**/workflow-checkpoint-*.json"))
        print_result(len(checkpoint_files) > 0, f"Checkpoint created: {len(checkpoint_files)} files")

        if checkpoint_files:
            # Test resumption from checkpoint
            print("\n🔄 Testing resumption from checkpoint...")

            # Load checkpoint and create new workflow
            checkpoint_path = checkpoint_files[0]
            new_workflow = SequentialNavigationWorkflow.from_checkpoint(
                checkpoint_path=checkpoint_path,
                browser_service=service
            )

            # Resume execution
            resume_result = await new_workflow.execute()
            print_result(resume_result.final_status == QueueStatus.COMPLETED, f"Resumed workflow completed: {resume_result.final_status}")
            print_result(resume_result.total_pages == len(test_urls), "All pages eventually processed")

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.shutdown()

async def test_mcp_tools():
    """Test MCP tools for workflow management."""
    print_test("MCP Tools for Workflow Management")

    # Import the MCP client for testing
    from scripts.test_mcp_client import SimpleMCPClient

    client = SimpleMCPClient()

    test_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
    ]

    try:
        # Test analyze_page_list tool
        print("🔧 Testing analyze_page_list MCP tool...")
        result = await client.call_tool("analyze_page_list", {
            "urls": test_urls,
            "project_id": "mcp-test-workflow",
            "max_retries_per_page": 2,
            "include_network_monitoring": False,  # Disable for faster testing
            "include_interaction_simulation": False,
            "enable_checkpointing": True,
            "checkpoint_interval": 1,
            "max_concurrent_sessions": 2
        })

        print_result(result.get("status") == "success", f"Page list analysis completed: {result.get('status')}")

        if result.get("progress_summary"):
            progress = result["progress_summary"]
            print_result(progress.get("pages_completed", 0) > 0, f"Pages processed: {progress.get('pages_completed', 0)}")
            print_result(progress.get("queue_status") == "completed", f"Queue status: {progress.get('queue_status')}")

        workflow_id = result.get("workflow_id")
        if workflow_id:
            print(f"  Workflow ID: {workflow_id}")

            # Test list_active_workflows
            print("\n🔧 Testing list_active_workflows MCP tool...")
            workflows_result = await client.call_tool("list_active_workflows", {})
            print_result(workflows_result.get("status") == "success", "Active workflows listed")

            active_count = workflows_result.get("active_workflows_count", 0)
            print_result(active_count >= 0, f"Active workflows: {active_count}")

    except Exception as e:
        print_result(False, f"MCP tools test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_performance():
    """Test workflow performance and resource management."""
    print_test("Workflow Performance and Resource Management")
    settings = MCPSettings()
    service = BrowserAutomationService(settings)
    project_id = "test-performance"
    project_root = Path(settings.OUTPUT_ROOT) / project_id

    # Clean up previous test runs
    if project_root.exists():
        shutil.rmtree(project_root)

    # Larger set of URLs for performance testing
    test_urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json",
        "https://httpbin.org/xml",
        "https://httpbin.org/user-agent",
        "https://httpbin.org/headers",
    ]

    try:
        await service.initialize()

        # Create workflow with performance tracking
        workflow = SequentialNavigationWorkflow(
            urls=test_urls,
            project_id=project_id,
            project_root=project_root,
            browser_service=service,
            max_retries_per_page=1,
            enable_checkpointing=True,
            max_concurrent_sessions=2  # Test concurrent session management
        )

        start_time = time.time()
        result = await workflow.execute()
        total_time = time.time() - start_time

        print_result(result.final_status == QueueStatus.COMPLETED, f"Performance test completed: {result.final_status}")
        print_result(result.execution_time > 0, f"Workflow execution time: {result.execution_time:.2f}s")
        print_result(total_time > 0, f"Total test time: {total_time:.2f}s")

        # Performance metrics
        if result.successful_pages > 0:
            avg_time_per_page = result.execution_time / result.successful_pages
            print_result(avg_time_per_page > 0, f"Average time per page: {avg_time_per_page:.2f}s")

        # Check resource usage from progress
        final_progress = result.final_progress
        print_result(final_progress.pages_per_minute > 0, f"Processing rate: {final_progress.pages_per_minute:.1f} pages/min")

        print_workflow_progress(result.final_progress)

    except Exception as e:
        print_result(False, f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await service.shutdown()

async def run_all_tests():
    """Run all tests in sequence."""
    print_section("Sequential Navigation Workflow Test Suite (Story 2.6)")
    await test_basic_workflow()
    await test_queue_control()
    await test_error_recovery()
    await test_checkpointing()
    await test_performance()
    await test_mcp_tools()
    print("\n🎉 All sequential workflow tests completed!")

async def main():
    """Main entry point for the test script."""
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        await run_all_tests()
        return

    command = sys.argv[1].lower()

    if command == "basic_workflow":
        await test_basic_workflow()
    elif command == "queue_control":
        await test_queue_control()
    elif command == "error_recovery":
        await test_error_recovery()
    elif command == "checkpointing":
        await test_checkpointing()
    elif command == "mcp_tools":
        await test_mcp_tools()
    elif command == "performance":
        await test_performance()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())