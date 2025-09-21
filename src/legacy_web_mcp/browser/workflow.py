"""Sequential navigation workflow for processing multiple pages systematically."""
from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog

from legacy_web_mcp.browser.analysis import PageAnalysisData, PageAnalyzer
from legacy_web_mcp.browser.service import BrowserAutomationService

_logger = structlog.get_logger("legacy_web_mcp.browser.workflow")


class QueueStatus(str, Enum):
    """Status of the navigation queue."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PageProcessingStatus(str, Enum):
    """Status of individual page processing."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass(slots=True)
class PageTask:
    """Individual page processing task."""

    url: str
    page_id: str
    status: PageProcessingStatus = PageProcessingStatus.PENDING
    attempts: int = 0
    max_attempts: int = 3
    error_message: str | None = None
    processing_start_time: datetime | None = None
    processing_end_time: datetime | None = None
    analysis_result: PageAnalysisData | None = None

    @property
    def processing_duration(self) -> float | None:
        """Get processing duration in seconds."""
        if self.processing_start_time and self.processing_end_time:
            return (self.processing_end_time - self.processing_start_time).total_seconds()
        return None

    @property
    def can_retry(self) -> bool:
        """Check if this task can be retried."""
        return self.attempts < self.max_attempts and self.status == PageProcessingStatus.FAILED


@dataclass(slots=True)
class WorkflowProgress:
    """Progress tracking for sequential navigation workflow."""

    total_pages: int
    completed_pages: int = 0
    failed_pages: int = 0
    skipped_pages: int = 0
    current_page_index: int = 0
    current_page_url: str | None = None

    # Timing information
    workflow_start_time: datetime | None = None
    workflow_end_time: datetime | None = None
    estimated_completion_time: datetime | None = None

    # Performance metrics
    average_page_processing_time: float = 0.0
    pages_per_minute: float = 0.0

    @property
    def pending_pages(self) -> int:
        """Get number of pending pages."""
        return self.total_pages - self.completed_pages - self.failed_pages - self.skipped_pages

    @property
    def completion_percentage(self) -> float:
        """Get completion percentage."""
        if self.total_pages == 0:
            return 100.0
        return ((self.completed_pages + self.failed_pages + self.skipped_pages) / self.total_pages) * 100

    @property
    def workflow_duration(self) -> float | None:
        """Get total workflow duration in seconds."""
        if self.workflow_start_time:
            end_time = self.workflow_end_time or datetime.now(UTC)
            return (end_time - self.workflow_start_time).total_seconds()
        return None

    def update_timing_estimates(self, completed_processing_times: list[float]) -> None:
        """Update timing estimates based on completed page processing times."""
        if completed_processing_times:
            self.average_page_processing_time = sum(completed_processing_times) / len(completed_processing_times)

            # Calculate pages per minute
            if self.workflow_duration:
                processed_pages = self.completed_pages + self.failed_pages + self.skipped_pages
                self.pages_per_minute = (processed_pages / self.workflow_duration) * 60

            # Estimate completion time
            if self.pending_pages > 0:
                estimated_remaining_seconds = self.pending_pages * self.average_page_processing_time
                self.estimated_completion_time = datetime.now(UTC).replace(
                    microsecond=0
                ) + timedelta(seconds=estimated_remaining_seconds)

    def to_dict(self) -> dict[str, Any]:
        """Convert progress to dictionary for JSON serialization."""
        return {
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "failed_pages": self.failed_pages,
            "skipped_pages": self.skipped_pages,
            "current_page_index": self.current_page_index,
            "current_page_url": self.current_page_url,
            "workflow_start_time": self.workflow_start_time.isoformat() if self.workflow_start_time else None,
            "workflow_end_time": self.workflow_end_time.isoformat() if self.workflow_end_time else None,
            "estimated_completion_time": self.estimated_completion_time.isoformat() if self.estimated_completion_time else None,
            "average_page_processing_time": self.average_page_processing_time,
            "pages_per_minute": self.pages_per_minute,
        }


@dataclass(slots=True)
class WorkflowCheckpoint:
    """Checkpoint data for resuming interrupted workflows."""

    project_id: str
    workflow_id: str
    created_at: datetime
    page_tasks: list[dict[str, Any]]
    progress: dict[str, Any]
    configuration: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "project_id": self.project_id,
            "workflow_id": self.workflow_id,
            "created_at": self.created_at.isoformat(),
            "page_tasks": self.page_tasks,
            "progress": self.progress,
            "configuration": self.configuration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowCheckpoint:
        """Create checkpoint from dictionary."""
        return cls(
            project_id=data["project_id"],
            workflow_id=data["workflow_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            page_tasks=data["page_tasks"],
            progress=data["progress"],
            configuration=data["configuration"],
        )


class SequentialNavigationWorkflow:
    """Orchestrates sequential analysis of multiple pages with queue management."""

    def __init__(
        self,
        browser_service: BrowserAutomationService,
        project_root: Path,
        project_id: str,
        max_concurrent_sessions: int = 3,
        default_max_retries: int = 3,
        checkpoint_interval: int = 5,  # Save checkpoint every N pages
        enable_resource_cleanup: bool = True,
    ):
        self.browser_service = browser_service
        self.project_root = project_root
        self.project_id = project_id
        self.max_concurrent_sessions = max_concurrent_sessions
        self.default_max_retries = default_max_retries
        self.checkpoint_interval = checkpoint_interval
        self.enable_resource_cleanup = enable_resource_cleanup

        # Workflow state
        self.workflow_id = self._generate_workflow_id()
        self.page_tasks: list[PageTask] = []
        self.progress = WorkflowProgress(total_pages=0)
        self.status = QueueStatus.PENDING

        # Control flags
        self._should_pause = False
        self._should_stop = False
        self._current_sessions: set[str] = set()

        # Checkpoint management
        self.checkpoint_dir = project_root / "workflow" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Page analyzer configuration
        self.analyzer_config = {
            "include_network_analysis": True,
            "include_interaction_analysis": True,
            "performance_budget_seconds": 120.0,
        }

    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"workflow_{timestamp}"

    def add_page_urls(self, urls: list[str], max_retries: int | None = None) -> None:
        """Add URLs to the processing queue."""
        if self.status not in [QueueStatus.PENDING, QueueStatus.PAUSED]:
            raise ValueError(f"Cannot add URLs when workflow status is {self.status}")

        max_retries = max_retries or self.default_max_retries

        for url in urls:
            page_id = self._generate_page_id(url)
            task = PageTask(
                url=url,
                page_id=page_id,
                max_attempts=max_retries,
            )
            self.page_tasks.append(task)

        self.progress.total_pages = len(self.page_tasks)

        _logger.info(
            "page_urls_added_to_workflow",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
            urls_added=len(urls),
            total_pages=self.progress.total_pages,
        )

    def _generate_page_id(self, url: str) -> str:
        """Generate unique page ID from URL."""
        import hashlib

        parsed = urlparse(url)
        path = parsed.path.strip("/") or "index"
        clean_path = "".join(c for c in path if c.isalnum() or c in "-_")[:50]
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{clean_path}-{url_hash}"

    async def start_workflow(
        self,
        analyzer_config: dict[str, Any] | None = None,
    ) -> None:
        """Start the sequential navigation workflow."""
        if self.status != QueueStatus.PENDING:
            raise ValueError(f"Workflow cannot be started from status {self.status}")

        if not self.page_tasks:
            raise ValueError("No pages to process")

        if analyzer_config:
            self.analyzer_config.update(analyzer_config)

        self.status = QueueStatus.RUNNING
        self.progress.workflow_start_time = datetime.now(UTC)
        self.progress.current_page_index = 0

        _logger.info(
            "sequential_workflow_started",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
            total_pages=self.progress.total_pages,
            analyzer_config=self.analyzer_config,
        )

        try:
            await self._process_queue()

            if self._should_stop:
                self.status = QueueStatus.CANCELLED
            elif self.progress.pending_pages == 0:
                self.status = QueueStatus.COMPLETED
                self.progress.workflow_end_time = datetime.now(UTC)
            else:
                self.status = QueueStatus.PAUSED

        except Exception as e:
            self.status = QueueStatus.FAILED
            _logger.error(
                "sequential_workflow_failed",
                workflow_id=self.workflow_id,
                project_id=self.project_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        finally:
            await self._cleanup_sessions()
            await self._save_checkpoint()

    async def _process_queue(self) -> None:
        """Process the page queue sequentially."""
        while self.progress.current_page_index < len(self.page_tasks):
            if self._should_pause or self._should_stop:
                break

            current_task = self.page_tasks[self.progress.current_page_index]

            if current_task.status in [PageProcessingStatus.COMPLETED, PageProcessingStatus.SKIPPED]:
                self.progress.current_page_index += 1
                continue

            self.progress.current_page_url = current_task.url

            try:
                await self._process_single_page(current_task)

                # Update progress and timing estimates
                self._update_progress_metrics()

                # Save checkpoint periodically
                if (self.progress.current_page_index + 1) % self.checkpoint_interval == 0:
                    await self._save_checkpoint()

            except Exception as e:
                _logger.error(
                    "page_processing_error",
                    workflow_id=self.workflow_id,
                    page_url=current_task.url,
                    page_id=current_task.page_id,
                    error=str(e),
                )

                current_task.status = PageProcessingStatus.FAILED
                current_task.error_message = str(e)
                self.progress.failed_pages += 1

            self.progress.current_page_index += 1

            # Resource cleanup between pages
            if self.enable_resource_cleanup:
                await self._cleanup_page_resources()

    async def _process_single_page(self, task: PageTask) -> None:
        """Process a single page with retry logic."""
        task.attempts += 1
        task.status = PageProcessingStatus.PROCESSING
        task.processing_start_time = datetime.now(UTC)

        _logger.info(
            "page_processing_started",
            workflow_id=self.workflow_id,
            page_url=task.url,
            page_id=task.page_id,
            attempt=task.attempts,
            max_attempts=task.max_attempts,
        )

        try:
            # Create page analyzer
            analyzer = PageAnalyzer(**self.analyzer_config)

            # Get browser session
            session_id = f"{self.workflow_id}_{task.page_id}"
            self._current_sessions.add(session_id)

            # Get or create session
            session = await self.browser_service.get_session(session_id)
            if not session:
                session = await self.browser_service.create_session(
                    project_id=session_id,
                    headless=True,
                )

            try:
                page = await session.create_page()

                # Perform page analysis
                analysis_result = await analyzer.analyze_page(
                    page=page,
                    url=task.url,
                    project_root=self.project_root,
                )

                # Save analysis result
                await self._save_page_analysis(task, analysis_result)

                task.analysis_result = analysis_result
                task.status = PageProcessingStatus.COMPLETED
                task.processing_end_time = datetime.now(UTC)
                self.progress.completed_pages += 1

                _logger.info(
                    "page_processing_completed",
                    workflow_id=self.workflow_id,
                    page_url=task.url,
                    page_id=task.page_id,
                    processing_duration=task.processing_duration,
                    analysis_duration=analysis_result.analysis_duration,
                )

            except Exception as e:
                task.processing_end_time = datetime.now(UTC)
                task.error_message = str(e)

                if task.can_retry:
                    task.status = PageProcessingStatus.RETRYING
                    _logger.warning(
                        "page_processing_retry",
                        workflow_id=self.workflow_id,
                        page_url=task.url,
                        page_id=task.page_id,
                        attempt=task.attempts,
                        max_attempts=task.max_attempts,
                        error=str(e),
                    )

                    # Retry with exponential backoff
                    wait_time = min(2 ** (task.attempts - 1), 30)  # Max 30 seconds
                    await asyncio.sleep(wait_time)

                    await self._process_single_page(task)
                else:
                    task.status = PageProcessingStatus.FAILED
                    self.progress.failed_pages += 1
                    _logger.error(
                        "page_processing_failed_permanently",
                        workflow_id=self.workflow_id,
                        page_url=task.url,
                        page_id=task.page_id,
                        attempts=task.attempts,
                        error=str(e),
                    )
                    raise

            finally:
                # Cleanup session
                await self.browser_service.close_session(session_id)

        finally:
            self._current_sessions.discard(session_id)

    async def _save_page_analysis(self, task: PageTask, analysis_result: PageAnalysisData) -> None:
        """Save page analysis result to project storage."""
        analysis_dir = self.project_root / "analysis" / "pages"
        analysis_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{task.page_id}.json"
        file_path = analysis_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result.to_dict(), f, indent=2, ensure_ascii=False)

        _logger.debug(
            "page_analysis_saved",
            workflow_id=self.workflow_id,
            page_id=task.page_id,
            file_path=str(file_path),
        )

    def _update_progress_metrics(self) -> None:
        """Update progress metrics and timing estimates."""
        completed_processing_times = [
            task.processing_duration
            for task in self.page_tasks
            if task.processing_duration is not None
        ]

        self.progress.update_timing_estimates(completed_processing_times)

        _logger.info(
            "workflow_progress_updated",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
            completion_percentage=self.progress.completion_percentage,
            completed_pages=self.progress.completed_pages,
            failed_pages=self.progress.failed_pages,
            pending_pages=self.progress.pending_pages,
            estimated_completion=self.progress.estimated_completion_time.isoformat() if self.progress.estimated_completion_time else None,
            pages_per_minute=self.progress.pages_per_minute,
        )

    async def _cleanup_page_resources(self) -> None:
        """Cleanup resources between page processing."""
        # Small delay to allow resource cleanup
        await asyncio.sleep(0.5)

        # Could add more sophisticated cleanup here
        # like memory garbage collection, browser context resets, etc.

    async def _cleanup_sessions(self) -> None:
        """Cleanup all active browser sessions."""
        for session_id in list(self._current_sessions):
            try:
                await self.browser_service.close_session(session_id)
            except Exception as e:
                _logger.warning(
                    "session_cleanup_error",
                    session_id=session_id,
                    error=str(e),
                )

        self._current_sessions.clear()

    async def _save_checkpoint(self) -> None:
        """Save workflow checkpoint for resuming."""
        checkpoint = WorkflowCheckpoint(
            project_id=self.project_id,
            workflow_id=self.workflow_id,
            created_at=datetime.now(UTC),
            page_tasks=[self._serialize_page_task(task) for task in self.page_tasks],
            progress=self.progress.to_dict(),
            configuration=self.analyzer_config,
        )

        checkpoint_file = self.checkpoint_dir / f"{self.workflow_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.to_dict(), f, indent=2, ensure_ascii=False)

        _logger.debug(
            "workflow_checkpoint_saved",
            workflow_id=self.workflow_id,
            checkpoint_file=str(checkpoint_file),
        )

    def _serialize_page_task(self, task: PageTask) -> dict[str, Any]:
        """Serialize page task for checkpoint storage."""
        data = asdict(task)

        # Convert datetime objects to ISO strings
        if data["processing_start_time"]:
            data["processing_start_time"] = task.processing_start_time.isoformat()
        if data["processing_end_time"]:
            data["processing_end_time"] = task.processing_end_time.isoformat()

        # Don't serialize large analysis result in checkpoint
        data["analysis_result"] = None

        return data

    @classmethod
    async def load_from_checkpoint(
        cls,
        checkpoint_file: Path,
        browser_service: BrowserAutomationService,
        project_root: Path,
    ) -> SequentialNavigationWorkflow:
        """Load workflow from checkpoint file."""
        with open(checkpoint_file, encoding="utf-8") as f:
            checkpoint_data = json.load(f)

        checkpoint = WorkflowCheckpoint.from_dict(checkpoint_data)

        # Create workflow instance
        workflow = cls(
            browser_service=browser_service,
            project_root=project_root,
            project_id=checkpoint.project_id,
        )

        # Restore workflow state
        workflow.workflow_id = checkpoint.workflow_id
        workflow.analyzer_config = checkpoint.configuration

        # Restore page tasks
        workflow.page_tasks = []
        for task_data in checkpoint.page_tasks:
            task = PageTask(
                url=task_data["url"],
                page_id=task_data["page_id"],
                status=PageProcessingStatus(task_data["status"]),
                attempts=task_data["attempts"],
                max_attempts=task_data["max_attempts"],
                error_message=task_data["error_message"],
            )

            # Restore datetime objects
            if task_data["processing_start_time"]:
                task.processing_start_time = datetime.fromisoformat(task_data["processing_start_time"])
            if task_data["processing_end_time"]:
                task.processing_end_time = datetime.fromisoformat(task_data["processing_end_time"])

            workflow.page_tasks.append(task)

        # Restore progress
        progress_data = checkpoint.progress
        workflow.progress = WorkflowProgress(
            total_pages=progress_data["total_pages"],
            completed_pages=progress_data["completed_pages"],
            failed_pages=progress_data["failed_pages"],
            skipped_pages=progress_data["skipped_pages"],
            current_page_index=progress_data["current_page_index"],
            current_page_url=progress_data["current_page_url"],
            average_page_processing_time=progress_data["average_page_processing_time"],
            pages_per_minute=progress_data["pages_per_minute"],
        )

        # Restore datetime objects
        if progress_data["workflow_start_time"]:
            workflow.progress.workflow_start_time = datetime.fromisoformat(progress_data["workflow_start_time"])
        if progress_data["workflow_end_time"]:
            workflow.progress.workflow_end_time = datetime.fromisoformat(progress_data["workflow_end_time"])
        if progress_data["estimated_completion_time"]:
            workflow.progress.estimated_completion_time = datetime.fromisoformat(progress_data["estimated_completion_time"])

        workflow.status = QueueStatus.PAUSED  # Start in paused state

        _logger.info(
            "workflow_loaded_from_checkpoint",
            workflow_id=workflow.workflow_id,
            project_id=workflow.project_id,
            checkpoint_file=str(checkpoint_file),
            current_page_index=workflow.progress.current_page_index,
            total_pages=workflow.progress.total_pages,
        )

        return workflow

    def pause(self) -> None:
        """Pause the workflow after current page completes."""
        self._should_pause = True
        self.status = QueueStatus.PAUSED

        _logger.info(
            "workflow_pause_requested",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
        )

    def resume(self) -> None:
        """Resume a paused workflow."""
        if self.status != QueueStatus.PAUSED:
            raise ValueError(f"Cannot resume workflow with status {self.status}")

        self._should_pause = False
        self.status = QueueStatus.RUNNING

        _logger.info(
            "workflow_resumed",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
        )

    def stop(self) -> None:
        """Stop the workflow gracefully after current page completes."""
        self._should_stop = True

        _logger.info(
            "workflow_stop_requested",
            workflow_id=self.workflow_id,
            project_id=self.project_id,
        )

    def skip_current_page(self) -> None:
        """Skip the currently processing page."""
        if self.progress.current_page_index < len(self.page_tasks):
            current_task = self.page_tasks[self.progress.current_page_index]
            current_task.status = PageProcessingStatus.SKIPPED
            self.progress.skipped_pages += 1

            _logger.info(
                "page_skipped",
                workflow_id=self.workflow_id,
                page_url=current_task.url,
                page_id=current_task.page_id,
            )

    def get_progress_summary(self) -> dict[str, Any]:
        """Get comprehensive progress summary."""
        return {
            "workflow_id": self.workflow_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "progress": {
                "total_pages": self.progress.total_pages,
                "completed_pages": self.progress.completed_pages,
                "failed_pages": self.progress.failed_pages,
                "skipped_pages": self.progress.skipped_pages,
                "pending_pages": self.progress.pending_pages,
                "current_page_index": self.progress.current_page_index,
                "current_page_url": self.progress.current_page_url,
                "completion_percentage": self.progress.completion_percentage,
            },
            "timing": {
                "workflow_start_time": self.progress.workflow_start_time.isoformat() if self.progress.workflow_start_time else None,
                "workflow_duration": self.progress.workflow_duration,
                "average_page_processing_time": self.progress.average_page_processing_time,
                "pages_per_minute": self.progress.pages_per_minute,
                "estimated_completion_time": self.progress.estimated_completion_time.isoformat() if self.progress.estimated_completion_time else None,
            },
            "tasks": [
                {
                    "url": task.url,
                    "page_id": task.page_id,
                    "status": task.status.value,
                    "attempts": task.attempts,
                    "processing_duration": task.processing_duration,
                    "error_message": task.error_message,
                }
                for task in self.page_tasks
            ],
        }


__all__ = [
    "QueueStatus",
    "PageProcessingStatus",
    "PageTask",
    "WorkflowProgress",
    "WorkflowCheckpoint",
    "SequentialNavigationWorkflow",
]