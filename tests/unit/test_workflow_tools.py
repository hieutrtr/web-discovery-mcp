"""Tests for workflow MCP tools."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp import Context, FastMCP

from legacy_web_mcp.browser.workflow import QueueStatus, SequentialNavigationWorkflow
from legacy_web_mcp.mcp.workflow_tools import register


class TestWorkflowTools:
    """Test workflow MCP tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with workflow tools."""
        mcp = FastMCP(name="test-server")
        register(mcp)
        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create mock context."""
        return AsyncMock(spec=Context)

    @pytest.fixture
    def mock_browser_service(self):
        """Create mock browser service."""
        service = AsyncMock()
        session = AsyncMock()
        session.page = AsyncMock()
        service.get_session.return_value.__aenter__.return_value = session
        return service

    @pytest.fixture
    def mock_workflow(self):
        """Create mock workflow."""
        workflow = Mock(spec=SequentialNavigationWorkflow)
        workflow.workflow_id = "test-workflow-123"
        workflow.project_id = "test-project"
        workflow.status = QueueStatus.COMPLETED
        workflow.progress = Mock()
        workflow.progress.total_pages = 5
        workflow.progress.completed_pages = 4
        workflow.progress.failed_pages = 1
        workflow.progress.completion_percentage = 100.0
        workflow.progress.workflow_duration = 45.5
        workflow.progress.average_page_processing_time = 9.1
        workflow.progress.pages_per_minute = 6.6
        workflow.page_tasks = []
        workflow._current_sessions = set()
        workflow.max_concurrent_sessions = 3
        return workflow

    @pytest.mark.asyncio
    async def test_analyze_page_list_success(
        self, mcp_server, mock_context, mock_browser_service, mock_workflow
    ):
        """Test successful page list analysis."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        with patch("legacy_web_mcp.mcp.workflow_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.workflow_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.create_project_store") as mock_store_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.SequentialNavigationWorkflow") as mock_workflow_cls:

            # Setup mocks
            mock_config.return_value = Mock()
            mock_browser_cls.return_value = mock_browser_service

            mock_project_store = Mock()
            mock_project_metadata = Mock()
            mock_project_metadata.root_path = Path("/tmp/test-project")
            mock_project_store.get_project_metadata.return_value = None
            mock_project_store.create_project.return_value = mock_project_metadata
            mock_store_cls.return_value = mock_project_store

            # Configure workflow mock
            mock_workflow.get_progress_summary.return_value = {
                "workflow_id": "test-workflow-123",
                "project_id": "test-project",
                "status": "completed",
                "progress": {
                    "total_pages": 3,
                    "completed_pages": 3,
                    "failed_pages": 0,
                    "completion_percentage": 100.0,
                },
                "timing": {
                    "workflow_duration": 30.0,
                    "average_page_processing_time": 10.0,
                    "pages_per_minute": 6.0,
                    "estimated_completion_time": None,
                },
            }

            # Mock successful page tasks
            mock_task_1 = Mock()
            mock_task_1.url = urls[0]
            mock_task_1.page_id = "page1-abc123"
            mock_task_1.status.value = "completed"
            mock_task_1.processing_duration = 9.5
            mock_task_1.attempts = 1
            mock_task_1.error_message = None
            mock_task_1.analysis_result = Mock()

            mock_task_2 = Mock()
            mock_task_2.url = urls[1]
            mock_task_2.page_id = "page2-def456"
            mock_task_2.status.value = "completed"
            mock_task_2.processing_duration = 10.2
            mock_task_2.attempts = 1
            mock_task_2.error_message = None
            mock_task_2.analysis_result = Mock()

            mock_task_3 = Mock()
            mock_task_3.url = urls[2]
            mock_task_3.page_id = "page3-ghi789"
            mock_task_3.status.value = "completed"
            mock_task_3.processing_duration = 10.3
            mock_task_3.attempts = 1
            mock_task_3.error_message = None
            mock_task_3.analysis_result = Mock()

            mock_workflow.page_tasks = [mock_task_1, mock_task_2, mock_task_3]
            mock_workflow_cls.return_value = mock_workflow

            # Get tool and call it
            tools = await mcp_server.get_tools()
            analyze_tool = tools["analyze_page_list"]

            result = await analyze_tool(
                context=mock_context,
                urls=urls,
                project_id="test-project",
                max_retries_per_page=3,
                include_network_monitoring=True,
                include_interaction_simulation=True,
            )

            # Verify result structure
            assert result["status"] == "success"
            assert result["workflow_id"] == "test-workflow-123"
            assert result["project_id"] == "test-project"

            # Verify progress summary
            progress = result["progress_summary"]
            assert progress["total_pages"] == 3
            assert progress["completed_pages"] == 3
            assert progress["failed_pages"] == 0
            assert progress["completion_percentage"] == 100.0

            # Verify timing metrics
            timing = result["timing_metrics"]
            assert "total_duration" in timing
            assert "average_page_processing_time" in timing
            assert "pages_per_minute" in timing

            # Verify page results
            page_results = result["page_results"]
            assert len(page_results) == 3
            for page_result in page_results:
                assert page_result["status"] == "completed"
                assert page_result["analysis_available"] is True

            # Verify error summary for successful case
            error_summary = result["error_summary"]
            assert error_summary["total_failed"] == 0

            # Verify checkpoint info
            checkpoint_info = result["checkpoint_info"]
            assert checkpoint_info["checkpointing_enabled"] is True

    @pytest.mark.asyncio
    async def test_analyze_page_list_with_failures(
        self, mcp_server, mock_context, mock_browser_service
    ):
        """Test page list analysis with some failures."""
        urls = ["https://example.com/page1", "https://example.com/page2"]

        with patch("legacy_web_mcp.mcp.workflow_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.workflow_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.create_project_store") as mock_store_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.SequentialNavigationWorkflow") as mock_workflow_cls:

            # Setup mocks
            mock_config.return_value = Mock()
            mock_browser_cls.return_value = mock_browser_service

            mock_project_store = Mock()
            mock_project_metadata = Mock()
            mock_project_metadata.root_path = Path("/tmp/test-project")
            mock_project_store.get_project_metadata.return_value = mock_project_metadata
            mock_store_cls.return_value = mock_project_store

            # Create workflow with mixed results
            mock_workflow = Mock()
            mock_workflow.workflow_id = "test-workflow-456"
            mock_workflow.project_id = "test-project"
            mock_workflow.status = QueueStatus.COMPLETED
            mock_workflow.progress = Mock()
            mock_workflow.progress.workflow_duration = 25.0
            mock_workflow.progress.average_page_processing_time = 12.5
            mock_workflow.progress.pages_per_minute = 4.8

            # Mock one successful, one failed task
            mock_success_task = Mock()
            mock_success_task.url = urls[0]
            mock_success_task.page_id = "page1-success"
            mock_success_task.status.value = "completed"
            mock_success_task.processing_duration = 10.0
            mock_success_task.attempts = 1
            mock_success_task.error_message = None
            mock_success_task.analysis_result = Mock()

            mock_failed_task = Mock()
            mock_failed_task.url = urls[1]
            mock_failed_task.page_id = "page2-failed"
            mock_failed_task.status.value = "failed"
            mock_failed_task.processing_duration = 15.0
            mock_failed_task.attempts = 3
            mock_failed_task.error_message = "Network timeout error"
            mock_failed_task.analysis_result = None

            mock_workflow.page_tasks = [mock_success_task, mock_failed_task]

            mock_workflow.get_progress_summary.return_value = {
                "workflow_id": "test-workflow-456",
                "project_id": "test-project",
                "status": "completed",
                "progress": {
                    "total_pages": 2,
                    "completed_pages": 1,
                    "failed_pages": 1,
                    "completion_percentage": 100.0,
                },
                "timing": {
                    "workflow_duration": 25.0,
                    "average_page_processing_time": 12.5,
                    "pages_per_minute": 4.8,
                },
            }

            mock_workflow_cls.return_value = mock_workflow

            # Get tool and call it
            tools = await mcp_server.get_tools()
            analyze_tool = tools["analyze_page_list"]

            result = await analyze_tool(
                context=mock_context,
                urls=urls,
                project_id="test-project",
            )

            # Should be partial success
            assert result["status"] == "partial"
            assert result["progress_summary"]["completed_pages"] == 1
            assert result["progress_summary"]["failed_pages"] == 1

            # Verify error summary
            error_summary = result["error_summary"]
            assert error_summary["total_failed"] == 1

            # Verify page results show mixed status
            page_results = result["page_results"]
            assert page_results[0]["status"] == "completed"
            assert page_results[0]["analysis_available"] is True
            assert page_results[1]["status"] == "failed"
            assert page_results[1]["analysis_available"] is False
            assert page_results[1]["error_message"] == "Network timeout error"

    @pytest.mark.asyncio
    async def test_analyze_page_list_validation_errors(self, mcp_server, mock_context):
        """Test validation errors in analyze_page_list."""
        tools = await mcp_server.get_tools()
        analyze_tool = tools["analyze_page_list"]

        # Test empty URL list
        result = await analyze_tool(
            context=mock_context,
            urls=[],
            project_id="test-project",
        )

        assert result["status"] == "error"
        assert "No URLs provided" in result["error"]
        assert result["error_type"] == "ValidationError"

    @pytest.mark.asyncio
    async def test_control_workflow_pause(self, mcp_server, mock_context):
        """Test workflow pause control."""
        # Mock active workflow
        mock_workflow = Mock()
        mock_workflow.project_id = "test-project"
        mock_workflow.status = QueueStatus.RUNNING
        mock_workflow.pause = Mock()
        mock_workflow.get_progress_summary.return_value = {
            "progress": {"total_pages": 5, "completed_pages": 2},
            "timing": {"workflow_duration": 20.0},
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="pause",
                project_id="test-project",
            )

            assert result["status"] == "success"
            assert result["action_performed"] == "pause"
            assert "pause requested" in result["control_result"]["message"]
            mock_workflow.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_workflow_resume(self, mcp_server, mock_context):
        """Test workflow resume control."""
        mock_workflow = AsyncMock()
        mock_workflow.project_id = "test-project"
        mock_workflow.status = QueueStatus.PAUSED
        mock_workflow.resume = Mock()
        mock_workflow.start_workflow = AsyncMock()
        mock_workflow.get_progress_summary.return_value = {
            "progress": {"total_pages": 5, "completed_pages": 2},
            "timing": {"workflow_duration": 20.0},
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="resume",
                project_id="test-project",
            )

            assert result["status"] == "success"
            assert result["action_performed"] == "resume"
            assert "resumed successfully" in result["control_result"]["message"]
            mock_workflow.resume.assert_called_once()
            mock_workflow.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_workflow_stop(self, mcp_server, mock_context):
        """Test workflow stop control."""
        mock_workflow = Mock()
        mock_workflow.project_id = "test-project"
        mock_workflow.status = QueueStatus.RUNNING
        mock_workflow.stop = Mock()
        mock_workflow.get_progress_summary.return_value = {
            "progress": {"total_pages": 5, "completed_pages": 2},
            "timing": {"workflow_duration": 20.0},
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="stop",
            )

            assert result["status"] == "success"
            assert result["action_performed"] == "stop"
            assert "stop requested" in result["control_result"]["message"]
            mock_workflow.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_workflow_skip(self, mcp_server, mock_context):
        """Test workflow skip current page control."""
        mock_workflow = Mock()
        mock_workflow.project_id = "test-project"
        mock_workflow.status = QueueStatus.RUNNING
        mock_workflow.progress = Mock()
        mock_workflow.progress.current_page_url = "https://example.com/current"
        mock_workflow.skip_current_page = Mock()
        mock_workflow.get_progress_summary.return_value = {
            "progress": {"total_pages": 5, "completed_pages": 2},
            "timing": {"workflow_duration": 20.0},
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="skip",
            )

            assert result["status"] == "success"
            assert result["action_performed"] == "skip"
            assert "Skipped current page" in result["control_result"]["message"]
            assert result["control_result"]["skipped_url"] == "https://example.com/current"
            mock_workflow.skip_current_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_control_workflow_status(self, mcp_server, mock_context):
        """Test workflow status query."""
        mock_workflow = Mock()
        mock_workflow.project_id = "test-project"
        mock_workflow.status = QueueStatus.RUNNING
        mock_workflow.get_progress_summary.return_value = {
            "progress": {"total_pages": 5, "completed_pages": 3},
            "timing": {"workflow_duration": 30.0},
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="status",
            )

            assert result["status"] == "success"
            assert result["action_performed"] == "status"
            assert result["workflow_status"] == "running"
            assert result["progress_summary"]["completed_pages"] == 3

    @pytest.mark.asyncio
    async def test_control_workflow_not_found(self, mcp_server, mock_context):
        """Test control workflow with non-existent workflow ID."""
        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="nonexistent-workflow",
                action="pause",
            )

            assert result["status"] == "error"
            assert "not found in active workflows" in result["error"]
            assert result["error_type"] == "WorkflowNotFoundError"

    @pytest.mark.asyncio
    async def test_control_workflow_project_mismatch(self, mcp_server, mock_context):
        """Test control workflow with project ID mismatch."""
        mock_workflow = Mock()
        mock_workflow.project_id = "correct-project"

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="pause",
                project_id="wrong-project",
            )

            assert result["status"] == "error"
            assert "Project ID mismatch" in result["error"]
            assert result["error_type"] == "ProjectMismatchError"

    @pytest.mark.asyncio
    async def test_control_workflow_invalid_action(self, mcp_server, mock_context):
        """Test control workflow with invalid action."""
        mock_workflow = Mock()
        mock_workflow.project_id = "test-project"

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {"workflow-123": mock_workflow}):
            tools = await mcp_server.get_tools()
            control_tool = tools["control_workflow"]

            result = await control_tool(
                context=mock_context,
                workflow_id="workflow-123",
                action="invalid_action",
            )

            assert result["status"] == "error"
            assert "Unknown action" in result["error"]
            assert result["error_type"] == "InvalidActionError"

    @pytest.mark.asyncio
    async def test_resume_workflow_from_checkpoint(self, mcp_server, mock_context, tmp_path):
        """Test resuming workflow from checkpoint."""
        # Create mock checkpoint file
        checkpoint_data = {
            "project_id": "test-project",
            "workflow_id": "checkpoint-workflow",
            "created_at": "2025-01-01T12:00:00+00:00",
            "page_tasks": [
                {
                    "url": "https://example.com/page1",
                    "page_id": "page1",
                    "status": "completed",
                    "attempts": 1,
                    "max_attempts": 3,
                    "error_message": None,
                    "processing_start_time": None,
                    "processing_end_time": None,
                    "analysis_result": None,
                },
                {
                    "url": "https://example.com/page2",
                    "page_id": "page2",
                    "status": "pending",
                    "attempts": 0,
                    "max_attempts": 3,
                    "error_message": None,
                    "processing_start_time": None,
                    "processing_end_time": None,
                    "analysis_result": None,
                },
            ],
            "progress": {
                "total_pages": 2,
                "completed_pages": 1,
                "failed_pages": 0,
                "skipped_pages": 0,
                "current_page_index": 1,
                "current_page_url": "https://example.com/page2",
                "workflow_start_time": "2025-01-01T12:00:00+00:00",
                "workflow_end_time": None,
                "estimated_completion_time": None,
                "average_page_processing_time": 10.0,
                "pages_per_minute": 6.0,
            },
            "configuration": {
                "include_network_analysis": True,
                "include_interaction_analysis": True,
            },
        }

        checkpoint_dir = tmp_path / "workflow" / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        checkpoint_file = checkpoint_dir / "checkpoint-workflow.json"

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)

        with patch("legacy_web_mcp.mcp.workflow_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.workflow_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.create_project_store") as mock_store_cls, \
             patch("legacy_web_mcp.mcp.workflow_tools.SequentialNavigationWorkflow.load_from_checkpoint") as mock_load:

            # Setup mocks
            mock_config.return_value = Mock()
            mock_browser_cls.return_value = Mock()

            mock_project_store = Mock()
            mock_project_metadata = Mock()
            mock_project_metadata.root_path = tmp_path
            mock_project_store.get_project_metadata.return_value = mock_project_metadata
            mock_store_cls.return_value = mock_project_store

            # Mock loaded workflow
            mock_workflow = Mock()
            mock_workflow.workflow_id = "checkpoint-workflow"
            mock_workflow.project_id = "test-project"
            mock_workflow.status = QueueStatus.PAUSED
            mock_workflow.progress = Mock()
            mock_workflow.progress.current_page_index = 1
            mock_workflow.progress.current_page_url = "https://example.com/page2"
            mock_workflow.page_tasks = [Mock(), Mock()]  # Two tasks
            mock_workflow.page_tasks[1].status.value = "pending"
            mock_workflow.page_tasks[1].can_retry = False

            mock_workflow.get_progress_summary.return_value = {
                "progress": {"total_pages": 2, "completed_pages": 1},
                "timing": {"workflow_duration": 15.0},
            }

            mock_load.return_value = mock_workflow

            tools = await mcp_server.get_tools()
            resume_tool = tools["resume_workflow_from_checkpoint"]

            result = await resume_tool(
                context=mock_context,
                project_id="test-project",
                continue_from_last=True,
            )

            assert result["status"] == "success"
            assert result["workflow_id"] == "checkpoint-workflow"
            assert result["project_id"] == "test-project"

            # Verify resume info
            resume_info = result["resume_info"]
            assert resume_info["workflow_status"] == "paused"
            assert resume_info["resume_from_page_index"] == 1

            # Verify remaining pages info
            remaining = result["remaining_pages"]
            assert remaining["total_remaining"] == 1
            assert remaining["failed_recoverable"] == 0

    @pytest.mark.asyncio
    async def test_resume_workflow_project_not_found(self, mcp_server, mock_context):
        """Test resume workflow with non-existent project."""
        with patch("legacy_web_mcp.mcp.workflow_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.workflow_tools.create_project_store") as mock_store_cls:

            mock_config.return_value = Mock()
            mock_project_store = Mock()
            mock_project_store.get_project_metadata.return_value = None
            mock_store_cls.return_value = mock_project_store

            tools = await mcp_server.get_tools()
            resume_tool = tools["resume_workflow_from_checkpoint"]

            result = await resume_tool(
                context=mock_context,
                project_id="nonexistent-project",
            )

            assert result["status"] == "error"
            assert "not found" in result["error"]
            assert result["error_type"] == "ProjectNotFoundError"

    @pytest.mark.asyncio
    async def test_list_active_workflows(self, mcp_server, mock_context):
        """Test listing active workflows."""
        # Create mock active workflows
        mock_workflow1 = Mock()
        mock_workflow1.project_id = "project1"
        mock_workflow1.status = QueueStatus.RUNNING
        mock_workflow1.progress = Mock()
        mock_workflow1.progress.total_pages = 10
        mock_workflow1.progress.completed_pages = 6
        mock_workflow1.progress.completion_percentage = 60.0
        mock_workflow1.progress.current_page_url = "https://example.com/page6"
        mock_workflow1.progress.workflow_duration = 45.0
        mock_workflow1.progress.pages_per_minute = 8.0
        mock_workflow1.max_concurrent_sessions = 3
        mock_workflow1._current_sessions = {"session1", "session2"}

        mock_workflow1.get_progress_summary.return_value = {
            "progress": {
                "total_pages": 10,
                "completed_pages": 6,
                "completion_percentage": 60.0,
                "current_page_url": "https://example.com/page6",
            },
            "timing": {
                "workflow_duration": 45.0,
                "pages_per_minute": 8.0,
                "estimated_completion": "2025-01-01T13:00:00+00:00",
            },
        }

        mock_workflow2 = Mock()
        mock_workflow2.project_id = "project2"
        mock_workflow2.status = QueueStatus.PAUSED
        mock_workflow2.progress = Mock()
        mock_workflow2.progress.total_pages = 5
        mock_workflow2.progress.completed_pages = 3
        mock_workflow2.progress.completion_percentage = 60.0
        mock_workflow2.progress.current_page_url = "https://test.com/page3"
        mock_workflow2.progress.workflow_duration = 20.0
        mock_workflow2.progress.pages_per_minute = 9.0
        mock_workflow2.max_concurrent_sessions = 2
        mock_workflow2._current_sessions = set()

        mock_workflow2.get_progress_summary.return_value = {
            "progress": {
                "total_pages": 5,
                "completed_pages": 3,
                "completion_percentage": 60.0,
                "current_page_url": "https://test.com/page3",
            },
            "timing": {
                "workflow_duration": 20.0,
                "pages_per_minute": 9.0,
                "estimated_completion": None,
            },
        }

        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {
            "workflow1": mock_workflow1,
            "workflow2": mock_workflow2,
        }):
            tools = await mcp_server.get_tools()
            list_tool = tools["list_active_workflows"]

            result = await list_tool(context=mock_context)

            assert result["status"] == "success"
            assert result["total_active"] == 2

            # Verify workflow summaries
            workflows = result["active_workflows"]
            assert len(workflows) == 2

            # Find specific workflows
            running_workflow = next(w for w in workflows if w["status"] == "running")
            paused_workflow = next(w for w in workflows if w["status"] == "paused")

            assert running_workflow["project_id"] == "project1"
            assert running_workflow["progress"]["total_pages"] == 10
            assert running_workflow["progress"]["completed_pages"] == 6

            assert paused_workflow["project_id"] == "project2"
            assert paused_workflow["progress"]["total_pages"] == 5

            # Verify system resources
            system_resources = result["system_resources"]
            assert system_resources["total_pages_across_workflows"] == 15
            assert system_resources["total_completed_across_workflows"] == 9
            assert system_resources["total_active_browser_sessions"] == 2
            assert system_resources["workflows_running"] == 1
            assert system_resources["workflows_paused"] == 1

    @pytest.mark.asyncio
    async def test_list_active_workflows_empty(self, mcp_server, mock_context):
        """Test listing active workflows when none exist."""
        with patch("legacy_web_mcp.mcp.workflow_tools._active_workflows", {}):
            tools = await mcp_server.get_tools()
            list_tool = tools["list_active_workflows"]

            result = await list_tool(context=mock_context)

            assert result["status"] == "success"
            assert result["total_active"] == 0
            assert result["active_workflows"] == []
            assert "No active workflows found" in result["message"]

    def test_mcp_tools_registration(self, mcp_server):
        """Test that all workflow tools are properly registered."""
        import asyncio
        tools = asyncio.run(mcp_server.get_tools())

        expected_tools = [
            "analyze_page_list",
            "control_workflow",
            "resume_workflow_from_checkpoint",
            "list_active_workflows",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"

        # Verify tools are callable
        for tool_name, tool_func in tools.items():
            if tool_name in expected_tools:
                assert callable(tool_func), f"Tool {tool_name} is not callable"


class TestWorkflowUtilityFunctions:
    """Test utility functions used by workflow tools."""

    def test_analyze_error_patterns_empty(self):
        """Test error pattern analysis with no failures."""
        from legacy_web_mcp.mcp.workflow_tools import _analyze_error_patterns

        result = _analyze_error_patterns([])

        assert result["total_failed"] == 0
        assert result["error_categories"] == {}
        assert result["most_common_errors"] == []
        assert result["retry_analysis"] == {}

    def test_analyze_error_patterns_with_failures(self):
        """Test error pattern analysis with various failure types."""
        from legacy_web_mcp.mcp.workflow_tools import _analyze_error_patterns

        # Mock failed tasks
        failed_tasks = []

        # Timeout errors
        task1 = Mock()
        task1.error_message = "Request timeout after 30 seconds"
        task1.attempts = 3
        failed_tasks.append(task1)

        task2 = Mock()
        task2.error_message = "Connection timeout"
        task2.attempts = 2
        failed_tasks.append(task2)

        # Network errors
        task3 = Mock()
        task3.error_message = "Network connection failed"
        task3.attempts = 1
        failed_tasks.append(task3)

        # 404 errors
        task4 = Mock()
        task4.error_message = "404 Page not found"
        task4.attempts = 1
        failed_tasks.append(task4)

        # Other errors
        task5 = Mock()
        task5.error_message = "JavaScript execution error"
        task5.attempts = 2
        failed_tasks.append(task5)

        result = _analyze_error_patterns(failed_tasks)

        assert result["total_failed"] == 5

        # Check error categorization
        categories = result["error_categories"]
        assert categories["timeout"] == 2
        assert categories["network"] == 1
        assert categories["not_found"] == 1
        assert categories["other"] == 1

        # Check retry analysis
        retry_analysis = result["retry_analysis"]
        assert retry_analysis["1_attempts"] == 2  # task3, task4
        assert retry_analysis["2_attempts"] == 2  # task2, task5
        assert retry_analysis["3_attempts"] == 1  # task1

        # Check most common errors
        most_common = result["most_common_errors"]
        assert len(most_common) == 5  # All unique errors
        assert all("error" in error and "count" in error for error in most_common)

    def test_analyze_error_patterns_duplicate_errors(self):
        """Test error pattern analysis with duplicate error messages."""
        from legacy_web_mcp.mcp.workflow_tools import _analyze_error_patterns

        # Create tasks with duplicate error messages
        failed_tasks = []
        for i in range(3):
            task = Mock()
            task.error_message = "Connection timeout"
            task.attempts = 1
            failed_tasks.append(task)

        for i in range(2):
            task = Mock()
            task.error_message = "404 Not Found"
            task.attempts = 2
            failed_tasks.append(task)

        result = _analyze_error_patterns(failed_tasks)

        assert result["total_failed"] == 5

        # Check most common errors are sorted by frequency
        most_common = result["most_common_errors"]
        assert most_common[0]["error"] == "Connection timeout"
        assert most_common[0]["count"] == 3
        assert most_common[1]["error"] == "404 Not Found"
        assert most_common[1]["count"] == 2