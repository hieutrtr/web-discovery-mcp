"""Tests for the sequential navigation workflow system."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.browser.workflow import (
    PageProcessingStatus,
    PageTask,
    QueueStatus,
    SequentialNavigationWorkflow,
    WorkflowCheckpoint,
    WorkflowProgress,
)


class TestWorkflowModels:
    """Test workflow data models."""

    def test_page_task_creation(self):
        """Test PageTask creation and properties."""
        task = PageTask(
            url="https://example.com/test",
            page_id="test-page-123",
            max_attempts=3,
        )

        assert task.url == "https://example.com/test"
        assert task.page_id == "test-page-123"
        assert task.status == PageProcessingStatus.PENDING
        assert task.attempts == 0
        assert task.max_attempts == 3
        assert task.can_retry is False  # No failures yet
        assert task.processing_duration is None

    def test_page_task_timing(self):
        """Test PageTask timing calculations."""
        task = PageTask(url="https://example.com", page_id="test")

        start_time = datetime.now(UTC)
        task.processing_start_time = start_time
        task.processing_end_time = start_time.replace(second=start_time.second + 5)

        assert task.processing_duration == 5.0

    def test_page_task_retry_logic(self):
        """Test PageTask retry logic."""
        task = PageTask(url="https://example.com", page_id="test", max_attempts=3)

        # First failure
        task.status = PageProcessingStatus.FAILED
        task.attempts = 1
        assert task.can_retry is True

        # Max attempts reached
        task.attempts = 3
        assert task.can_retry is False

        # Not failed status
        task.status = PageProcessingStatus.COMPLETED
        assert task.can_retry is False

    def test_workflow_progress_calculations(self):
        """Test WorkflowProgress calculations."""
        progress = WorkflowProgress(
            total_pages=20,
            completed_pages=8,
            failed_pages=2,
            skipped_pages=1,
        )

        assert progress.pending_pages == 9
        assert progress.completion_percentage == 55.0  # (8+2+1)/20 * 100

    def test_workflow_progress_timing_updates(self):
        """Test WorkflowProgress timing estimate updates."""
        progress = WorkflowProgress(
            total_pages=10,
            completed_pages=3,
            failed_pages=1,
            workflow_start_time=datetime.now(UTC),
        )

        # Update with processing times
        processing_times = [2.5, 3.0, 1.8, 4.2]  # 4 completed pages
        progress.update_timing_estimates(processing_times)

        assert progress.average_page_processing_time == 2.875  # Average of times
        assert progress.estimated_completion_time is not None

    def test_workflow_checkpoint_serialization(self):
        """Test WorkflowCheckpoint serialization."""
        checkpoint = WorkflowCheckpoint(
            project_id="test-project",
            workflow_id="workflow-123",
            created_at=datetime.now(UTC),
            page_tasks=[{"url": "https://example.com", "status": "completed"}],
            progress={"total_pages": 5, "completed_pages": 2},
            configuration={"include_network": True},
        )

        data_dict = checkpoint.to_dict()

        assert data_dict["project_id"] == "test-project"
        assert data_dict["workflow_id"] == "workflow-123"
        assert "created_at" in data_dict
        assert len(data_dict["page_tasks"]) == 1

        # Test round-trip
        restored = WorkflowCheckpoint.from_dict(data_dict)
        assert restored.project_id == checkpoint.project_id
        assert restored.workflow_id == checkpoint.workflow_id


class TestSequentialNavigationWorkflow:
    """Test the SequentialNavigationWorkflow class."""

    @pytest.fixture
    def mock_browser_service(self):
        """Create mock browser service."""
        service = AsyncMock()
        session = AsyncMock()
        session.page = AsyncMock()
        service.get_session.return_value.__aenter__.return_value = session
        service.close_session = AsyncMock()
        return service

    @pytest.fixture
    def workflow(self, mock_browser_service, tmp_path):
        """Create a workflow instance."""
        return SequentialNavigationWorkflow(
            browser_service=mock_browser_service,
            project_root=tmp_path,
            project_id="test-project",
            max_concurrent_sessions=2,
            default_max_retries=2,
            checkpoint_interval=3,
        )

    def test_workflow_initialization(self, workflow):
        """Test workflow initialization."""
        assert workflow.project_id == "test-project"
        assert workflow.max_concurrent_sessions == 2
        assert workflow.default_max_retries == 2
        assert workflow.checkpoint_interval == 3
        assert workflow.status == QueueStatus.PENDING
        assert len(workflow.page_tasks) == 0

    def test_add_page_urls(self, workflow):
        """Test adding URLs to workflow."""
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        workflow.add_page_urls(urls, max_retries=3)

        assert len(workflow.page_tasks) == 3
        assert workflow.progress.total_pages == 3

        for i, task in enumerate(workflow.page_tasks):
            assert task.url == urls[i]
            assert task.status == PageProcessingStatus.PENDING
            assert task.max_attempts == 3

    def test_add_urls_invalid_state(self, workflow):
        """Test adding URLs when workflow is in invalid state."""
        workflow.status = QueueStatus.RUNNING

        with pytest.raises(ValueError, match="Cannot add URLs when workflow status is"):
            workflow.add_page_urls(["https://example.com"])

    def test_generate_page_id(self, workflow):
        """Test page ID generation."""
        page_id = workflow._generate_page_id("https://example.com/products/123?ref=home")

        assert isinstance(page_id, str)
        assert len(page_id) > 8  # Should include path and hash
        assert "products" in page_id or "123" in page_id  # Should include path elements

    def test_workflow_control_methods(self, workflow):
        """Test workflow control methods."""
        # Initial state
        assert workflow.status == QueueStatus.PENDING

        # Cannot pause/resume when not running
        workflow.status = QueueStatus.RUNNING
        workflow.pause()
        assert workflow._should_pause is True
        assert workflow.status == QueueStatus.PAUSED

        workflow.resume()
        assert workflow._should_pause is False
        assert workflow.status == QueueStatus.RUNNING

        # Stop workflow
        workflow.stop()
        assert workflow._should_stop is True

    def test_skip_current_page(self, workflow):
        """Test skipping current page."""
        urls = ["https://example.com/page1", "https://example.com/page2"]
        workflow.add_page_urls(urls)

        # Skip first page
        workflow.skip_current_page()

        first_task = workflow.page_tasks[0]
        assert first_task.status == PageProcessingStatus.SKIPPED
        assert workflow.progress.skipped_pages == 1

    @pytest.mark.asyncio
    async def test_start_workflow_validation(self, workflow):
        """Test workflow start validation."""
        # Cannot start without pages
        with pytest.raises(ValueError, match="No pages to process"):
            await workflow.start_workflow()

        # Cannot start from non-pending state
        workflow.add_page_urls(["https://example.com"])
        workflow.status = QueueStatus.COMPLETED

        with pytest.raises(ValueError, match="Workflow cannot be started from status"):
            await workflow.start_workflow()

    @pytest.mark.asyncio
    async def test_process_single_page_success(self, workflow, mock_browser_service):
        """Test successful single page processing."""
        # Create a task
        task = PageTask(url="https://example.com", page_id="test-page")

        # Mock analysis result
        mock_analysis = PageAnalysisData(
            url="https://example.com",
            title="Test Page",
            analysis_duration=2.5,
        )

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.return_value = mock_analysis
            mock_analyzer_cls.return_value = mock_analyzer

            # Mock file operations
            with patch("builtins.open", mock_open_write()), \
                 patch("pathlib.Path.mkdir"):

                await workflow._process_single_page(task)

                assert task.status == PageProcessingStatus.COMPLETED
                assert task.attempts == 1
                assert task.analysis_result == mock_analysis
                assert task.processing_start_time is not None
                assert task.processing_end_time is not None

    @pytest.mark.asyncio
    async def test_process_single_page_with_retry(self, workflow, mock_browser_service):
        """Test single page processing with retry logic."""
        task = PageTask(url="https://example.com", page_id="test-page", max_attempts=3)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            # Success on third attempt
            return PageAnalysisData(
                url="https://example.com",
                title="Test Page",
                analysis_duration=1.0,
            )

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.side_effect = side_effect
            mock_analyzer_cls.return_value = mock_analyzer

            with patch("builtins.open", mock_open_write()), \
                 patch("pathlib.Path.mkdir"), \
                 patch("asyncio.sleep"):  # Speed up retries

                await workflow._process_single_page(task)

                assert task.status == PageProcessingStatus.COMPLETED
                assert task.attempts == 3
                assert call_count == 3

    @pytest.mark.asyncio
    async def test_process_single_page_permanent_failure(self, workflow, mock_browser_service):
        """Test single page processing with permanent failure."""
        task = PageTask(url="https://example.com", page_id="test-page", max_attempts=2)

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.side_effect = Exception("Permanent failure")
            mock_analyzer_cls.return_value = mock_analyzer

            with patch("asyncio.sleep"):  # Speed up retries
                with pytest.raises(Exception, match="Permanent failure"):
                    await workflow._process_single_page(task)

                assert task.status == PageProcessingStatus.FAILED
                assert task.attempts == 2
                assert task.error_message == "Permanent failure"

    @pytest.mark.asyncio
    async def test_save_page_analysis(self, workflow, tmp_path):
        """Test saving page analysis results."""
        task = PageTask(url="https://example.com", page_id="test-page")
        analysis_result = PageAnalysisData(
            url="https://example.com",
            title="Test Page",
        )

        await workflow._save_page_analysis(task, analysis_result)

        # Verify file was created
        expected_file = tmp_path / "analysis" / "pages" / "test-page.json"
        assert expected_file.exists()

        # Verify content
        with open(expected_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["url"] == "https://example.com"
        assert saved_data["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_save_and_load_checkpoint(self, workflow, tmp_path):
        """Test checkpoint save and load functionality."""
        # Setup workflow with some tasks
        urls = ["https://example.com/page1", "https://example.com/page2"]
        workflow.add_page_urls(urls)

        # Mark one task as completed
        workflow.page_tasks[0].status = PageProcessingStatus.COMPLETED
        workflow.page_tasks[0].processing_start_time = datetime.now(UTC)
        workflow.page_tasks[0].processing_end_time = datetime.now(UTC)
        workflow.progress.completed_pages = 1

        # Save checkpoint
        await workflow._save_checkpoint()

        # Verify checkpoint file exists
        checkpoint_file = workflow.checkpoint_dir / f"{workflow.workflow_id}.json"
        assert checkpoint_file.exists()

        # Load checkpoint
        with patch("legacy_web_mcp.browser.workflow.BrowserAutomationService"):
            loaded_workflow = await SequentialNavigationWorkflow.load_from_checkpoint(
                checkpoint_file=checkpoint_file,
                browser_service=AsyncMock(),
                project_root=tmp_path,
            )

            assert loaded_workflow.workflow_id == workflow.workflow_id
            assert loaded_workflow.project_id == workflow.project_id
            assert len(loaded_workflow.page_tasks) == 2
            assert loaded_workflow.progress.completed_pages == 1

    def test_get_progress_summary(self, workflow):
        """Test progress summary generation."""
        # Setup workflow with tasks
        urls = ["https://example.com/page1", "https://example.com/page2", "https://example.com/page3"]
        workflow.add_page_urls(urls)

        # Set some progress
        workflow.page_tasks[0].status = PageProcessingStatus.COMPLETED
        workflow.page_tasks[1].status = PageProcessingStatus.FAILED
        workflow.page_tasks[1].error_message = "Network error"
        workflow.progress.completed_pages = 1
        workflow.progress.failed_pages = 1
        workflow.progress.current_page_index = 1
        workflow.progress.current_page_url = "https://example.com/page2"

        summary = workflow.get_progress_summary()

        assert summary["workflow_id"] == workflow.workflow_id
        assert summary["project_id"] == workflow.project_id
        assert summary["status"] == QueueStatus.PENDING.value
        assert summary["progress"]["total_pages"] == 3
        assert summary["progress"]["completed_pages"] == 1
        assert summary["progress"]["failed_pages"] == 1
        assert summary["progress"]["pending_pages"] == 1
        assert summary["progress"]["completion_percentage"] == 66.67  # Approximately

        # Check task details
        assert len(summary["tasks"]) == 3
        assert summary["tasks"][0]["status"] == "completed"
        assert summary["tasks"][1]["status"] == "failed"
        assert summary["tasks"][1]["error_message"] == "Network error"


class TestWorkflowIntegration:
    """Integration tests for workflow functionality."""

    @pytest.fixture
    def mock_browser_service(self):
        """Create comprehensive mock browser service."""
        service = AsyncMock()

        def create_session(*args, **kwargs):
            session = AsyncMock()
            session.page = AsyncMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            return session

        service.get_session.side_effect = create_session
        service.close_session = AsyncMock()
        return service

    @pytest.mark.asyncio
    async def test_full_workflow_execution(self, mock_browser_service, tmp_path):
        """Test complete workflow execution with multiple pages."""
        workflow = SequentialNavigationWorkflow(
            browser_service=mock_browser_service,
            project_root=tmp_path,
            project_id="integration-test",
            checkpoint_interval=2,
        )

        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]
        workflow.add_page_urls(urls)

        # Mock successful analysis for all pages
        mock_results = [
            PageAnalysisData(url=url, title=f"Page {i+1}", analysis_duration=1.0)
            for i, url in enumerate(urls)
        ]

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.side_effect = mock_results
            mock_analyzer_cls.return_value = mock_analyzer

            with patch("builtins.open", mock_open_write()), \
                 patch("pathlib.Path.mkdir"):

                await workflow.start_workflow()

                # Verify final state
                assert workflow.status == QueueStatus.COMPLETED
                assert workflow.progress.completed_pages == 3
                assert workflow.progress.failed_pages == 0
                assert workflow.progress.completion_percentage == 100.0

                # Verify all tasks completed
                for task in workflow.page_tasks:
                    assert task.status == PageProcessingStatus.COMPLETED
                    assert task.analysis_result is not None

    @pytest.mark.asyncio
    async def test_workflow_with_failures_and_retries(self, mock_browser_service, tmp_path):
        """Test workflow with some failures and retries."""
        workflow = SequentialNavigationWorkflow(
            browser_service=mock_browser_service,
            project_root=tmp_path,
            project_id="failure-test",
            default_max_retries=2,
        )

        urls = ["https://example.com/page1", "https://example.com/page2"]
        workflow.add_page_urls(urls)

        call_count = 0

        def analysis_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            # First page succeeds
            if "page1" in str(args[1]):
                return PageAnalysisData(url=args[1], title="Page 1", analysis_duration=1.0)

            # Second page fails twice, then succeeds
            if call_count <= 2:
                raise Exception("Temporary failure")
            return PageAnalysisData(url=args[1], title="Page 2", analysis_duration=1.5)

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.side_effect = analysis_side_effect
            mock_analyzer_cls.return_value = mock_analyzer

            with patch("builtins.open", mock_open_write()), \
                 patch("pathlib.Path.mkdir"), \
                 patch("asyncio.sleep"):  # Speed up retries

                await workflow.start_workflow()

                # Verify final state
                assert workflow.status == QueueStatus.COMPLETED
                assert workflow.progress.completed_pages == 2
                assert workflow.progress.failed_pages == 0

                # Verify retry behavior
                assert workflow.page_tasks[1].attempts > 1

    @pytest.mark.asyncio
    async def test_workflow_pause_and_resume(self, mock_browser_service, tmp_path):
        """Test workflow pause and resume functionality."""
        workflow = SequentialNavigationWorkflow(
            browser_service=mock_browser_service,
            project_root=tmp_path,
            project_id="pause-test",
        )

        urls = ["https://example.com/page1", "https://example.com/page2"]
        workflow.add_page_urls(urls)

        # Mock analysis that takes some time
        async def slow_analysis(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return PageAnalysisData(url=args[1], title="Test Page", analysis_duration=0.1)

        with patch("legacy_web_mcp.browser.workflow.PageAnalyzer") as mock_analyzer_cls:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_page.side_effect = slow_analysis
            mock_analyzer_cls.return_value = mock_analyzer

            with patch("builtins.open", mock_open_write()), \
                 patch("pathlib.Path.mkdir"):

                # Start workflow
                start_task = asyncio.create_task(workflow.start_workflow())

                # Pause after short delay
                await asyncio.sleep(0.05)
                workflow.pause()

                # Wait for workflow to complete
                await start_task

                # Should be paused
                assert workflow.status == QueueStatus.PAUSED
                assert workflow.progress.completed_pages < 2  # Not all pages completed


def mock_open_write():
    """Create a mock for open() that supports writing."""
    mock_open = MagicMock()
    mock_file = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file
    mock_open.return_value.__exit__.return_value = None
    return mock_open