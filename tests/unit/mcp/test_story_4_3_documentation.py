"""Unit tests for Story 4.3: Structured Documentation Generation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC
from typing import List, Dict, Any

from legacy_web_mcp.documentation.assembler import (
    DocumentationAssembler,
    DocumentationSection,
    ProjectSummary,
    ProjectDocumentation
)
from legacy_web_mcp.mcp.documentation_tools import (
    generate_project_documentation,
    generate_executive_summary,
    list_available_artifacts,
    generate_api_documentation,
    validate_documentation_artifacts
)
from legacy_web_mcp.llm.artifacts import AnalysisArtifact
from legacy_web_mcp.llm.models import ContentSummary, FeatureAnalysis
from fastmcp import Context


class TestDocumentationAssembler:
    """Test suite for DocumentationAssembler class."""

    @pytest.fixture
    def mock_artifact_manager(self):
        """Create mock artifact manager."""
        manager = AsyncMock()
        return manager

    @pytest.fixture
    def sample_artifacts(self) -> List[AnalysisArtifact]:
        """Create sample analysis artifacts for testing."""
        return [
            AnalysisArtifact(
                artifact_id="art_001",
                url="https://example.com/page1",
                artifact_type="content_summary",
                timestamp=datetime.now(UTC),
                result_data={
                    "page_title": "Home Page",
                    "content_type": "homepage",
                    "business_importance": 9.0,
                    "key_elements": ["navigation", "hero section", "featured products"]
                },
                metadata={
                    "quality_score": 0.85,
                    "page_title": "Home Page",
                    "analysis_status": "completed"
                }
            ),
            AnalysisArtifact(
                artifact_id="art_002",
                url="https://example.com/page1",
                artifact_type="feature_analysis",
                timestamp=datetime.now(UTC),
                result_data={
                    "features": [
                        {
                            "feature_name": "Product Search",
                            "priority_score": 8.5,
                            "technical_complexity": "medium"
                        }
                    ],
                    "api_endpoints": [
                        {
                            "endpoint": "/api/products/search",
                            "method": "GET"
                        }
                    ]
                },
                metadata={
                    "quality_score": 0.90,
                    "page_title": "Home Page",
                    "analysis_status": "completed"
                }
            )
        ]

    @pytest.fixture
    def assembler(self, mock_artifact_manager):
        """Create DocumentationAssembler instance."""
        return DocumentationAssembler(mock_artifact_manager)

    async def test_compute_project_summary(self, assembler, sample_artifacts):
        """Test project summary computation from artifacts."""
        # Test project summary generation
        project_summary = await assembler._compute_project_summary(
            artifacts=sample_artifacts,
            project_name="Test Project",
            quality_threshold=0.7
        )

        assert isinstance(project_summary, ProjectSummary)
        assert project_summary.total_pages_analyzed == 1  # Same URL
        assert project_summary.successful_analyses == 2
        assert project_summary.average_quality_score == 0.875
        assert project_summary.total_features_identified == 1
        assert project_summary.total_api_endpoints == 1
        assert project_summary.business_importance_average == 9.0

    async def test_generate_executive_summary(self, assembler):
        """Test executive summary generation."""
        project_summary = ProjectSummary(
            total_pages_analyzed=5,
            successful_analyses=10,
            average_quality_score=0.85,
            total_features_identified=25,
            total_api_endpoints=8,
            total_interactive_elements=15,
            complexity_assessment="Medium",
            estimated_rebuild_effort="6-8 weeks",
            business_importance_average=7.5
        )

        section = await assembler._generate_executive_summary(
            project_summary=project_summary,
            project_name="Test Project"
        )

        assert isinstance(section, DocumentationSection)
        assert section.title == "Executive Summary"
        assert section.level == 1
        assert "Test Project" in section.content
        assert "5 pages" in section.content
        assert "25 features" in section.content
        assert "6-8 weeks" in section.content

    async def test_generate_per_page_analysis(self, assembler, sample_artifacts):
        """Test per-page analysis section generation."""
        section = await assembler._generate_per_page_analysis(
            artifacts=sample_artifacts,
            project_name="Test Project"
        )

        assert isinstance(section, DocumentationSection)
        assert section.title == "Page Analysis"
        assert section.level == 1
        assert len(section.subsections) == 1  # One unique URL
        assert "Home Page" in section.content
        assert "Product Search" in section.content

    async def test_generate_api_integration_summary(self, assembler, sample_artifacts):
        """Test API integration summary generation."""
        section = await assembler._generate_api_integration_summary(
            artifacts=sample_artifacts,
            project_name="Test Project"
        )

        assert isinstance(section, DocumentationSection)
        assert section.title == "API Integration Summary"
        assert section.level == 1
        assert "/api/products/search" in section.content
        assert "GET" in section.content

    async def test_generate_business_logic_documentation(self, assembler, sample_artifacts):
        """Test business logic documentation generation."""
        section = await assembler._generate_business_logic_documentation(
            artifacts=sample_artifacts,
            project_name="Test Project"
        )

        assert isinstance(section, DocumentationSection)
        assert section.title == "Business Logic and Workflows"
        assert section.level == 1
        assert "business_importance" in section.content.lower()

    async def test_generate_technical_specifications(self, assembler, sample_artifacts):
        """Test technical specifications generation."""
        section = await assembler._generate_technical_specifications(
            artifacts=sample_artifacts,
            project_name="Test Project"
        )

        assert isinstance(section, DocumentationSection)
        assert section.title == "Technical Specifications"
        assert section.level == 1
        assert "architecture" in section.content.lower()

    async def test_assemble_markdown_document(self, assembler):
        """Test markdown document assembly with TOC."""
        sections = [
            DocumentationSection(
                title="Section 1",
                content="Content 1",
                level=1,
                anchor="section-1"
            ),
            DocumentationSection(
                title="Section 2",
                content="Content 2",
                level=1,
                anchor="section-2",
                subsections=[
                    DocumentationSection(
                        title="Subsection 2.1",
                        content="Subcontent 2.1",
                        level=2,
                        anchor="subsection-2-1"
                    )
                ]
            )
        ]

        project_summary = ProjectSummary(
            total_pages_analyzed=5,
            successful_analyses=10,
            average_quality_score=0.85,
            total_features_identified=25,
            total_api_endpoints=8,
            total_interactive_elements=15,
            complexity_assessment="Medium",
            estimated_rebuild_effort="6-8 weeks",
            business_importance_average=7.5
        )

        documentation = await assembler._assemble_markdown_document(
            sections=sections,
            project_summary=project_summary,
            project_name="Test Project"
        )

        assert isinstance(documentation, ProjectDocumentation)
        assert "# Test Project" in documentation.content
        assert "## Table of Contents" in documentation.content
        assert "[Section 1](#section-1)" in documentation.content
        assert "[Subsection 2.1](#subsection-2-1)" in documentation.content
        assert "# Section 1" in documentation.content
        assert "## Subsection 2.1" in documentation.content

    @patch('legacy_web_mcp.documentation.assembler.load_configuration')
    async def test_generate_project_documentation_integration(
        self,
        mock_load_config,
        assembler,
        sample_artifacts
    ):
        """Test complete project documentation generation."""
        # Mock configuration
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        # Mock artifact manager
        assembler.artifact_manager.list_artifacts.return_value = sample_artifacts

        # Generate documentation
        documentation = await assembler.generate_project_documentation(
            project_name="Test Project",
            include_technical_specs=True,
            include_api_docs=True,
            include_business_logic=True,
            quality_threshold=0.7
        )

        assert isinstance(documentation, ProjectDocumentation)
        assert "Test Project" in documentation.content
        assert len(documentation.sections) >= 4  # Executive, Pages, API, Business, Technical


class TestDocumentationTools:
    """Test suite for MCP documentation tools."""

    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        context = AsyncMock(spec=Context)
        return context

    @pytest.fixture
    def sample_artifacts(self) -> List[AnalysisArtifact]:
        """Create sample analysis artifacts for testing."""
        return [
            AnalysisArtifact(
                artifact_id="art_001",
                url="https://example.com/page1",
                artifact_type="content_summary",
                timestamp=datetime.now(UTC),
                result_data={
                    "page_title": "Home Page",
                    "content_type": "homepage",
                    "business_importance": 9.0
                },
                metadata={
                    "quality_score": 0.85,
                    "page_title": "Home Page",
                    "analysis_status": "completed"
                }
            )
        ]

    @patch('legacy_web_mcp.mcp.documentation_tools.load_configuration')
    @patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager')
    @patch('legacy_web_mcp.mcp.documentation_tools.DocumentationAssembler')
    async def test_generate_project_documentation_tool(
        self,
        mock_assembler_class,
        mock_artifact_manager_class,
        mock_load_config,
        mock_context
    ):
        """Test generate_project_documentation MCP tool."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_artifact_manager = AsyncMock()
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_assembler = AsyncMock()
        mock_documentation = MagicMock()
        mock_documentation.content = "# Test Documentation\n\nContent here"
        mock_documentation.sections = [MagicMock(), MagicMock()]
        mock_documentation.project_summary = MagicMock()
        mock_documentation.project_summary.total_pages_analyzed = 5
        mock_documentation.project_summary.successful_analyses = 10
        mock_documentation.project_summary.average_quality_score = 0.85
        mock_documentation.project_summary.total_features_identified = 25

        mock_assembler.generate_project_documentation.return_value = mock_documentation
        mock_assembler_class.return_value = mock_assembler

        # Test the tool
        result = await generate_project_documentation(
            context=mock_context,
            project_name="Test Project",
            output_path="/tmp/test_doc.md",
            include_technical_specs=True,
            include_api_docs=True,
            include_business_logic=True,
            quality_threshold=0.7
        )

        # Verify results
        assert result["status"] == "success"
        assert result["project_name"] == "Test Project"
        assert "documentation_content" in result
        assert result["sections_generated"] == 2
        assert result["metadata"]["total_pages"] == 5

        # Verify tool calls
        mock_assembler.generate_project_documentation.assert_called_once()
        mock_context.info.assert_called()

    @patch('legacy_web_mcp.mcp.documentation_tools.load_configuration')
    @patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager')
    @patch('legacy_web_mcp.mcp.documentation_tools.DocumentationAssembler')
    async def test_generate_executive_summary_tool(
        self,
        mock_assembler_class,
        mock_artifact_manager_class,
        mock_load_config,
        mock_context
    ):
        """Test generate_executive_summary MCP tool."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_artifact_manager = AsyncMock()
        mock_artifact_manager.list_artifacts.return_value = []
        mock_artifact_manager_class.return_value = mock_artifact_manager

        mock_assembler = AsyncMock()
        mock_project_summary = MagicMock()
        mock_project_summary.total_pages_analyzed = 5
        mock_project_summary.successful_analyses = 10
        mock_project_summary.average_quality_score = 0.85
        mock_project_summary.total_features_identified = 25
        mock_project_summary.total_api_endpoints = 8
        mock_project_summary.complexity_assessment = "Medium"
        mock_project_summary.estimated_rebuild_effort = "6-8 weeks"

        mock_executive_summary = MagicMock()
        mock_executive_summary.content = "Executive summary content"

        mock_assembler._compute_project_summary.return_value = mock_project_summary
        mock_assembler._generate_executive_summary.return_value = mock_executive_summary
        mock_assembler_class.return_value = mock_assembler

        # Test the tool
        result = await generate_executive_summary(
            context=mock_context,
            project_name="Test Project",
            quality_threshold=0.7
        )

        # Verify results
        assert result["status"] == "success"
        assert result["project_name"] == "Test Project"
        assert "executive_summary" in result
        assert result["project_metrics"]["total_pages"] == 5
        assert result["project_metrics"]["features_identified"] == 25

    @patch('legacy_web_mcp.mcp.documentation_tools.load_configuration')
    @patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager')
    async def test_list_available_artifacts_tool(
        self,
        mock_artifact_manager_class,
        mock_load_config,
        mock_context,
        sample_artifacts
    ):
        """Test list_available_artifacts MCP tool."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_artifact_manager = AsyncMock()
        mock_artifact_manager.list_artifacts.return_value = sample_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        # Test the tool
        result = await list_available_artifacts(
            context=mock_context,
            quality_threshold=0.8,
            artifact_type="content_summary"
        )

        # Verify results
        assert result["status"] == "success"
        assert result["total_artifacts"] == 1
        assert result["filtered_artifacts"] == 1
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["artifact_id"] == "art_001"

    @patch('legacy_web_mcp.mcp.documentation_tools.load_configuration')
    @patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager')
    async def test_validate_documentation_artifacts_tool(
        self,
        mock_artifact_manager_class,
        mock_load_config,
        mock_context,
        sample_artifacts
    ):
        """Test validate_documentation_artifacts MCP tool."""
        # Setup mocks
        mock_config = MagicMock()
        mock_load_config.return_value = mock_config

        mock_artifact_manager = AsyncMock()
        mock_artifact_manager.list_artifacts.return_value = sample_artifacts
        mock_artifact_manager_class.return_value = mock_artifact_manager

        # Test the tool
        result = await validate_documentation_artifacts(
            context=mock_context,
            quality_threshold=0.7
        )

        # Verify results
        assert result["status"] == "success"
        validation_results = result["validation_results"]
        assert validation_results["total_artifacts"] == 1
        assert validation_results["high_quality_artifacts"] == 1
        assert validation_results["content_summaries"] == 1
        assert len(validation_results["recommendations"]) >= 0

    async def test_tool_error_handling(self, mock_context):
        """Test error handling in MCP tools."""
        # Test with invalid configuration
        with patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_load_config:
            mock_load_config.side_effect = Exception("Config error")

            result = await generate_project_documentation(
                context=mock_context,
                project_name="Test Project"
            )

            assert result["status"] == "error"
            assert "Config error" in result["error"]
            mock_context.error.assert_called()


class TestDocumentationDataModels:
    """Test suite for documentation data models."""

    def test_documentation_section_model(self):
        """Test DocumentationSection data model."""
        section = DocumentationSection(
            title="Test Section",
            content="Test content",
            level=2,
            anchor="test-section"
        )

        assert section.title == "Test Section"
        assert section.content == "Test content"
        assert section.level == 2
        assert section.anchor == "test-section"
        assert section.subsections == []

    def test_documentation_section_with_subsections(self):
        """Test DocumentationSection with nested subsections."""
        subsection = DocumentationSection(
            title="Subsection",
            content="Sub content",
            level=3,
            anchor="subsection"
        )

        section = DocumentationSection(
            title="Main Section",
            content="Main content",
            level=2,
            anchor="main-section",
            subsections=[subsection]
        )

        assert len(section.subsections) == 1
        assert section.subsections[0].title == "Subsection"

    def test_project_summary_model(self):
        """Test ProjectSummary data model."""
        summary = ProjectSummary(
            total_pages_analyzed=10,
            successful_analyses=18,
            average_quality_score=0.85,
            total_features_identified=45,
            total_api_endpoints=12,
            total_interactive_elements=28,
            complexity_assessment="High",
            estimated_rebuild_effort="8-10 weeks",
            business_importance_average=7.8
        )

        assert summary.total_pages_analyzed == 10
        assert summary.successful_analyses == 18
        assert summary.average_quality_score == 0.85
        assert summary.complexity_assessment == "High"

    def test_project_documentation_model(self):
        """Test ProjectDocumentation data model."""
        sections = [
            DocumentationSection(
                title="Section 1",
                content="Content 1",
                level=1,
                anchor="section-1"
            )
        ]

        summary = ProjectSummary(
            total_pages_analyzed=5,
            successful_analyses=10,
            average_quality_score=0.85,
            total_features_identified=25,
            total_api_endpoints=8,
            total_interactive_elements=15,
            complexity_assessment="Medium",
            estimated_rebuild_effort="6-8 weeks",
            business_importance_average=7.5
        )

        documentation = ProjectDocumentation(
            project_name="Test Project",
            sections=sections,
            content="# Test Project Documentation",
            project_summary=summary
        )

        assert documentation.project_name == "Test Project"
        assert len(documentation.sections) == 1
        assert documentation.project_summary.total_pages_analyzed == 5


class TestDocumentationIntegration:
    """Integration tests for documentation generation."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        return config

    @pytest.fixture
    def real_artifacts(self) -> List[AnalysisArtifact]:
        """Create realistic analysis artifacts for integration testing."""
        return [
            AnalysisArtifact(
                artifact_id="art_home",
                url="https://example.com/",
                artifact_type="content_summary",
                timestamp=datetime.now(UTC),
                result_data={
                    "page_title": "Example.com - Home",
                    "content_type": "homepage",
                    "business_importance": 9.5,
                    "key_elements": ["navigation", "hero section", "product showcase"],
                    "content_summary": "Main landing page with product showcase and navigation"
                },
                metadata={
                    "quality_score": 0.92,
                    "page_title": "Example.com - Home",
                    "analysis_status": "completed"
                }
            ),
            AnalysisArtifact(
                artifact_id="art_home_features",
                url="https://example.com/",
                artifact_type="feature_analysis",
                timestamp=datetime.now(UTC),
                result_data={
                    "features": [
                        {
                            "feature_name": "Product Search",
                            "priority_score": 9.0,
                            "technical_complexity": "medium",
                            "rebuild_notes": "Implement with search API and filters"
                        },
                        {
                            "feature_name": "User Login",
                            "priority_score": 8.5,
                            "technical_complexity": "low",
                            "rebuild_notes": "Standard authentication with JWT"
                        }
                    ],
                    "api_endpoints": [
                        {
                            "endpoint": "/api/products/search",
                            "method": "GET",
                            "description": "Product search with filters"
                        },
                        {
                            "endpoint": "/api/auth/login",
                            "method": "POST",
                            "description": "User authentication"
                        }
                    ],
                    "interactive_elements": [
                        "search_form",
                        "login_button",
                        "product_filters"
                    ]
                },
                metadata={
                    "quality_score": 0.88,
                    "page_title": "Example.com - Home",
                    "analysis_status": "completed"
                }
            )
        ]

    async def test_end_to_end_documentation_generation(self, mock_config, real_artifacts):
        """Test complete documentation generation workflow."""
        # Create mock artifact manager
        mock_artifact_manager = AsyncMock()
        mock_artifact_manager.list_artifacts.return_value = real_artifacts

        # Create assembler
        assembler = DocumentationAssembler(mock_artifact_manager)

        # Generate complete documentation
        documentation = await assembler.generate_project_documentation(
            project_name="Example.com Analysis",
            include_technical_specs=True,
            include_api_docs=True,
            include_business_logic=True,
            quality_threshold=0.8
        )

        # Verify documentation structure
        assert isinstance(documentation, ProjectDocumentation)
        assert "Example.com Analysis" in documentation.content
        assert documentation.project_summary.total_pages_analyzed == 1
        assert documentation.project_summary.total_features_identified == 2
        assert documentation.project_summary.total_api_endpoints == 2

        # Verify content includes key elements
        assert "Product Search" in documentation.content
        assert "/api/products/search" in documentation.content
        assert "Table of Contents" in documentation.content
        assert "Executive Summary" in documentation.content