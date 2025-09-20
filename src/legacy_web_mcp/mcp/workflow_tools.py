"""MCP tools for sequential navigation workflow management."""
from __future__ import annotations

from typing import Any

import structlog
from fastmcp import Context, FastMCP

from legacy_web_mcp.browser import BrowserAutomationService
from legacy_web_mcp.browser.workflow import QueueStatus, SequentialNavigationWorkflow
from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.storage.projects import create_project_store

_logger = structlog.get_logger("legacy_web_mcp.mcp.workflow_tools")

# Global workflow registry to track active workflows
_active_workflows: dict[str, SequentialNavigationWorkflow] = {}


def register(mcp: FastMCP) -> None:
    """Register sequential workflow tools with the MCP server."""

    @mcp.tool()
    async def analyze_page_list(
        context: Context,
        urls: list[str],
        project_id: str = "multi-page-analysis",
        max_retries_per_page: int = 3,
        include_network_monitoring: bool = True,
        include_interaction_simulation: bool = True,
        enable_checkpointing: bool = True,
        checkpoint_interval: int = 5,
        max_concurrent_sessions: int = 3,
    ) -> dict[str, Any]:
        """Process multiple pages in systematic sequence with queue management and error recovery.

        Orchestrates comprehensive analysis of multiple pages with intelligent queue management,
        progress tracking, checkpoint creation for resumability, and resource optimization.
        Designed for analyzing entire websites or selected page subsets efficiently.

        Args:
            urls: Ordered list of URLs to analyze systematically (required)
            project_id: Project identifier for organizing results and checkpoints (default: "multi-page-analysis")
            max_retries_per_page: Maximum retry attempts per failed page (default: 3)
            include_network_monitoring: Enable network traffic monitoring for each page (default: True)
            include_interaction_simulation: Enable user interaction simulation (default: True)
            enable_checkpointing: Create checkpoints for workflow resumption (default: True)
            checkpoint_interval: Save checkpoint every N pages (default: 5)
            max_concurrent_sessions: Maximum concurrent browser sessions (default: 3)

        Returns:
            Dictionary containing:
            - status: "success", "error", or "partial"
            - workflow_id: Unique identifier for this analysis workflow
            - project_id: Project identifier used for organization
            - progress_summary: Detailed progress metrics and completion statistics
            - timing_metrics: Performance analysis and estimated completion times
            - page_results: Summary of individual page analysis results
            - error_summary: Details of any failed pages and error patterns
            - checkpoint_info: Checkpoint creation status and resume capabilities
            - resource_usage: Browser session and memory utilization metrics

        Workflow Features:
            - Sequential Processing: Pages analyzed in specified order with session reuse
            - Error Recovery: Automatic retry with exponential backoff for failed pages
            - Progress Tracking: Real-time progress updates with ETA calculation
            - Checkpoint Creation: Automatic save points for workflow resumption
            - Resource Management: Intelligent browser session lifecycle management
            - Pause/Resume Support: Workflow can be paused and resumed via separate tools

        Performance Optimizations:
            - Browser session reuse between pages to minimize overhead
            - Intelligent resource cleanup to prevent memory leaks
            - Concurrent session management within specified limits
            - Checkpoint interval optimization for large page sets

        Error Handling:
            - Individual page failures don't stop entire workflow
            - Configurable retry logic with exponential backoff
            - Detailed error reporting and categorization
            - Graceful degradation for partial completions
        """
        try:
            if not urls:
                return {
                    "status": "error",
                    "error": "No URLs provided for analysis",
                    "error_type": "ValidationError",
                }

            config = load_configuration()

            _logger.info(
                "page_list_analysis_started",
                urls_count=len(urls),
                project_id=project_id,
                max_retries_per_page=max_retries_per_page,
                include_network_monitoring=include_network_monitoring,
                include_interaction_simulation=include_interaction_simulation,
            )

            # Initialize services
            browser_service = BrowserAutomationService(config)
            project_store = create_project_store(config)

            # Get or create project
            project_metadata = project_store.get_project_metadata(project_id)
            if not project_metadata:
                project_metadata = project_store.create_project(
                    project_id=project_id,
                    website_url=urls[0] if urls else "multi-page-analysis",
                    config={
                        "analysis_type": "sequential_workflow",
                        "page_count": len(urls),
                    }
                )

            project_root = project_metadata.root_path

            # Create workflow
            workflow = SequentialNavigationWorkflow(
                browser_service=browser_service,
                project_root=project_root,
                project_id=project_id,
                max_concurrent_sessions=max_concurrent_sessions,
                default_max_retries=max_retries_per_page,
                checkpoint_interval=checkpoint_interval if enable_checkpointing else 999999,
                enable_resource_cleanup=True,
            )

            # Add URLs to workflow
            workflow.add_page_urls(urls, max_retries=max_retries_per_page)

            # Store in global registry
            _active_workflows[workflow.workflow_id] = workflow

            # Configure analyzer
            analyzer_config = {
                "include_network_analysis": include_network_monitoring,
                "include_interaction_analysis": include_interaction_simulation,
                "performance_budget_seconds": 120.0,
            }

            # Start workflow
            await workflow.start_workflow(analyzer_config)

            # Generate progress summary
            progress_summary = workflow.get_progress_summary()

            # Analyze results
            completed_pages = [
                task for task in workflow.page_tasks
                if task.status.value == "completed"
            ]
            failed_pages = [
                task for task in workflow.page_tasks
                if task.status.value == "failed"
            ]

            # Determine overall status
            if len(completed_pages) == len(urls):
                overall_status = "success"
            elif len(completed_pages) > 0:
                overall_status = "partial"
            else:
                overall_status = "error"

            # Generate error summary
            error_summary = _analyze_error_patterns(failed_pages)

            # Resource usage metrics
            resource_usage = {
                "max_concurrent_sessions": max_concurrent_sessions,
                "total_processing_time": workflow.progress.workflow_duration,
                "average_page_time": workflow.progress.average_page_processing_time,
                "pages_per_minute": workflow.progress.pages_per_minute,
            }

            await context.info(f"Sequential workflow completed: {len(completed_pages)}/{len(urls)} pages successful")

            result = {
                "status": overall_status,
                "workflow_id": workflow.workflow_id,
                "project_id": project_id,
                "progress_summary": {
                    "total_pages": len(urls),
                    "completed_pages": len(completed_pages),
                    "failed_pages": len(failed_pages),
                    "completion_percentage": progress_summary["progress"]["completion_percentage"],
                    "workflow_status": workflow.status.value,
                },
                "timing_metrics": {
                    "total_duration": workflow.progress.workflow_duration,
                    "average_page_processing_time": workflow.progress.average_page_processing_time,
                    "pages_per_minute": workflow.progress.pages_per_minute,
                    "estimated_completion_time": progress_summary["timing"]["estimated_completion_time"],
                },
                "page_results": [
                    {
                        "url": task.url,
                        "page_id": task.page_id,
                        "status": task.status.value,
                        "processing_duration": task.processing_duration,
                        "attempts": task.attempts,
                        "error_message": task.error_message,
                        "analysis_available": task.analysis_result is not None,
                    }
                    for task in workflow.page_tasks
                ],
                "error_summary": error_summary,
                "checkpoint_info": {
                    "checkpointing_enabled": enable_checkpointing,
                    "checkpoint_interval": checkpoint_interval,
                    "checkpoint_directory": str(workflow.checkpoint_dir),
                    "workflow_resumable": workflow.status == QueueStatus.COMPLETED,
                },
                "resource_usage": resource_usage,
            }

            # Cleanup workflow from registry if completed
            if workflow.status in [QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED]:
                _active_workflows.pop(workflow.workflow_id, None)

            _logger.info(
                "page_list_analysis_completed",
                workflow_id=workflow.workflow_id,
                project_id=project_id,
                overall_status=overall_status,
                completed_pages=len(completed_pages),
                failed_pages=len(failed_pages),
                total_duration=workflow.progress.workflow_duration,
            )

            return result

        except Exception as e:
            await context.error(f"Page list analysis failed: {e}")
            _logger.error(
                "page_list_analysis_failed",
                project_id=project_id,
                urls_count=len(urls) if urls else 0,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def control_workflow(
        context: Context,
        workflow_id: str,
        action: str,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Control active workflow execution with pause, resume, stop, and skip operations.

        Provides runtime control over sequential navigation workflows including pause/resume
        functionality, graceful stopping, individual page skipping, and progress monitoring.
        Essential for managing long-running analysis workflows.

        Args:
            workflow_id: Unique identifier of the workflow to control (required)
            action: Control action - "pause", "resume", "stop", "skip", "status" (required)
            project_id: Project identifier for additional validation (optional)

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - workflow_id: Workflow identifier
            - action_performed: Action that was executed
            - workflow_status: Current workflow status after action
            - progress_summary: Updated progress information
            - control_result: Specific results of the control action

        Supported Actions:
            - pause: Gracefully pause workflow after current page completes
            - resume: Resume a paused workflow from where it left off
            - stop: Stop workflow gracefully, allowing current page to finish
            - skip: Skip the currently processing page and move to next
            - status: Get current workflow status and progress without changes

        Control Features:
            - Graceful Operations: Actions wait for current page to complete safely
            - State Validation: Ensures actions are valid for current workflow state
            - Progress Preservation: All control actions maintain progress tracking
            - Checkpoint Integration: Pause/stop operations trigger checkpoint creation
        """
        try:
            if workflow_id not in _active_workflows:
                return {
                    "status": "error",
                    "workflow_id": workflow_id,
                    "error": f"Workflow {workflow_id} not found in active workflows",
                    "error_type": "WorkflowNotFoundError",
                }

            workflow = _active_workflows[workflow_id]

            # Validate project_id if provided
            if project_id and workflow.project_id != project_id:
                return {
                    "status": "error",
                    "workflow_id": workflow_id,
                    "error": f"Project ID mismatch: expected {workflow.project_id}, got {project_id}",
                    "error_type": "ProjectMismatchError",
                }

            _logger.info(
                "workflow_control_action",
                workflow_id=workflow_id,
                action=action,
                current_status=workflow.status.value,
                project_id=workflow.project_id,
            )

            control_result = {}

            if action == "pause":
                if workflow.status == QueueStatus.RUNNING:
                    workflow.pause()
                    control_result = {"message": "Workflow pause requested, will pause after current page"}
                else:
                    control_result = {"message": f"Cannot pause workflow in status {workflow.status.value}"}

            elif action == "resume":
                if workflow.status == QueueStatus.PAUSED:
                    workflow.resume()
                    # Resume workflow execution
                    await workflow.start_workflow()
                    control_result = {"message": "Workflow resumed successfully"}
                else:
                    control_result = {"message": f"Cannot resume workflow in status {workflow.status.value}"}

            elif action == "stop":
                if workflow.status in [QueueStatus.RUNNING, QueueStatus.PAUSED]:
                    workflow.stop()
                    control_result = {"message": "Workflow stop requested, will stop after current page"}
                else:
                    control_result = {"message": f"Workflow already in final status {workflow.status.value}"}

            elif action == "skip":
                if workflow.status == QueueStatus.RUNNING:
                    current_url = workflow.progress.current_page_url
                    workflow.skip_current_page()
                    control_result = {
                        "message": f"Skipped current page: {current_url}",
                        "skipped_url": current_url,
                    }
                else:
                    control_result = {"message": f"Cannot skip page when workflow status is {workflow.status.value}"}

            elif action == "status":
                control_result = {"message": "Status retrieved successfully"}

            else:
                return {
                    "status": "error",
                    "workflow_id": workflow_id,
                    "error": f"Unknown action: {action}. Supported actions: pause, resume, stop, skip, status",
                    "error_type": "InvalidActionError",
                }

            # Get updated progress summary
            progress_summary = workflow.get_progress_summary()

            await context.info(f"Workflow control action '{action}' performed on workflow {workflow_id}")

            return {
                "status": "success",
                "workflow_id": workflow_id,
                "action_performed": action,
                "workflow_status": workflow.status.value,
                "progress_summary": progress_summary["progress"],
                "timing_metrics": progress_summary["timing"],
                "control_result": control_result,
            }

        except Exception as e:
            await context.error(f"Workflow control failed: {e}")
            _logger.error(
                "workflow_control_failed",
                workflow_id=workflow_id,
                action=action,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "workflow_id": workflow_id,
                "action": action,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def resume_workflow_from_checkpoint(
        context: Context,
        project_id: str,
        checkpoint_file: str | None = None,
        continue_from_last: bool = True,
    ) -> dict[str, Any]:
        """Resume an interrupted workflow from saved checkpoint with full state restoration.

        Loads and resumes a previously interrupted sequential navigation workflow from
        checkpoint data, restoring all progress tracking, queue state, and configuration.
        Enables reliable recovery from system interruptions or manual workflow stops.

        Args:
            project_id: Project identifier containing the workflow checkpoints (required)
            checkpoint_file: Specific checkpoint file to resume from (optional)
            continue_from_last: Resume from the most recent checkpoint if no file specified (default: True)

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - workflow_id: Restored workflow identifier
            - project_id: Project identifier
            - resume_info: Details about the resumed workflow state
            - progress_summary: Current progress after restoration
            - remaining_pages: Information about pages still to be processed
            - checkpoint_details: Details about the loaded checkpoint

        Resume Features:
            - Complete State Restoration: All progress, timing, and configuration preserved
            - Intelligent Checkpoint Selection: Automatically finds most recent checkpoint
            - Queue State Recovery: Resumes from exact page where workflow was interrupted
            - Error State Handling: Properly handles failed pages and retry counts
            - Configuration Preservation: Maintains original analyzer settings

        Recovery Capabilities:
            - Handles partial page completions gracefully
            - Preserves timing estimates and performance metrics
            - Maintains error tracking and retry logic
            - Restores browser session management configuration
        """
        try:
            config = load_configuration()
            browser_service = BrowserAutomationService(config)
            project_store = create_project_store(config)

            # Get project metadata
            project_metadata = project_store.get_project_metadata(project_id)
            if not project_metadata:
                return {
                    "status": "error",
                    "project_id": project_id,
                    "error": f"Project {project_id} not found",
                    "error_type": "ProjectNotFoundError",
                }

            project_root = project_metadata.root_path
            checkpoint_dir = project_root / "workflow" / "checkpoints"

            if not checkpoint_dir.exists():
                return {
                    "status": "error",
                    "project_id": project_id,
                    "error": f"No checkpoints found for project {project_id}",
                    "error_type": "CheckpointNotFoundError",
                }

            # Find checkpoint file
            checkpoint_path = None

            if checkpoint_file:
                # Use specific checkpoint file
                checkpoint_path = checkpoint_dir / checkpoint_file
                if not checkpoint_path.exists():
                    return {
                        "status": "error",
                        "project_id": project_id,
                        "error": f"Checkpoint file {checkpoint_file} not found",
                        "error_type": "CheckpointFileNotFoundError",
                    }
            elif continue_from_last:
                # Find most recent checkpoint
                checkpoint_files = list(checkpoint_dir.glob("*.json"))
                if not checkpoint_files:
                    return {
                        "status": "error",
                        "project_id": project_id,
                        "error": "No checkpoint files found in project",
                        "error_type": "NoCheckpointsError",
                    }

                # Sort by modification time, newest first
                checkpoint_path = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

            if not checkpoint_path:
                return {
                    "status": "error",
                    "project_id": project_id,
                    "error": "No valid checkpoint file identified",
                    "error_type": "CheckpointSelectionError",
                }

            _logger.info(
                "workflow_resume_from_checkpoint",
                project_id=project_id,
                checkpoint_file=str(checkpoint_path),
            )

            # Load workflow from checkpoint
            workflow = await SequentialNavigationWorkflow.load_from_checkpoint(
                checkpoint_file=checkpoint_path,
                browser_service=browser_service,
                project_root=project_root,
            )

            # Add to active workflows registry
            _active_workflows[workflow.workflow_id] = workflow

            # Get progress summary
            progress_summary = workflow.get_progress_summary()

            # Analyze remaining work
            remaining_pages = [
                task for task in workflow.page_tasks
                if task.status.value in ["pending", "failed", "retrying"]
            ]

            failed_pages_recoverable = [
                task for task in workflow.page_tasks
                if task.status.value == "failed" and task.can_retry
            ]

            await context.info(f"Workflow resumed from checkpoint: {len(remaining_pages)} pages remaining")

            return {
                "status": "success",
                "workflow_id": workflow.workflow_id,
                "project_id": project_id,
                "resume_info": {
                    "checkpoint_file": checkpoint_path.name,
                    "workflow_status": workflow.status.value,
                    "resume_from_page_index": workflow.progress.current_page_index,
                    "resume_from_url": workflow.progress.current_page_url,
                },
                "progress_summary": progress_summary["progress"],
                "timing_metrics": progress_summary["timing"],
                "remaining_pages": {
                    "total_remaining": len(remaining_pages),
                    "failed_recoverable": len(failed_pages_recoverable),
                    "pages": [
                        {
                            "url": task.url,
                            "page_id": task.page_id,
                            "status": task.status.value,
                            "attempts": task.attempts,
                            "can_retry": task.can_retry,
                        }
                        for task in remaining_pages[:10]  # Limit for response size
                    ],
                },
                "checkpoint_details": {
                    "checkpoint_file": str(checkpoint_path),
                    "checkpoint_size": checkpoint_path.stat().st_size,
                    "checkpoint_modified": checkpoint_path.stat().st_mtime,
                },
            }

        except Exception as e:
            await context.error(f"Workflow resume failed: {e}")
            _logger.error(
                "workflow_resume_failed",
                project_id=project_id,
                checkpoint_file=checkpoint_file,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "project_id": project_id,
                "checkpoint_file": checkpoint_file,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def list_active_workflows(
        context: Context,
    ) -> dict[str, Any]:
        """List all currently active workflows with status and progress information.

        Provides an overview of all running, paused, or recently completed workflows
        in the system. Useful for monitoring multiple concurrent analysis operations
        and managing workflow resources.

        Returns:
            Dictionary containing:
            - status: "success"
            - active_workflows: List of workflow summaries
            - total_active: Count of active workflows
            - system_resources: Resource usage across all workflows

        Workflow Information:
            - workflow_id: Unique identifier
            - project_id: Associated project
            - status: Current workflow status
            - progress: Completion statistics
            - timing: Performance metrics
            - resource_usage: Browser sessions and memory
        """
        try:
            if not _active_workflows:
                return {
                    "status": "success",
                    "active_workflows": [],
                    "total_active": 0,
                    "message": "No active workflows found",
                }

            workflow_summaries = []
            total_pages = 0
            total_completed = 0
            total_sessions = 0

            for workflow_id, workflow in _active_workflows.items():
                progress_summary = workflow.get_progress_summary()

                workflow_summaries.append({
                    "workflow_id": workflow_id,
                    "project_id": workflow.project_id,
                    "status": workflow.status.value,
                    "progress": {
                        "total_pages": workflow.progress.total_pages,
                        "completed_pages": workflow.progress.completed_pages,
                        "completion_percentage": workflow.progress.completion_percentage,
                        "current_page_url": workflow.progress.current_page_url,
                    },
                    "timing": {
                        "workflow_duration": workflow.progress.workflow_duration,
                        "pages_per_minute": workflow.progress.pages_per_minute,
                        "estimated_completion": progress_summary["timing"]["estimated_completion_time"],
                    },
                    "resource_usage": {
                        "active_sessions": len(workflow._current_sessions),
                        "max_concurrent_sessions": workflow.max_concurrent_sessions,
                    },
                })

                total_pages += workflow.progress.total_pages
                total_completed += workflow.progress.completed_pages
                total_sessions += len(workflow._current_sessions)

            await context.info(f"Listed {len(_active_workflows)} active workflows")

            return {
                "status": "success",
                "active_workflows": workflow_summaries,
                "total_active": len(_active_workflows),
                "system_resources": {
                    "total_pages_across_workflows": total_pages,
                    "total_completed_across_workflows": total_completed,
                    "total_active_browser_sessions": total_sessions,
                    "workflows_running": len([w for w in _active_workflows.values() if w.status == QueueStatus.RUNNING]),
                    "workflows_paused": len([w for w in _active_workflows.values() if w.status == QueueStatus.PAUSED]),
                },
            }

        except Exception as e:
            await context.error(f"List active workflows failed: {e}")
            _logger.error(
                "list_active_workflows_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }


def _analyze_error_patterns(failed_pages: list[Any]) -> dict[str, Any]:
    """Analyze error patterns in failed pages."""
    if not failed_pages:
        return {
            "total_failed": 0,
            "error_categories": {},
            "most_common_errors": [],
            "retry_analysis": {},
        }

    error_messages = [task.error_message for task in failed_pages if task.error_message]
    error_categories = {}
    retry_counts = {}

    for task in failed_pages:
        # Categorize errors
        if task.error_message:
            if "timeout" in task.error_message.lower():
                error_categories["timeout"] = error_categories.get("timeout", 0) + 1
            elif "network" in task.error_message.lower():
                error_categories["network"] = error_categories.get("network", 0) + 1
            elif "404" in task.error_message or "not found" in task.error_message.lower():
                error_categories["not_found"] = error_categories.get("not_found", 0) + 1
            elif "403" in task.error_message or "forbidden" in task.error_message.lower():
                error_categories["access_denied"] = error_categories.get("access_denied", 0) + 1
            else:
                error_categories["other"] = error_categories.get("other", 0) + 1

        # Analyze retry patterns
        retry_key = f"{task.attempts}_attempts"
        retry_counts[retry_key] = retry_counts.get(retry_key, 0) + 1

    # Find most common error messages
    from collections import Counter
    error_counter = Counter(error_messages)
    most_common_errors = [
        {"error": error, "count": count}
        for error, count in error_counter.most_common(5)
    ]

    return {
        "total_failed": len(failed_pages),
        "error_categories": error_categories,
        "most_common_errors": most_common_errors,
        "retry_analysis": retry_counts,
    }


__all__ = ["register"]