"""Artifact file organization and management for project documentation structure.

This module implements the file organization requirements from Story 4.4,
organizing analysis artifacts within the project's docs/web_discovery structure.
"""

import json
import re
import structlog
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from legacy_web_mcp.llm.artifacts import ArtifactManager, AnalysisArtifact

_logger = structlog.get_logger(__name__)


class ProjectMetadata(BaseModel):
    """Metadata for the analyzed project."""

    project_name: str = Field(description="Name of the project being analyzed")
    website_url: str = Field(description="Base URL of the analyzed website")
    analysis_start_date: datetime = Field(description="When analysis began")
    last_update_date: datetime = Field(description="Last update timestamp")
    total_pages_analyzed: int = Field(description="Total number of pages analyzed")
    completed_pages: int = Field(description="Number of successfully analyzed pages")
    failed_pages: int = Field(description="Number of failed page analyses")
    average_quality_score: float = Field(description="Average quality score across all analyses")
    analysis_status: str = Field(description="Overall analysis status (in_progress, completed, failed)")

    # Configuration snapshot
    config_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Analysis configuration used")

    # Page tracking
    pages_analyzed: List[str] = Field(default_factory=list, description="List of analyzed page URLs")
    pages_in_progress: List[str] = Field(default_factory=list, description="List of pages currently being analyzed")
    pages_failed: List[str] = Field(default_factory=list, description="List of pages that failed analysis")


class ProjectArtifactOrganizer:
    """Organizes analysis artifacts within project documentation structure."""

    def __init__(self, project_root: str, artifact_manager: Optional[ArtifactManager] = None):
        """Initialize the artifact organizer.

        Args:
            project_root: Root directory of the project
            artifact_manager: Optional artifact manager for data access
        """
        from ..config.settings import load_settings

        self.project_root = Path(project_root)

        if artifact_manager is None:
            settings = load_settings()
            self.artifact_manager = ArtifactManager(settings=settings)
        else:
            self.artifact_manager = artifact_manager

        # Define the documentation structure
        self.docs_root = self.project_root / "docs" / "web_discovery"
        self.progress_dir = self.docs_root / "progress"
        self.pages_dir = self.docs_root / "pages"
        self.reports_dir = self.docs_root / "reports"

        # Key files
        self.metadata_file = self.docs_root / "analysis-metadata.json"
        self.master_report_file = self.docs_root / "analysis-report.md"

    def setup_project_structure(self) -> None:
        """Create the project documentation folder structure."""
        _logger.info("setting_up_project_structure", project_root=str(self.project_root))

        # Create all required directories
        directories = [
            self.docs_root,
            self.progress_dir,
            self.pages_dir,
            self.reports_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            _logger.debug("created_directory", path=str(directory))

        # Create .gitkeep files to ensure empty directories are tracked
        for directory in [self.progress_dir, self.pages_dir, self.reports_dir]:
            gitkeep = directory / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("# This file ensures the directory is tracked by git\n")

        _logger.info("project_structure_setup_complete", docs_root=str(self.docs_root))

    def generate_url_slug(self, url: str) -> str:
        """Generate a URL slug for file naming.

        Args:
            url: The URL to convert to a slug

        Returns:
            URL slug suitable for filename
        """
        # Parse URL
        parsed = urlparse(url)

        # Start with the domain
        domain = parsed.netloc.replace('www.', '')
        slug_parts = [domain]

        # Add path components
        if parsed.path and parsed.path != '/':
            path_parts = [part for part in parsed.path.split('/') if part]
            slug_parts.extend(path_parts)

        # Add query parameters if present
        if parsed.query:
            # Convert query to readable format
            query_slug = re.sub(r'[&=]', '-', parsed.query)
            slug_parts.append(f"query-{query_slug}")

        # Join and clean up
        slug = '-'.join(slug_parts)

        # Clean slug: keep only alphanumeric, hyphens, and underscores
        slug = re.sub(r'[^a-zA-Z0-9\-_]', '-', slug)

        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Ensure reasonable length (max 100 chars)
        if len(slug) > 100:
            slug = slug[:100].rstrip('-')

        return slug

    def get_page_file_path(self, url: str) -> Path:
        """Get the file path for a page analysis markdown file.

        Args:
            url: The page URL

        Returns:
            Path to the page markdown file
        """
        slug = self.generate_url_slug(url)
        return self.pages_dir / f"page-{slug}.md"

    def write_page_analysis_markdown(self, artifact: AnalysisArtifact) -> Path:
        """Write a page analysis to a markdown file.

        Args:
            artifact: The analysis artifact to write

        Returns:
            Path to the written file
        """
        file_path = self.get_page_file_path(artifact.page_url)

        # Generate markdown content
        content = self._generate_page_markdown_content(artifact)

        # Write file
        file_path.write_text(content, encoding='utf-8')

        _logger.info(
            "page_analysis_written",
            url=artifact.page_url,
            file_path=str(file_path),
            artifact_id=artifact.artifact_id
        )

        return file_path

    def _generate_page_markdown_content(self, artifact: AnalysisArtifact) -> str:
        """Generate markdown content for a page analysis.

        Args:
            artifact: The analysis artifact

        Returns:
            Markdown content as string
        """
        url = artifact.page_url
        timestamp = artifact.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        content = f"""# Page Analysis: {url}

**Analysis ID**: {artifact.artifact_id}
**Analysis Type**: {artifact.analysis_type}
**Timestamp**: {timestamp}
**Status**: {artifact.status}

---

"""

        # Add metadata
        if artifact.metadata:
            content += "## Page Information\n\n"
            page_title = artifact.metadata.get('page_title', 'Unknown')
            content += f"- **Page Title**: {page_title}\n"
            content += f"- **Analysis Status**: {artifact.metadata.get('analysis_status', 'Unknown')}\n"
            processing_time = artifact.metadata.get('processing_time', 'Unknown')
            content += f"- **Processing Time**: {processing_time}s\n\n"

        # Add Step 1 Results (Content Summary)
        if artifact.step1_result:
            content += "## Content Summary\n\n"
            step1 = artifact.step1_result

            content += f"**Purpose**: {step1.get('purpose', 'Not specified')}\n\n"
            content += f"**User Context**: {step1.get('user_context', 'Not specified')}\n\n"
            content += f"**Business Logic**: {step1.get('business_logic', 'Not specified')}\n\n"
            content += f"**Navigation Role**: {step1.get('navigation_role', 'Not specified')}\n\n"

            # Metrics
            business_importance = step1.get('business_importance', 0.0)
            confidence_score = step1.get('confidence_score', 0.0)
            content += f"**Business Importance**: {business_importance:.1%}\n\n"
            content += f"**Confidence Score**: {confidence_score:.1%}\n\n"

            # Workflows
            workflows = step1.get('key_workflows', [])
            if workflows:
                content += "**Key Workflows**:\n"
                for workflow in workflows:
                    content += f"- {workflow.replace('_', ' ').title()}\n"
                content += "\n"

            # Journey stage
            journey_stage = step1.get('user_journey_stage', 'Unknown')
            content += f"**User Journey Stage**: {journey_stage.title()}\n\n"

            # Keywords
            keywords = step1.get('contextual_keywords', [])
            if keywords:
                content += f"**Keywords**: {', '.join(keywords)}\n\n"

        # Add Step 2 Results (Feature Analysis)
        if artifact.step2_result:
            content += "## Feature Analysis\n\n"
            step2 = artifact.step2_result

            # Interactive Elements
            interactive_elements = step2.get('interactive_elements', [])
            if interactive_elements:
                content += "### Interactive Elements\n\n"
                content += "| Type | Selector | Purpose | Behavior |\n"
                content += "|------|----------|---------|----------|\n"
                for element in interactive_elements:
                    elem_type = element.get('type', 'Unknown')
                    selector = element.get('selector', 'N/A')
                    purpose = element.get('purpose', 'Not specified')
                    behavior = element.get('behavior', 'Not specified')
                    content += f"| {elem_type} | `{selector}` | {purpose} | {behavior} |\n"
                content += "\n"

            # Functional Capabilities
            capabilities = step2.get('functional_capabilities', [])
            if capabilities:
                content += "### Functional Capabilities\n\n"
                for cap in capabilities:
                    name = cap.get('name', 'Unnamed')
                    description = cap.get('description', 'No description')
                    capability_type = cap.get('type', 'Unknown')
                    complexity = cap.get('complexity_score', 'Not rated')

                    content += f"#### {name}\n"
                    content += f"- **Type**: {capability_type}\n"
                    content += f"- **Description**: {description}\n"
                    if complexity != 'Not rated':
                        content += f"- **Complexity Score**: {complexity}/10\n"
                    content += "\n"

            # API Integrations
            apis = step2.get('api_integrations', [])
            if apis:
                content += "### API Integrations\n\n"
                content += "| Method | Endpoint | Purpose | Data Flow |\n"
                content += "|--------|----------|---------|----------|\n"
                for api in apis:
                    method = api.get('method', 'Unknown')
                    endpoint = api.get('endpoint', 'Not specified')
                    purpose = api.get('purpose', 'Not specified')
                    data_flow = api.get('data_flow', 'Not specified')
                    content += f"| {method} | `{endpoint}` | {purpose} | {data_flow} |\n"
                content += "\n"

            # Business Rules
            business_rules = step2.get('business_rules', [])
            if business_rules:
                content += "### Business Rules\n\n"
                for rule in business_rules:
                    name = rule.get('name', 'Unnamed Rule')
                    description = rule.get('description', 'No description')
                    validation_logic = rule.get('validation_logic', 'Not specified')

                    content += f"#### {name}\n"
                    content += f"- **Description**: {description}\n"
                    content += f"- **Validation Logic**: {validation_logic}\n\n"

            # Rebuild Specifications
            rebuild_specs = step2.get('rebuild_specifications', [])
            if rebuild_specs:
                content += "### Rebuild Specifications\n\n"
                for spec in rebuild_specs:
                    name = spec.get('name', 'Unnamed Component')
                    description = spec.get('description', 'No description')
                    priority = spec.get('priority_score', 'Not rated')
                    complexity = spec.get('complexity', 'Unknown')
                    dependencies = spec.get('dependencies', [])

                    content += f"#### {name}\n"
                    content += f"- **Description**: {description}\n"
                    content += f"- **Complexity**: {complexity}\n"
                    if priority != 'Not rated':
                        content += f"- **Priority Score**: {priority:.1f}/10\n"
                    if dependencies:
                        content += f"- **Dependencies**: {', '.join(dependencies)}\n"
                    content += "\n"

        # Add Quality Metrics
        if artifact.quality_metrics:
            content += "## Quality Metrics\n\n"
            quality = artifact.quality_metrics

            overall_quality = quality.get('overall_quality_score', 0.0)
            completeness = quality.get('completeness_score', 0.0)
            technical_depth = quality.get('technical_depth_score', 0.0)

            content += f"- **Overall Quality**: {overall_quality:.1%}\n"
            content += f"- **Completeness**: {completeness:.1%}\n"
            content += f"- **Technical Depth**: {technical_depth:.1%}\n\n"

            # Quality issues
            quality_issues = quality.get('quality_issues', [])
            if quality_issues:
                content += "**Quality Issues**:\n"
                for issue in quality_issues:
                    content += f"- {issue}\n"
                content += "\n"

            # Review requirements
            if quality.get('needs_manual_review', False):
                review_reasons = quality.get('review_reasons', [])
                content += "⚠️ **Manual Review Required**\n"
                if review_reasons:
                    content += "**Reasons**:\n"
                    for reason in review_reasons:
                        content += f"- {reason}\n"
                content += "\n"

        # Add errors if any
        if artifact.errors:
            content += "## Analysis Errors\n\n"
            for error in artifact.errors:
                timestamp = error.get('timestamp', 'Unknown')
                error_type = error.get('error_type', 'Unknown')
                error_message = error.get('error_message', 'Unknown error')
                content += f"- **{timestamp}** ({error_type}): {error_message}\n"
            content += "\n"

        # Add cross-references
        content += "---\n\n"
        content += "## Cross-References\n\n"
        content += f"- [Back to Analysis Report](../analysis-report.md)\n"
        content += f"- [Project Metadata](../analysis-metadata.json)\n"
        content += f"- [All Pages](./)\n\n"

        content += f"*Generated on {timestamp} by Legacy Web MCP Server*\n"

        return content

    def load_or_create_metadata(self, project_name: str, website_url: str) -> ProjectMetadata:
        """Load existing metadata or create new metadata.

        Args:
            project_name: Name of the project
            website_url: Base URL of the website being analyzed

        Returns:
            Project metadata object
        """
        if self.metadata_file.exists():
            # Load existing metadata
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            metadata = ProjectMetadata(**data)
            _logger.info("loaded_existing_metadata", project_name=project_name)
        else:
            # Create new metadata
            metadata = ProjectMetadata(
                project_name=project_name,
                website_url=website_url,
                analysis_start_date=datetime.now(),
                last_update_date=datetime.now(),
                total_pages_analyzed=0,
                completed_pages=0,
                failed_pages=0,
                average_quality_score=0.0,
                analysis_status="in_progress"
            )
            _logger.info("created_new_metadata", project_name=project_name)

        return metadata

    def update_metadata_from_artifacts(self, metadata: ProjectMetadata, project_id: str) -> ProjectMetadata:
        """Update metadata based on current artifacts.

        Args:
            metadata: Current metadata object
            project_id: Project identifier to filter artifacts

        Returns:
            Updated metadata object
        """
        # Get all artifacts for the project
        artifacts = self.artifact_manager.list_artifacts(project_id=project_id)

        # Update counts
        metadata.total_pages_analyzed = len(artifacts)
        metadata.completed_pages = len([a for a in artifacts if a.status == "completed"])
        metadata.failed_pages = len([a for a in artifacts if a.status == "failed"])

        # Update page lists
        metadata.pages_analyzed = [a.page_url for a in artifacts]
        metadata.pages_in_progress = [a.page_url for a in artifacts if a.status == "in_progress"]
        metadata.pages_failed = [a.page_url for a in artifacts if a.status == "failed"]

        # Calculate average quality score
        quality_scores = []
        for artifact in artifacts:
            if artifact.quality_metrics:
                score = artifact.quality_metrics.get('overall_quality_score', 0.0)
                quality_scores.append(score)

        if quality_scores:
            metadata.average_quality_score = sum(quality_scores) / len(quality_scores)

        # Update status
        if metadata.failed_pages > 0 and metadata.completed_pages == 0:
            metadata.analysis_status = "failed"
        elif metadata.pages_in_progress:
            metadata.analysis_status = "in_progress"
        elif metadata.completed_pages > 0:
            metadata.analysis_status = "completed"

        metadata.last_update_date = datetime.now()

        _logger.info(
            "metadata_updated",
            total_pages=metadata.total_pages_analyzed,
            completed=metadata.completed_pages,
            failed=metadata.failed_pages,
            status=metadata.analysis_status
        )

        return metadata

    def save_metadata(self, metadata: ProjectMetadata) -> None:
        """Save metadata to the JSON file.

        Args:
            metadata: Metadata object to save
        """
        # Convert to dict with proper serialization
        data = metadata.model_dump()

        # Handle datetime serialization
        data['analysis_start_date'] = metadata.analysis_start_date.isoformat()
        data['last_update_date'] = metadata.last_update_date.isoformat()

        # Write to file
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        _logger.info("metadata_saved", file_path=str(self.metadata_file))

    def organize_project_artifacts(self, project_id: str, project_name: str, website_url: str) -> Dict[str, Any]:
        """Organize all artifacts for a project into the documentation structure.

        Args:
            project_id: Project identifier
            project_name: Human-readable project name
            website_url: Base URL of the analyzed website

        Returns:
            Summary of organization results
        """
        _logger.info("organizing_project_artifacts", project_id=project_id, project_name=project_name)

        # Setup project structure
        self.setup_project_structure()

        # Load or create metadata
        metadata = self.load_or_create_metadata(project_name, website_url)

        # Get all artifacts for the project
        artifacts = self.artifact_manager.list_artifacts(project_id=project_id)

        # Write individual page files
        page_files_written = []
        for artifact in artifacts:
            try:
                file_path = self.write_page_analysis_markdown(artifact)
                page_files_written.append(str(file_path))
            except Exception as e:
                _logger.error(
                    "failed_to_write_page_file",
                    artifact_id=artifact.artifact_id,
                    url=artifact.page_url,
                    error=str(e)
                )

        # Update metadata from current artifacts
        metadata = self.update_metadata_from_artifacts(metadata, project_id)

        # Save updated metadata
        self.save_metadata(metadata)

        result = {
            "project_id": project_id,
            "project_name": project_name,
            "docs_root": str(self.docs_root),
            "artifacts_processed": len(artifacts),
            "page_files_written": len(page_files_written),
            "page_files": page_files_written,
            "metadata_file": str(self.metadata_file),
            "analysis_status": metadata.analysis_status,
            "quality_score": metadata.average_quality_score
        }

        _logger.info("project_artifacts_organized", **result)

        return result

    def copy_master_report(self, source_path: str) -> Path:
        """Copy the master analysis report to the required location.

        Args:
            source_path: Path to the source master report

        Returns:
            Path to the copied report
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source report not found: {source_path}")

        # Copy the report
        content = source.read_text(encoding='utf-8')
        self.master_report_file.write_text(content, encoding='utf-8')

        _logger.info(
            "master_report_copied",
            source=str(source),
            destination=str(self.master_report_file)
        )

        return self.master_report_file

    def get_project_file_listing(self) -> Dict[str, Any]:
        """Get a listing of all project files for MCP resource exposure.

        Returns:
            Dictionary containing file structure information
        """
        result = {
            "project_root": str(self.project_root),
            "docs_root": str(self.docs_root),
            "structure": {
                "metadata": {
                    "file": str(self.metadata_file) if self.metadata_file.exists() else None,
                    "exists": self.metadata_file.exists()
                },
                "master_report": {
                    "file": str(self.master_report_file) if self.master_report_file.exists() else None,
                    "exists": self.master_report_file.exists()
                },
                "pages": [],
                "progress": [],
                "reports": []
            }
        }

        # List page files
        if self.pages_dir.exists():
            for page_file in self.pages_dir.glob("page-*.md"):
                result["structure"]["pages"].append(str(page_file))

        # List progress files
        if self.progress_dir.exists():
            for progress_file in self.progress_dir.glob("*"):
                if progress_file.name != ".gitkeep":
                    result["structure"]["progress"].append(str(progress_file))

        # List report files
        if self.reports_dir.exists():
            for report_file in self.reports_dir.glob("*"):
                if report_file.name != ".gitkeep":
                    result["structure"]["reports"].append(str(report_file))

        return result