"""MCP tools for LLM analysis debugging and quality monitoring.

This module exposes debugging capabilities as MCP tools for inspecting
analysis quality, troubleshooting issues, and monitoring performance.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastmcp import Context, FastMCP

from legacy_web_mcp.llm.artifacts import ArtifactManager
from legacy_web_mcp.llm.debugging import DebugInspector
from legacy_web_mcp.llm.quality import ResponseValidator, QualityAnalyzer

_logger = structlog.get_logger(__name__)

# Global instances for debugging
_artifact_manager: Optional[ArtifactManager] = None
_debug_inspector: Optional[DebugInspector] = None
_response_validator: Optional[ResponseValidator] = None
_quality_analyzer: Optional[QualityAnalyzer] = None


def _get_artifact_manager() -> ArtifactManager:
    """Get or create global artifact manager."""
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactManager()
    return _artifact_manager


def _get_debug_inspector() -> DebugInspector:
    """Get or create global debug inspector."""
    global _debug_inspector
    if _debug_inspector is None:
        _debug_inspector = DebugInspector(_get_artifact_manager())
    return _debug_inspector


def _get_response_validator() -> ResponseValidator:
    """Get or create global response validator."""
    global _response_validator
    if _response_validator is None:
        _response_validator = ResponseValidator()
    return _response_validator


def _get_quality_analyzer() -> QualityAnalyzer:
    """Get or create global quality analyzer."""
    global _quality_analyzer
    if _quality_analyzer is None:
        _quality_analyzer = QualityAnalyzer()
    return _quality_analyzer


async def list_analysis_artifacts(
    context: Context,
    status: Optional[str] = None,
    analysis_type: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """List analysis artifacts for debugging and review.

    Args:
        status: Filter by status (active, completed, failed)
        analysis_type: Filter by analysis type (step1, step2, combined)
        project_id: Filter by project ID
        limit: Maximum number of artifacts to return

    Returns:
        List of matching artifacts with metadata
    """
    try:
        artifact_manager = _get_artifact_manager()

        # Get artifacts since last week by default
        since = datetime.now() - timedelta(days=7)

        artifacts = artifact_manager.list_artifacts(
            status=status,
            analysis_type=analysis_type,
            project_id=project_id,
            since=since
        )

        # Limit results
        artifacts = artifacts[:limit]

        # Convert to summary format
        artifact_summaries = []
        for artifact in artifacts:
            summary = {
                "artifact_id": artifact.artifact_id,
                "analysis_type": artifact.analysis_type,
                "page_url": artifact.page_url,
                "status": artifact.status,
                "timestamp": artifact.timestamp.isoformat(),
                "has_step1_result": artifact.step1_result is not None,
                "has_step2_result": artifact.step2_result is not None,
                "error_count": len(artifact.errors),
                "warning_count": len(artifact.warnings),
                "retry_count": len(artifact.retry_history),
                "project_id": artifact.project_id
            }

            # Add quality summary if available
            if artifact.quality_metrics:
                quality_data = artifact.quality_metrics
                summary["quality_summary"] = {
                    "overall_score": quality_data.get("overall_quality_score", 0.0),
                    "needs_manual_review": quality_data.get("needs_manual_review", False),
                    "completeness_score": quality_data.get("completeness_score", 0.0)
                }

            artifact_summaries.append(summary)

        await context.info(f"Retrieved {len(artifact_summaries)} artifacts")

        return {
            "status": "success",
            "artifacts": artifact_summaries,
            "total_count": len(artifact_summaries),
            "filters_applied": {
                "status": status,
                "analysis_type": analysis_type,
                "project_id": project_id,
                "limit": limit
            }
        }

    except Exception as e:
        await context.error(f"Failed to list artifacts: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def get_analysis_artifact(
    context: Context,
    artifact_id: str,
    include_raw_data: bool = False
) -> Dict[str, Any]:
    """Get detailed information about a specific analysis artifact.

    Args:
        artifact_id: Unique artifact identifier
        include_raw_data: Whether to include raw LLM request/response data

    Returns:
        Detailed artifact information for debugging
    """
    try:
        artifact_manager = _get_artifact_manager()
        artifact = artifact_manager.get_artifact(artifact_id)

        if not artifact:
            await context.error(f"Artifact {artifact_id} not found")
            return {
                "status": "error",
                "error": f"Artifact {artifact_id} not found"
            }

        # Build comprehensive artifact details
        artifact_details = {
            "artifact_id": artifact.artifact_id,
            "analysis_type": artifact.analysis_type,
            "page_url": artifact.page_url,
            "status": artifact.status,
            "timestamp": artifact.timestamp.isoformat(),
            "project_id": artifact.project_id,
            "metadata": artifact.metadata
        }

        # Add analysis results summary
        if artifact.step1_result:
            step1_summary = {
                "confidence_score": artifact.step1_result.get("confidence_score", 0.0),
                "purpose": artifact.step1_result.get("purpose", ""),
                "business_importance": artifact.step1_result.get("business_importance", 0.0),
                "field_count": len(artifact.step1_result.keys())
            }
            artifact_details["step1_summary"] = step1_summary

        if artifact.step2_result:
            step2_data = artifact.step2_result
            step2_summary = {
                "confidence_score": step2_data.get("confidence_score", 0.0),
                "quality_score": step2_data.get("quality_score", 0.0),
                "interactive_elements_count": len(step2_data.get("interactive_elements", [])),
                "functional_capabilities_count": len(step2_data.get("functional_capabilities", [])),
                "api_integrations_count": len(step2_data.get("api_integrations", [])),
                "business_rules_count": len(step2_data.get("business_rules", []))
            }
            artifact_details["step2_summary"] = step2_summary

        # Add quality metrics summary
        if artifact.quality_metrics:
            artifact_details["quality_metrics"] = artifact.quality_metrics

        # Add validation results
        if artifact.validation_result:
            artifact_details["validation_result"] = artifact.validation_result

        # Add error and retry information
        artifact_details["errors"] = artifact.errors
        artifact_details["warnings"] = artifact.warnings
        artifact_details["retry_history"] = artifact.retry_history

        # Optionally include raw LLM data
        if include_raw_data:
            artifact_details["llm_requests"] = artifact.llm_requests
            artifact_details["llm_responses"] = artifact.llm_responses
        else:
            artifact_details["llm_interaction_count"] = {
                "requests": len(artifact.llm_requests),
                "responses": len(artifact.llm_responses)
            }

        await context.info(f"Retrieved artifact {artifact_id}")

        return {
            "status": "success",
            "artifact": artifact_details
        }

    except Exception as e:
        await context.error(f"Failed to get artifact: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def validate_analysis_response(
    context: Context,
    analysis_type: str,
    response_data: str,
    calculate_quality: bool = True
) -> Dict[str, Any]:
    """Validate an analysis response and calculate quality metrics.

    Args:
        analysis_type: Type of analysis (step1 or step2)
        response_data: JSON response data to validate
        calculate_quality: Whether to calculate quality metrics

    Returns:
        Validation results and quality assessment
    """
    try:
        # Parse JSON response
        try:
            response_json = json.loads(response_data)
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"Invalid JSON: {str(e)}",
                "error_type": "json_parse_error"
            }

        # Validate response
        validator = _get_response_validator()

        if analysis_type == "step1":
            validation_result = validator.validate_step1_response(response_json)
        elif analysis_type == "step2":
            validation_result = validator.validate_step2_response(response_json)
        else:
            return {
                "status": "error",
                "error": f"Unknown analysis type: {analysis_type}"
            }

        result = {
            "status": "success",
            "validation": {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "error_code": validation_result.error_code.value if validation_result.error_code else None,
                "completeness_score": validation_result.completeness_score,
                "confidence_score": validation_result.confidence_score,
                "metadata": validation_result.metadata
            }
        }

        # Calculate quality metrics if requested
        if calculate_quality:
            quality_analyzer = _get_quality_analyzer()
            quality_metrics = quality_analyzer.calculate_quality_metrics(
                analysis_data=response_json,
                analysis_type=analysis_type
            )

            result["quality_metrics"] = {
                "overall_quality_score": quality_metrics.overall_quality_score,
                "completeness_score": quality_metrics.completeness_score,
                "specificity_score": quality_metrics.specificity_score,
                "technical_depth_score": quality_metrics.technical_depth_score,
                "llm_confidence_score": quality_metrics.llm_confidence_score,
                "needs_manual_review": quality_metrics.needs_manual_review,
                "review_reasons": quality_metrics.review_reasons,
                "quality_issues": quality_metrics.quality_issues,
                "field_completeness": quality_metrics.field_completeness,
                "detail_scores": quality_metrics.detail_scores
            }

        await context.info(f"Validated {analysis_type} response")

        return result

    except Exception as e:
        await context.error(f"Failed to validate response: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def start_debug_session(
    context: Context,
    page_url: str,
    analysis_type: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Start a new debugging session for analysis monitoring.

    Args:
        page_url: URL being analyzed
        analysis_type: Type of analysis (step1, step2, combined)
        session_id: Optional custom session ID

    Returns:
        Debug session information
    """
    try:
        debug_inspector = _get_debug_inspector()

        session = debug_inspector.start_debug_session(
            page_url=page_url,
            analysis_type=analysis_type,
            session_id=session_id
        )

        await context.info(f"Started debug session {session.session_id}")

        return {
            "status": "success",
            "session": {
                "session_id": session.session_id,
                "page_url": session.page_url,
                "analysis_type": session.analysis_type,
                "created_at": session.created_at.isoformat()
            }
        }

    except Exception as e:
        await context.error(f"Failed to start debug session: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def get_debug_session_report(
    context: Context,
    session_id: str,
    include_raw_data: bool = False
) -> Dict[str, Any]:
    """Get comprehensive debug report for a session.

    Args:
        session_id: Debug session ID
        include_raw_data: Whether to include raw LLM interaction data

    Returns:
        Comprehensive debug report
    """
    try:
        debug_inspector = _get_debug_inspector()

        if session_id not in debug_inspector.active_sessions:
            return {
                "status": "error",
                "error": f"Debug session {session_id} not found or closed"
            }

        # Generate comprehensive report
        report = debug_inspector.generate_debug_report(session_id)

        # Optionally exclude raw data for performance
        if not include_raw_data:
            if "raw_data" in report:
                del report["raw_data"]

        await context.info(f"Generated debug report for session {session_id}")

        return {
            "status": "success",
            "report": report
        }

    except Exception as e:
        await context.error(f"Failed to generate debug report: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def close_debug_session(
    context: Context,
    session_id: str
) -> Dict[str, Any]:
    """Close a debug session and persist results.

    Args:
        session_id: Debug session ID

    Returns:
        Session closure confirmation
    """
    try:
        debug_inspector = _get_debug_inspector()

        session = debug_inspector.close_session(session_id)

        if not session:
            return {
                "status": "error",
                "error": f"Debug session {session_id} not found"
            }

        await context.info(f"Closed debug session {session_id}")

        return {
            "status": "success",
            "session_id": session_id,
            "session_duration": (datetime.now() - session.created_at).total_seconds(),
            "total_prompts": len(session.prompts),
            "total_responses": len(session.responses),
            "quality_assessments": len(session.quality_assessments)
        }

    except Exception as e:
        await context.error(f"Failed to close debug session: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def cleanup_old_artifacts(
    context: Context,
    older_than_days: int = 30,
    dry_run: bool = True
) -> Dict[str, Any]:
    """Clean up old analysis artifacts to manage storage.

    Args:
        older_than_days: Delete artifacts older than this many days
        dry_run: If True, only count artifacts without deleting

    Returns:
        Cleanup results
    """
    try:
        artifact_manager = _get_artifact_manager()

        if dry_run:
            # Count artifacts that would be deleted
            cutoff_date = datetime.now() - timedelta(days=older_than_days)
            all_artifacts = artifact_manager.list_artifacts()
            old_artifacts = [
                a for a in all_artifacts
                if a.timestamp < cutoff_date and a.status in ["completed", "failed"]
            ]

            await context.info(f"Dry run: would delete {len(old_artifacts)} artifacts")

            return {
                "status": "success",
                "dry_run": True,
                "artifacts_to_delete": len(old_artifacts),
                "cutoff_date": cutoff_date.isoformat()
            }
        else:
            # Actually delete old artifacts
            deleted_count = artifact_manager.cleanup_old_artifacts(older_than_days)

            await context.info(f"Deleted {deleted_count} old artifacts")

            return {
                "status": "success",
                "dry_run": False,
                "deleted_count": deleted_count,
                "older_than_days": older_than_days
            }

    except Exception as e:
        await context.error(f"Failed to cleanup artifacts: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def create_debug_export(
    context: Context,
    artifact_ids: List[str],
    export_name: Optional[str] = None
) -> Dict[str, Any]:
    """Create a debug export containing specified artifacts.

    Args:
        artifact_ids: List of artifact IDs to export
        export_name: Optional name for export file

    Returns:
        Export creation results
    """
    try:
        artifact_manager = _get_artifact_manager()

        export_path = artifact_manager.create_debug_export(
            artifact_ids=artifact_ids,
            export_path=export_name
        )

        await context.info(f"Created debug export at {export_path}")

        return {
            "status": "success",
            "export_path": export_path,
            "artifact_count": len(artifact_ids)
        }

    except Exception as e:
        await context.error(f"Failed to create debug export: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def register(mcp: FastMCP) -> None:
    """Register debugging tools with FastMCP server.

    Args:
        mcp: FastMCP server instance
    """
    mcp.tool()(list_analysis_artifacts)
    mcp.tool()(get_analysis_artifact)
    mcp.tool()(validate_analysis_response)
    mcp.tool()(start_debug_session)
    mcp.tool()(get_debug_session_report)
    mcp.tool()(close_debug_session)
    mcp.tool()(cleanup_old_artifacts)
    mcp.tool()(create_debug_export)

    _logger.info("Debugging tools registered with MCP server")