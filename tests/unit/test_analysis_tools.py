"""Tests for the analysis MCP tools."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastmcp import Context, FastMCP

from legacy_web_mcp.browser.analysis import PageAnalysisData, PageAnalyzer
from legacy_web_mcp.mcp.analysis_tools import register


class TestAnalysisTools:
    """Test the analysis MCP tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create a FastMCP server with analysis tools registered."""
        mcp = FastMCP(name="test-server")
        register(mcp)
        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        context = AsyncMock(spec=Context)
        return context

    @pytest.fixture
    def mock_browser_service(self):
        """Create a mock browser automation service."""
        service = AsyncMock()
        session = AsyncMock()
        session.page = AsyncMock()
        session.session_id = "test-session"
        service.get_session.return_value.__aenter__.return_value = session
        return service

    @pytest.fixture
    def mock_analysis_result(self):
        """Create a mock analysis result."""
        from legacy_web_mcp.browser.analysis import (
            DOMStructureAnalysis,
            FunctionalityAnalysis,
            AccessibilityAnalysis,
            TechnologyAnalysis,
            CSSAnalysis,
            PerformanceAnalysis,
            JSFramework,
            PageType,
        )
        from datetime import UTC, datetime

        analysis_data = PageAnalysisData(
            url="https://example.com/test",
            title="Test Page",
            description="A test page",
            timestamp=datetime.now(UTC),
        )

        analysis_data.dom_analysis = DOMStructureAnalysis(
            total_elements=150,
            interactive_elements=25,
            form_elements=2,
            semantic_elements=20,
        )

        analysis_data.functionality_analysis = FunctionalityAnalysis(
            page_type=PageType.FORM_PAGE,
            primary_functions=["data_collection", "user_interaction"],
            navigation_complexity="moderate",
            content_density="medium",
            form_complexity="simple",
        )

        analysis_data.accessibility_analysis = AccessibilityAnalysis(
            aria_labels=[{"role": "button", "label": "Submit", "tag": "button"}],
            alt_texts=["Company logo", "Product image"],
            heading_hierarchy=[{"level": 1, "text": "Main Title"}],
            semantic_roles=["button", "textbox"],
        )

        analysis_data.technology_analysis = TechnologyAnalysis(
            js_frameworks=[JSFramework.REACT],
            js_libraries=["lodash", "axios"],
            css_frameworks=["bootstrap"],
            cms_detection="WordPress",
        )

        analysis_data.css_analysis = CSSAnalysis(
            external_stylesheets=["https://cdn.bootstrap.com/css/bootstrap.css"],
            inline_styles_count=5,
            responsive_breakpoints=[768, 1024],
            css_frameworks_detected=["bootstrap"],
        )

        analysis_data.performance_analysis = PerformanceAnalysis(
            navigation_timing={"total_load": 2500, "dns_lookup": 50},
            resource_timing={"total_size": 1024000, "resource_count": 20},
            total_resource_size=1024000,
            javascript_bundle_size=512000,
            css_bundle_size=102400,
        )

        analysis_data.analysis_duration = 5.2

        return analysis_data

    @pytest.mark.asyncio
    async def test_analyze_page_comprehensive_success(
        self, mcp_server, mock_context, mock_browser_service, mock_analysis_result
    ):
        """Test successful comprehensive page analysis."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.create_project_store") as mock_store_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_analyzer_cls:

            # Setup mocks
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_cls.return_value = mock_browser_service

            mock_project_store = Mock()
            mock_project_metadata = Mock()
            mock_project_metadata.root_path = Path("/tmp/test-project")
            mock_project_store.get_project_metadata.return_value = mock_project_metadata
            mock_store_cls.return_value = mock_project_store

            mock_analyzer = Mock()
            mock_analyzer.analyze_page.return_value = mock_analysis_result
            mock_analyzer_cls.return_value = mock_analyzer

            # Get the tool function
            tools = await mcp_server.get_tools()
            analyze_tool = None
            for tool_name, tool_func in tools.items():
                if tool_name == "analyze_page_comprehensive":
                    analyze_tool = tool_func
                    break

            assert analyze_tool is not None

            # Call the tool
            result = await analyze_tool(
                context=mock_context,
                url="https://example.com/test",
                project_id="test-project",
                include_network_monitoring=True,
                include_interaction_simulation=True,
                save_analysis_data=True,
            )

            # Verify result structure
            assert result["status"] == "success"
            assert result["url"] == "https://example.com/test"
            assert result["project_id"] == "test-project"
            assert "analysis_summary" in result
            assert "page_classification" in result
            assert "technology_stack" in result
            assert "accessibility_score" in result
            assert "performance_metrics" in result
            assert "complexity_assessment" in result

            # Verify analysis summary
            summary = result["analysis_summary"]
            assert summary["total_elements"] == 150
            assert summary["interactive_elements"] == 25
            assert summary["page_type"] == "form_page"
            assert "complexity_score" in summary
            assert "modernization_priority" in summary

            # Verify technology stack
            tech_stack = result["technology_stack"]
            assert "react" in tech_stack["javascript_frameworks"]
            assert "lodash" in tech_stack["javascript_libraries"]
            assert "bootstrap" in tech_stack["css_frameworks"]
            assert tech_stack["cms_detected"] == "WordPress"

            # Verify performance metrics
            perf_metrics = result["performance_metrics"]
            assert perf_metrics["load_time_seconds"] == 2.5
            assert perf_metrics["total_resource_size_kb"] == 1000
            assert perf_metrics["javascript_bundle_size_kb"] == 500

            # Verify accessibility score
            access_score = result["accessibility_score"]
            assert access_score["semantic_elements"] == 20
            assert access_score["aria_usage_count"] == 1
            assert access_score["alt_text_coverage"] == 2

            # Verify complexity assessment
            complexity = result["complexity_assessment"]
            assert "overall_score" in complexity
            assert "modernization_priority" in complexity
            assert "technical_debt_indicators" in complexity

            assert result["analysis_duration"] == 5.2

    @pytest.mark.asyncio
    async def test_analyze_page_comprehensive_error_handling(
        self, mcp_server, mock_context
    ):
        """Test error handling in comprehensive page analysis."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls:

            # Setup mocks to raise an exception
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_service = AsyncMock()
            mock_browser_service.get_session.side_effect = Exception("Browser session failed")
            mock_browser_cls.return_value = mock_browser_service

            # Get the tool function
            tools = await mcp_server.get_tools()
            analyze_tool = tools["analyze_page_comprehensive"]

            # Call the tool
            result = await analyze_tool(
                context=mock_context,
                url="https://example.com/test",
            )

            # Verify error result
            assert result["status"] == "error"
            assert result["url"] == "https://example.com/test"
            assert "error" in result
            assert "Browser session failed" in result["error"]
            assert result["error_type"] == "Exception"

    @pytest.mark.asyncio
    async def test_analyze_dom_structure_success(
        self, mcp_server, mock_context, mock_browser_service
    ):
        """Test successful DOM structure analysis."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_analyzer_cls:

            # Setup mocks
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_cls.return_value = mock_browser_service

            # Mock DOM analysis result
            from legacy_web_mcp.browser.analysis import DOMStructureAnalysis

            dom_result = DOMStructureAnalysis(
                total_elements=200,
                semantic_elements=30,
                interactive_elements=40,
                form_elements=3,
                link_elements=25,
                image_elements=10,
                max_nesting_depth=8,
                forms=[
                    {
                        "action": "/submit",
                        "method": "POST",
                        "inputs": 5,
                        "buttons": 2,
                    }
                ],
                buttons=[
                    {"type": "submit", "text": "Submit", "disabled": False},
                    {"type": "button", "text": "Cancel", "disabled": False},
                ],
                inputs=[
                    {"type": "text", "name": "username", "required": True},
                    {"type": "email", "name": "email", "required": True},
                ],
            )

            mock_analyzer = Mock()
            mock_analyzer._analyze_dom_structure.return_value = dom_result
            mock_analyzer_cls.return_value = mock_analyzer

            # Mock additional page evaluations for interactivity and form details
            mock_page = mock_browser_service.get_session.return_value.__aenter__.return_value.page
            mock_page.evaluate.side_effect = [
                {  # interactivity_details
                    "clickable_elements": 15,
                    "focusable_elements": 25,
                    "hover_targets": 5,
                    "keyboard_shortcuts": 2,
                    "dynamic_content": 8,
                },
                [  # form_details
                    {
                        "action": "/api/submit",
                        "method": "POST",
                        "fields": [
                            {
                                "type": "text",
                                "name": "username",
                                "required": True,
                                "validation_attributes": {
                                    "required": True,
                                    "pattern": False,
                                    "min_max": False,
                                    "length_limits": True,
                                }
                            }
                        ]
                    }
                ]
            ]

            # Get the tool function
            tools = await mcp_server.get_tools()
            dom_tool = tools["analyze_dom_structure"]

            # Call the tool
            result = await dom_tool(
                context=mock_context,
                url="https://example.com/test",
                focus_on_interactivity=True,
                extract_form_details=True,
            )

            # Verify result structure
            assert result["status"] == "success"
            assert result["url"] == "https://example.com/test"

            # Verify DOM metrics
            dom_metrics = result["dom_metrics"]
            assert dom_metrics["total_elements"] == 200
            assert dom_metrics["semantic_elements"] == 30
            assert dom_metrics["interactive_elements"] == 40
            assert dom_metrics["form_elements"] == 3

            # Verify semantic structure
            semantic = result["semantic_structure"]
            assert semantic["max_nesting_depth"] == 8

            # Verify interactive elements
            interactive = result["interactive_elements"]
            assert len(interactive["forms"]) == 1
            assert len(interactive["buttons"]) == 2
            assert interactive["clickable_elements"] == 15

            # Verify complexity indicators
            complexity = result["complexity_indicators"]
            assert "structural_complexity" in complexity
            assert "interactivity_ratio" in complexity
            assert "nesting_depth" in complexity

            # Verify form analysis
            form_analysis = result["form_analysis"]
            assert form_analysis["total_forms"] == 1
            assert len(form_analysis["form_details"]) == 1

    @pytest.mark.asyncio
    async def test_detect_technologies_success(
        self, mcp_server, mock_context, mock_browser_service
    ):
        """Test successful technology detection."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_analyzer_cls:

            # Setup mocks
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_cls.return_value = mock_browser_service

            # Mock technology analysis result
            from legacy_web_mcp.browser.analysis import TechnologyAnalysis, JSFramework

            tech_result = TechnologyAnalysis(
                js_frameworks=[JSFramework.REACT, JSFramework.VUE],
                js_libraries=["lodash", "axios", "moment"],
                css_frameworks=["bootstrap", "tailwind"],
                cms_detection="WordPress",
            )

            mock_analyzer = Mock()
            mock_analyzer._analyze_technology.return_value = tech_result
            mock_analyzer_cls.return_value = mock_analyzer

            # Mock page evaluations for deep scan and version detection
            mock_page = mock_browser_service.get_session.return_value.__aenter__.return_value.page
            mock_page.evaluate.side_effect = [
                {  # deep_scan_results
                    "meta_frameworks": ["Next.js"],
                    "build_tools": ["Webpack", "Babel"],
                    "hosting_indicators": [],
                    "analytics_tools": ["Google Analytics", "Mixpanel"],
                    "performance_tools": ["Sentry"],
                    "testing_tools": [],
                },
                {  # version_info
                    "React": "18.2.0",
                    "jQuery": "3.6.0",
                },
                "WordPress",  # cms_detection
            ]

            # Get the tool function
            tools = await mcp_server.get_tools()
            tech_tool = tools["detect_technologies"]

            # Call the tool
            result = await tech_tool(
                context=mock_context,
                url="https://example.com/test",
                deep_scan=True,
                include_version_detection=True,
            )

            # Verify result structure
            assert result["status"] == "success"
            assert result["url"] == "https://example.com/test"

            # Verify JavaScript technologies
            js_tech = result["javascript_technologies"]
            assert "react" in js_tech["frameworks"]
            assert "vue" in js_tech["frameworks"]
            assert "lodash" in js_tech["libraries"]
            assert js_tech["versions"]["React"] == "18.2.0"
            assert "Next.js" in js_tech["meta_frameworks"]

            # Verify CSS technologies
            css_tech = result["css_technologies"]
            assert "bootstrap" in css_tech["frameworks"]
            assert "tailwind" in css_tech["frameworks"]

            # Verify build tools
            assert "Webpack" in result["build_tools"]
            assert "Babel" in result["build_tools"]

            # Verify CMS detection
            assert result["cms_platform"] == "WordPress"

            # Verify analytics tools
            assert "Google Analytics" in result["analytics_tools"]
            assert "Mixpanel" in result["analytics_tools"]

            # Verify performance tools
            assert "Sentry" in result["performance_tools"]

            # Verify modernization assessment
            modernization = result["modernization_assessment"]
            assert "priority" in modernization
            assert "modernization_score" in modernization
            assert "recommendations" in modernization
            assert "technology_age" in modernization

    @pytest.mark.asyncio
    async def test_detect_technologies_no_deep_scan(
        self, mcp_server, mock_context, mock_browser_service
    ):
        """Test technology detection without deep scan."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_analyzer_cls:

            # Setup mocks
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_cls.return_value = mock_browser_service

            # Mock technology analysis result
            from legacy_web_mcp.browser.analysis import TechnologyAnalysis, JSFramework

            tech_result = TechnologyAnalysis(
                js_frameworks=[JSFramework.JQUERY],
                js_libraries=["jquery"],
                css_frameworks=[],
            )

            mock_analyzer = Mock()
            mock_analyzer._analyze_technology.return_value = tech_result
            mock_analyzer_cls.return_value = mock_analyzer

            # Mock page evaluation for CMS detection only
            mock_page = mock_browser_service.get_session.return_value.__aenter__.return_value.page
            mock_page.evaluate.return_value = None  # No CMS detected

            # Get the tool function
            tools = await mcp_server.get_tools()
            tech_tool = tools["detect_technologies"]

            # Call the tool without deep scan
            result = await tech_tool(
                context=mock_context,
                url="https://example.com/legacy-site",
                deep_scan=False,
                include_version_detection=False,
            )

            # Verify result structure
            assert result["status"] == "success"
            assert "jquery" in result["javascript_technologies"]["frameworks"]
            assert result["cms_platform"] is None

            # Verify modernization assessment suggests high priority for jQuery-only sites
            modernization = result["modernization_assessment"]
            assert modernization["priority"] in ["high", "medium"]  # Should suggest modernization

    @pytest.mark.asyncio
    async def test_analyze_dom_structure_without_forms(
        self, mcp_server, mock_context, mock_browser_service
    ):
        """Test DOM structure analysis for a page without forms."""
        with patch("legacy_web_mcp.mcp.analysis_tools.load_configuration") as mock_config, \
             patch("legacy_web_mcp.mcp.analysis_tools.BrowserAutomationService") as mock_browser_cls, \
             patch("legacy_web_mcp.mcp.analysis_tools.PageAnalyzer") as mock_analyzer_cls:

            # Setup mocks
            mock_config.return_value = Mock(BROWSER_HEADLESS=True)
            mock_browser_cls.return_value = mock_browser_service

            # Mock DOM analysis result for content page
            from legacy_web_mcp.browser.analysis import DOMStructureAnalysis

            dom_result = DOMStructureAnalysis(
                total_elements=80,
                semantic_elements=15,
                interactive_elements=8,
                form_elements=0,  # No forms
                link_elements=12,
                image_elements=5,
                max_nesting_depth=4,
                forms=[],  # Empty forms array
                buttons=[],  # No buttons
                inputs=[],  # No inputs
            )

            mock_analyzer = Mock()
            mock_analyzer._analyze_dom_structure.return_value = dom_result
            mock_analyzer_cls.return_value = mock_analyzer

            # Mock page evaluations
            mock_page = mock_browser_service.get_session.return_value.__aenter__.return_value.page
            mock_page.evaluate.side_effect = [
                {  # interactivity_details
                    "clickable_elements": 8,
                    "focusable_elements": 12,
                    "hover_targets": 2,
                    "keyboard_shortcuts": 0,
                    "dynamic_content": 3,
                },
                [],  # form_details - empty array
            ]

            # Get the tool function
            tools = await mcp_server.get_tools()
            dom_tool = tools["analyze_dom_structure"]

            # Call the tool
            result = await dom_tool(
                context=mock_context,
                url="https://example.com/content-page",
                extract_form_details=True,
            )

            # Verify result
            assert result["status"] == "success"
            assert result["dom_metrics"]["form_elements"] == 0
            assert result["form_analysis"]["total_forms"] == 0
            assert len(result["form_analysis"]["form_details"]) == 0

            # Verify complexity indicators reflect simple structure
            complexity = result["complexity_indicators"]
            assert complexity["form_complexity"] == 0
            assert not complexity["modernization_needs"]  # Simple content page

    def test_mcp_tools_registration(self, mcp_server):
        """Test that all analysis tools are properly registered."""
        # This is a synchronous test to verify tool registration
        import asyncio
        tools = asyncio.run(mcp_server.get_tools())

        expected_tools = [
            "analyze_page_comprehensive",
            "analyze_dom_structure",
            "detect_technologies",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"Tool {tool_name} not registered"

        # Verify tool functions are callable
        for tool_name, tool_func in tools.items():
            if tool_name in expected_tools:
                assert callable(tool_func), f"Tool {tool_name} is not callable"


class TestAnalysisUtilityFunctions:
    """Test utility functions used by analysis tools."""

    def test_calculate_complexity_score(self):
        """Test complexity score calculation."""
        from legacy_web_mcp.mcp.analysis_tools import _calculate_complexity_score
        from legacy_web_mcp.browser.analysis import (
            PageAnalysisData,
            DOMStructureAnalysis,
            TechnologyAnalysis,
            PerformanceAnalysis,
            JSFramework,
        )

        # Create analysis result with high complexity
        analysis_result = PageAnalysisData(
            url="https://example.com",
            title="Complex App",
        )

        analysis_result.dom_analysis = DOMStructureAnalysis(
            total_elements=600,  # High element count
            interactive_elements=80,
            form_elements=8,
        )

        analysis_result.technology_analysis = TechnologyAnalysis(
            js_frameworks=[JSFramework.REACT, JSFramework.VUE, JSFramework.ANGULAR],  # Multiple frameworks
        )

        analysis_result.performance_analysis = PerformanceAnalysis(
            navigation_timing={"total_load": 6000}  # Slow load time
        )

        score = _calculate_complexity_score(analysis_result)

        # Should be a high complexity score
        assert score > 70

    def test_determine_modernization_priority(self):
        """Test modernization priority determination."""
        from legacy_web_mcp.mcp.analysis_tools import _determine_modernization_priority
        from legacy_web_mcp.browser.analysis import (
            PageAnalysisData,
            DOMStructureAnalysis,
            TechnologyAnalysis,
            FunctionalityAnalysis,
            PageType,
        )

        # Test high priority case - admin panel without modern frameworks
        analysis_result = PageAnalysisData(url="https://example.com", title="Admin")
        analysis_result.dom_analysis = DOMStructureAnalysis(total_elements=400, form_elements=5)
        analysis_result.technology_analysis = TechnologyAnalysis(js_frameworks=[])  # No frameworks
        analysis_result.functionality_analysis = FunctionalityAnalysis(page_type=PageType.ADMIN_PANEL)

        priority = _determine_modernization_priority(analysis_result)
        assert priority == "high"

        # Test low priority case - simple content page
        analysis_result.dom_analysis = DOMStructureAnalysis(total_elements=50, form_elements=0)
        analysis_result.functionality_analysis = FunctionalityAnalysis(page_type=PageType.UNKNOWN)

        priority = _determine_modernization_priority(analysis_result)
        assert priority == "low"

    def test_assess_accessibility_compliance(self):
        """Test accessibility compliance assessment."""
        from legacy_web_mcp.mcp.analysis_tools import _assess_accessibility_compliance
        from legacy_web_mcp.browser.analysis import (
            PageAnalysisData,
            DOMStructureAnalysis,
            AccessibilityAnalysis,
        )

        # Test page with good accessibility
        analysis_result = PageAnalysisData(url="https://example.com", title="Accessible Page")
        analysis_result.dom_analysis = DOMStructureAnalysis(
            image_elements=5,
            form_elements=2,
        )
        analysis_result.accessibility_analysis = AccessibilityAnalysis(
            aria_labels=[{"role": "button", "label": "Submit", "tag": "button"}],
            alt_texts=["Logo", "Hero image", "Product photo", "Icon", "Chart"],  # All images have alt text
            heading_hierarchy=[{"level": 1, "text": "Main Title"}],
            semantic_roles=["button", "textbox"],
        )

        compliance = _assess_accessibility_compliance(analysis_result)
        assert compliance["compliance_score"] >= 80
        assert len(compliance["violations"]) <= 1

        # Test page with poor accessibility
        analysis_result.accessibility_analysis = AccessibilityAnalysis(
            aria_labels=[],  # No ARIA labels
            alt_texts=["Logo"],  # Missing alt text for 4 images
            heading_hierarchy=[],  # No headings
            semantic_roles=[],  # No semantic roles
        )

        compliance = _assess_accessibility_compliance(analysis_result)
        assert compliance["compliance_score"] < 50
        assert len(compliance["violations"]) >= 3

    def test_calculate_performance_score(self):
        """Test performance score calculation."""
        from legacy_web_mcp.mcp.analysis_tools import _calculate_performance_score
        from legacy_web_mcp.browser.analysis import PageAnalysisData, PerformanceAnalysis

        # Test fast loading page
        analysis_result = PageAnalysisData(url="https://example.com", title="Fast Page")
        analysis_result.performance_analysis = PerformanceAnalysis(
            navigation_timing={"total_load": 1500},  # 1.5 seconds
            total_resource_size=512 * 1024,  # 512KB
            javascript_bundle_size=256 * 1024,  # 256KB
        )

        score = _calculate_performance_score(analysis_result)
        assert score >= 80

        # Test slow loading page
        analysis_result.performance_analysis = PerformanceAnalysis(
            navigation_timing={"total_load": 8000},  # 8 seconds
            total_resource_size=10 * 1024 * 1024,  # 10MB
            javascript_bundle_size=3 * 1024 * 1024,  # 3MB
        )

        score = _calculate_performance_score(analysis_result)
        assert score < 40

    def test_identify_technical_debt(self):
        """Test technical debt identification."""
        from legacy_web_mcp.mcp.analysis_tools import _identify_technical_debt
        from legacy_web_mcp.browser.analysis import (
            PageAnalysisData,
            DOMStructureAnalysis,
            TechnologyAnalysis,
            PerformanceAnalysis,
        )

        # Create analysis result with technical debt indicators
        analysis_result = PageAnalysisData(url="https://example.com", title="Legacy App")
        analysis_result.dom_analysis = DOMStructureAnalysis(total_elements=800)  # High complexity
        analysis_result.technology_analysis = TechnologyAnalysis(
            js_frameworks=[],  # No modern frameworks
            js_libraries=["jquery"],  # Legacy jQuery
        )
        analysis_result.performance_analysis = PerformanceAnalysis(
            navigation_timing={"total_load": 8000},  # Poor performance
            javascript_bundle_size=2 * 1024 * 1024,  # Large bundles
        )

        debt_indicators = _identify_technical_debt(analysis_result)

        expected_indicators = [
            "legacy_jquery_usage",
            "no_modern_js_framework",
            "high_dom_complexity",
            "poor_performance",
            "large_javascript_bundles",
        ]

        for indicator in expected_indicators:
            assert indicator in debt_indicators

    def test_analyze_validation_patterns(self):
        """Test form validation pattern analysis."""
        from legacy_web_mcp.mcp.analysis_tools import _analyze_validation_patterns

        # Test complex validation
        form_details = [
            {
                "action": "/submit",
                "method": "POST",
                "fields": [
                    {
                        "type": "text",
                        "name": "username",
                        "validation_attributes": {
                            "required": True,
                            "pattern": True,
                            "length_limits": True,
                            "min_max": False,
                        }
                    },
                    {
                        "type": "email",
                        "name": "email",
                        "validation_attributes": {
                            "required": True,
                            "pattern": False,
                            "length_limits": False,
                            "min_max": False,
                        }
                    },
                    {
                        "type": "number",
                        "name": "age",
                        "validation_attributes": {
                            "required": False,
                            "pattern": False,
                            "length_limits": False,
                            "min_max": True,
                        }
                    },
                ]
            }
        ]

        result = _analyze_validation_patterns(form_details)

        assert result["client_side_validation"] is True
        assert result["required_fields"] == 2
        assert result["pattern_validation"] == 1
        assert result["range_validation"] == 1
        assert result["complexity_score"] in ["moderate", "complex"]

        # Test simple validation
        simple_form = [
            {
                "fields": [
                    {
                        "type": "text",
                        "validation_attributes": {
                            "required": False,
                            "pattern": False,
                            "length_limits": False,
                            "min_max": False,
                        }
                    }
                ]
            }
        ]

        result = _analyze_validation_patterns(simple_form)

        assert result["client_side_validation"] is False
        assert result["complexity_score"] == "simple"

    def test_assess_technology_modernization(self):
        """Test technology modernization assessment."""
        from legacy_web_mcp.mcp.analysis_tools import _assess_technology_modernization
        from legacy_web_mcp.browser.analysis import TechnologyAnalysis

        # Test legacy technology stack
        tech_analysis = TechnologyAnalysis(
            js_frameworks=[],  # No modern frameworks
            js_libraries=["jquery"],
        )

        deep_scan_results = {"build_tools": []}
        version_info = {"jQuery": "1.12.4"}  # Very old version

        assessment = _assess_technology_modernization(tech_analysis, deep_scan_results, version_info)

        assert assessment["priority"] == "high"
        assert assessment["modernization_score"] < 50
        assert "Adopt a modern JavaScript framework" in assessment["recommendations"]
        assert "Update jQuery from legacy version" in assessment["recommendations"]
        assert assessment["technology_age"] == "legacy"

        # Test modern technology stack
        tech_analysis = TechnologyAnalysis(
            js_frameworks=["react"],
            js_libraries=["lodash"],
        )

        deep_scan_results = {"build_tools": ["webpack"]}
        version_info = {"React": "18.2.0"}

        assessment = _assess_technology_modernization(tech_analysis, deep_scan_results, version_info)

        assert assessment["priority"] == "low"
        assert assessment["modernization_score"] >= 80
        assert assessment["technology_age"] == "modern"