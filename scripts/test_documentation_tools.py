#!/usr/bin/env python3
"""Test script for Story 4.3 Documentation Generation Tools.

This script demonstrates and tests the documentation generation functionality
by creating sample analysis artifacts and generating comprehensive documentation.

Usage:
    python scripts/test_documentation_tools.py [command]

Commands:
    generate        - Generate sample documentation
    validate        - Validate artifacts for documentation
    executive       - Generate executive summary only
    api            - Generate API documentation only
    list           - List available artifacts
    help           - Show this help message

Examples:
    python scripts/test_documentation_tools.py generate
    python scripts/test_documentation_tools.py validate
    python scripts/test_documentation_tools.py executive
"""

import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context

# Import MCP server and documentation tools
from legacy_web_mcp.mcp.server import create_mcp
from legacy_web_mcp.mcp.documentation_tools import (
    generate_project_documentation,
    generate_executive_summary,
    list_available_artifacts,
    generate_api_documentation,
    validate_documentation_artifacts
)

# Import data models for creating sample artifacts
from legacy_web_mcp.llm.artifacts import AnalysisArtifact


class MockMCPSession:
    """Mock MCP session for testing."""

    def __init__(self):
        self.session_id = "test-session-documentation"

    async def send_log_message(self, level: str, data: Any, logger: str = None, related_request_id: str = None):
        """Mock log message sending - print to console with formatting."""
        prefix = f"[{level.upper()}]"
        if logger:
            prefix += f" {logger}:"
        print(f"{prefix} {data}")


class TestDocumentationContext:
    """Test context for documentation tools."""

    def __init__(self):
        self._session = MockMCPSession()

    @property
    def session(self):
        return self._session

    async def info(self, message: str) -> None:
        """Log info message."""
        print(f"[INFO] {message}")

    async def error(self, message: str) -> None:
        """Log error message."""
        print(f"[ERROR] {message}")

    async def warn(self, message: str) -> None:
        """Log warning message."""
        print(f"[WARN] {message}")


def create_sample_artifacts() -> List[AnalysisArtifact]:
    """Create sample analysis artifacts for testing documentation generation."""
    return [
        # Home page content summary
        AnalysisArtifact(
            artifact_id="home_content_summary",
            analysis_type="step1",
            page_url="https://example-ecommerce.com/",
            timestamp=datetime.now(UTC),
            step1_result={
                "purpose": "Product discovery and user conversion",
                "user_context": "Potential customers browsing for products",
                "business_logic": "E-commerce homepage with product showcase and navigation",
                "navigation_role": "Primary entry point for site navigation",
                "business_importance": 0.95,
                "confidence_score": 0.92,
                "key_workflows": ["product_browsing", "search", "account_login"],
                "user_journey_stage": "entry",
                "contextual_keywords": ["ecommerce", "products", "shopping", "navigation"]
            },
            quality_metrics={
                "overall_quality_score": 0.92,
                "completeness_score": 0.90,
                "technical_depth_score": 0.85
            },
            metadata={
                "page_title": "Example E-commerce - Home",
                "analysis_status": "completed",
                "processing_time": 2.3
            },
            status="completed"
        ),

        # Home page feature analysis
        AnalysisArtifact(
            artifact_id="home_feature_analysis",
            analysis_type="step2",
            page_url="https://example-ecommerce.com/",
            timestamp=datetime.now(UTC),
            step2_result={
                "interactive_elements": [
                    {
                        "type": "form",
                        "selector": "#search-form",
                        "purpose": "Product search functionality",
                        "behavior": "submit"
                    },
                    {
                        "type": "button",
                        "selector": ".login-btn",
                        "purpose": "User authentication",
                        "behavior": "click"
                    },
                    {
                        "type": "button",
                        "selector": ".add-to-cart",
                        "purpose": "Add products to shopping cart",
                        "behavior": "click"
                    }
                ],
                "functional_capabilities": [
                    {
                        "name": "Product Search",
                        "description": "Search products with filters and pagination",
                        "type": "feature",
                        "complexity_score": 0.7
                    },
                    {
                        "name": "User Authentication",
                        "description": "JWT-based authentication with social login",
                        "type": "service",
                        "complexity_score": 0.4
                    },
                    {
                        "name": "Shopping Cart",
                        "description": "Session-based cart management",
                        "type": "feature",
                        "complexity_score": 0.6
                    }
                ],
                "api_integrations": [
                    {
                        "endpoint": "/api/products/search",
                        "method": "GET",
                        "purpose": "Product search with filters and pagination",
                        "data_flow": "client-to-server"
                    },
                    {
                        "endpoint": "/api/auth/login",
                        "method": "POST",
                        "purpose": "User authentication endpoint",
                        "data_flow": "client-to-server"
                    },
                    {
                        "endpoint": "/api/cart",
                        "method": "GET",
                        "purpose": "Retrieve user's shopping cart",
                        "data_flow": "server-to-client"
                    }
                ],
                "business_rules": [
                    {
                        "name": "Search Validation",
                        "description": "Validate search query parameters",
                        "validation_logic": "Require minimum 2 characters for search"
                    }
                ],
                "rebuild_specifications": [
                    {
                        "name": "Product Search Component",
                        "description": "React component with search filters",
                        "priority_score": 0.9,
                        "complexity": "medium",
                        "dependencies": ["search-api", "filter-component"]
                    }
                ]
            },
            quality_metrics={
                "overall_quality_score": 0.89,
                "completeness_score": 0.88,
                "technical_depth_score": 0.82
            },
            metadata={
                "page_title": "Example E-commerce - Home",
                "analysis_status": "completed",
                "processing_time": 4.1
            },
            status="completed"
        ),

    ]


async def test_generate_documentation():
    """Test complete project documentation generation."""
    print("=== Testing Complete Documentation Generation ===")

    context = TestDocumentationContext()

    # Mock artifacts by patching the artifact manager
    import unittest.mock
    sample_artifacts = create_sample_artifacts()

    with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager') as mock_manager_class:
        mock_manager = unittest.mock.MagicMock()  # Use MagicMock instead of AsyncMock
        mock_manager.list_artifacts.return_value = sample_artifacts
        mock_manager_class.return_value = mock_manager

        with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_config:
            mock_config.return_value = unittest.mock.MagicMock()

            result = await generate_project_documentation(
                context=context,
                project_name="Example E-commerce Platform",
                output_path="/tmp/example_ecommerce_documentation.md",
                include_technical_specs=True,
                include_api_docs=True,
                include_business_logic=True,
                quality_threshold=0.8
            )

    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Project: {result['project_name']}")
        print(f"Word Count: {result['word_count']}")
        print(f"Sections Generated: {result['sections_generated']}")
        print(f"Total Pages Analyzed: {result['metadata']['total_pages']}")
        print(f"Features Identified: {result['metadata']['features_identified']}")
        print(f"Average Quality Score: {result['metadata']['average_quality']:.2f}")

        # Show sample of documentation content
        print("\n=== Documentation Preview ===")
        content_lines = result['documentation_content'].split('\n')
        preview_lines = content_lines[:50]  # Show first 50 lines
        print('\n'.join(preview_lines))
        if len(content_lines) > 50:
            print(f"\n... [Content truncated - showing first 50 of {len(content_lines)} lines] ...")
    else:
        print(f"Error: {result['error']}")


async def test_executive_summary():
    """Test executive summary generation."""
    print("=== Testing Executive Summary Generation ===")

    context = TestDocumentationContext()
    sample_artifacts = create_sample_artifacts()

    with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager') as mock_manager_class:
        mock_manager = unittest.mock.MagicMock()  # Use MagicMock instead of AsyncMock
        mock_manager.list_artifacts.return_value = sample_artifacts
        mock_manager_class.return_value = mock_manager

        with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_config:
            mock_config.return_value = unittest.mock.MagicMock()

            result = await generate_executive_summary(
                context=context,
                project_name="Example E-commerce Platform",
                quality_threshold=0.8
            )

    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Project: {result['project_name']}")
        print("\n=== Executive Summary Content ===")
        print(result['executive_summary'])

        print("\n=== Project Metrics ===")
        metrics = result['project_metrics']
        for key, value in metrics.items():
            print(f"  {key}: {value}")
    else:
        print(f"Error: {result['error']}")


async def test_validate_artifacts():
    """Test artifact validation for documentation readiness."""
    print("=== Testing Artifact Validation ===")

    context = TestDocumentationContext()
    sample_artifacts = create_sample_artifacts()

    with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager') as mock_manager_class:
        mock_manager = unittest.mock.MagicMock()  # Use MagicMock instead of AsyncMock
        mock_manager.list_artifacts.return_value = sample_artifacts
        mock_manager_class.return_value = mock_manager

        with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_config:
            mock_config.return_value = unittest.mock.MagicMock()

            result = await validate_documentation_artifacts(
                context=context,
                quality_threshold=0.8
            )

    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        validation = result['validation_results']
        print(f"Total Artifacts: {validation['total_artifacts']}")
        print(f"High Quality Artifacts: {validation['high_quality_artifacts']}")
        print(f"Medium Quality Artifacts: {validation['medium_quality_artifacts']}")
        print(f"Low Quality Artifacts: {validation['low_quality_artifacts']}")
        print(f"Content Summaries: {validation['content_summaries']}")
        print(f"Feature Analyses: {validation['feature_analyses']}")
        print(f"Documentation Ready: {validation['documentation_ready']}")

        if validation['recommendations']:
            print("\n=== Recommendations ===")
            for rec in validation['recommendations']:
                print(f"  • {rec}")
    else:
        print(f"Error: {result['error']}")


async def test_list_artifacts():
    """Test listing available artifacts."""
    print("=== Testing Artifact Listing ===")

    context = TestDocumentationContext()
    sample_artifacts = create_sample_artifacts()

    with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager') as mock_manager_class:
        mock_manager = unittest.mock.MagicMock()  # Use MagicMock instead of AsyncMock
        mock_manager.list_artifacts.return_value = sample_artifacts
        mock_manager_class.return_value = mock_manager

        with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_config:
            mock_config.return_value = unittest.mock.MagicMock()

            result = await list_available_artifacts(
                context=context,
                quality_threshold=0.8,
                artifact_type=None
            )

    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Total Artifacts: {result['total_artifacts']}")
        print(f"Filtered Artifacts: {result['filtered_artifacts']}")

        print("\n=== Available Artifacts ===")
        for artifact in result['artifacts']:
            print(f"  ID: {artifact['artifact_id']}")
            print(f"  URL: {artifact['url']}")
            print(f"  Type: {artifact['artifact_type']}")
            print(f"  Quality: {artifact['quality_score']:.2f}")
            print(f"  Title: {artifact['page_title']}")
            print()
    else:
        print(f"Error: {result['error']}")


async def test_api_documentation():
    """Test API documentation generation."""
    print("=== Testing API Documentation Generation ===")

    context = TestDocumentationContext()
    sample_artifacts = create_sample_artifacts()

    with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.ArtifactManager') as mock_manager_class:
        mock_manager = unittest.mock.MagicMock()  # Use MagicMock instead of AsyncMock
        mock_manager.list_artifacts.return_value = sample_artifacts
        mock_manager_class.return_value = mock_manager

        with unittest.mock.patch('legacy_web_mcp.mcp.documentation_tools.load_configuration') as mock_config:
            mock_config.return_value = unittest.mock.MagicMock()

            result = await generate_api_documentation(
                context=context,
                project_name="Example E-commerce Platform",
                quality_threshold=0.8
            )

    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Project: {result['project_name']}")
        print(f"Artifacts Analyzed: {result['artifacts_analyzed']}")

        print("\n=== API Documentation Content ===")
        print(result['api_documentation'])
    else:
        print(f"Error: {result['error']}")


def show_help():
    """Show usage help."""
    print(__doc__)


async def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        command = "generate"
    else:
        command = sys.argv[1].lower()

    print(f"Story 4.3 Documentation Tools Test Script")
    print(f"Command: {command}")
    print("=" * 60)

    try:
        if command == "generate":
            await test_generate_documentation()
        elif command == "validate":
            await test_validate_artifacts()
        elif command == "executive":
            await test_executive_summary()
        elif command == "api":
            await test_api_documentation()
        elif command == "list":
            await test_list_artifacts()
        elif command == "help":
            show_help()
        else:
            print(f"Unknown command: {command}")
            show_help()
            sys.exit(1)

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Test completed successfully!")


if __name__ == "__main__":
    # Import required modules for mocking
    import unittest.mock

    asyncio.run(main())