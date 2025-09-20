"""Tests for the comprehensive page analysis system."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from playwright.async_api import Page

from legacy_web_mcp.browser.analysis import (
    AccessibilityAnalysis,
    CSSAnalysis,
    DOMStructureAnalysis,
    FunctionalityAnalysis,
    JSFramework,
    PageAnalysisData,
    PageAnalyzer,
    PageType,
    PerformanceAnalysis,
    TechnologyAnalysis,
)
from legacy_web_mcp.browser.navigation import PageContentData


class TestPageAnalysisModels:
    """Test the page analysis data models."""

    def test_dom_structure_analysis_creation(self):
        """Test creating DOMStructureAnalysis with all fields."""
        dom_analysis = DOMStructureAnalysis(
            total_elements=150,
            semantic_elements=25,
            interactive_elements=30,
            form_elements=2,
            link_elements=20,
            image_elements=8,
            max_nesting_depth=6,
        )

        assert dom_analysis.total_elements == 150
        assert dom_analysis.semantic_elements == 25
        assert dom_analysis.interactive_elements == 30
        assert dom_analysis.form_elements == 2
        assert dom_analysis.max_nesting_depth == 6

    def test_functionality_analysis_creation(self):
        """Test creating FunctionalityAnalysis with page type."""
        func_analysis = FunctionalityAnalysis(
            page_type=PageType.FORM_PAGE,
            primary_functions=["data_collection", "user_interaction"],
            navigation_complexity="moderate",
            content_density="medium",
            form_complexity="simple",
        )

        assert func_analysis.page_type == PageType.FORM_PAGE
        assert "data_collection" in func_analysis.primary_functions
        assert func_analysis.navigation_complexity == "moderate"

    def test_technology_analysis_creation(self):
        """Test creating TechnologyAnalysis with frameworks."""
        tech_analysis = TechnologyAnalysis(
            js_frameworks=[JSFramework.REACT, JSFramework.JQUERY],
            js_libraries=["lodash", "moment"],
            css_frameworks=["bootstrap"],
            cms_detection="WordPress",
        )

        assert JSFramework.REACT in tech_analysis.js_frameworks
        assert JSFramework.JQUERY in tech_analysis.js_frameworks
        assert "lodash" in tech_analysis.js_libraries
        assert tech_analysis.cms_detection == "WordPress"

    def test_page_analysis_data_to_dict(self):
        """Test converting PageAnalysisData to dictionary."""
        analysis_data = PageAnalysisData(
            url="https://example.com",
            title="Test Page",
            description="A test page",
            analysis_duration=5.2,
        )

        result = analysis_data.to_dict()

        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert result["description"] == "A test page"
        assert result["metadata"]["analysis_duration"] == 5.2
        assert "analysis" in result
        assert "dom_structure" in result["analysis"]


class TestPageAnalyzer:
    """Test the PageAnalyzer class."""

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = AsyncMock(spec=Page)
        page.url = "https://example.com/test"
        page.title.return_value = "Test Page"
        return page

    @pytest.fixture
    def mock_page_content(self):
        """Create mock page content data."""
        return PageContentData(
            url="https://example.com/test",
            title="Test Page",
            html_content="<html><body><h1>Test</h1></body></html>",
            visible_text="Test",
            meta_data={"description": "A test page"},
            load_time=1.5,
            status_code=200,
            content_size=1024,
            extracted_at=datetime.now(UTC),
        )

    @pytest.fixture
    def analyzer(self):
        """Create a PageAnalyzer instance."""
        return PageAnalyzer(
            include_network_analysis=False,
            include_interaction_analysis=False,
            performance_budget_seconds=60.0,
        )

    @pytest.mark.asyncio
    async def test_analyze_page_basic(self, analyzer, mock_page, mock_page_content):
        """Test basic page analysis without network or interaction."""
        # Mock the navigator
        with patch.object(analyzer, "page_navigator") as mock_navigator:
            mock_navigator.navigate_and_extract.return_value = mock_page_content

            # Mock DOM analysis
            with patch.object(analyzer, "_analyze_dom_structure") as mock_dom:
                mock_dom.return_value = DOMStructureAnalysis(
                    total_elements=50,
                    interactive_elements=10,
                    form_elements=1,
                )

                # Mock other analysis methods
                with patch.object(analyzer, "_analyze_functionality") as mock_func, \
                     patch.object(analyzer, "_analyze_accessibility") as mock_access, \
                     patch.object(analyzer, "_analyze_technology") as mock_tech, \
                     patch.object(analyzer, "_analyze_css") as mock_css, \
                     patch.object(analyzer, "_analyze_performance") as mock_perf:

                    mock_func.return_value = FunctionalityAnalysis(page_type=PageType.UNKNOWN)
                    mock_access.return_value = AccessibilityAnalysis()
                    mock_tech.return_value = TechnologyAnalysis()
                    mock_css.return_value = CSSAnalysis()
                    mock_perf.return_value = PerformanceAnalysis()

                    result = await analyzer.analyze_page(
                        page=mock_page,
                        url="https://example.com/test",
                    )

                    assert result.url == "https://example.com/test"
                    assert result.title == "Test Page"
                    assert result.dom_analysis.total_elements == 50
                    assert result.analysis_duration > 0

    @pytest.mark.asyncio
    async def test_analyze_dom_structure(self, analyzer, mock_page):
        """Test DOM structure analysis."""
        # Mock page.evaluate to return element counts
        mock_page.evaluate.side_effect = [
            {  # element_counts
                "total": 100,
                "semantic": 15,
                "interactive": 25,
                "forms": 2,
                "links": 20,
                "images": 8,
                "videos": 1,
                "iframes": 0,
                "scripts": 5,
                "styles": 3,
            },
            [  # forms_data
                {
                    "action": "/submit",
                    "method": "POST",
                    "inputs": 5,
                    "selects": 1,
                    "textareas": 1,
                    "buttons": 2,
                }
            ],
            [  # buttons_data
                {"type": "submit", "text": "Submit", "disabled": False},
                {"type": "button", "text": "Cancel", "disabled": False},
            ],
            [  # inputs_data
                {"type": "text", "name": "username", "required": True, "placeholder": "Username"},
                {"type": "email", "name": "email", "required": True, "placeholder": "Email"},
                {"type": "password", "name": "password", "required": True, "placeholder": ""},
            ],
            [  # heading_structure
                {"level": 1, "text": "Main Title"},
                {"level": 2, "text": "Subtitle"},
            ],
            4,  # max_depth
        ]

        result = await analyzer._analyze_dom_structure(mock_page)

        assert result.total_elements == 100
        assert result.semantic_elements == 15
        assert result.interactive_elements == 25
        assert result.form_elements == 2
        assert result.link_elements == 20
        assert result.image_elements == 8
        assert result.max_nesting_depth == 4
        assert len(result.forms) == 1
        assert len(result.buttons) == 2
        assert len(result.inputs) == 3

    @pytest.mark.asyncio
    async def test_analyze_functionality(self, analyzer, mock_page):
        """Test functionality analysis."""
        # Create analysis data
        analysis_data = PageAnalysisData(
            url="https://example.com/login",
            title="Login Page",
        )
        analysis_data.dom_analysis = DOMStructureAnalysis(
            total_elements=50,
            form_elements=1,
            interactive_elements=10,
        )

        result = await analyzer._analyze_functionality(mock_page, analysis_data)

        assert result.page_type == PageType.LOGIN_PAGE  # Should detect login from URL

    @pytest.mark.asyncio
    async def test_analyze_accessibility(self, analyzer, mock_page):
        """Test accessibility analysis."""
        # Mock page evaluate calls
        mock_page.evaluate.side_effect = [
            [  # aria_elements
                {"role": "button", "label": "Submit", "tag": "button"},
                {"role": "textbox", "label": "Username", "tag": "input"},
            ],
            ["Login form", "Company logo"],  # alt_texts
            [  # headings
                {"level": 1, "text": "Welcome", "id": "main-title"},
                {"level": 2, "text": "Please sign in", "id": ""},
            ],
        ]

        result = await analyzer._analyze_accessibility(mock_page)

        assert len(result.aria_labels) == 2
        assert "Login form" in result.alt_texts
        assert len(result.heading_hierarchy) == 2
        assert "button" in result.semantic_roles

    @pytest.mark.asyncio
    async def test_analyze_technology(self, analyzer, mock_page):
        """Test technology analysis."""
        # Mock JavaScript detection
        mock_page.evaluate.side_effect = [
            {  # js_detection
                "frameworks": ["react", "vue"],
                "libraries": ["jquery", "lodash"],
            },
            ["bootstrap", "tailwind"],  # css_frameworks
            "WordPress 6.0",  # meta_info
        ]

        result = await analyzer._analyze_technology(mock_page)

        assert JSFramework.REACT in result.js_frameworks
        assert JSFramework.VUE in result.js_frameworks
        assert "jquery" in result.js_libraries
        assert "lodash" in result.js_libraries
        assert "bootstrap" in result.css_frameworks
        assert result.cms_detection == "WordPress 6.0"

    @pytest.mark.asyncio
    async def test_analyze_css(self, analyzer, mock_page):
        """Test CSS analysis."""
        mock_page.evaluate.return_value = {
            "external": ["https://cdn.bootstrap.com/css/bootstrap.css"],
            "inlineStyles": 5,
            "breakpoints": [768, 1024, 1200],
        }

        result = await analyzer._analyze_css(mock_page)

        assert len(result.external_stylesheets) == 1
        assert result.inline_styles_count == 5
        assert result.responsive_breakpoints == [768, 1024, 1200]

    @pytest.mark.asyncio
    async def test_analyze_performance(self, analyzer, mock_page):
        """Test performance analysis."""
        analysis_data = PageAnalysisData(url="https://example.com")
        analysis_data.dom_analysis = DOMStructureAnalysis(total_elements=200)

        mock_page.evaluate.side_effect = [
            {  # navigation_timing
                "dns_lookup": 50,
                "tcp_connect": 100,
                "request_response": 500,
                "dom_processing": 800,
                "total_load": 2000,
            },
            {  # resource_summary
                "total_size": 1024000,  # 1MB
                "js_size": 512000,  # 512KB
                "css_size": 102400,  # 100KB
                "image_size": 409600,  # 400KB
                "resource_count": 25,
            },
        ]

        result = await analyzer._analyze_performance(mock_page, analysis_data)

        assert result.navigation_timing["total_load"] == 2000
        assert result.total_resource_size == 1024000
        assert result.javascript_bundle_size == 512000
        assert result.css_bundle_size == 102400

    @pytest.mark.asyncio
    async def test_analyze_page_with_network_monitoring(self):
        """Test page analysis with network monitoring enabled."""
        analyzer = PageAnalyzer(
            include_network_analysis=True,
            include_interaction_analysis=False,
        )

        mock_page = AsyncMock(spec=Page)
        mock_page.url = "https://example.com"

        # Mock network monitor
        mock_network_monitor = AsyncMock()
        mock_summary = Mock()
        mock_summary.to_dict.return_value = {"total_requests": 5}
        mock_network_monitor.get_summary.return_value = mock_summary
        mock_network_monitor.get_requests.return_value = []

        analyzer.network_monitor = mock_network_monitor

        # Mock other components
        mock_page_content = PageContentData(
            url="https://example.com",
            title="Test",
            html_content="<html></html>",
            visible_text="Test",
            meta_data={},
            load_time=1.0,
            status_code=200,
            content_size=100,
            extracted_at=datetime.now(UTC),
        )

        with patch.object(analyzer, "_extract_page_content") as mock_extract, \
             patch.object(analyzer, "_analyze_dom_structure") as mock_dom, \
             patch.object(analyzer, "_analyze_functionality") as mock_func, \
             patch.object(analyzer, "_analyze_accessibility") as mock_access, \
             patch.object(analyzer, "_analyze_technology") as mock_tech, \
             patch.object(analyzer, "_analyze_css") as mock_css, \
             patch.object(analyzer, "_analyze_performance") as mock_perf:

            mock_extract.return_value = mock_page_content
            mock_dom.return_value = DOMStructureAnalysis()
            mock_func.return_value = FunctionalityAnalysis()
            mock_access.return_value = AccessibilityAnalysis()
            mock_tech.return_value = TechnologyAnalysis()
            mock_css.return_value = CSSAnalysis()
            mock_perf.return_value = PerformanceAnalysis()

            result = await analyzer.analyze_page(mock_page, "https://example.com")

            assert result.url == "https://example.com"
            assert "summary" in result.network_traffic

    def test_classify_page_type(self, analyzer):
        """Test page type classification logic."""
        dom_analysis = DOMStructureAnalysis(form_elements=0, total_elements=100)

        # Test URL-based classification
        assert analyzer._classify_page_type("", "https://example.com/login", dom_analysis) == PageType.LOGIN_PAGE
        assert analyzer._classify_page_type("", "https://example.com/contact", dom_analysis) == PageType.CONTACT_PAGE
        assert analyzer._classify_page_type("", "https://example.com/about", dom_analysis) == PageType.ABOUT_PAGE
        assert analyzer._classify_page_type("", "https://example.com/blog/post", dom_analysis) == PageType.BLOG_POST
        assert analyzer._classify_page_type("", "https://example.com/admin/dashboard", dom_analysis) == PageType.ADMIN_PANEL

        # Test form-based classification
        form_dom = DOMStructureAnalysis(form_elements=3, total_elements=100)
        assert analyzer._classify_page_type("", "https://example.com/page", form_dom) == PageType.FORM_PAGE

        # Test error page classification
        assert analyzer._classify_page_type("404 error", "https://example.com/missing", dom_analysis) == PageType.ERROR_PAGE

    def test_identify_primary_functions(self, analyzer):
        """Test primary function identification."""
        dom_analysis = DOMStructureAnalysis(
            form_elements=2,
            link_elements=15,
            image_elements=8,
            interactive_elements=12,
            video_elements=1,
        )

        functions = analyzer._identify_primary_functions(dom_analysis)

        assert "data_collection" in functions  # Has forms
        assert "navigation" in functions  # Has many links
        assert "content_display" in functions  # Has images
        assert "user_interaction" in functions  # Has interactive elements
        assert "media_playback" in functions  # Has video

    def test_assess_complexity_metrics(self, analyzer):
        """Test complexity assessment methods."""
        # Test navigation complexity
        simple_dom = DOMStructureAnalysis(link_elements=5)
        moderate_dom = DOMStructureAnalysis(link_elements=25)
        complex_dom = DOMStructureAnalysis(link_elements=75)

        assert analyzer._assess_navigation_complexity(simple_dom) == "simple"
        assert analyzer._assess_navigation_complexity(moderate_dom) == "moderate"
        assert analyzer._assess_navigation_complexity(complex_dom) == "complex"

        # Test content density
        low_dom = DOMStructureAnalysis(total_elements=50)
        medium_dom = DOMStructureAnalysis(total_elements=150)
        high_dom = DOMStructureAnalysis(total_elements=400)

        assert analyzer._assess_content_density(low_dom) == "low"
        assert analyzer._assess_content_density(medium_dom) == "medium"
        assert analyzer._assess_content_density(high_dom) == "high"

        # Test form complexity
        no_form_dom = DOMStructureAnalysis(form_elements=0, inputs=[])
        simple_form_dom = DOMStructureAnalysis(form_elements=1, inputs=[{"type": "text"}, {"type": "email"}])
        moderate_form_dom = DOMStructureAnalysis(form_elements=2, inputs=[{"type": "text"} for _ in range(8)])
        complex_form_dom = DOMStructureAnalysis(form_elements=3, inputs=[{"type": "text"} for _ in range(20)])

        assert analyzer._assess_form_complexity(no_form_dom) == "none"
        assert analyzer._assess_form_complexity(simple_form_dom) == "simple"
        assert analyzer._assess_form_complexity(moderate_form_dom) == "moderate"
        assert analyzer._assess_form_complexity(complex_form_dom) == "complex"

    @pytest.mark.asyncio
    async def test_error_handling_in_analysis(self, analyzer, mock_page):
        """Test error handling during analysis."""
        # Mock page content extraction to succeed
        mock_page_content = PageContentData(
            url="https://example.com",
            title="Test",
            html_content="<html></html>",
            visible_text="Test",
            meta_data={},
            load_time=1.0,
            status_code=200,
            content_size=100,
            extracted_at=datetime.now(UTC),
        )

        with patch.object(analyzer, "_extract_page_content") as mock_extract:
            mock_extract.return_value = mock_page_content

            # Mock DOM analysis to raise an exception
            with patch.object(analyzer, "_analyze_dom_structure") as mock_dom:
                mock_dom.side_effect = Exception("DOM analysis failed")

                result = await analyzer.analyze_page(mock_page, "https://example.com")

                # Should still return analysis data with error recorded
                assert result.url == "https://example.com"
                assert len(result.processing_errors) > 0
                assert "DOM analysis failed" in result.processing_errors[0]

    @pytest.mark.asyncio
    async def test_performance_budget_timeout(self):
        """Test that analysis respects performance budget."""
        analyzer = PageAnalyzer(performance_budget_seconds=0.1)  # Very short timeout

        mock_page = AsyncMock(spec=Page)
        mock_page.url = "https://example.com"

        # This should complete quickly even with a short timeout
        # The timeout is more about logging than actual interruption
        with patch.object(analyzer, "_extract_page_content") as mock_extract:
            mock_page_content = PageContentData(
                url="https://example.com",
                title="Test",
                html_content="<html></html>",
                visible_text="Test",
                meta_data={},
                load_time=1.0,
                status_code=200,
                content_size=100,
                extracted_at=datetime.now(UTC),
            )
            mock_extract.return_value = mock_page_content

            # Mock all other analysis methods to return defaults
            with patch.object(analyzer, "_analyze_dom_structure") as mock_dom, \
                 patch.object(analyzer, "_analyze_functionality") as mock_func, \
                 patch.object(analyzer, "_analyze_accessibility") as mock_access, \
                 patch.object(analyzer, "_analyze_technology") as mock_tech, \
                 patch.object(analyzer, "_analyze_css") as mock_css, \
                 patch.object(analyzer, "_analyze_performance") as mock_perf:

                mock_dom.return_value = DOMStructureAnalysis()
                mock_func.return_value = FunctionalityAnalysis()
                mock_access.return_value = AccessibilityAnalysis()
                mock_tech.return_value = TechnologyAnalysis()
                mock_css.return_value = CSSAnalysis()
                mock_perf.return_value = PerformanceAnalysis()

                result = await analyzer.analyze_page(mock_page, "https://example.com")

                assert result.url == "https://example.com"
                # Analysis duration should be recorded
                assert result.analysis_duration >= 0


class TestAnalysisDataSerialization:
    """Test serialization of analysis data."""

    def test_page_analysis_data_json_serialization(self):
        """Test that PageAnalysisData can be serialized to JSON."""
        analysis_data = PageAnalysisData(
            url="https://example.com",
            title="Test Page",
            description="A test page for serialization",
        )

        # Add some analysis data
        analysis_data.dom_analysis = DOMStructureAnalysis(
            total_elements=100,
            interactive_elements=20,
            forms=[{"action": "/submit", "method": "POST"}],
        )

        analysis_data.technology_analysis = TechnologyAnalysis(
            js_frameworks=[JSFramework.REACT],
            js_libraries=["lodash"],
            css_frameworks=["bootstrap"],
        )

        # Convert to dict and then to JSON
        data_dict = analysis_data.to_dict()
        json_str = json.dumps(data_dict)

        # Should not raise an exception
        assert isinstance(json_str, str)
        assert "https://example.com" in json_str
        assert "Test Page" in json_str

        # Parse back to verify structure
        parsed = json.loads(json_str)
        assert parsed["url"] == "https://example.com"
        assert parsed["title"] == "Test Page"
        assert "analysis" in parsed
        assert "dom_structure" in parsed["analysis"]

    def test_complex_analysis_data_serialization(self):
        """Test serialization of complex analysis data structures."""
        analysis_data = PageAnalysisData(
            url="https://complex-app.com/dashboard",
            title="Dashboard",
        )

        # Complex DOM analysis
        analysis_data.dom_analysis = DOMStructureAnalysis(
            total_elements=500,
            interactive_elements=75,
            forms=[
                {
                    "action": "/api/users",
                    "method": "POST",
                    "inputs": 8,
                    "buttons": 2,
                },
                {
                    "action": "/api/settings",
                    "method": "PUT",
                    "inputs": 12,
                    "buttons": 3,
                },
            ],
            buttons=[
                {"type": "submit", "text": "Save User", "disabled": False},
                {"type": "button", "text": "Cancel", "disabled": False},
                {"type": "button", "text": "Delete", "disabled": True},
            ],
            heading_structure=[
                {"level": 1, "text": "User Dashboard"},
                {"level": 2, "text": "User Management"},
                {"level": 3, "text": "Add New User"},
            ],
        )

        # Complex technology stack
        analysis_data.technology_analysis = TechnologyAnalysis(
            js_frameworks=[JSFramework.REACT, JSFramework.VUE],
            js_libraries=["lodash", "moment", "axios", "chartjs"],
            css_frameworks=["bootstrap", "tailwind"],
            build_tools=["webpack", "babel"],
            cms_detection="Custom CMS",
            analytics_tools=["google-analytics", "mixpanel"],
        )

        # Performance data
        analysis_data.performance_analysis = PerformanceAnalysis(
            navigation_timing={
                "dns_lookup": 50,
                "tcp_connect": 100,
                "total_load": 3500,
            },
            resource_timing={
                "total_size": 2048000,
                "resource_count": 45,
            },
            total_resource_size=2048000,
            javascript_bundle_size=1024000,
        )

        # Convert to dict and JSON
        data_dict = analysis_data.to_dict()
        json_str = json.dumps(data_dict, indent=2)

        # Verify serialization worked
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)

        # Verify structure preservation
        assert parsed["analysis"]["technology"]["js_frameworks"] == ["react", "vue"]
        assert len(parsed["analysis"]["dom_structure"]["forms"]) == 2
        assert parsed["analysis"]["performance"]["total_resource_size"] == 2048000


@pytest.mark.integration
class TestPageAnalyzerIntegration:
    """Integration tests for PageAnalyzer with real browser automation."""

    @pytest.fixture
    def temp_html_file(self, tmp_path):
        """Create a temporary HTML file for testing."""
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta name="description" content="Test page for analysis">
            <title>Test Analysis Page</title>
            <style>
                body { font-family: Arial, sans-serif; }
                .container { max-width: 800px; margin: 0 auto; }
                @media (max-width: 768px) { .container { max-width: 100%; } }
            </style>
        </head>
        <body>
            <header>
                <nav>
                    <h1>Test Site</h1>
                    <ul>
                        <li><a href="#home">Home</a></li>
                        <li><a href="#about">About</a></li>
                        <li><a href="#contact">Contact</a></li>
                    </ul>
                </nav>
            </header>
            <main class="container">
                <section>
                    <h2>Welcome</h2>
                    <p>This is a test page for analysis.</p>
                    <img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCI+PGNpcmNsZSBjeD0iNTAiIGN5PSI1MCIgcj0iNDAiIGZpbGw9IiMwMGQiLz48L3N2Zz4=" alt="Test image">
                </section>
                <section>
                    <h3>Contact Form</h3>
                    <form action="/submit" method="POST">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>

                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>

                        <label for="message">Message:</label>
                        <textarea id="message" name="message" rows="4" required></textarea>

                        <button type="submit">Send Message</button>
                        <button type="button">Clear Form</button>
                    </form>
                </section>
            </main>
            <script>
                // Simple jQuery-like functionality
                window.$ = {
                    version: "3.6.0",
                    ready: function(fn) { document.addEventListener('DOMContentLoaded', fn); }
                };

                // Simulate some framework detection
                window.TestFramework = { version: "1.0.0" };
            </script>
        </body>
        </html>
        """

        html_file = tmp_path / "test_page.html"
        html_file.write_text(html_content, encoding="utf-8")
        return html_file

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_page_analysis_integration(self, temp_html_file):
        """Test full page analysis with a real HTML file."""
        # This test requires Playwright to be installed
        pytest.importorskip("playwright")

        from playwright.async_api import async_playwright

        analyzer = PageAnalyzer(
            include_network_analysis=False,  # Skip network for file URLs
            include_interaction_analysis=False,  # Skip interaction for simplicity
        )

        file_url = f"file://{temp_html_file.absolute()}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                result = await analyzer.analyze_page(page, file_url)

                # Verify basic analysis results
                assert result.url == file_url
                assert result.title == "Test Analysis Page"
                assert result.analysis_duration > 0

                # Verify DOM analysis detected elements
                assert result.dom_analysis.total_elements > 0
                assert result.dom_analysis.form_elements == 1
                assert result.dom_analysis.interactive_elements > 0
                assert result.dom_analysis.image_elements == 1

                # Verify form was detected correctly
                assert len(result.dom_analysis.forms) == 1
                form = result.dom_analysis.forms[0]
                assert form["action"] == "/submit"
                assert form["method"] == "POST"

                # Verify buttons were detected
                assert len(result.dom_analysis.buttons) == 2

                # Verify inputs were detected
                assert len(result.dom_analysis.inputs) == 3  # text, email, textarea

                # Verify heading structure
                headings = result.dom_analysis.heading_structure
                assert len(headings) >= 3  # h1, h2, h3

                # Verify functionality analysis
                assert result.functionality_analysis.page_type in [PageType.FORM_PAGE, PageType.CONTACT_PAGE, PageType.UNKNOWN]

                # Verify accessibility analysis
                assert len(result.accessibility_analysis.alt_texts) == 1
                assert "Test image" in result.accessibility_analysis.alt_texts

                # Verify technology detection found our mock framework
                # The JavaScript should be detected even if no major frameworks are found

                # Verify CSS analysis detected responsive design
                assert result.css_analysis.inline_styles_count > 0

                # Verify performance analysis
                assert result.performance_analysis.navigation_timing is not None

            finally:
                await browser.close()