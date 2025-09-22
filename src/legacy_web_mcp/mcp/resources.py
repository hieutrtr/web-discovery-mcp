"""MCP resources for exposing project documentation files.

This module provides MCP resources to expose analysis artifacts and documentation
files for access by Claude Code and other AI development tools.
"""

import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote

from fastmcp import FastMCP, Context
# Note: Using dict instead of Resource class for compatibility

from ..file_management.organizer import ProjectArtifactOrganizer
from ..llm.artifacts import ArtifactManager


class WebDiscoveryResourceProvider:
    """Provides MCP resources for web discovery documentation files."""

    def __init__(self, project_root: str):
        """Initialize the resource provider.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.artifact_manager = ArtifactManager()
        self.organizer = ProjectArtifactOrganizer(str(project_root), self.artifact_manager)

    def get_resource_uri(self, file_path: Path) -> str:
        """Generate a resource URI for a file.

        Args:
            file_path: Path to the file

        Returns:
            Resource URI string
        """
        # Make relative to project root
        try:
            relative_path = file_path.relative_to(self.project_root)
        except ValueError:
            # File is not under project root, use absolute path
            relative_path = file_path

        # Convert to URI format
        uri_path = str(relative_path).replace('\\', '/')
        return f"web_discovery://{quote(uri_path)}"

    def list_all_resources(self) -> List[Dict[str, str]]:
        """List all available web discovery resources.

        Returns:
            List of resource dictionaries
        """
        resources = []

        # Get file listing
        file_listing = self.organizer.get_project_file_listing()

        # Add metadata file
        if file_listing["structure"]["metadata"]["exists"]:
            metadata_path = Path(file_listing["structure"]["metadata"]["file"])
            resources.append({
                "uri": self.get_resource_uri(metadata_path),
                "name": f"Analysis Metadata",
                "description": "Project analysis metadata and progress tracking",
                "mimeType": "application/json"
            })

        # Add master report
        if file_listing["structure"]["master_report"]["exists"]:
            report_path = Path(file_listing["structure"]["master_report"]["file"])
            resources.append({
                "uri": self.get_resource_uri(report_path),
                "name": f"Master Analysis Report",
                "description": "Comprehensive analysis report for the entire project",
                "mimeType": "text/markdown"
            })

        # Add page files
        for page_file_str in file_listing["structure"]["pages"]:
            page_path = Path(page_file_str)
            page_name = page_path.stem.replace("page-", "").replace("-", " ").title()
            resources.append({
                "uri": self.get_resource_uri(page_path),
                "name": f"Page Analysis: {page_name}",
                "description": f"Detailed analysis for individual page",
                "mimeType": "text/markdown"
            })

        # Add progress files
        for progress_file_str in file_listing["structure"]["progress"]:
            progress_path = Path(progress_file_str)
            resources.append({
                "uri": self.get_resource_uri(progress_path),
                "name": f"Progress: {progress_path.name}",
                "description": "Analysis progress tracking file",
                "mimeType": mimetypes.guess_type(str(progress_path))[0] or "text/plain"
            })

        # Add report files
        for report_file_str in file_listing["structure"]["reports"]:
            report_path = Path(report_file_str)
            resources.append({
                "uri": self.get_resource_uri(report_path),
                "name": f"Report: {report_path.name}",
                "description": "Additional analysis report",
                "mimeType": mimetypes.guess_type(str(report_path))[0] or "text/plain"
            })

        return resources

    def get_resource_content(self, uri: str) -> str:
        """Get the content of a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If the resource doesn't exist
            ValueError: If the URI is invalid
        """
        # Parse URI
        if not uri.startswith("web_discovery://"):
            raise ValueError(f"Invalid URI scheme: {uri}")

        # Extract file path
        uri_path = uri[len("web_discovery://"):]
        relative_path = unquote(uri_path)
        file_path = self.project_root / relative_path

        # Security check: ensure file is under project root
        try:
            file_path.resolve().relative_to(self.project_root.resolve())
        except ValueError:
            raise ValueError(f"Access denied: File outside project root: {file_path}")

        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Resource not found: {file_path}")

        # Read and return content
        try:
            return file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Try reading as binary and convert to base64 for non-text files
            import base64
            binary_content = file_path.read_bytes()
            return base64.b64encode(binary_content).decode('ascii')


# Global resource providers for different projects
_resource_providers: Dict[str, WebDiscoveryResourceProvider] = {}


def register_project_resources(mcp: FastMCP, project_root: str, project_name: str) -> None:
    """Register resources for a specific project.

    Args:
        mcp: FastMCP instance
        project_root: Root directory of the project
        project_name: Name of the project (used as identifier)
    """
    global _resource_providers

    # Create resource provider
    provider = WebDiscoveryResourceProvider(project_root)
    _resource_providers[project_name] = provider

    # Register list resources handler


    # Register read resource handler
    @mcp.resource("web_discovery://{file_path}")
    async def read_web_discovery_resource(file_path: str) -> str:
        """Read a web discovery resource by URI path."""
        # Reconstruct the full URI
        uri = f"web_discovery://{file_path}"
        # Try each provider until we find one that can handle the URI
        for project_name, provider in _resource_providers.items():
            try:
                return provider.get_resource_content(uri)
            except (FileNotFoundError, ValueError):
                continue

        # If no provider could handle the URI, raise an error
        raise FileNotFoundError(f"Resource not found: {uri}")


def register_default_project_resources(mcp: FastMCP) -> None:
    """Register resources for the current working directory as default project.

    Args:
        mcp: FastMCP instance
    """
    import os
    current_dir = os.getcwd()
    register_project_resources(mcp, current_dir, "current-project")


def add_project_resources(project_root: str, project_name: str) -> None:
    """Add resources for a new project (for use outside MCP registration).

    Args:
        project_root: Root directory of the project
        project_name: Name of the project
    """
    global _resource_providers
    provider = WebDiscoveryResourceProvider(project_root)
    _resource_providers[project_name] = provider


def list_registered_projects() -> List[str]:
    """List all registered project names.

    Returns:
        List of project names
    """
    return list(_resource_providers.keys())


def get_project_resource_summary(project_name: str) -> Optional[Dict[str, Any]]:
    """Get a summary of resources for a specific project.

    Args:
        project_name: Name of the project

    Returns:
        Dictionary containing resource summary or None if project not found
    """
    provider = _resource_providers.get(project_name)
    if not provider:
        return None

    try:
        resources = provider.list_all_resources()
        file_listing = provider.organizer.get_project_file_listing()

        return {
            "project_name": project_name,
            "project_root": str(provider.project_root),
            "total_resources": len(resources),
            "resource_types": {
                "metadata": 1 if file_listing["structure"]["metadata"]["exists"] else 0,
                "master_report": 1 if file_listing["structure"]["master_report"]["exists"] else 0,
                "pages": len(file_listing["structure"]["pages"]),
                "progress": len(file_listing["structure"]["progress"]),
                "reports": len(file_listing["structure"]["reports"])
            },
            "resources": resources
        }
    except Exception as e:
        import structlog
        logger = structlog.get_logger(__name__)
        logger.error("failed_to_get_project_summary", project=project_name, error=str(e))
        return {
            "project_name": project_name,
            "error": str(e)
        }