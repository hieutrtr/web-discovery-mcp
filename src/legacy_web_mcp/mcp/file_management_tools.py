"""MCP tools for artifact file management and organization.

This module provides MCP tools to organize analysis artifacts within the
project's documentation structure as specified in Story 4.4.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from fastmcp import FastMCP, Context

from ..file_management.organizer import ProjectArtifactOrganizer
from ..documentation.assembler import DocumentationAssembler
from ..config.loader import load_configuration
from ..llm.artifacts import ArtifactManager


async def setup_project_documentation_structure(
    context: Context,
    project_root: str,
    project_name: str,
    website_url: str
) -> Dict[str, Any]:
    """Setup the project documentation folder structure.

    Args:
        project_root: Root directory of the project
        project_name: Human-readable project name
        website_url: Base URL of the website being analyzed

    Returns:
        Dict containing setup results and folder structure information
    """
    try:
        await context.info(f"Setting up documentation structure for project: {project_name}")

        # Initialize organizer
        artifact_manager = ArtifactManager()
        organizer = ProjectArtifactOrganizer(project_root, artifact_manager)

        # Setup folder structure
        organizer.setup_project_structure()

        # Create initial metadata
        metadata = organizer.load_or_create_metadata(project_name, website_url)
        organizer.save_metadata(metadata)

        # Get file structure info
        file_listing = organizer.get_project_file_listing()

        return {
            "status": "success",
            "project_name": project_name,
            "project_root": project_root,
            "docs_root": str(organizer.docs_root),
            "folders_created": [
                str(organizer.docs_root),
                str(organizer.progress_dir),
                str(organizer.pages_dir),
                str(organizer.reports_dir)
            ],
            "metadata_file": str(organizer.metadata_file),
            "file_structure": file_listing
        }

    except Exception as e:
        await context.error(f"Project setup failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_name": project_name
        }


async def organize_project_artifacts(
    context: Context,
    project_root: str,
    project_id: str,
    project_name: str,
    website_url: str
) -> Dict[str, Any]:
    """Organize analysis artifacts into the project documentation structure.

    Args:
        project_root: Root directory of the project
        project_id: Project identifier used in artifacts
        project_name: Human-readable project name
        website_url: Base URL of the analyzed website

    Returns:
        Dict containing organization results
    """
    try:
        await context.info(f"Organizing artifacts for project: {project_name}")

        # Initialize components
        artifact_manager = ArtifactManager()
        organizer = ProjectArtifactOrganizer(project_root, artifact_manager)

        # Organize all artifacts
        result = organizer.organize_project_artifacts(project_id, project_name, website_url)

        return {
            "status": "success",
            **result
        }

    except Exception as e:
        await context.error(f"Artifact organization failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_id": project_id
        }


async def generate_master_analysis_report(
    context: Context,
    project_root: str,
    project_id: str,
    project_name: str,
    include_technical_specs: bool = True,
    include_debug_info: bool = False
) -> Dict[str, Any]:
    """Generate the master analysis report and place it at the required location.

    Args:
        project_root: Root directory of the project
        project_id: Project identifier used in artifacts
        project_name: Human-readable project name
        include_technical_specs: Whether to include technical specifications
        include_debug_info: Whether to include debugging information

    Returns:
        Dict containing generation results
    """
    try:
        await context.info(f"Generating master analysis report for project: {project_name}")

        # Initialize components
        config = load_configuration()
        artifact_manager = ArtifactManager()
        assembler = DocumentationAssembler(artifact_manager)
        organizer = ProjectArtifactOrganizer(project_root, artifact_manager)

        # Ensure project structure exists
        organizer.setup_project_structure()

        # Generate master report using DocumentationAssembler
        temp_output_path = "/tmp/master_analysis_report.md"
        documentation_content = assembler.generate_project_documentation(
            project_id=project_id,
            output_path=temp_output_path,
            include_technical_specs=include_technical_specs,
            include_debug_info=include_debug_info
        )

        # Copy to the required location
        master_report_path = organizer.copy_master_report(temp_output_path)

        # Update metadata to reflect report generation
        metadata = organizer.load_or_create_metadata(project_name, "")
        metadata = organizer.update_metadata_from_artifacts(metadata, project_id)
        organizer.save_metadata(metadata)

        return {
            "status": "success",
            "project_id": project_id,
            "project_name": project_name,
            "master_report_path": str(master_report_path),
            "content_length": len(documentation_content),
            "sections_generated": len(assembler.sections) if assembler.sections else 0,
            "project_summary": {
                "total_pages": assembler.project_summary.total_pages_analyzed if assembler.project_summary else 0,
                "features_identified": assembler.project_summary.total_features_identified if assembler.project_summary else 0,
                "api_endpoints": assembler.project_summary.total_api_endpoints if assembler.project_summary else 0,
                "complexity": assembler.project_summary.complexity_assessment if assembler.project_summary else "Unknown"
            }
        }

    except Exception as e:
        await context.error(f"Master report generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_id": project_id
        }


async def list_project_documentation_files(
    context: Context,
    project_root: str
) -> Dict[str, Any]:
    """List all documentation files in the project structure.

    Args:
        project_root: Root directory of the project

    Returns:
        Dict containing file listing information
    """
    try:
        await context.info(f"Listing documentation files for project: {project_root}")

        # Initialize organizer
        artifact_manager = ArtifactManager()
        organizer = ProjectArtifactOrganizer(project_root, artifact_manager)

        # Get file listing
        file_listing = organizer.get_project_file_listing()

        # Add file content info
        file_info = {}

        # Check metadata file
        if organizer.metadata_file.exists():
            stat = organizer.metadata_file.stat()
            file_info["metadata"] = {
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "exists": True
            }

        # Check master report
        if organizer.master_report_file.exists():
            stat = organizer.master_report_file.stat()
            file_info["master_report"] = {
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "exists": True
            }

        # Count page files
        page_count = len(file_listing["structure"]["pages"])
        file_info["pages"] = {
            "count": page_count,
            "files": file_listing["structure"]["pages"]
        }

        return {
            "status": "success",
            "project_root": project_root,
            "file_listing": file_listing,
            "file_info": file_info
        }

    except Exception as e:
        await context.error(f"File listing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_root": project_root
        }


async def generate_url_slug(
    context: Context,
    url: str
) -> Dict[str, Any]:
    """Generate a URL slug for file naming.

    Args:
        url: The URL to convert to a slug

    Returns:
        Dict containing the generated slug
    """
    try:
        # Initialize organizer (we just need the slug generation method)
        organizer = ProjectArtifactOrganizer("/tmp")
        slug = organizer.generate_url_slug(url)

        return {
            "status": "success",
            "url": url,
            "slug": slug,
            "filename": f"page-{slug}.md"
        }

    except Exception as e:
        await context.error(f"Slug generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "url": url
        }


async def create_gitignore_for_web_discovery(
    context: Context,
    project_root: str,
    exclude_progress: bool = False,
    exclude_large_reports: bool = False
) -> Dict[str, Any]:
    """Create or update .gitignore with web discovery considerations.

    Args:
        project_root: Root directory of the project
        exclude_progress: Whether to exclude progress files from version control
        exclude_large_reports: Whether to exclude large report files

    Returns:
        Dict containing gitignore update results
    """
    try:
        await context.info(f"Creating gitignore guidance for project: {project_root}")

        project_path = Path(project_root)
        gitignore_path = project_path / ".gitignore"

        # Gitignore content for web discovery
        web_discovery_section = """
# Web Discovery Analysis Files
# Generated by Legacy Web MCP Server

"""

        if exclude_progress:
            web_discovery_section += """# Exclude progress tracking files (frequently changing)
docs/web_discovery/progress/
"""

        if exclude_large_reports:
            web_discovery_section += """# Exclude large analysis reports (can be regenerated)
docs/web_discovery/analysis-report.md
docs/web_discovery/reports/*.md
"""

        web_discovery_section += """# Keep metadata and page analyses (valuable for team)
!docs/web_discovery/analysis-metadata.json
!docs/web_discovery/pages/

# Exclude temporary analysis files
*.analysis-temp
*.artifact-backup
"""

        # Read existing gitignore or create new
        existing_content = ""
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text(encoding='utf-8')

        # Check if web discovery section already exists
        if "# Web Discovery Analysis Files" in existing_content:
            await context.info("Web discovery section already exists in .gitignore")
            action = "already_exists"
        else:
            # Append web discovery section
            new_content = existing_content + web_discovery_section
            gitignore_path.write_text(new_content, encoding='utf-8')
            action = "added"

        # Create guidance document
        guidance_content = f"""# Version Control Guidance for Web Discovery

## Overview
This document provides guidance for managing web discovery analysis files in version control.

## Recommended Approach

### Include in Version Control
- `docs/web_discovery/analysis-metadata.json` - Project metadata and progress tracking
- `docs/web_discovery/pages/page-*.md` - Individual page analysis files
- `docs/web_discovery/analysis-report.md` - Master analysis report (if not too large)

### Consider Excluding
- `docs/web_discovery/progress/` - Progress tracking files (change frequently)
- Large report files that can be regenerated from artifacts

### Team Collaboration
- Page analysis files provide valuable context for developers
- Metadata file helps track overall project analysis status
- Master report can be regenerated as needed

## Git Configuration Applied
The following rules have been {"added to" if action == "added" else "found in"} .gitignore:

```gitignore
{web_discovery_section.strip()}
```

Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Legacy Web MCP Server
"""

        guidance_path = project_path / "docs" / "web_discovery" / "VCS-GUIDANCE.md"
        guidance_path.parent.mkdir(parents=True, exist_ok=True)
        guidance_path.write_text(guidance_content, encoding='utf-8')

        return {
            "status": "success",
            "project_root": project_root,
            "gitignore_path": str(gitignore_path),
            "guidance_path": str(guidance_path),
            "action": action,
            "exclude_progress": exclude_progress,
            "exclude_large_reports": exclude_large_reports
        }

    except Exception as e:
        await context.error(f"Gitignore creation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_root": project_root
        }


def register(mcp: FastMCP) -> None:
    """Register file management tools with the MCP server."""
    mcp.tool(setup_project_documentation_structure)
    mcp.tool(organize_project_artifacts)
    mcp.tool(generate_master_analysis_report)
    mcp.tool(list_project_documentation_files)
    mcp.tool(generate_url_slug)
    mcp.tool(create_gitignore_for_web_discovery)