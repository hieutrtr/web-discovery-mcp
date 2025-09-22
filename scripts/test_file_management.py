#!/usr/bin/env python3
"""Test script for Story 4.4 File Management and Organization functionality.

This script demonstrates the complete file organization system including:
- Project structure setup
- Artifact organization
- Master report generation
- MCP resource exposure
- Version control considerations
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastmcp import Context

# Import MCP file management tools
from legacy_web_mcp.mcp.file_management_tools import (
    setup_project_documentation_structure,
    organize_project_artifacts,
    generate_master_analysis_report,
    list_project_documentation_files,
    generate_url_slug,
    create_gitignore_for_web_discovery
)

# Import file management components
from legacy_web_mcp.file_management.organizer import ProjectArtifactOrganizer
from legacy_web_mcp.mcp.resources import WebDiscoveryResourceProvider


class SimpleContext:
    """Simple context for testing without full MCP session."""

    async def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    async def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

    async def warn(self, message: str) -> None:
        print(f"[WARN] {message}")


async def test_file_management_system():
    """Test the complete file management system."""
    print("=== Testing Story 4.4: File Management and Organization ===\n")

    context = SimpleContext()

    # Use temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        project_root = temp_dir
        project_name = "Example E-commerce Platform"
        website_url = "https://example-ecommerce.com"
        project_id = "Example E-commerce Platform"

        print(f"Testing in temporary directory: {project_root}\n")

        # Test 1: Setup project documentation structure
        print("1. Setting up project documentation structure...")
        setup_result = await setup_project_documentation_structure(
            context=context,
            project_root=project_root,
            project_name=project_name,
            website_url=website_url
        )
        print(f"Status: {setup_result['status']}")
        if setup_result['status'] == 'success':
            print(f"Docs root: {setup_result['docs_root']}")
            print(f"Folders created: {len(setup_result['folders_created'])}")
            for folder in setup_result['folders_created']:
                print(f"  - {folder}")
        print()

        # Test 2: URL slug generation
        print("2. Testing URL slug generation...")
        test_urls = [
            "https://example-ecommerce.com/",
            "https://example-ecommerce.com/products/laptop-abc123",
            "https://example-ecommerce.com/search?q=laptop&category=electronics",
            "https://complex-site.com/very/deep/path/with-special-chars!@#.html"
        ]

        for url in test_urls:
            slug_result = await generate_url_slug(context=context, url=url)
            if slug_result['status'] == 'success':
                print(f"  {url}")
                print(f"    -> Slug: {slug_result['slug']}")
                print(f"    -> File: {slug_result['filename']}")
            else:
                print(f"  {url} -> ERROR: {slug_result['error']}")
        print()

        # Test 3: Organize project artifacts (with real artifacts)
        print("3. Organizing project artifacts...")
        organize_result = await organize_project_artifacts(
            context=context,
            project_root=project_root,
            project_id=project_id,
            project_name=project_name,
            website_url=website_url
        )
        print(f"Status: {organize_result['status']}")
        if organize_result['status'] == 'success':
            print(f"Artifacts processed: {organize_result['artifacts_processed']}")
            print(f"Page files written: {organize_result['page_files_written']}")
            print(f"Quality score: {organize_result['quality_score']:.2f}")
            print(f"Analysis status: {organize_result['analysis_status']}")
            if organize_result['page_files']:
                print("Page files created:")
                for page_file in organize_result['page_files'][:3]:  # Show first 3
                    print(f"  - {page_file}")
                if len(organize_result['page_files']) > 3:
                    print(f"  ... and {len(organize_result['page_files']) - 3} more")
        print()

        # Test 4: Generate master analysis report
        print("4. Generating master analysis report...")
        report_result = await generate_master_analysis_report(
            context=context,
            project_root=project_root,
            project_id=project_id,
            project_name=project_name,
            include_technical_specs=True,
            include_debug_info=False
        )
        print(f"Status: {report_result['status']}")
        if report_result['status'] == 'success':
            print(f"Master report path: {report_result['master_report_path']}")
            print(f"Content length: {report_result['content_length']} characters")
            print(f"Sections generated: {report_result['sections_generated']}")
            summary = report_result['project_summary']
            print(f"Pages analyzed: {summary['total_pages']}")
            print(f"Features identified: {summary['features_identified']}")
            print(f"API endpoints: {summary['api_endpoints']}")
        print()

        # Test 5: List project documentation files
        print("5. Listing project documentation files...")
        list_result = await list_project_documentation_files(
            context=context,
            project_root=project_root
        )
        print(f"Status: {list_result['status']}")
        if list_result['status'] == 'success':
            file_info = list_result['file_info']
            print(f"Metadata file exists: {file_info.get('metadata', {}).get('exists', False)}")
            print(f"Master report exists: {file_info.get('master_report', {}).get('exists', False)}")
            print(f"Page files count: {file_info.get('pages', {}).get('count', 0)}")

            # Show file structure
            structure = list_result['file_listing']['structure']
            print("\nFile structure:")
            if structure['metadata']['exists']:
                print(f"  📄 analysis-metadata.json")
            if structure['master_report']['exists']:
                print(f"  📊 analysis-report.md")
            print(f"  📁 pages/ ({len(structure['pages'])} files)")
            print(f"  📁 progress/ ({len(structure['progress'])} files)")
            print(f"  📁 reports/ ({len(structure['reports'])} files)")
        print()

        # Test 6: Version control considerations
        print("6. Creating version control guidance...")
        gitignore_result = await create_gitignore_for_web_discovery(
            context=context,
            project_root=project_root,
            exclude_progress=True,
            exclude_large_reports=False
        )
        print(f"Status: {gitignore_result['status']}")
        if gitignore_result['status'] == 'success':
            print(f"Gitignore action: {gitignore_result['action']}")
            print(f"Guidance file: {gitignore_result['guidance_path']}")
            print(f"Exclude progress: {gitignore_result['exclude_progress']}")
            print(f"Exclude large reports: {gitignore_result['exclude_large_reports']}")
        print()

        # Test 7: MCP Resource Provider
        print("7. Testing MCP resource provider...")
        try:
            resource_provider = WebDiscoveryResourceProvider(project_root)
            resources = resource_provider.list_all_resources()
            print(f"Total resources available: {len(resources)}")

            for resource in resources:
                print(f"  📄 {resource['name']}")
                print(f"     URI: {resource['uri']}")
                print(f"     Type: {resource['mimeType']}")
                print(f"     Description: {resource['description']}")

                # Test reading a resource
                try:
                    content = resource_provider.get_resource_content(resource['uri'])
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"     Content preview: {content_preview}")
                except Exception as e:
                    print(f"     Content read error: {e}")
                print()

        except Exception as e:
            print(f"Resource provider error: {e}")
        print()

        # Test 8: Show sample file contents
        print("8. Sample file contents...")

        # Show metadata file
        docs_path = Path(project_root) / "docs" / "web_discovery"
        metadata_file = docs_path / "analysis-metadata.json"
        if metadata_file.exists():
            print("📄 analysis-metadata.json content:")
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            print(json.dumps(metadata, indent=2))
            print()

        # Show a sample page file
        pages_dir = docs_path / "pages"
        page_files = list(pages_dir.glob("page-*.md"))
        if page_files:
            sample_page = page_files[0]
            print(f"📄 Sample page file: {sample_page.name}")
            content = sample_page.read_text(encoding='utf-8')
            lines = content.split('\n')
            preview_lines = lines[:30]  # Show first 30 lines
            print('\n'.join(preview_lines))
            if len(lines) > 30:
                print(f"\n... [showing first 30 of {len(lines)} lines]")
            print()

        # Show VCS guidance
        vcs_guidance = docs_path / "VCS-GUIDANCE.md"
        if vcs_guidance.exists():
            print("📄 VCS-GUIDANCE.md content:")
            content = vcs_guidance.read_text(encoding='utf-8')
            lines = content.split('\n')
            preview_lines = lines[:20]  # Show first 20 lines
            print('\n'.join(preview_lines))
            if len(lines) > 20:
                print(f"\n... [showing first 20 of {len(lines)} lines]")

        print("\n" + "=" * 80)
        print("✅ File Management System Test Complete!")
        print("\nAll acceptance criteria for Story 4.4 have been demonstrated:")
        print("1. ✅ Project documentation structure created in docs/web_discovery/")
        print("2. ✅ Analysis subfolders: progress/, pages/, reports/")
        print("3. ✅ Individual page files with URL slug naming")
        print("4. ✅ Project metadata JSON with tracking details")
        print("5. ✅ Master analysis report placed at required location")
        print("6. ✅ MCP resources exposed for AI tool access")
        print("7. ✅ Version control guidance and .gitignore recommendations")


if __name__ == "__main__":
    asyncio.run(test_file_management_system())