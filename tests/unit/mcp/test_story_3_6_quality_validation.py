"""
Test suite for Story 3.6: Analysis Quality and Error Handling

Tests the comprehensive quality validation, retry/fallback logic,
error categorization, partial result persistence, and debugging capabilities.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from legacy_web_mcp.llm.quality import (
    ResponseValidator,
    QualityAnalyzer,
    ValidationResult,
    QualityMetrics,
    ErrorCode,
    AnalysisError
)
from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis, LLMResponse, LLMUsage
from legacy_web_mcp.llm.artifacts import ArtifactManager, AnalysisArtifact
from legacy_web_mcp.llm.debugging import DebugInspector, DebugSession


class TestResponseValidation:
    """Test schema validators for Step 1 and Step 2 responses."""

    def test_step1_schema_validation_success(self):
        """Test valid ContentSummary JSON response validation."""
        validator = ResponseValidator()

        valid_response = {
            "purpose": "User authentication and login",
            "user_context": "Registered users accessing their accounts",
            "business_logic": "Users enter credentials to access personalized content",
            "navigation_role": "Entry point for authenticated users",
            "confidence_score": 0.9,
            "key_workflows": ["user_authentication", "account_access"],
            "user_journey_stage": "entry",
            "content_hierarchy": {"main_content": "login_form"},
            "business_importance": 0.8,
            "entry_exit_points": {"entry": ["homepage"], "exit": ["dashboard"]},
            "contextual_keywords": ["authentication", "security"]
        }

        result = validator.validate_step1_response(valid_response)

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.completeness_score > 0.8
        assert result.quality_score > 0.7
        assert result.confidence_score == 0.9

    def test_step2_schema_validation_success(self):
        """Test valid FeatureAnalysis JSON response validation."""
        validator = ResponseValidator()

        valid_response = {
            "interactive_elements": [
                {
                    "type": "form",
                    "selector": "#login-form",
                    "purpose": "User authentication",
                    "behavior": "Submit credentials for validation"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "User Authentication",
                    "description": "Validates user credentials and creates session",
                    "type": "security",
                    "complexity_score": 7
                }
            ],
            "api_integrations": [
                {
                    "endpoint": "/api/auth/login",
                    "method": "POST",
                    "purpose": "Authenticate user credentials",
                    "data_flow": "credentials -> validation -> session",
                    "auth_type": "session"
                }
            ],
            "business_rules": [
                {
                    "name": "Password Requirements",
                    "description": "Minimum 8 characters with special characters",
                    "validation_logic": "length >= 8 && hasSpecialChars",
                    "error_handling": "Display validation message"
                }
            ],
            "rebuild_specifications": [
                {
                    "name": "Authentication System",
                    "description": "Modern OAuth2 implementation",
                    "priority_score": 0.9,
                    "complexity": "medium",
                    "dependencies": ["user_management", "session_storage"]
                }
            ],
            "confidence_score": 0.85,
            "quality_score": 0.8
        }

        result = validator.validate_step2_response(valid_response)

        assert result.is_valid
        assert len(result.errors) == 0
        assert result.completeness_score > 0.8
        assert result.quality_score > 0.7

    def test_malformed_json_response_handling(self):
        """Test handling of invalid JSON syntax."""
        validator = ResponseValidator()

        # This should be handled by the LLM engine's validation method
        # but let's test the direct JSON parsing scenario
        invalid_json = '{"purpose": "test", "incomplete": '

        try:
            json.loads(invalid_json)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError as e:
            # Verify error contains location information
            assert "line" in str(e).lower() or "column" in str(e).lower()

    def test_missing_required_fields_validation(self):
        """Test validation with missing required fields."""
        validator = ResponseValidator()

        incomplete_response = {
            "purpose": "Test purpose",
            # Missing user_context, business_logic, navigation_role, confidence_score
        }

        result = validator.validate_step1_response(incomplete_response)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.error_code == ErrorCode.AQL_001
        assert any("incomplete" in error.lower() for error in result.errors)

    def test_invalid_field_types_validation(self):
        """Test validation with incorrect field data types."""
        validator = ResponseValidator()

        invalid_types_response = {
            "purpose": "Valid purpose",
            "user_context": "Valid context",
            "business_logic": "Valid logic",
            "navigation_role": "Valid role",
            "confidence_score": "invalid_string_should_be_float",  # Wrong type
            "key_workflows": "should_be_list",  # Wrong type
            "business_importance": "should_be_float"  # Wrong type
        }

        result = validator.validate_step1_response(invalid_types_response)

        assert not result.is_valid
        assert result.error_code == ErrorCode.VAL_005


class TestQualityScoring:
    """Test quality scoring calculations."""

    def test_analysis_completeness_scoring(self):
        """Test completeness scoring calculation."""
        analyzer = QualityAnalyzer()

        # High completeness data
        complete_data = {
            "purpose": "Comprehensive user authentication system",
            "user_context": "Registered and new users requiring secure access",
            "business_logic": "Multi-factor authentication with role-based access control",
            "navigation_role": "Primary entry point for authenticated user workflows",
            "confidence_score": 0.9,
            "key_workflows": ["authentication", "authorization", "session_management"],
            "user_journey_stage": "entry",
            "content_hierarchy": {"header": "navigation", "main": "login_form", "footer": "help_links"},
            "business_importance": 0.85,
            "contextual_keywords": ["security", "authentication", "access_control"]
        }

        metrics = analyzer.calculate_quality_metrics(complete_data, "step1")

        assert metrics.completeness_score > 0.8
        assert metrics.overall_quality_score > 0.7
        assert not metrics.needs_manual_review

    def test_specificity_scoring_calculation(self):
        """Test specificity scoring for analysis detail level."""
        analyzer = QualityAnalyzer()

        # High specificity data (detailed descriptions)
        specific_data = {
            "interactive_elements": [
                {
                    "type": "form",
                    "selector": "#authentication-form",
                    "purpose": "Secure credential collection with real-time validation",
                    "behavior": "Multi-step validation with progress indicators"
                }
            ],
            "functional_capabilities": [
                {
                    "name": "OAuth2 Authentication",
                    "description": "Implements OAuth2 authorization code flow with PKCE for enhanced security",
                    "type": "authentication",
                    "complexity_score": 8
                }
            ],
            "confidence_score": 0.85,
            "quality_score": 0.8
        }

        metrics = analyzer.calculate_quality_metrics(specific_data, "step2")

        assert metrics.specificity_score > 0.7
        assert metrics.technical_depth_score > 0.6

    def test_technical_detail_level_assessment(self):
        """Test technical detail scoring calculation."""
        validator = ResponseValidator()

        technical_data = {
            "functional_capabilities": [
                {
                    "name": "API Authentication",
                    "description": "RESTful API with JWT tokens, database validation, session management, cookie handling, and AJAX requests for real-time user feedback",
                    "type": "api",
                    "complexity_score": 9
                }
            ]
        }

        tech_score = validator._calculate_technical_detail_score(technical_data)

        assert tech_score > 0.8  # Should score high due to technical keywords

    def test_quality_threshold_validation(self):
        """Test quality threshold triggers for review flags."""
        analyzer = QualityAnalyzer()

        # Low quality data
        low_quality_data = {
            "purpose": "page",  # Generic term
            "user_context": "users",  # Vague
            "business_logic": "stuff",  # Non-specific
            "navigation_role": "page",  # Generic
            "confidence_score": 0.3,  # Low confidence
        }

        metrics = analyzer.calculate_quality_metrics(low_quality_data, "step1")

        assert metrics.overall_quality_score < 0.6
        assert metrics.needs_manual_review
        assert len(metrics.review_reasons) > 0


class TestErrorCategorization:
    """Test error categorization and structured logging."""

    def test_error_categorization_taxonomy(self):
        """Test error classification using architecture error codes."""
        # Test different error types
        validation_error = AnalysisError(
            error_code=ErrorCode.VAL_001,
            error_message="Invalid JSON syntax in response",
            category="validation",
            severity="high",
            recoverable=True
        )

        llm_error = AnalysisError(
            error_code=ErrorCode.LLM_002,
            error_message="Rate limiting exceeded",
            category="provider",
            severity="medium",
            recoverable=True
        )

        quality_error = AnalysisError(
            error_code=ErrorCode.AQL_003,
            error_message="Low confidence indicators",
            category="quality",
            severity="low",
            recoverable=True
        )

        # Verify error categorization
        assert validation_error.error_code == ErrorCode.VAL_001
        assert validation_error.category == "validation"
        assert validation_error.recoverable

        assert llm_error.error_code == ErrorCode.LLM_002
        assert llm_error.category == "provider"

        assert quality_error.error_code == ErrorCode.AQL_003
        assert quality_error.category == "quality"


class TestArtifactPersistence:
    """Test partial result persistence mechanisms."""

    def test_analysis_artifact_creation(self):
        """Test artifact creation and persistence."""
        artifact_manager = ArtifactManager(artifacts_dir="test_artifacts")

        # Create test artifact
        artifact = artifact_manager.create_artifact(
            analysis_type="step2",
            page_url="https://example.com/test",
            project_id="test_project",
            metadata={"test": "data"}
        )

        assert artifact.artifact_id is not None
        assert artifact.analysis_type == "step2"
        assert artifact.page_url == "https://example.com/test"
        assert artifact.status == "in_progress"
        assert artifact.project_id == "test_project"

    def test_partial_result_persistence_mechanisms(self):
        """Test partial result preservation during failures."""
        artifact_manager = ArtifactManager(artifacts_dir="test_artifacts")

        # Create artifact
        artifact = artifact_manager.create_artifact(
            analysis_type="step1",
            page_url="https://example.com/test"
        )

        # Add partial results
        partial_step1 = ContentSummary(
            purpose="Test purpose",
            user_context="Test users",
            business_logic="Test logic",
            navigation_role="Test role",
            confidence_score=0.7
        )

        updated_artifact = artifact_manager.add_analysis_result(
            artifact=artifact,
            result=partial_step1
        )

        assert updated_artifact.step1_result is not None
        assert updated_artifact.step1_result["purpose"] == "Test purpose"
        assert updated_artifact.step1_result["confidence_score"] == 0.7

    def test_artifact_error_tracking(self):
        """Test error tracking in artifacts."""
        artifact_manager = ArtifactManager(artifacts_dir="test_artifacts")

        artifact = artifact_manager.create_artifact(
            analysis_type="step2",
            page_url="https://example.com/error-test"
        )

        # Add error
        test_error = AnalysisError(
            error_code=ErrorCode.LLM_001,
            error_message="Provider connection failed",
            category="provider",
            severity="high",
            recoverable=True
        )

        updated_artifact = artifact_manager.add_error(
            artifact=artifact,
            error=test_error,
            context={"phase": "step2_analysis"}
        )

        assert len(updated_artifact.errors) == 1
        assert updated_artifact.errors[0]["error_message"] == "Provider connection failed"
        assert updated_artifact.errors[0]["error_code"] == ErrorCode.LLM_001.value


class TestDebuggingInterface:
    """Test debugging tools and interfaces."""

    def test_debug_session_creation(self):
        """Test debug session creation and management."""
        debug_inspector = DebugInspector()

        session = debug_inspector.start_debug_session(
            page_url="https://example.com/debug",
            analysis_type="step2"
        )

        assert session.session_id is not None
        assert session.page_url == "https://example.com/debug"
        assert session.analysis_type == "step2"
        assert isinstance(session.created_at, datetime)

    def test_llm_interaction_logging(self):
        """Test LLM interaction logging for debugging."""
        debug_inspector = DebugInspector()

        session = debug_inspector.start_debug_session(
            page_url="https://example.com/debug",
            analysis_type="step1"
        )

        # Mock LLM request/response
        mock_request = {
            "messages": [{"role": "user", "content": "Test prompt"}],
            "model": "gpt-4",
            "temperature": 0.7
        }

        mock_response = {
            "content": '{"purpose": "test", "confidence_score": 0.8}',
            "model": "gpt-4",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

        # Log interaction
        debug_inspector.log_prompt_details(
            session_id=session.session_id,
            request=MagicMock(**mock_request),
            context={"test": "context"}
        )

        debug_inspector.log_response_details(
            session_id=session.session_id,
            response=MagicMock(**mock_response),
            processing_time=1.5
        )

        # Verify logging
        assert len(session.prompts) == 1
        assert len(session.responses) == 1
        assert session.prompts[0]["model"] == "gpt-4"
        assert session.responses[0]["processing_time"] == 1.5

    def test_quality_assessment_logging(self):
        """Test quality assessment logging in debug sessions."""
        debug_inspector = DebugInspector()

        session = debug_inspector.start_debug_session(
            page_url="https://example.com/debug",
            analysis_type="step2"
        )

        # Mock quality metrics and validation
        quality_metrics = QualityMetrics(
            completeness_score=0.85,
            specificity_score=0.75,
            technical_depth_score=0.8,
            llm_confidence_score=0.9,
            overall_quality_score=0.825,
            needs_manual_review=False
        )

        validation_result = ValidationResult(
            is_valid=True,
            completeness_score=0.85,
            quality_score=0.8,
            confidence_score=0.9
        )

        # Log assessment
        debug_inspector.log_quality_assessment(
            session_id=session.session_id,
            quality_metrics=quality_metrics,
            validation_result=validation_result,
            decision_rationale="High quality analysis, proceeding"
        )

        # Verify logging
        assert len(session.quality_assessments) == 1
        assessment = session.quality_assessments[0]
        assert assessment["quality_score"] == 0.825
        assert assessment["validation_passed"] == True
        assert assessment["decision_rationale"] == "High quality analysis, proceeding"

    def test_debug_report_generation(self):
        """Test comprehensive debug report generation."""
        debug_inspector = DebugInspector()

        session = debug_inspector.start_debug_session(
            page_url="https://example.com/debug",
            analysis_type="step2"
        )

        # Add some mock data
        session.prompts.append({
            "timestamp": datetime.now().isoformat(),
            "total_prompt_length": 500,
            "message_count": 2
        })

        session.responses.append({
            "timestamp": datetime.now().isoformat(),
            "content_length": 300,
            "is_valid_json": True,
            "processing_time": 2.1
        })

        # Generate report
        report = debug_inspector.generate_debug_report(session.session_id)

        assert "session_info" in report
        assert "execution_timeline" in report
        assert "quality_assessment_summary" in report
        assert "improvement_opportunities" in report

        assert report["session_info"]["session_id"] == session.session_id
        assert report["session_info"]["page_url"] == "https://example.com/debug"


class TestEndToEndQualityValidation:
    """Test complete quality validation workflow integration."""

    @pytest.mark.asyncio
    async def test_end_to_end_validation_workflow(self):
        """Test complete validation workflow from request to quality assessment."""
        # This would test the full integration but requires actual LLM engine
        # For now, test the workflow structure

        validator = ResponseValidator()
        analyzer = QualityAnalyzer()
        artifact_manager = ArtifactManager(artifacts_dir="test_artifacts")

        # Mock analysis workflow
        test_response = {
            "purpose": "User authentication and access control",
            "user_context": "Registered users and administrators",
            "business_logic": "Multi-factor authentication with role-based permissions",
            "navigation_role": "Primary security gateway for the application",
            "confidence_score": 0.85,
            "key_workflows": ["authentication", "authorization", "session_management"],
            "user_journey_stage": "entry",
            "business_importance": 0.9
        }

        # Validate response
        validation_result = validator.validate_step1_response(test_response)
        assert validation_result.is_valid

        # Calculate quality metrics
        quality_metrics = analyzer.calculate_quality_metrics(test_response, "step1")
        assert quality_metrics.overall_quality_score > 0.7

        # Create artifact for persistence
        artifact = artifact_manager.create_artifact(
            analysis_type="step1",
            page_url="https://example.com/integration-test"
        )

        # Simulate adding results
        content_summary = ContentSummary(**test_response)
        artifact_manager.add_analysis_result(
            artifact=artifact,
            result=content_summary,
            quality_metrics=quality_metrics,
            validation_result=validation_result
        )

        # Verify end-to-end workflow
        assert artifact.step1_result is not None
        assert artifact.quality_metrics is not None
        assert artifact.validation_result is not None

        # Complete artifact
        final_artifact = artifact_manager.complete_artifact(artifact, status="completed")
        assert final_artifact.status == "completed"


if __name__ == "__main__":
    pytest.main([__file__])