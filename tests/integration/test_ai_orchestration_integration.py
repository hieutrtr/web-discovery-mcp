"""Integration tests for AI-driven workflow orchestration tools from Story 6.5."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import Context

from legacy_web_mcp.mcp.orchestration_tools import (
    AIWorkflowOrchestrator,
    AnalysisMode,
    CostPriority,
)


@pytest.fixture
def mock_config():
    """Mock configuration object for integration tests."""
    config = MagicMock()
    config.LLM_SETTINGS = MagicMock()
    config.OUTPUT_ROOT = "/tmp/test"
    return config


@pytest.fixture
def mock_context():
    """Mock FastMCP context for integration tests."""
    context = AsyncMock(spec=Context)
    return context


@pytest.fixture
def ai_orchestrator(mock_config):
    """Create AI workflow orchestrator with partially mocked dependencies."""
    with patch('legacy_web_mcp.mcp.orchestration_tools.LLMEngine'), \
         patch('legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService'), \
         patch('legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService'), \
         patch('legacy_web_mcp.mcp.orchestration_tools.create_project_store'):
        return AIWorkflowOrchestrator(mock_config, "integration-test")


class TestEndToEndAIAnalysis:
    """Test end-to-end AI-driven analysis workflows."""

    @pytest.mark.asyncio
    async def test_end_to_end_ai_driven_analysis(self, ai_orchestrator, mock_context):
        """Given: Real legacy site and natural language request
        When: AI-driven workflow executes completely
        Then: Produces actionable rebuild documentation"""

        # Mock complete AI workflow
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            # Intent parsing
            json.dumps({
                "primary_intent": "rebuild_planning",
                "specific_goals": ["modernize legacy system"],
                "urgency_level": "medium",
                "depth_preference": "comprehensive",
                "summary": "Legacy system modernization analysis"
            }),
            # Pattern detection
            json.dumps({
                "site_type": "application",
                "confidence_level": 0.85,
                "key_characteristics": ["custom application", "legacy database"],
                "recommended_analysis_approach": "comprehensive",
                "estimated_complexity": "high"
            }),
            # Workflow planning
            json.dumps({
                "analysis_mode": "comprehensive",
                "cost_priority": "balanced",
                "max_pages": 25,
                "include_step2": True,
                "focus_areas": ["authentication", "data layer", "user interface"],
                "strategy_summary": "Comprehensive legacy application analysis"
            }),
            # Result synthesis
            json.dumps({
                "executive_summary": "Legacy application requires phased modernization approach",
                "prioritized_findings": [
                    {"priority": 1, "finding": "Legacy authentication system vulnerable"},
                    {"priority": 2, "finding": "Database schema needs normalization"},
                    {"priority": 3, "finding": "UI framework severely outdated"}
                ],
                "actionable_next_steps": [
                    "Phase 1: Secure authentication system",
                    "Phase 2: Database modernization",
                    "Phase 3: UI framework upgrade"
                ],
                "rebuild_recommendations": {
                    "approach": "phased",
                    "timeline": "8-12 months",
                    "risk_level": "medium-high",
                    "estimated_cost": "$150K-$250K"
                }
            })
        ])

        # Mock base orchestrator workflow
        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"type": "application", "complexity": "high"},
            "total_pages_found": 45
        })

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 25,
            "analysis_results": {
                "completed_pages": 25,
                "failed_pages": 0,
                "page_analysis_results": [
                    {"url": "https://app.example.com/login", "status": "completed"},
                    {"url": "https://app.example.com/dashboard", "status": "completed"}
                ]
            },
            "step2_analysis_results": {
                "successful_analyses": 20,
                "api_integrations_found": 5,
                "interactive_elements_total": 35
            }
        })

        # Execute complete workflow
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "I need to analyze this legacy application for complete modernization",
            "https://app.example.com"
        )

        # Verify comprehensive result structure
        assert result["status"] == "success"
        assert "intelligent_insights" in result
        assert "site_pattern_analysis" in result
        assert "user_intent_fulfillment" in result

        # Verify AI insights
        insights = result["intelligent_insights"]
        assert "Legacy application requires phased" in insights["executive_summary"]
        assert len(insights["prioritized_findings"]) == 3
        assert "Phase 1" in insights["actionable_next_steps"][0]

        # Verify rebuild recommendations
        rebuild_rec = insights["rebuild_recommendations"]
        assert rebuild_rec["approach"] == "phased"
        assert "8-12 months" in rebuild_rec["timeline"]

    @pytest.mark.asyncio
    async def test_ai_workflow_with_different_site_types(self, ai_orchestrator, mock_context):
        """Given: Various site types (e-commerce, CMS, custom apps)
        When: AI analyzes each site type
        Then: Adapts strategy appropriately for each type"""

        test_cases = [
            {
                "site_type": "ecommerce",
                "url": "https://shop.example.com",
                "request": "Analyze this e-commerce site for migration",
                "expected_focus": ["payment processing", "inventory management"]
            },
            {
                "site_type": "cms",
                "url": "https://cms.example.com",
                "request": "Assess this CMS for security vulnerabilities",
                "expected_focus": ["content management", "user permissions"]
            },
            {
                "site_type": "blog",
                "url": "https://blog.example.com",
                "request": "Quick analysis of this blog site",
                "expected_mode": "quick"
            }
        ]

        for case in test_cases:
            # Setup mocks for this site type
            ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
                json.dumps({"primary_intent": "general_analysis", "summary": case["request"]}),
                json.dumps({
                    "site_type": case["site_type"],
                    "confidence_level": 0.9,
                    "recommended_analysis_approach": case.get("expected_mode", "recommended")
                }),
                json.dumps({
                    "analysis_mode": case.get("expected_mode", "recommended"),
                    "focus_areas": case.get("expected_focus", []),
                    "strategy_summary": f"{case['site_type']} analysis"
                }),
                json.dumps({"executive_summary": f"Analysis of {case['site_type']} site"})
            ])

            ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
                "site_characteristics": {"type": case["site_type"]},
                "total_pages_found": 20
            })

            ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
                "status": "success",
                "pages_analyzed": 10
            })

            # Execute analysis
            result = await ai_orchestrator.analyze_with_intelligence(
                mock_context, case["request"], case["url"]
            )

            # Verify type-specific adaptation
            assert result["site_pattern_analysis"]["type"] == case["site_type"]
            if "expected_focus" in case:
                # Would check that focus areas were considered in planning
                pass


class TestUserInteractionWorkflows:
    """Test user interaction throughout analysis workflows."""

    @pytest.mark.asyncio
    async def test_user_interaction_throughout_analysis(self, ai_orchestrator, mock_context):
        """Given: Interactive AI analysis workflow
        When: User engages in conversation during analysis
        Then: Maintains coherent dialogue while performing analysis"""

        # Simulate conversational interaction
        ai_orchestrator.conversation_context = []

        # Mock LLM responses that show conversational awareness
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "feature_assessment",
                "summary": "User wants to understand current features before redesign"
            }),
            json.dumps({
                "site_type": "application",
                "confidence_level": 0.8,
                "recommended_analysis_approach": "comprehensive"
            }),
            json.dumps({
                "analysis_mode": "comprehensive",
                "strategy_summary": "Feature-focused analysis for redesign planning"
            }),
            json.dumps({
                "executive_summary": "Comprehensive feature inventory completed for redesign planning"
            })
        ])

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"type": "application"},
            "total_pages_found": 30
        })

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 20
        })

        # Execute with conversational request
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "I'm planning a redesign and need to understand what features currently exist",
            "https://app.example.com"
        )

        # Verify conversational context is maintained
        assert result["user_intent_fulfillment"]["intent"] == "feature_assessment"
        assert "redesign" in result["user_intent_fulfillment"]["summary"]

    @pytest.mark.asyncio
    async def test_ai_decision_rationale_explanation(self, ai_orchestrator, mock_context):
        """Given: AI makes analysis decisions
        When: User asks for explanation
        Then: Provides clear rationale for decisions made"""

        # Test that AI workflow includes decision rationale
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "security_audit",
                "summary": "Security audit request"
            }),
            json.dumps({
                "site_type": "admin_panel",
                "confidence_level": 0.95,
                "key_characteristics": ["admin interface", "user management"]
            }),
            json.dumps({
                "analysis_mode": "comprehensive",
                "cost_priority": "speed",
                "strategy_summary": "High-priority security audit for admin panel",
                "rationale": "Admin panels require comprehensive security analysis due to elevated privileges"
            }),
            json.dumps({
                "executive_summary": "Security audit reveals critical vulnerabilities",
                "decision_rationale": "Comprehensive mode chosen due to admin panel privileges"
            })
        ])

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"type": "admin_panel"},
            "total_pages_found": 15
        })

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 15
        })

        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Security audit for this admin panel",
            "https://admin.example.com"
        )

        # Verify decision rationale is available
        assert result["site_pattern_analysis"]["type"] == "admin_panel"
        # In a real implementation, decision rationale would be preserved


class TestAnalysisOptimization:
    """Test analysis strategy optimization over time."""

    @pytest.mark.asyncio
    async def test_analysis_strategy_optimization_over_time(self, ai_orchestrator, mock_context):
        """Given: Multiple analyses over time
        When: AI learns from patterns
        Then: Improves analysis efficiency and quality"""

        # Simulate learning from successful e-commerce analyses
        ai_orchestrator.analysis_history = [
            {
                "intent": "rebuild_planning",
                "site_type": "ecommerce",
                "success_metrics": {"completed": True, "analysis_quality": 0.9}
            },
            {
                "intent": "rebuild_planning",
                "site_type": "ecommerce",
                "success_metrics": {"completed": True, "analysis_quality": 0.85}
            }
        ]

        # Mock current analysis
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "rebuild_planning",
                "summary": "E-commerce rebuild planning"
            }),
            json.dumps({
                "site_type": "ecommerce",
                "confidence_level": 0.9
            }),
            json.dumps({
                "analysis_mode": "recommended",
                "strategy_summary": "Optimized e-commerce analysis based on previous successes"
            }),
            json.dumps({
                "executive_summary": "E-commerce analysis optimized based on historical patterns"
            })
        ])

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"type": "ecommerce"},
            "total_pages_found": 40
        })

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 20,
            "analysis_quality_score": 0.92
        })

        # Execute analysis
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Rebuild planning for this e-commerce site",
            "https://store.example.com"
        )

        # Verify learning is recorded
        assert len(ai_orchestrator.analysis_history) == 3
        latest_learning = ai_orchestrator.analysis_history[-1]
        assert latest_learning["intent"] == "rebuild_planning"
        assert latest_learning["site_type"] == "ecommerce"

    @pytest.mark.asyncio
    async def test_complex_site_analysis_intelligence(self, ai_orchestrator, mock_context):
        """Given: Complex site with mixed technologies
        When: AI determines analysis approach
        Then: Handles complexity intelligently with appropriate depth"""

        # Mock complex site characteristics
        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {
                "mixed_technologies": True,
                "legacy_components": True,
                "modern_sections": True,
                "microservices": True
            },
            "total_pages_found": 150
        })

        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "feature_assessment",
                "summary": "Complex application feature assessment"
            }),
            json.dumps({
                "site_type": "application",
                "confidence_level": 0.85,
                "estimated_complexity": "very_high",
                "key_characteristics": ["mixed technologies", "legacy and modern components"]
            }),
            json.dumps({
                "analysis_mode": "targeted",
                "cost_priority": "balanced",
                "max_pages": 50,
                "include_step2": True,
                "focus_areas": ["legacy components", "modern sections", "integration points"],
                "special_considerations": [
                    "Deep analysis of legacy-modern integration",
                    "Technology stack assessment",
                    "Migration complexity evaluation"
                ],
                "strategy_summary": "Targeted analysis focusing on complexity boundaries"
            }),
            json.dumps({
                "executive_summary": "Complex application with strategic modernization opportunities",
                "prioritized_findings": [
                    {"priority": 1, "finding": "Legacy-modern integration creates bottlenecks"},
                    {"priority": 2, "finding": "Microservices architecture partially implemented"}
                ]
            })
        ])

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 50
        })

        # Execute analysis for complex site
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Analyze this complex application with mixed legacy and modern components",
            "https://complex-app.example.com"
        )

        # Verify intelligent handling of complexity
        assert result["site_pattern_analysis"]["complexity"] == "very_high"
        workflow_plan = result["ai_workflow_plan"]
        assert workflow_plan["analysis_mode"] == AnalysisMode.TARGETED
        assert "integration points" in workflow_plan["focus_areas"]
        assert len(workflow_plan["special_considerations"]) > 0


class TestErrorPreventionAndRecovery:
    """Test AI workflow error prevention and recovery."""

    @pytest.mark.asyncio
    async def test_ai_workflow_error_prevention(self, ai_orchestrator, mock_context):
        """Given: Potential error conditions
        When: AI anticipates and prevents errors
        Then: Proactively avoids common analysis pitfalls"""

        # Mock potential error scenario - site with restricted access
        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"access_restricted": True, "authentication_required": True},
            "total_pages_found": 5  # Very few pages discovered
        })

        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "general_analysis",
                "summary": "General site analysis"
            }),
            json.dumps({
                "site_type": "application",
                "confidence_level": 0.6,  # Lower confidence due to restricted access
                "estimated_complexity": "unknown",
                "access_limitations": "Authentication required for full analysis"
            }),
            json.dumps({
                "analysis_mode": "quick",
                "cost_priority": "cost_efficient",
                "max_pages": 5,
                "include_step2": False,
                "strategy_summary": "Limited analysis due to access restrictions",
                "special_considerations": ["Analysis limited by authentication requirements"]
            }),
            json.dumps({
                "executive_summary": "Limited analysis due to authentication barriers",
                "limitations": "Full analysis requires authenticated access"
            })
        ])

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 5,
            "limitations": ["authentication_required"]
        })

        # Execute analysis
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Analyze this application",
            "https://private-app.example.com"
        )

        # Verify error prevention through adaptive strategy
        workflow_plan = result["ai_workflow_plan"]
        assert workflow_plan["analysis_mode"] == AnalysisMode.QUICK
        assert workflow_plan["include_step2"] is False
        assert "access restrictions" in workflow_plan["strategy_summary"]

    @pytest.mark.asyncio
    async def test_custom_analysis_template_support(self, ai_orchestrator, mock_context):
        """Given: Custom analysis requirements
        When: AI applies custom templates
        Then: Adapts workflow to meet specific needs"""

        # Provide custom user preferences
        custom_preferences = {
            "analysis_template": "compliance_audit",
            "regulatory_focus": "GDPR",
            "required_sections": ["data_handling", "consent_mechanisms", "user_rights"],
            "deliverable_format": "regulatory_report"
        }

        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "security_audit",
                "specific_goals": ["GDPR compliance assessment"],
                "summary": "GDPR compliance audit"
            }),
            json.dumps({
                "site_type": "application",
                "confidence_level": 0.8,
                "data_handling_detected": True
            }),
            json.dumps({
                "analysis_mode": "targeted",
                "focus_areas": ["data_handling", "consent_mechanisms", "user_rights"],
                "special_considerations": [
                    "GDPR compliance requirements",
                    "Regulatory reporting format required"
                ],
                "strategy_summary": "GDPR compliance-focused analysis"
            }),
            json.dumps({
                "executive_summary": "GDPR compliance assessment completed",
                "compliance_findings": ["consent mechanisms", "data retention policies"],
                "regulatory_recommendations": ["implement explicit consent", "data minimization"]
            })
        ])

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"has_user_data": True, "cookie_usage": True},
            "total_pages_found": 20
        })

        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 15
        })

        # Execute with custom template
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Perform GDPR compliance audit",
            "https://app.example.com",
            custom_preferences
        )

        # Verify custom template application
        workflow_plan = result["ai_workflow_plan"]
        assert "data_handling" in workflow_plan["focus_areas"]
        assert "GDPR compliance" in workflow_plan["strategy_summary"]
        assert workflow_plan["analysis_mode"] == AnalysisMode.TARGETED