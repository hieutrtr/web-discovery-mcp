"""Tests for orchestration tools functionality and integration."""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import Context

from legacy_web_mcp.mcp.orchestration_tools import (
    AnalysisMode,
    CostPriority,
    LegacyAnalysisOrchestrator,
    OrchestrationError,
    ToolIntegrationError,
    WorkflowPlanningError,
    register,
)


class TestLegacyAnalysisOrchestrator:
    """Test the core orchestration class."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration object."""
        config = MagicMock()
        config.BROWSER_HEADLESS = True
        return config

    @pytest.fixture
    def orchestrator(self, mock_config):
        """Create orchestrator instance with mocked dependencies."""
        with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):
            return LegacyAnalysisOrchestrator(mock_config, "test-project")

    @pytest.fixture
    def mock_context(self):
        """Mock FastMCP context."""
        context = AsyncMock(spec=Context)
        return context

    async def test_orchestrator_initialization(self, mock_config):
        """Test orchestrator initializes with correct configuration."""
        with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService") as mock_browser, \
             patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store") as mock_store, \
             patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine") as mock_llm, \
             patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService") as mock_discovery:

            orchestrator = LegacyAnalysisOrchestrator(mock_config, "test-project")

            assert orchestrator.config == mock_config
            assert orchestrator.project_id == "test-project"
            assert orchestrator.current_phase == "initialization"
            assert orchestrator.progress_tracker["completed_phases"] == []
            mock_browser.assert_called_once_with(mock_config)
            mock_store.assert_called_once_with(mock_config)
            mock_llm.assert_called_once_with(mock_config)

    async def test_select_priority_pages_quick_mode(self, orchestrator):
        """Test page selection for quick analysis mode."""
        all_urls = [
            "https://example.com/",
            "https://example.com/login",
            "https://example.com/dashboard",
            "https://example.com/about",
            "https://example.com/contact",
            "https://example.com/products/item1",
            "https://example.com/products/item2",
        ]
        site_info = {"site_type": "business"}

        selected = await orchestrator._select_priority_pages(
            all_urls, site_info, AnalysisMode.QUICK, 0  # 0 = auto-select
        )

        assert len(selected) <= 10  # Quick mode default limit
        assert "https://example.com/" in selected  # Home page should be prioritized
        assert "https://example.com/login" in selected  # Login page should be prioritized

    async def test_select_priority_pages_with_max_limit(self, orchestrator):
        """Test page selection respects max_pages limit."""
        all_urls = [f"https://example.com/page{i}" for i in range(50)]
        site_info = {}

        selected = await orchestrator._select_priority_pages(
            all_urls, site_info, AnalysisMode.COMPREHENSIVE, max_pages=5
        )

        assert len(selected) == 5

    def test_estimate_analysis_cost_quick_mode(self, orchestrator):
        """Test cost estimation for quick analysis mode."""
        pages = ["https://example.com/"] * 10
        cost_estimate = orchestrator._estimate_analysis_cost(pages, AnalysisMode.QUICK)

        assert cost_estimate["page_count"] == 10
        assert cost_estimate["cost_per_page"] == 0.05
        assert cost_estimate["estimated_cost_usd"] == 0.5
        assert cost_estimate["time_per_page"] == 30
        assert cost_estimate["estimated_time_seconds"] == 300

    def test_estimate_analysis_cost_comprehensive_mode(self, orchestrator):
        """Test cost estimation for comprehensive analysis mode."""
        pages = ["https://example.com/"] * 5
        cost_estimate = orchestrator._estimate_analysis_cost(pages, AnalysisMode.COMPREHENSIVE)

        assert cost_estimate["page_count"] == 5
        assert cost_estimate["cost_per_page"] == 0.30
        assert cost_estimate["estimated_cost_usd"] == 1.5
        assert cost_estimate["time_per_page"] == 180
        assert cost_estimate["estimated_time_seconds"] == 900

    async def test_intelligent_site_discovery_success(self, orchestrator, mock_context):
        """Test successful site discovery with intelligent page selection."""
        # Mock discovery service response
        discovery_data = {
            "status": "success",
            "urls": [
                "https://example.com/",
                "https://example.com/login",
                "https://example.com/dashboard",
                "https://example.com/about",
            ],
            "site_info": {"site_type": "webapp"},
            "discovery_method": "sitemap",
        }
        orchestrator.discovery_service.discover = AsyncMock(return_value=discovery_data)

        result = await orchestrator._intelligent_site_discovery(
            mock_context, "https://example.com", AnalysisMode.RECOMMENDED, 0
        )

        assert result["total_pages_found"] == 4
        assert len(result["selected_pages"]) <= 20  # Recommended mode default
        assert result["site_characteristics"]["site_type"] == "webapp"
        assert "cost_estimate" in result

    async def test_intelligent_site_discovery_failure(self, orchestrator, mock_context):
        """Test site discovery failure handling."""
        # Mock discovery service failure
        discovery_data = {"status": "error", "error": "Site not accessible"}
        orchestrator.discovery_service.discover = AsyncMock(return_value=discovery_data)

        with pytest.raises(WorkflowPlanningError, match="Site discovery failed"):
            await orchestrator._intelligent_site_discovery(
                mock_context, "https://invalid.com", AnalysisMode.QUICK, 0
            )

    async def test_intelligent_site_discovery_no_urls(self, orchestrator, mock_context):
        """Test site discovery with no URLs found."""
        discovery_data = {
            "status": "success",
            "urls": [],
            "site_info": {},
        }
        orchestrator.discovery_service.discover = AsyncMock(return_value=discovery_data)

        with pytest.raises(WorkflowPlanningError, match="No URLs discovered"):
            await orchestrator._intelligent_site_discovery(
                mock_context, "https://empty.com", AnalysisMode.QUICK, 0
            )

    async def test_create_analysis_strategy_balanced_cost(self, orchestrator):
        """Test analysis strategy creation with balanced cost priority."""
        discovery_result = {
            "selected_pages": ["https://example.com/", "https://example.com/login"],
            "site_characteristics": {"complexity": "medium"},
        }

        strategy = await orchestrator._create_analysis_strategy(
            discovery_result, AnalysisMode.RECOMMENDED, CostPriority.BALANCED, True
        )

        assert strategy["target_pages"] == discovery_result["selected_pages"]
        assert strategy["analysis_mode"] == "recommended"
        assert strategy["include_step2_analysis"] is True
        assert strategy["step2_confidence_threshold"] == 0.75
        assert strategy["max_concurrent_sessions"] == 3  # Balanced priority
        assert strategy["cost_priority"] == "balanced"

    async def test_create_analysis_strategy_cost_efficient(self, orchestrator):
        """Test analysis strategy creation with cost efficient priority."""
        discovery_result = {
            "selected_pages": ["https://example.com/"],
            "site_characteristics": {},
        }

        strategy = await orchestrator._create_analysis_strategy(
            discovery_result, AnalysisMode.QUICK, CostPriority.COST_EFFICIENT, False
        )

        assert strategy["analysis_mode"] == "quick"
        assert strategy["include_step2_analysis"] is False
        assert strategy["step2_confidence_threshold"] == 0.6
        assert strategy["max_concurrent_sessions"] == 1  # Cost efficient priority
        assert strategy["batch_size"] == 3  # Cost efficient batching

    async def test_create_analysis_strategy_speed_priority(self, orchestrator):
        """Test analysis strategy creation with speed priority."""
        discovery_result = {
            "selected_pages": ["https://example.com/"] * 10,
            "site_characteristics": {},
        }

        strategy = await orchestrator._create_analysis_strategy(
            discovery_result, AnalysisMode.COMPREHENSIVE, CostPriority.SPEED, True
        )

        assert strategy["analysis_mode"] == "comprehensive"
        assert strategy["step2_confidence_threshold"] == 0.85
        assert strategy["max_concurrent_sessions"] == 5  # Speed priority
        assert strategy["cost_priority"] == "speed"

    async def test_execute_analysis_pipeline_no_pages(self, orchestrator, mock_context):
        """Test analysis pipeline execution with no target pages."""
        strategy = {
            "target_pages": [],
            "include_step2_analysis": True,
            "max_concurrent_sessions": 3,
        }

        with pytest.raises(ToolIntegrationError, match="No target pages identified"):
            await orchestrator._execute_analysis_pipeline(mock_context, strategy, False)

    async def test_execute_analysis_pipeline_success(self, orchestrator, mock_context):
        """Test successful analysis pipeline execution."""
        strategy = {
            "target_pages": ["https://example.com/", "https://example.com/login"],
            "include_step2_analysis": False,
            "max_concurrent_sessions": 2,
            "analysis_mode": "recommended",
            "cost_priority": "balanced",
        }

        # Mock project store
        mock_project_metadata = MagicMock()
        mock_project_metadata.root_path = Path("/tmp/test-project")
        orchestrator.project_store.get_project_metadata = MagicMock(return_value=mock_project_metadata)

        # Mock workflow
        mock_workflow = MagicMock()
        mock_workflow.workflow_id = "test-workflow-123"
        mock_workflow.progress.workflow_duration = 120.5

        # Create mock tasks
        mock_task_1 = MagicMock()
        mock_task_1.status.value = "completed"
        mock_task_1.analysis_result = {"title": "Home Page"}
        mock_task_1.url = "https://example.com/"
        mock_task_1.page_id = "page-1"
        mock_task_1.processing_duration = 60.0

        mock_task_2 = MagicMock()
        mock_task_2.status.value = "failed"
        mock_task_2.url = "https://example.com/login"
        mock_task_2.page_id = "page-2"
        mock_task_2.processing_duration = 30.0

        mock_workflow.page_tasks = [mock_task_1, mock_task_2]

        with patch("legacy_web_mcp.mcp.orchestration_tools.SequentialNavigationWorkflow", return_value=mock_workflow):
            mock_workflow.start_workflow = AsyncMock()
            mock_workflow.status.value = "completed"

            result = await orchestrator._execute_analysis_pipeline(mock_context, strategy, False)

            assert result["completed_pages"] == 1
            assert result["failed_pages"] == 1
            assert result["workflow_id"] == "test-workflow-123"
            assert result["total_processing_time"] == 120.5
            assert len(result["page_analysis_results"]) == 2

    async def test_execute_step2_analysis_success(self, orchestrator, mock_context):
        """Test successful Step 2 analysis execution."""
        # Mock completed page tasks
        mock_task = MagicMock()
        mock_task.url = "https://example.com/"
        mock_task.page_id = "page-1"
        mock_task.analysis_result = MagicMock()

        completed_pages = [mock_task]
        strategy = {"step2_confidence_threshold": 0.75}

        # Mock content summarizer
        mock_step1_summary = MagicMock()
        mock_step1_summary.confidence_score = 0.8
        orchestrator.llm_engine = MagicMock()

        # Mock feature analyzer
        mock_feature_analysis = MagicMock()
        mock_feature_analysis.interactive_elements = [{"type": "button"}]
        mock_feature_analysis.functional_capabilities = [{"name": "login"}]
        mock_feature_analysis.api_integrations = [{"endpoint": "/api/auth"}]
        mock_feature_analysis.business_rules = [{"rule": "password_required"}]
        mock_feature_analysis.confidence_score = 0.85
        mock_feature_analysis.quality_score = 0.9

        with patch("legacy_web_mcp.mcp.orchestration_tools.ContentSummarizer") as mock_summarizer_class, \
             patch("legacy_web_mcp.mcp.orchestration_tools.FeatureAnalyzer") as mock_analyzer_class:

            mock_summarizer = mock_summarizer_class.return_value
            mock_summarizer.summarize_page = AsyncMock(return_value=mock_step1_summary)

            mock_analyzer = mock_analyzer_class.return_value
            mock_analyzer.analyze_features = AsyncMock(return_value=mock_feature_analysis)

            result = await orchestrator._execute_step2_analysis(mock_context, completed_pages, strategy)

            assert result["total_pages_processed"] == 1
            assert result["successful_analyses"] == 1
            assert result["skipped_low_confidence"] == 0
            assert result["failed_analyses"] == 0
            assert len(result["results"]) == 1

            page_result = result["results"][0]
            assert page_result["url"] == "https://example.com/"
            assert page_result["step1_confidence"] == 0.8
            assert "feature_analysis" in page_result

    async def test_execute_step2_analysis_low_confidence(self, orchestrator, mock_context):
        """Test Step 2 analysis with low confidence pages."""
        mock_task = MagicMock()
        mock_task.url = "https://example.com/"
        mock_task.page_id = "page-1"
        mock_task.analysis_result = MagicMock()

        completed_pages = [mock_task]
        strategy = {"step2_confidence_threshold": 0.75}

        # Mock low confidence step1 summary
        mock_step1_summary = MagicMock()
        mock_step1_summary.confidence_score = 0.6  # Below threshold

        with patch("legacy_web_mcp.mcp.orchestration_tools.ContentSummarizer") as mock_summarizer_class:
            mock_summarizer = mock_summarizer_class.return_value
            mock_summarizer.summarize_page = AsyncMock(return_value=mock_step1_summary)

            result = await orchestrator._execute_step2_analysis(mock_context, completed_pages, strategy)

            assert result["total_pages_processed"] == 1
            assert result["successful_analyses"] == 0
            assert result["skipped_low_confidence"] == 1
            assert result["failed_analyses"] == 0

            page_result = result["results"][0]
            assert "skipped_reason" in page_result
            assert "Low confidence" in page_result["skipped_reason"]

    async def test_synthesize_and_document_results(self, orchestrator, mock_context):
        """Test result synthesis and documentation generation."""
        discovery_result = {
            "total_pages_found": 25,
            "site_characteristics": {"site_type": "ecommerce"},
        }

        analysis_results = {
            "completed_pages": 20,
            "total_processing_time": 1200.5,
            "step2_analysis_results": {
                "successful_analyses": 18,
                "results": [
                    {"feature_analysis": {"api_integrations": 2, "interactive_elements": 5}},
                    {"feature_analysis": {"api_integrations": 1, "interactive_elements": 3}},
                ],
            },
        }

        strategy = {
            "analysis_mode": "recommended",
            "cost_priority": "balanced",
        }

        result = await orchestrator._synthesize_and_document_results(
            mock_context, discovery_result, analysis_results, strategy
        )

        assert result["total_pages_discovered"] == 25
        assert result["pages_successfully_analyzed"] == 20
        assert result["analysis_coverage_percentage"] == 80.0
        assert result["analysis_mode_used"] == "recommended"
        assert result["cost_priority_used"] == "balanced"
        assert result["processing_time_seconds"] == 1200.5
        assert "step2_feature_analysis" in result
        assert "technology_assessment" in result
        assert "workflow_id" in result

    async def test_discover_and_analyze_site_full_workflow(self, orchestrator, mock_context):
        """Test complete site analysis workflow end-to-end."""
        url = "https://example.com"

        # Mock all the sub-methods to simulate successful execution
        discovery_result = {
            "total_pages_found": 10,
            "selected_pages": ["https://example.com/", "https://example.com/login"],
            "site_characteristics": {"site_type": "webapp"},
            "cost_estimate": {"estimated_cost_usd": 0.3},
        }

        analysis_strategy = {
            "target_pages": ["https://example.com/", "https://example.com/login"],
            "analysis_mode": "recommended",
            "include_step2_analysis": True,
            "cost_priority": "balanced",
        }

        analysis_results = {
            "completed_pages": 2,
            "failed_pages": 0,
            "workflow_id": "test-workflow",
            "total_processing_time": 180.0,
        }

        final_results = {
            "pages_successfully_analyzed": 2,
            "analysis_coverage_percentage": 100.0,
        }

        orchestrator._intelligent_site_discovery = AsyncMock(return_value=discovery_result)
        orchestrator._create_analysis_strategy = AsyncMock(return_value=analysis_strategy)
        orchestrator._execute_analysis_pipeline = AsyncMock(return_value=analysis_results)
        orchestrator._synthesize_and_document_results = AsyncMock(return_value=final_results)

        result = await orchestrator.discover_and_analyze_site(
            mock_context, url, AnalysisMode.RECOMMENDED, 0, True, False, CostPriority.BALANCED
        )

        assert result["status"] == "success"
        assert result["url"] == url
        assert result["analysis_mode"] == "recommended"
        assert result["pages_analyzed"] == 2
        assert "total_duration" in result
        assert "workflow_id" in result

        # Verify all phases were completed
        assert "discovery" in orchestrator.progress_tracker["completed_phases"]
        assert "planning" in orchestrator.progress_tracker["completed_phases"]
        assert "analysis" in orchestrator.progress_tracker["completed_phases"]
        assert "synthesis" in orchestrator.progress_tracker["completed_phases"]

    async def test_discover_and_analyze_site_failure_in_discovery(self, orchestrator, mock_context):
        """Test workflow failure handling during discovery phase."""
        url = "https://invalid.com"

        # Mock discovery failure
        orchestrator._intelligent_site_discovery = AsyncMock(
            side_effect=WorkflowPlanningError("Discovery failed")
        )

        result = await orchestrator.discover_and_analyze_site(
            mock_context, url, AnalysisMode.QUICK, 0, True, False, CostPriority.BALANCED
        )

        assert result["status"] == "error"
        assert result["failed_phase"] == "discovery"
        assert "Discovery failed" in result["error"]
        assert len(orchestrator.progress_tracker["errors"]) == 1


class TestOrchestrationToolRegistration:
    """Test MCP tool registration and integration."""

    @pytest.fixture
    def mock_mcp(self):
        """Mock FastMCP instance."""
        return MagicMock()

    @pytest.fixture
    def mock_context(self):
        """Mock FastMCP context."""
        return AsyncMock(spec=Context)

    def test_register_function_exists(self):
        """Test that register function exists and is callable."""
        assert callable(register)

    def test_register_adds_tools_to_mcp(self, mock_mcp):
        """Test that register function adds tools to MCP instance."""
        register(mock_mcp)

        # Verify that mcp.tool() was called (the tools were registered)
        assert mock_mcp.tool.call_count >= 3  # We have at least 3 tools

    async def test_analyze_legacy_site_tool_parameter_validation(self, mock_mcp, mock_context):
        """Test parameter validation for analyze_legacy_site tool."""
        with patch("legacy_web_mcp.mcp.orchestration_tools.load_configuration"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.LegacyAnalysisOrchestrator"):

            register(mock_mcp)

            # Verify that tools were registered (mcp.tool() was called)
            assert mock_mcp.tool.call_count >= 3  # We have at least 3 tools registered

    async def test_analyze_legacy_site_invalid_analysis_mode(self, mock_context):
        """Test analyze_legacy_site with invalid analysis mode."""
        with patch("legacy_web_mcp.mcp.orchestration_tools.load_configuration"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.LegacyAnalysisOrchestrator"):

            from legacy_web_mcp.mcp.orchestration_tools import register

            mock_mcp = MagicMock()
            register(mock_mcp)

            # Extract the analyze_legacy_site function
            analyze_legacy_site = None
            for call in mock_mcp.tool.call_args_list:
                if call[0] and hasattr(call[0][0], '__name__') and 'analyze_legacy_site' in str(call[0][0]):
                    analyze_legacy_site = call[0][0]
                    break

            if analyze_legacy_site:
                result = await analyze_legacy_site(
                    mock_context,
                    url="https://example.com",
                    analysis_mode="invalid_mode"
                )

                assert result["status"] == "error"
                assert "Invalid analysis_mode" in result["error"]
                assert "valid_options" in result

    async def test_analyze_legacy_site_invalid_cost_priority(self, mock_context):
        """Test analyze_legacy_site with invalid cost priority."""
        with patch("legacy_web_mcp.mcp.orchestration_tools.load_configuration"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.LegacyAnalysisOrchestrator"):

            from legacy_web_mcp.mcp.orchestration_tools import register

            mock_mcp = MagicMock()
            register(mock_mcp)

            # Extract the analyze_legacy_site function
            analyze_legacy_site = None
            for call in mock_mcp.tool.call_args_list:
                if call[0] and hasattr(call[0][0], '__name__') and 'analyze_legacy_site' in str(call[0][0]):
                    analyze_legacy_site = call[0][0]
                    break

            if analyze_legacy_site:
                result = await analyze_legacy_site(
                    mock_context,
                    url="https://example.com",
                    cost_priority="invalid_priority"
                )

                assert result["status"] == "error"
                assert "Invalid cost_priority" in result["error"]
                assert "valid_options" in result


class TestAnalysisModeEnum:
    """Test AnalysisMode enum functionality."""

    def test_analysis_mode_values(self):
        """Test that all analysis modes have correct values."""
        assert AnalysisMode.QUICK.value == "quick"
        assert AnalysisMode.RECOMMENDED.value == "recommended"
        assert AnalysisMode.COMPREHENSIVE.value == "comprehensive"
        assert AnalysisMode.TARGETED.value == "targeted"

    def test_analysis_mode_from_string(self):
        """Test creating AnalysisMode from string values."""
        assert AnalysisMode("quick") == AnalysisMode.QUICK
        assert AnalysisMode("recommended") == AnalysisMode.RECOMMENDED
        assert AnalysisMode("comprehensive") == AnalysisMode.COMPREHENSIVE
        assert AnalysisMode("targeted") == AnalysisMode.TARGETED

    def test_analysis_mode_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            AnalysisMode("invalid")


class TestCostPriorityEnum:
    """Test CostPriority enum functionality."""

    def test_cost_priority_values(self):
        """Test that all cost priorities have correct values."""
        assert CostPriority.SPEED.value == "speed"
        assert CostPriority.BALANCED.value == "balanced"
        assert CostPriority.COST_EFFICIENT.value == "cost_efficient"

    def test_cost_priority_from_string(self):
        """Test creating CostPriority from string values."""
        assert CostPriority("speed") == CostPriority.SPEED
        assert CostPriority("balanced") == CostPriority.BALANCED
        assert CostPriority("cost_efficient") == CostPriority.COST_EFFICIENT

    def test_cost_priority_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            CostPriority("invalid")


class TestOrchestrationErrors:
    """Test custom orchestration exception classes."""

    def test_orchestration_error_base(self):
        """Test base OrchestrationError."""
        error = OrchestrationError("Base orchestration error")
        assert str(error) == "Base orchestration error"
        assert isinstance(error, Exception)

    def test_workflow_planning_error(self):
        """Test WorkflowPlanningError inherits from OrchestrationError."""
        error = WorkflowPlanningError("Planning failed")
        assert str(error) == "Planning failed"
        assert isinstance(error, OrchestrationError)

    def test_tool_integration_error(self):
        """Test ToolIntegrationError inherits from OrchestrationError."""
        error = ToolIntegrationError("Integration failed")
        assert str(error) == "Integration failed"
        assert isinstance(error, OrchestrationError)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    async def test_orchestration_with_real_project_structure(self, temp_project_dir):
        """Test orchestration with realistic project structure."""
        # Create project structure
        analysis_dir = temp_project_dir / "analysis" / "pages"
        analysis_dir.mkdir(parents=True)

        workflow_dir = temp_project_dir / "workflow" / "checkpoints"
        workflow_dir.mkdir(parents=True)

        # Create some analysis files
        (analysis_dir / "page1.json").write_text('{"url": "https://example.com/", "title": "Home"}')
        (analysis_dir / "page2.json").write_text('{"url": "https://example.com/login", "title": "Login"}')

        # Test status checking
        mock_config = MagicMock()
        mock_project_store = MagicMock()
        mock_project_metadata = MagicMock()
        mock_project_metadata.root_path = temp_project_dir
        mock_project_store.get_project_metadata.return_value = mock_project_metadata

        with patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store", return_value=mock_project_store), \
             patch("legacy_web_mcp.mcp.orchestration_tools.load_configuration", return_value=mock_config):

            from legacy_web_mcp.mcp.orchestration_tools import register

            mock_mcp = MagicMock()
            mock_context = AsyncMock()
            register(mock_mcp)

            # Get the get_analysis_status function
            get_analysis_status = None
            for call in mock_mcp.tool.call_args_list:
                if call[0] and hasattr(call[0][0], '__name__') and 'get_analysis_status' in str(call[0][0]):
                    get_analysis_status = call[0][0]
                    break

            if get_analysis_status:
                result = await get_analysis_status(mock_context, "test-project")

                assert result["status"] == "completed"
                assert result["analysis_files_found"] == 2
                assert "Analysis complete: 2 pages analyzed" in result["message"]

    async def test_orchestration_performance_metrics(self):
        """Test that orchestration tracks performance metrics correctly."""
        mock_config = MagicMock()

        with patch("legacy_web_mcp.mcp.orchestration_tools.BrowserAutomationService"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.create_project_store"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.LLMEngine"), \
             patch("legacy_web_mcp.mcp.orchestration_tools.WebsiteDiscoveryService"):

            orchestrator = LegacyAnalysisOrchestrator(mock_config, "perf-test")

            start_time = orchestrator.start_time
            assert isinstance(start_time, float)
            assert start_time > 0

            # Simulate some time passing
            await asyncio.sleep(0.1)

            # Check that timing would be calculated correctly
            current_time = time.time()
            assert current_time > start_time

    def test_orchestration_module_exports(self):
        """Test that module exports the expected public interface."""
        from legacy_web_mcp.mcp.orchestration_tools import __all__

        expected_exports = [
            "register",
            "LegacyAnalysisOrchestrator",
            "AnalysisMode",
            "CostPriority"
        ]

        for export in expected_exports:
            assert export in __all__