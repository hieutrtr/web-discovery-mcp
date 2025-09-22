"""Artifact persistence and management for analysis resumption and debugging.

This module provides functionality to persist partial analysis results,
enable resumption after failures, and support comprehensive debugging.
"""

from __future__ import annotations

import json
import os
import shutil
import structlog
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from ..config.settings import MCPSettings

from pydantic import BaseModel, Field

from legacy_web_mcp.llm.models import (
    ContentSummary,
    FeatureAnalysis,
)
from legacy_web_mcp.browser.analysis import PageAnalysisData
from legacy_web_mcp.llm.quality import QualityMetrics, ValidationResult, AnalysisError

_logger = structlog.get_logger(__name__)


class AnalysisArtifact(BaseModel):
    """Represents a persistent analysis artifact for debugging and resumption."""

    artifact_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique artifact identifier")
    analysis_type: str = Field(description="Type of analysis (step1, step2, combined)")
    page_url: str = Field(description="URL of the analyzed page")
    timestamp: datetime = Field(default_factory=datetime.now, description="When artifact was created")

    # Analysis data
    page_analysis_data: Optional[Dict[str, Any]] = Field(default=None, description="Raw page analysis data")
    step1_result: Optional[Dict[str, Any]] = Field(default=None, description="Step 1 analysis result")
    step2_result: Optional[Dict[str, Any]] = Field(default=None, description="Step 2 analysis result")

    # Quality and validation data
    quality_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Quality assessment metrics")
    validation_result: Optional[Dict[str, Any]] = Field(default=None, description="Validation results")

    # LLM interaction data for debugging
    llm_requests: List[Dict[str, Any]] = Field(default_factory=list, description="LLM requests made")
    llm_responses: List[Dict[str, Any]] = Field(default_factory=list, description="LLM responses received")
    retry_history: List[Dict[str, Any]] = Field(default_factory=list, description="Retry attempt history")

    # Error information
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings generated")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    status: str = Field(default="in_progress", description="Artifact status (in_progress, completed, failed)")
    project_id: Optional[str] = Field(default=None, description="Project identifier")


class ArtifactManager:
    """Manages persistence and retrieval of analysis artifacts."""

    def __init__(self, artifacts_dir: str = "artifacts", settings: Optional["MCPSettings"] = None):
        """Initialize artifact manager.

        Args:
            artifacts_dir: Directory to store artifacts (relative to current working directory)
            settings: Optional MCPSettings instance for OUTPUT_ROOT-based configuration
        """
        from ..config.settings import load_settings

        # If settings provided, use OUTPUT_ROOT-based path, otherwise use provided artifacts_dir
        if settings is not None:
            self.artifacts_dir = settings.OUTPUT_ROOT / "artifacts"
        else:
            # Try to get global settings for OUTPUT_ROOT integration
            try:
                global_settings = load_settings()
                self.artifacts_dir = global_settings.OUTPUT_ROOT / "artifacts"
            except Exception:
                # Fallback to the old behavior if settings unavailable
                self.artifacts_dir = Path(artifacts_dir)
        
        self.artifacts_dir.mkdir(exist_ok=True, parents=True)

        # Create subdirectories for organization
        (self.artifacts_dir / "active").mkdir(exist_ok=True)
        (self.artifacts_dir / "completed").mkdir(exist_ok=True)
        (self.artifacts_dir / "failed").mkdir(exist_ok=True)
        (self.artifacts_dir / "debug").mkdir(exist_ok=True)

    def create_artifact(
        self,
        analysis_type: str,
        page_url: str,
        page_analysis_data: Optional[PageAnalysisData] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AnalysisArtifact:
        """Create a new analysis artifact.

        Args:
            analysis_type: Type of analysis being performed
            page_url: URL being analyzed
            page_analysis_data: Raw page analysis data
            project_id: Project identifier
            metadata: Additional metadata

        Returns:
            Created analysis artifact
        """
        artifact = AnalysisArtifact(
            analysis_type=analysis_type,
            page_url=page_url,
            project_id=project_id,
            metadata=metadata or {}
        )

        if page_analysis_data:
            # Convert to dict for serialization, handling datetime objects
            artifact.page_analysis_data = self._serialize_analysis_data(page_analysis_data)

        # Persist artifact
        self._save_artifact(artifact)

        _logger.info(
            "analysis_artifact_created",
            artifact_id=artifact.artifact_id,
            analysis_type=analysis_type,
            page_url=page_url
        )

        return artifact

    def update_artifact(
        self,
        artifact: AnalysisArtifact,
        **updates
    ) -> AnalysisArtifact:
        """Update an existing artifact with new data.

        Args:
            artifact: Artifact to update
            **updates: Fields to update

        Returns:
            Updated artifact
        """
        # Update fields
        for field, value in updates.items():
            if hasattr(artifact, field):
                setattr(artifact, field, value)

        # Update timestamp
        artifact.timestamp = datetime.now()

        # Persist updated artifact
        self._save_artifact(artifact)

        _logger.debug(
            "analysis_artifact_updated",
            artifact_id=artifact.artifact_id,
            updated_fields=list(updates.keys())
        )

        return artifact

    def add_llm_interaction(
        self,
        artifact: AnalysisArtifact,
        request: Dict[str, Any],
        response: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        error: Optional[str] = None
    ) -> AnalysisArtifact:
        """Add LLM interaction data to artifact for debugging.

        Args:
            artifact: Artifact to update
            request: LLM request data
            response: LLM response data (if successful)
            retry_count: Current retry attempt number
            error: Error message (if failed)

        Returns:
            Updated artifact
        """
        # Add request
        request_record = {
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            "request": self._sanitize_for_storage(request)
        }
        artifact.llm_requests.append(request_record)

        # Add response if available
        if response:
            response_record = {
                "timestamp": datetime.now().isoformat(),
                "retry_count": retry_count,
                "response": self._sanitize_for_storage(response)
            }
            artifact.llm_responses.append(response_record)

        # Add retry history
        retry_record = {
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            "success": response is not None,
            "error": error
        }
        artifact.retry_history.append(retry_record)

        # Persist updated artifact
        self._save_artifact(artifact)

        return artifact

    def add_analysis_result(
        self,
        artifact: AnalysisArtifact,
        result: Union[ContentSummary, FeatureAnalysis],
        quality_metrics: Optional[QualityMetrics] = None,
        validation_result: Optional[ValidationResult] = None
    ) -> AnalysisArtifact:
        """Add analysis result to artifact.

        Args:
            artifact: Artifact to update
            result: Analysis result (Step 1 or Step 2)
            quality_metrics: Quality assessment metrics
            validation_result: Validation results

        Returns:
            Updated artifact
        """
        result_data = self._serialize_analysis_data(result)

        if isinstance(result, ContentSummary):
            artifact.step1_result = result_data
        elif isinstance(result, FeatureAnalysis):
            artifact.step2_result = result_data

        if quality_metrics:
            artifact.quality_metrics = quality_metrics.model_dump()

        if validation_result:
            artifact.validation_result = validation_result.model_dump()

        # Persist updated artifact
        self._save_artifact(artifact)

        _logger.info(
            "analysis_result_added_to_artifact",
            artifact_id=artifact.artifact_id,
            result_type=type(result).__name__,
            quality_score=quality_metrics.overall_quality_score if quality_metrics else None
        )

        return artifact

    def add_error(
        self,
        artifact: AnalysisArtifact,
        error: Union[AnalysisError, Exception, str],
        context: Optional[Dict[str, Any]] = None
    ) -> AnalysisArtifact:
        """Add error information to artifact.

        Args:
            artifact: Artifact to update
            error: Error that occurred
            context: Additional error context

        Returns:
            Updated artifact
        """
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__ if isinstance(error, Exception) else "string",
            "error_message": str(error),
            "context": context or {}
        }

        if isinstance(error, AnalysisError):
            error_record.update({
                "error_code": error.error_code.value,
                "category": error.category,
                "severity": error.severity,
                "recoverable": error.recoverable
            })

        artifact.errors.append(error_record)

        # Persist updated artifact
        self._save_artifact(artifact)

        _logger.warning(
            "error_added_to_artifact",
            artifact_id=artifact.artifact_id,
            error_type=error_record["error_type"],
            error_message=error_record["error_message"]
        )

        return artifact

    def complete_artifact(
        self,
        artifact: AnalysisArtifact,
        status: str = "completed"
    ) -> AnalysisArtifact:
        """Mark artifact as completed and move to appropriate directory.

        Args:
            artifact: Artifact to complete
            status: Final status (completed, failed)

        Returns:
            Updated artifact
        """
        artifact.status = status
        artifact.timestamp = datetime.now()

        # Move artifact to appropriate directory
        source_path = self.artifacts_dir / "active" / f"{artifact.artifact_id}.json"
        if status == "completed":
            target_path = self.artifacts_dir / "completed" / f"{artifact.artifact_id}.json"
        else:
            target_path = self.artifacts_dir / "failed" / f"{artifact.artifact_id}.json"

        # Save to new location
        self._save_artifact_to_path(artifact, target_path)

        # Remove from active directory
        if source_path.exists():
            source_path.unlink()

        _logger.info(
            "analysis_artifact_completed",
            artifact_id=artifact.artifact_id,
            status=status,
            final_location=str(target_path)
        )

        return artifact

    def get_artifact(self, artifact_id: str) -> Optional[AnalysisArtifact]:
        """Retrieve an artifact by ID.

        Args:
            artifact_id: Artifact identifier

        Returns:
            Artifact if found, None otherwise
        """
        # Search in all directories
        for subdir in ["active", "completed", "failed"]:
            artifact_path = self.artifacts_dir / subdir / f"{artifact_id}.json"
            if artifact_path.exists():
                try:
                    with open(artifact_path, 'r') as f:
                        data = json.load(f)
                    return AnalysisArtifact(**data)
                except Exception as e:
                    _logger.error(
                        "artifact_load_failed",
                        artifact_id=artifact_id,
                        path=str(artifact_path),
                        error=str(e)
                    )

        return None

    def list_artifacts(
        self,
        status: Optional[str] = None,
        analysis_type: Optional[str] = None,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[AnalysisArtifact]:
        """List artifacts matching criteria.

        Args:
            status: Filter by status (active, completed, failed)
            analysis_type: Filter by analysis type
            project_id: Filter by project ID
            since: Filter by creation date

        Returns:
            List of matching artifacts
        """
        artifacts = []

        # Determine directories to search
        if status:
            search_dirs = [status]
        else:
            search_dirs = ["active", "completed", "failed"]

        for subdir in search_dirs:
            dir_path = self.artifacts_dir / subdir
            if not dir_path.exists():
                continue

            for artifact_file in dir_path.glob("*.json"):
                try:
                    with open(artifact_file, 'r') as f:
                        data = json.load(f)

                    artifact = AnalysisArtifact(**data)

                    # Apply filters
                    if analysis_type and artifact.analysis_type != analysis_type:
                        continue
                    if project_id and artifact.project_id != project_id:
                        continue
                    if since and artifact.timestamp < since:
                        continue

                    artifacts.append(artifact)

                except Exception as e:
                    _logger.warning(
                        "artifact_list_load_failed",
                        file_path=str(artifact_file),
                        error=str(e)
                    )

        # Sort by timestamp (most recent first)
        artifacts.sort(key=lambda x: x.timestamp, reverse=True)
        return artifacts

    def cleanup_old_artifacts(self, older_than_days: int = 30) -> int:
        """Clean up old artifacts to manage storage.

        Args:
            older_than_days: Delete artifacts older than this many days

        Returns:
            Number of artifacts deleted
        """
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        deleted_count = 0

        # Only clean up completed and failed artifacts, preserve active ones
        for subdir in ["completed", "failed"]:
            dir_path = self.artifacts_dir / subdir
            if not dir_path.exists():
                continue

            for artifact_file in dir_path.glob("*.json"):
                try:
                    with open(artifact_file, 'r') as f:
                        data = json.load(f)

                    artifact_date = datetime.fromisoformat(data.get('timestamp', ''))
                    if artifact_date < cutoff_date:
                        artifact_file.unlink()
                        deleted_count += 1

                except Exception as e:
                    _logger.warning(
                        "artifact_cleanup_failed",
                        file_path=str(artifact_file),
                        error=str(e)
                    )

        _logger.info(
            "artifacts_cleanup_completed",
            deleted_count=deleted_count,
            cutoff_date=cutoff_date.isoformat()
        )

        return deleted_count

    def create_debug_export(
        self,
        artifact_ids: List[str],
        export_path: Optional[str] = None
    ) -> str:
        """Create a debug export containing specified artifacts.

        Args:
            artifact_ids: List of artifact IDs to export
            export_path: Path for export file (default: timestamped)

        Returns:
            Path to created export file
        """
        if not export_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"debug_export_{timestamp}.json"

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "artifact_count": len(artifact_ids),
            "artifacts": []
        }

        for artifact_id in artifact_ids:
            artifact = self.get_artifact(artifact_id)
            if artifact:
                export_data["artifacts"].append(artifact.model_dump())
            else:
                _logger.warning("artifact_not_found_for_export", artifact_id=artifact_id)

        # Save export file
        export_file_path = self.artifacts_dir / "debug" / export_path
        with open(export_file_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        _logger.info(
            "debug_export_created",
            export_path=str(export_file_path),
            artifact_count=len(export_data["artifacts"])
        )

        return str(export_file_path)

    def _save_artifact(self, artifact: AnalysisArtifact) -> None:
        """Save artifact to active directory."""
        artifact_path = self.artifacts_dir / "active" / f"{artifact.artifact_id}.json"
        self._save_artifact_to_path(artifact, artifact_path)

    def _save_artifact_to_path(self, artifact: AnalysisArtifact, path: Path) -> None:
        """Save artifact to specific path."""
        try:
            with open(path, 'w') as f:
                json.dump(artifact.model_dump(), f, indent=2, default=str)
        except Exception as e:
            _logger.error(
                "artifact_save_failed",
                artifact_id=artifact.artifact_id,
                path=str(path),
                error=str(e)
            )
            raise

    def _serialize_analysis_data(self, data: Any) -> Dict[str, Any]:
        """Serialize analysis data for storage, handling special types."""
        if hasattr(data, 'model_dump'):
            return data.model_dump()
        elif hasattr(data, '__dict__'):
            return self._sanitize_for_storage(data.__dict__)
        else:
            return self._sanitize_for_storage(data)

    def _sanitize_for_storage(self, data: Any) -> Any:
        """Sanitize data for JSON storage."""
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {k: self._sanitize_for_storage(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_storage(item) for item in data]
        elif hasattr(data, 'model_dump'):
            return data.model_dump()
        else:
            try:
                json.dumps(data)  # Test if serializable
                return data
            except TypeError:
                return str(data)  # Convert non-serializable to string