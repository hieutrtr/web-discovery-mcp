"""Debugging tools and interfaces for LLM analysis.

This module provides comprehensive debugging capabilities including
prompt inspection, response analysis, and decision rationale tracking.
"""

from __future__ import annotations

import json
import structlog
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from legacy_web_mcp.llm.models import LLMRequest, LLMResponse, ContentSummary, FeatureAnalysis
from legacy_web_mcp.llm.quality import QualityMetrics, ValidationResult
from legacy_web_mcp.llm.artifacts import AnalysisArtifact, ArtifactManager

_logger = structlog.get_logger(__name__)


class DebugSession(BaseModel):
    """Represents a debugging session for analysis inspection."""

    session_id: str = Field(description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    page_url: str = Field(description="URL being debugged")
    analysis_type: str = Field(description="Type of analysis being debugged")

    # Debug data
    prompts: List[Dict[str, Any]] = Field(default_factory=list, description="Prompts used")
    responses: List[Dict[str, Any]] = Field(default_factory=list, description="LLM responses")
    quality_assessments: List[Dict[str, Any]] = Field(default_factory=list, description="Quality evaluations")
    validation_results: List[Dict[str, Any]] = Field(default_factory=list, description="Validation outcomes")
    retry_decisions: List[Dict[str, Any]] = Field(default_factory=list, description="Retry decision rationale")

    # Analysis insights
    improvement_suggestions: List[str] = Field(default_factory=list, description="Suggested improvements")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance measurements")


class DebugInspector:
    """Inspector for detailed analysis debugging and troubleshooting."""

    def __init__(self, artifact_manager: Optional[ArtifactManager] = None):
        """Initialize debug inspector.

        Args:
            artifact_manager: Optional artifact manager for persistent debugging
        """
        self.artifact_manager = artifact_manager or ArtifactManager()
        self.active_sessions: Dict[str, DebugSession] = {}

    def start_debug_session(
        self,
        page_url: str,
        analysis_type: str,
        session_id: Optional[str] = None
    ) -> DebugSession:
        """Start a new debugging session.

        Args:
            page_url: URL being analyzed
            analysis_type: Type of analysis (step1, step2, combined)
            session_id: Optional custom session ID

        Returns:
            Created debug session
        """
        if not session_id:
            from uuid import uuid4
            session_id = str(uuid4())

        session = DebugSession(
            session_id=session_id,
            page_url=page_url,
            analysis_type=analysis_type
        )

        self.active_sessions[session_id] = session

        _logger.info(
            "debug_session_started",
            session_id=session_id,
            page_url=page_url,
            analysis_type=analysis_type
        )

        return session

    def log_prompt_details(
        self,
        session_id: str,
        request: LLMRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log detailed prompt information for debugging.

        Args:
            session_id: Debug session ID
            request: LLM request being made
            context: Additional context information
        """
        if session_id not in self.active_sessions:
            _logger.warning("debug_session_not_found", session_id=session_id)
            return

        session = self.active_sessions[session_id]

        prompt_info = {
            "timestamp": datetime.now().isoformat(),
            "request_type": request.request_type.value if request.request_type else "unknown",
            "model": request.model,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "message_count": len(request.messages),
            "total_prompt_length": sum(len(msg.content) for msg in request.messages),
            "context": context or {},
            "messages": [
                {
                    "role": msg.role.value,
                    "content_length": len(msg.content),
                    "content_preview": msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                }
                for msg in request.messages
            ]
        }

        session.prompts.append(prompt_info)

    def log_response_details(
        self,
        session_id: str,
        response: LLMResponse,
        processing_time: Optional[float] = None,
        retry_count: int = 0
    ) -> None:
        """Log detailed response information for debugging.

        Args:
            session_id: Debug session ID
            response: LLM response received
            processing_time: Time taken to process request
            retry_count: Current retry attempt number
        """
        if session_id not in self.active_sessions:
            _logger.warning("debug_session_not_found", session_id=session_id)
            return

        session = self.active_sessions[session_id]

        response_info = {
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            "processing_time": processing_time,
            "provider": response.provider.value if hasattr(response, 'provider') else "unknown",
            "model": response.model,
            "content_length": len(response.content) if response.content else 0,
            "content_preview": response.content[:300] + "..." if response.content and len(response.content) > 300 else response.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0
            },
            "cost_estimate": response.cost_estimate,
            "is_valid_json": self._check_json_validity(response.content)
        }

        session.responses.append(response_info)

    def log_quality_assessment(
        self,
        session_id: str,
        quality_metrics: QualityMetrics,
        validation_result: ValidationResult,
        decision_rationale: Optional[str] = None
    ) -> None:
        """Log quality assessment details for debugging.

        Args:
            session_id: Debug session ID
            quality_metrics: Quality assessment metrics
            validation_result: Validation results
            decision_rationale: Rationale for quality decisions
        """
        if session_id not in self.active_sessions:
            _logger.warning("debug_session_not_found", session_id=session_id)
            return

        session = self.active_sessions[session_id]

        assessment_info = {
            "timestamp": datetime.now().isoformat(),
            "quality_score": quality_metrics.overall_quality_score,
            "completeness_score": quality_metrics.completeness_score,
            "specificity_score": quality_metrics.specificity_score,
            "technical_depth_score": quality_metrics.technical_depth_score,
            "llm_confidence_score": quality_metrics.llm_confidence_score,
            "needs_manual_review": quality_metrics.needs_manual_review,
            "review_reasons": quality_metrics.review_reasons,
            "quality_issues": quality_metrics.quality_issues,
            "validation_passed": validation_result.is_valid,
            "validation_errors": validation_result.errors,
            "validation_warnings": validation_result.warnings,
            "decision_rationale": decision_rationale,
            "field_completeness": quality_metrics.field_completeness,
            "detail_scores": quality_metrics.detail_scores
        }

        session.quality_assessments.append(assessment_info)

        # Update session-level quality issues
        session.quality_issues.extend(quality_metrics.quality_issues)

    def log_retry_decision(
        self,
        session_id: str,
        retry_count: int,
        reason: str,
        quality_score: float,
        threshold: float,
        decision: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log retry decision rationale for debugging.

        Args:
            session_id: Debug session ID
            retry_count: Current retry attempt
            reason: Reason for retry
            quality_score: Current quality score
            threshold: Quality threshold required
            decision: Decision made (retry, accept, fail)
            context: Additional decision context
        """
        if session_id not in self.active_sessions:
            _logger.warning("debug_session_not_found", session_id=session_id)
            return

        session = self.active_sessions[session_id]

        retry_info = {
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            "reason": reason,
            "quality_score": quality_score,
            "threshold": threshold,
            "decision": decision,
            "gap": threshold - quality_score,
            "context": context or {}
        }

        session.retry_decisions.append(retry_info)

    def analyze_session_patterns(self, session_id: str) -> Dict[str, Any]:
        """Analyze patterns in a debug session to identify improvement opportunities.

        Args:
            session_id: Debug session ID

        Returns:
            Analysis insights and recommendations
        """
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}

        session = self.active_sessions[session_id]

        analysis = {
            "session_summary": {
                "total_prompts": len(session.prompts),
                "total_responses": len(session.responses),
                "total_retries": len(session.retry_decisions),
                "session_duration": (datetime.now() - session.created_at).total_seconds()
            },
            "quality_trends": self._analyze_quality_trends(session),
            "prompt_analysis": self._analyze_prompt_patterns(session),
            "response_analysis": self._analyze_response_patterns(session),
            "improvement_recommendations": self._generate_improvement_recommendations(session)
        }

        return analysis

    def generate_debug_report(self, session_id: str) -> Dict[str, Any]:
        """Generate comprehensive debug report for a session.

        Args:
            session_id: Debug session ID

        Returns:
            Comprehensive debug report
        """
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}

        session = self.active_sessions[session_id]
        pattern_analysis = self.analyze_session_patterns(session_id)

        report = {
            "session_info": {
                "session_id": session_id,
                "page_url": session.page_url,
                "analysis_type": session.analysis_type,
                "created_at": session.created_at.isoformat(),
                "report_generated_at": datetime.now().isoformat()
            },
            "execution_timeline": self._build_execution_timeline(session),
            "quality_assessment_summary": self._summarize_quality_assessments(session),
            "retry_analysis": self._analyze_retry_patterns(session),
            "prompt_effectiveness": self._analyze_prompt_effectiveness(session),
            "response_quality_evolution": self._analyze_response_quality_evolution(session),
            "improvement_opportunities": pattern_analysis["improvement_recommendations"],
            "raw_data": {
                "prompts": session.prompts,
                "responses": session.responses,
                "quality_assessments": session.quality_assessments,
                "retry_decisions": session.retry_decisions
            }
        }

        return report

    def close_session(self, session_id: str) -> Optional[DebugSession]:
        """Close a debug session and optionally persist to artifacts.

        Args:
            session_id: Debug session ID

        Returns:
            Closed session if found
        """
        if session_id not in self.active_sessions:
            return None

        session = self.active_sessions.pop(session_id)

        # Optionally persist session as artifact for long-term debugging
        if self.artifact_manager:
            try:
                # Create artifact from debug session
                artifact = self.artifact_manager.create_artifact(
                    analysis_type=f"debug_{session.analysis_type}",
                    page_url=session.page_url,
                    metadata={
                        "debug_session": session.model_dump(),
                        "session_type": "debugging"
                    }
                )

                self.artifact_manager.complete_artifact(artifact, status="completed")

                _logger.info(
                    "debug_session_persisted",
                    session_id=session_id,
                    artifact_id=artifact.artifact_id
                )

            except Exception as e:
                _logger.error(
                    "debug_session_persistence_failed",
                    session_id=session_id,
                    error=str(e)
                )

        _logger.info("debug_session_closed", session_id=session_id)
        return session

    def _check_json_validity(self, content: Optional[str]) -> bool:
        """Check if content is valid JSON."""
        if not content:
            return False

        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False

    def _analyze_quality_trends(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze quality score trends over time."""
        quality_scores = [
            assessment["quality_score"]
            for assessment in session.quality_assessments
        ]

        if not quality_scores:
            return {"no_data": True}

        return {
            "initial_score": quality_scores[0],
            "final_score": quality_scores[-1],
            "improvement": quality_scores[-1] - quality_scores[0],
            "max_score": max(quality_scores),
            "min_score": min(quality_scores),
            "average_score": sum(quality_scores) / len(quality_scores),
            "trend": "improving" if quality_scores[-1] > quality_scores[0] else "declining"
        }

    def _analyze_prompt_patterns(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze prompt patterns and characteristics."""
        if not session.prompts:
            return {"no_data": True}

        total_lengths = [prompt["total_prompt_length"] for prompt in session.prompts]
        message_counts = [prompt["message_count"] for prompt in session.prompts]

        return {
            "total_prompts": len(session.prompts),
            "average_length": sum(total_lengths) / len(total_lengths),
            "max_length": max(total_lengths),
            "min_length": min(total_lengths),
            "average_messages": sum(message_counts) / len(message_counts),
            "length_variation": max(total_lengths) - min(total_lengths)
        }

    def _analyze_response_patterns(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze response patterns and characteristics."""
        if not session.responses:
            return {"no_data": True}

        valid_json_count = sum(1 for resp in session.responses if resp["is_valid_json"])
        content_lengths = [resp["content_length"] for resp in session.responses]
        processing_times = [resp["processing_time"] for resp in session.responses if resp["processing_time"]]

        analysis = {
            "total_responses": len(session.responses),
            "valid_json_rate": valid_json_count / len(session.responses),
            "average_content_length": sum(content_lengths) / len(content_lengths),
            "max_content_length": max(content_lengths),
            "min_content_length": min(content_lengths)
        }

        if processing_times:
            analysis.update({
                "average_processing_time": sum(processing_times) / len(processing_times),
                "max_processing_time": max(processing_times),
                "min_processing_time": min(processing_times)
            })

        return analysis

    def _generate_improvement_recommendations(self, session: DebugSession) -> List[str]:
        """Generate improvement recommendations based on session analysis."""
        recommendations = []

        # Analyze quality trends
        quality_scores = [
            assessment["quality_score"]
            for assessment in session.quality_assessments
        ]

        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            if avg_quality < 0.7:
                recommendations.append("Consider refining prompts to improve overall quality scores")

            if len(quality_scores) > 1 and quality_scores[-1] < quality_scores[0]:
                recommendations.append("Quality declined over retries - review retry strategy")

        # Analyze retry patterns
        if len(session.retry_decisions) > 2:
            recommendations.append("High retry count - consider adjusting quality thresholds or prompt engineering")

        # Analyze JSON validity
        json_failures = sum(1 for resp in session.responses if not resp["is_valid_json"])
        if json_failures > 0:
            recommendations.append("JSON parsing failures detected - enhance prompt clarity for structured output")

        # Analyze common quality issues
        all_issues = []
        for assessment in session.quality_assessments:
            all_issues.extend(assessment.get("quality_issues", []))

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        for issue, count in issue_counts.items():
            if count > 1:
                recommendations.append(f"Recurring issue: {issue} (occurred {count} times)")

        return recommendations

    def _build_execution_timeline(self, session: DebugSession) -> List[Dict[str, Any]]:
        """Build chronological execution timeline."""
        timeline = []

        # Combine all events with timestamps
        events = []

        for prompt in session.prompts:
            events.append({
                "timestamp": prompt["timestamp"],
                "type": "prompt",
                "data": prompt
            })

        for response in session.responses:
            events.append({
                "timestamp": response["timestamp"],
                "type": "response",
                "data": response
            })

        for assessment in session.quality_assessments:
            events.append({
                "timestamp": assessment["timestamp"],
                "type": "quality_assessment",
                "data": assessment
            })

        for decision in session.retry_decisions:
            events.append({
                "timestamp": decision["timestamp"],
                "type": "retry_decision",
                "data": decision
            })

        # Sort by timestamp
        events.sort(key=lambda x: x["timestamp"])

        return events

    def _summarize_quality_assessments(self, session: DebugSession) -> Dict[str, Any]:
        """Summarize quality assessments across the session."""
        if not session.quality_assessments:
            return {"no_data": True}

        assessments = session.quality_assessments

        return {
            "total_assessments": len(assessments),
            "average_quality_score": sum(a["quality_score"] for a in assessments) / len(assessments),
            "quality_score_range": {
                "min": min(a["quality_score"] for a in assessments),
                "max": max(a["quality_score"] for a in assessments)
            },
            "validation_success_rate": sum(1 for a in assessments if a["validation_passed"]) / len(assessments),
            "manual_review_rate": sum(1 for a in assessments if a["needs_manual_review"]) / len(assessments),
            "common_issues": self._get_common_issues(assessments)
        }

    def _analyze_retry_patterns(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze retry decision patterns."""
        if not session.retry_decisions:
            return {"no_retries": True}

        decisions = session.retry_decisions
        retry_counts = [d["retry_count"] for d in decisions]

        return {
            "total_retry_attempts": len(decisions),
            "max_retry_count": max(retry_counts),
            "retry_reasons": list(set(d["reason"] for d in decisions)),
            "final_decisions": list(set(d["decision"] for d in decisions)),
            "average_quality_gap": sum(d["gap"] for d in decisions) / len(decisions)
        }

    def _analyze_prompt_effectiveness(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze prompt effectiveness based on results."""
        if not session.prompts or not session.quality_assessments:
            return {"insufficient_data": True}

        # Correlate prompt characteristics with quality outcomes
        prompt_lengths = [p["total_prompt_length"] for p in session.prompts]
        quality_scores = [a["quality_score"] for a in session.quality_assessments]

        if len(prompt_lengths) == len(quality_scores):
            # Simple correlation analysis
            avg_length = sum(prompt_lengths) / len(prompt_lengths)
            avg_quality = sum(quality_scores) / len(quality_scores)

            return {
                "average_prompt_length": avg_length,
                "average_quality_result": avg_quality,
                "length_quality_correlation": "positive" if avg_length > 1000 and avg_quality > 0.7 else "unclear"
            }

        return {"correlation_analysis_failed": True}

    def _analyze_response_quality_evolution(self, session: DebugSession) -> Dict[str, Any]:
        """Analyze how response quality evolved over time."""
        if not session.responses or not session.quality_assessments:
            return {"insufficient_data": True}

        return {
            "quality_evolution": [
                {
                    "attempt": i + 1,
                    "quality_score": assessment["quality_score"],
                    "validation_passed": assessment["validation_passed"]
                }
                for i, assessment in enumerate(session.quality_assessments)
            ]
        }

    def _get_common_issues(self, assessments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get common quality issues across assessments."""
        issue_counts = {}

        for assessment in assessments:
            for issue in assessment.get("quality_issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort by frequency
        common_issues = [
            {"issue": issue, "frequency": count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return common_issues[:5]  # Top 5 issues