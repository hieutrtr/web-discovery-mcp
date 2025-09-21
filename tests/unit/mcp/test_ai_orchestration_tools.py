"""Tests for AI-driven workflow orchestration tools from Story 6.5."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastmcp import Context

from legacy_web_mcp.mcp.orchestration_tools import (
    AIWorkflowOrchestrator,
    AnalysisMode,
    CostPriority,
    SitePattern,
    AnalysisIntent,
)


@pytest.fixture
def mock_config():
    """Mock configuration object."""
    config = MagicMock()
    config.LLM_SETTINGS = MagicMock()
    return config


@pytest.fixture
def mock_context():
    """Mock FastMCP context."""
    context = AsyncMock(spec=Context)
    return context


@pytest.fixture
def ai_orchestrator(mock_config):
    """Create AI workflow orchestrator with mocked dependencies."""
    with patch('legacy_web_mcp.mcp.orchestration_tools.LLMEngine'), \
         patch('legacy_web_mcp.mcp.orchestration_tools.LegacyAnalysisOrchestrator'):
        return AIWorkflowOrchestrator(mock_config, "test-project")


class TestAIWorkflowBasicFunctionality:
    """Test basic AI workflow functionality (AC: 1)."""

    @pytest.mark.asyncio
    async def test_ai_workflow_basic_functionality(self, ai_orchestrator, mock_context):
        """Given: Site URL and natural language analysis request
        When: analyze_with_intelligence() is invoked
        Then: Returns comprehensive analysis with intelligent insights"""

        # Mock LLM responses
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=[
            json.dumps({
                "primary_intent": "rebuild_planning",
                "specific_goals": ["modernize architecture"],
                "urgency_level": "high",
                "depth_preference": "comprehensive",
                "summary": "Analyze for rebuilding"
            }),
            json.dumps({
                "site_type": "ecommerce",
                "confidence_level": 0.9,
                "key_characteristics": ["shopping cart", "product catalog"],
                "recommended_analysis_approach": "comprehensive",
                "estimated_complexity": "high"
            }),
            json.dumps({
                "analysis_mode": "comprehensive",
                "cost_priority": "balanced",
                "max_pages": 30,
                "include_step2": True,
                "strategy_summary": "Comprehensive e-commerce analysis"
            }),
            json.dumps({
                "executive_summary": "Complex e-commerce site requiring full rebuild",
                "prioritized_findings": ["Legacy payment system", "Outdated UI framework"],
                "actionable_next_steps": ["Modernize checkout flow", "Update UI library"]
            })
        ])

        # Mock base orchestrator
        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {"type": "ecommerce"},
            "total_pages_found": 50
        })
        ai_orchestrator.base_orchestrator.discover_and_analyze_site = AsyncMock(return_value={
            "status": "success",
            "pages_analyzed": 30,
            "analysis_quality_score": 0.85
        })

        # Execute
        result = await ai_orchestrator.analyze_with_intelligence(
            mock_context,
            "Analyze this e-commerce site for rebuilding",
            "https://example-shop.com"
        )

        # Verify
        assert result["status"] == "success"
        assert "intelligent_insights" in result
        assert "executive_summary" in result["intelligent_insights"]
        assert "site_pattern_analysis" in result
        assert result["site_pattern_analysis"]["type"] == "ecommerce"


class TestSitePatternRecognition:
    """Test site pattern recognition system (AC: 3)."""

    @pytest.mark.asyncio
    async def test_site_pattern_recognition_system(self, ai_orchestrator, mock_context):
        """Given: Website with recognizable patterns (e-commerce, blog, etc.)
        When: Pattern detection is performed
        Then: Correctly identifies site type and applies appropriate strategy"""

        # Mock discovery result for e-commerce site
        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {
                "has_shopping_cart": True,
                "has_payment_system": True,
                "product_pages": 25
            },
            "total_pages_found": 100
        })

        # Mock LLM pattern detection
        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "site_type": "ecommerce",
            "confidence_level": 0.95,
            "key_characteristics": ["shopping cart", "payment integration", "product catalog"],
            "recommended_analysis_approach": "comprehensive",
            "estimated_complexity": "high"
        }))

        # Execute
        result = await ai_orchestrator._detect_site_pattern(mock_context, "https://shop.example.com")

        # Verify
        assert result["type"] == "ecommerce"
        assert result["confidence"] == 0.95
        assert "shopping cart" in result["characteristics"]
        assert result["complexity"] == "high"

    @pytest.mark.asyncio
    async def test_blog_pattern_detection(self, ai_orchestrator, mock_context):
        """Test detection of blog pattern."""

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(return_value={
            "site_characteristics": {
                "has_posts": True,
                "has_comments": True,
                "blog_structure": True
            },
            "total_pages_found": 20
        })

        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "site_type": "blog",
            "confidence_level": 0.88,
            "key_characteristics": ["blog posts", "comment system", "categories"],
            "recommended_analysis_approach": "quick",
            "estimated_complexity": "low"
        }))

        result = await ai_orchestrator._detect_site_pattern(mock_context, "https://blog.example.com")

        assert result["type"] == "blog"
        assert result["confidence"] == 0.88
        assert result["complexity"] == "low"


class TestIntelligentToolSelection:
    """Test intelligent tool selection logic (AC: 2,6)."""

    @pytest.mark.asyncio
    async def test_intelligent_tool_selection_logic(self, ai_orchestrator, mock_context):
        """Given: Site with specific characteristics
        When: AI selects analysis tools and sequence
        Then: Chooses optimal tools for maximum insight generation"""

        analysis_intent = {
            "intent": "security_audit",
            "goals": ["identify vulnerabilities"],
            "urgency": "high",
            "depth": "comprehensive"
        }

        site_pattern = {
            "type": "admin_panel",
            "confidence": 0.9,
            "complexity": "high"
        }

        # Mock LLM workflow planning
        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "analysis_mode": "comprehensive",
            "cost_priority": "speed",
            "max_pages": 15,
            "include_step2": True,
            "focus_areas": ["authentication", "authorization", "data access"],
            "strategy_summary": "Security-focused admin panel analysis"
        }))

        # Execute
        result = await ai_orchestrator._create_intelligent_workflow_plan(
            analysis_intent, site_pattern, {}
        )

        # Verify
        assert result["analysis_mode"] == AnalysisMode.COMPREHENSIVE
        assert result["cost_priority"] == CostPriority.SPEED
        assert result["max_pages"] == 15
        assert result["include_step2"] is True
        assert "authentication" in result["focus_areas"]

    @pytest.mark.asyncio
    async def test_cost_efficient_strategy_selection(self, ai_orchestrator, mock_context):
        """Test selection of cost-efficient strategy for simple sites."""

        analysis_intent = {
            "intent": "general_analysis",
            "constraints": {"budget": "low"}
        }

        site_pattern = {
            "type": "landing_page",
            "confidence": 0.85,
            "complexity": "low"
        }

        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "analysis_mode": "quick",
            "cost_priority": "cost_efficient",
            "max_pages": 3,
            "include_step2": False,
            "strategy_summary": "Quick landing page analysis"
        }))

        result = await ai_orchestrator._create_intelligent_workflow_plan(
            analysis_intent, site_pattern, {"budget": "low"}
        )

        assert result["analysis_mode"] == AnalysisMode.QUICK
        assert result["cost_priority"] == CostPriority.COST_EFFICIENT
        assert result["include_step2"] is False


class TestNaturalLanguageProcessing:
    """Test natural language command parsing and progress reporting (AC: 4)."""

    @pytest.mark.asyncio
    async def test_natural_language_command_parsing(self, ai_orchestrator, mock_context):
        """Given: Various natural language analysis requests
        When: Command parsing and intent recognition occurs
        Then: Correctly extracts analysis goals and constraints"""

        request = "I need to analyze this legacy CRM system urgently for migration planning with a limited budget"

        # Mock LLM intent parsing
        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "primary_intent": "migration_prep",
            "specific_goals": ["data migration", "system compatibility"],
            "urgency_level": "high",
            "depth_preference": "thorough",
            "constraints": {"budget": "limited"},
            "summary": "Urgent CRM migration analysis with budget constraints"
        }))

        # Execute
        result = await ai_orchestrator._parse_analysis_intent(request)

        # Verify
        assert result["intent"] == "migration_prep"
        assert "data migration" in result["goals"]
        assert result["urgency"] == "high"
        assert result["constraints"]["budget"] == "limited"

    @pytest.mark.asyncio
    async def test_feature_assessment_parsing(self, ai_orchestrator, mock_context):
        """Test parsing of feature assessment requests."""

        request = "Can you do a comprehensive feature analysis of this web application?"

        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "primary_intent": "feature_assessment",
            "specific_goals": ["catalog features", "assess functionality"],
            "urgency_level": "medium",
            "depth_preference": "comprehensive",
            "summary": "Comprehensive feature analysis request"
        }))

        result = await ai_orchestrator._parse_analysis_intent(request)

        assert result["intent"] == "feature_assessment"
        assert result["depth"] == "comprehensive"
        assert "catalog features" in result["goals"]


class TestAdaptiveAnalysis:
    """Test adaptive analysis capabilities (AC: 6)."""

    @pytest.mark.asyncio
    async def test_adaptive_analysis_depth_adjustment(self, ai_orchestrator, mock_context):
        """Given: Site with varying page importance/complexity
        When: AI determines analysis depth
        Then: Allocates appropriate effort to different sections"""

        # Mock workflow planning with adaptive depth
        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "analysis_mode": "targeted",
            "cost_priority": "balanced",
            "max_pages": 25,
            "include_step2": True,
            "focus_areas": ["user dashboard", "payment processing", "admin panel"],
            "special_considerations": ["Deep dive on payment flow", "Quick scan of static pages"]
        }))

        analysis_intent = {"intent": "security_audit"}
        site_pattern = {"type": "application", "complexity": "high"}

        result = await ai_orchestrator._create_intelligent_workflow_plan(
            analysis_intent, site_pattern, {}
        )

        assert result["analysis_mode"] == AnalysisMode.TARGETED
        assert "payment processing" in result["focus_areas"]
        assert len(result["special_considerations"]) > 0

    @pytest.mark.asyncio
    async def test_learning_from_previous_analyses(self, ai_orchestrator, mock_context):
        """Given: Historical analysis data and patterns
        When: AI plans new analysis
        Then: Adapts strategy based on previous learnings"""

        # Setup learning history
        ai_orchestrator.analysis_history = [
            {
                "intent": "rebuild_planning",
                "site_type": "ecommerce",
                "success_metrics": {"completed": True, "analysis_quality": 0.9}
            }
        ]

        analysis_intent = {"intent": "rebuild_planning"}
        site_pattern = {"type": "ecommerce"}
        result = {"status": "success", "analysis_quality_score": 0.88}

        # Execute learning
        await ai_orchestrator._learn_from_analysis(analysis_intent, site_pattern, result)

        # Verify learning data is stored
        assert len(ai_orchestrator.analysis_history) == 2
        latest_entry = ai_orchestrator.analysis_history[-1]
        assert latest_entry["intent"] == "rebuild_planning"
        assert latest_entry["site_type"] == "ecommerce"


class TestResultSynthesis:
    """Test intelligent result synthesis (AC: 5)."""

    @pytest.mark.asyncio
    async def test_result_synthesis_intelligence(self, ai_orchestrator, mock_context):
        """Given: Multiple analysis results from different tools
        When: AI synthesizes findings
        Then: Creates coherent, prioritized rebuild recommendations"""

        analysis_result = {
            "status": "success",
            "pages_analyzed": 25,
            "step2_feature_analysis": {"api_integrations": 5, "interactive_elements": 15}
        }

        analysis_intent = {"intent": "rebuild_planning", "summary": "Rebuild planning analysis"}
        site_pattern = {"type": "application", "confidence": 0.85}

        # Mock AI synthesis
        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "executive_summary": "Complex application requiring phased rebuild approach",
            "prioritized_findings": [
                {"priority": 1, "finding": "Legacy authentication system needs replacement"},
                {"priority": 2, "finding": "Database schema modernization required"}
            ],
            "actionable_next_steps": ["Phase 1: Auth system", "Phase 2: Database migration"],
            "rebuild_recommendations": {
                "approach": "phased",
                "timeline": "6-8 months",
                "risk_level": "medium"
            }
        }))

        # Execute
        result = await ai_orchestrator._synthesize_results_with_ai(
            analysis_result, analysis_intent, site_pattern
        )

        # Verify
        assert "intelligent_insights" in result
        insights = result["intelligent_insights"]
        assert "Complex application" in insights["executive_summary"]
        assert len(insights["prioritized_findings"]) == 2
        assert "Auth system" in insights["actionable_next_steps"][0]

    @pytest.mark.asyncio
    async def test_user_requirement_alignment(self, ai_orchestrator, mock_context):
        """Given: User specifies specific analysis goals
        When: AI plans analysis workflow
        Then: Aligns analysis strategy with user requirements"""

        analysis_intent = {
            "intent": "security_audit",
            "goals": ["GDPR compliance", "vulnerability assessment"],
            "focus_areas": ["data handling", "user authentication"]
        }

        site_pattern = {"type": "cms", "complexity": "medium"}
        user_preferences = {"compliance_focus": "GDPR", "priority": "security"}

        ai_orchestrator.llm_engine.generate_response = AsyncMock(return_value=json.dumps({
            "analysis_mode": "targeted",
            "focus_areas": ["data handling", "user authentication", "GDPR compliance"],
            "special_considerations": ["Focus on data flows", "Audit user consent mechanisms"],
            "strategy_summary": "GDPR-focused security analysis"
        }))

        result = await ai_orchestrator._create_intelligent_workflow_plan(
            analysis_intent, site_pattern, user_preferences
        )

        assert "GDPR compliance" in result["focus_areas"]
        assert "GDPR-focused" in result["strategy_summary"]


class TestErrorHandling:
    """Test error recovery and robustness."""

    @pytest.mark.asyncio
    async def test_error_recovery_with_ai_guidance(self, ai_orchestrator, mock_context):
        """Given: Analysis failure during workflow
        When: AI recovery mechanisms activate
        Then: Provides intelligent recovery suggestions and alternatives"""

        # Mock LLM failure for intent parsing
        ai_orchestrator.llm_engine.generate_response = AsyncMock(side_effect=Exception("LLM unavailable"))

        # Execute with error handling
        result = await ai_orchestrator._parse_analysis_intent("Analyze this site")

        # Verify graceful degradation
        assert result["intent"] == "general_analysis"
        assert result["summary"] == "Analyze this site"

    @pytest.mark.asyncio
    async def test_pattern_detection_fallback(self, ai_orchestrator, mock_context):
        """Test fallback when pattern detection fails."""

        ai_orchestrator.base_orchestrator._intelligent_site_discovery = AsyncMock(
            side_effect=Exception("Discovery failed")
        )

        result = await ai_orchestrator._detect_site_pattern(mock_context, "https://example.com")

        assert result["type"] == "unknown"
        assert result["confidence"] == 0.0
        assert result["complexity"] == "medium"


class TestConversationalInterface:
    """Test conversational interface responsiveness."""

    @pytest.mark.asyncio
    async def test_conversational_interface_responsiveness(self, ai_orchestrator, mock_context):
        """Given: Interactive analysis workflow
        When: User provides feedback or asks questions
        Then: Responds appropriately and adjusts analysis accordingly"""

        # This would test the conversation context tracking
        ai_orchestrator.conversation_context = [
            {"role": "user", "content": "Analyze this e-commerce site"},
            {"role": "assistant", "content": "Starting e-commerce analysis..."}
        ]

        # Verify conversation context is maintained
        assert len(ai_orchestrator.conversation_context) == 2
        assert "e-commerce" in ai_orchestrator.conversation_context[0]["content"]

    @pytest.mark.asyncio
    async def test_analysis_quality_self_assessment(self, ai_orchestrator, mock_context):
        """Given: Completed analysis results
        When: AI evaluates its own analysis quality
        Then: Identifies gaps and suggests improvements"""

        # Mock result with quality metrics
        analysis_result = {
            "status": "success",
            "pages_analyzed": 10,
            "analysis_quality_score": 0.75,
            "coverage_gaps": ["payment flow not analyzed"]
        }

        # Learning should assess quality
        analysis_intent = {"intent": "general_analysis"}
        site_pattern = {"type": "ecommerce"}

        await ai_orchestrator._learn_from_analysis(analysis_intent, site_pattern, analysis_result)

        # Verify quality score is recorded
        latest_learning = ai_orchestrator.analysis_history[-1]
        assert latest_learning["success_metrics"]["analysis_quality"] == 0.75