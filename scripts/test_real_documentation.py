#!/usr/bin/env python3
"""Test script for real artifact documentation generation.

This script tests the documentation generation using actual artifacts
stored in the artifact system, without mocking.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context

# Import MCP documentation tools directly
from legacy_web_mcp.mcp.documentation_tools import (
    generate_project_documentation,
    generate_executive_summary,
    list_available_artifacts,
    generate_api_documentation,
    validate_documentation_artifacts
)

class SimpleContext:
    """Simple context for testing without full MCP session."""

    async def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    async def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    async def warn(self, message: str) -> None:
        print(f"[WARN] {message}")


async def test_real_documentation():
    """Test documentation generation with real artifacts."""
    print("=== Testing Real Artifact Documentation Generation ===\n")

    context = SimpleContext()
    project_name = "Example E-commerce Platform"

    # Test 1: List available artifacts
    print("1. Listing available artifacts...")
    list_result = await list_available_artifacts(
        context=context,
        quality_threshold=0.8
    )
    print(f"Status: {list_result['status']}")
    if list_result['status'] == 'success':
        print(f"Total artifacts: {list_result['total_artifacts']}")
        print(f"Filtered artifacts: {list_result['filtered_artifacts']}")
        for artifact in list_result.get('artifacts', [])[:2]:  # Show first 2
            print(f"  - {artifact['artifact_id']}: {artifact['url']} (Quality: {artifact['quality_score']:.2f})")
    print()

    # Test 2: Validate artifacts
    print("2. Validating artifacts for documentation...")
    validate_result = await validate_documentation_artifacts(
        context=context,
        quality_threshold=0.8
    )
    print(f"Status: {validate_result['status']}")
    if validate_result['status'] == 'success':
        validation = validate_result['validation_results']
        print(f"Documentation ready: {validation['documentation_ready']}")
        print(f"High quality artifacts: {validation['high_quality_artifacts']}")
        print(f"Content summaries: {validation['content_summaries']}")
        print(f"Feature analyses: {validation['feature_analyses']}")
    print()

    # Test 3: Generate executive summary
    print("3. Generating executive summary...")
    exec_result = await generate_executive_summary(
        context=context,
        project_name=project_name,
        quality_threshold=0.8
    )
    print(f"Status: {exec_result['status']}")
    if exec_result['status'] == 'success':
        print("Executive Summary Generated!")
        print(f"Preview: {exec_result['executive_summary'][:200]}...")
        metrics = exec_result['project_metrics']
        print(f"Pages analyzed: {metrics['total_pages']}")
        print(f"Features found: {metrics['features_identified']}")
        print(f"API endpoints: {metrics['api_endpoints']}")
    else:
        print(f"Error: {exec_result['error']}")
    print()

    # Test 4: Generate API documentation
    print("4. Generating API documentation...")
    api_result = await generate_api_documentation(
        context=context,
        project_name=project_name,
        quality_threshold=0.8
    )
    print(f"Status: {api_result['status']}")
    if api_result['status'] == 'success':
        print("API Documentation Generated!")
        print(f"Artifacts analyzed: {api_result['artifacts_analyzed']}")
        print(f"Preview: {api_result['api_documentation'][:200]}...")
    else:
        print(f"Error: {api_result['error']}")
    print()

    # Test 5: Generate complete documentation
    print("5. Generating complete project documentation...")
    output_path = "/tmp/real_artifact_documentation.md"
    doc_result = await generate_project_documentation(
        context=context,
        project_name=project_name,
        output_path=output_path,
        include_technical_specs=True,
        include_api_docs=True,
        include_business_logic=True,
        quality_threshold=0.8
    )
    print(f"Status: {doc_result['status']}")
    if doc_result['status'] == 'success':
        print("Complete Documentation Generated!")
        print(f"Word count: {doc_result['word_count']}")
        print(f"Sections: {doc_result['sections_generated']}")
        print(f"Output saved to: {doc_result['output_path']}")

        # Show first few lines of generated documentation
        if Path(output_path).exists():
            with open(output_path, 'r') as f:
                lines = f.readlines()[:20]
            print("\n=== Documentation Preview ===")
            print(''.join(lines))
            print(f"... [showing first 20 lines of {len(f.readlines()) + 20} total lines]")
    else:
        print(f"Error: {doc_result['error']}")
        if 'available_projects' in doc_result:
            print(f"Available projects: {doc_result['available_projects']}")


if __name__ == "__main__":
    asyncio.run(test_real_documentation())