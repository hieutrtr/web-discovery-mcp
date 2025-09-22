"""Documentation assembler for creating comprehensive analysis reports.

This module provides functionality to consume analysis artifacts from Epic 3
and generate structured, markdown-formatted documentation suitable for
development teams, architects, and stakeholders.
"""

from __future__ import annotations

import re
import structlog
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from pydantic import BaseModel, Field

from legacy_web_mcp.llm.models import (
    ContentSummary,
    FeatureAnalysis,
    CombinedAnalysisResult,
    InteractiveElement,
    FunctionalCapability,
    APIIntegration,
    BusinessRule,
    RebuildSpecification
)
from legacy_web_mcp.llm.artifacts import ArtifactManager, AnalysisArtifact

_logger = structlog.get_logger(__name__)


class DocumentationSection(BaseModel):
    """Represents a section in the generated documentation."""

    title: str = Field(description="Section title")
    content: str = Field(description="Section content in markdown")
    level: int = Field(default=1, description="Heading level (1-6)")
    anchor: str = Field(description="URL anchor for cross-referencing")
    subsections: List['DocumentationSection'] = Field(default_factory=list, description="Nested subsections")


class ProjectSummary(BaseModel):
    """High-level project summary metrics."""

    total_pages_analyzed: int = Field(description="Total number of pages analyzed")
    successful_analyses: int = Field(description="Number of successful analyses")
    average_quality_score: float = Field(description="Average analysis quality score")
    total_features_identified: int = Field(description="Total functional capabilities found")
    total_api_endpoints: int = Field(description="Total API endpoints discovered")
    total_interactive_elements: int = Field(description="Total interactive elements found")
    complexity_assessment: str = Field(description="Overall complexity assessment")
    estimated_rebuild_effort: str = Field(description="Estimated rebuild effort")
    business_importance_average: float = Field(description="Average business importance score")


class DocumentationAssembler:
    """Assembles comprehensive documentation from analysis artifacts."""

    def __init__(self, artifact_manager: Optional[ArtifactManager] = None):
        """Initialize documentation assembler.

        Args:
            artifact_manager: Optional artifact manager for data access
        """
        from ..config.settings import load_settings

        if artifact_manager is None:
            settings = load_settings()
            self.artifact_manager = ArtifactManager(settings=settings)
        else:
            self.artifact_manager = artifact_manager
        self.project_summary: Optional[ProjectSummary] = None
        self.sections: List[DocumentationSection] = []

    def generate_project_documentation(
        self,
        project_id: str,
        output_path: Optional[str] = None,
        include_technical_specs: bool = True,
        include_debug_info: bool = False
    ) -> str:
        """Generate comprehensive project documentation from analysis artifacts.

        Args:
            project_id: Project identifier to generate documentation for
            output_path: Optional path to save documentation file
            include_technical_specs: Whether to include technical specifications
            include_debug_info: Whether to include debugging information

        Returns:
            Generated markdown documentation as string
        """
        _logger.info(
            "generating_project_documentation",
            project_id=project_id,
            include_technical_specs=include_technical_specs,
            include_debug_info=include_debug_info
        )

        try:
            # Load analysis artifacts for the project
            artifacts = self._load_project_artifacts(project_id)

            if not artifacts:
                raise ValueError(f"No analysis artifacts found for project {project_id}")

            # Generate project summary
            self.project_summary = self._generate_project_summary(artifacts)

            # Build documentation sections
            self.sections = []

            # 1. Executive Summary
            self.sections.append(self._generate_executive_summary(artifacts))

            # 2. Project Overview
            self.sections.append(self._generate_project_overview(artifacts))

            # 3. Per-Page Analysis
            self.sections.append(self._generate_per_page_analysis(artifacts))

            # 4. API Integration Summary
            self.sections.append(self._generate_api_integration_summary(artifacts))

            # 5. Business Logic Documentation
            self.sections.append(self._generate_business_logic_documentation(artifacts))

            # 6. Technical Specifications (if requested)
            if include_technical_specs:
                self.sections.append(self._generate_technical_specifications(artifacts))

            # 7. Debug Information (if requested)
            if include_debug_info:
                self.sections.append(self._generate_debug_information(artifacts))

            # Assemble final document
            markdown_content = self._assemble_markdown_document(project_id)

            # Save to file if path provided
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(markdown_content, encoding='utf-8')
                _logger.info("documentation_saved", output_path=output_path)

            _logger.info(
                "project_documentation_generated",
                project_id=project_id,
                sections_count=len(self.sections),
                content_length=len(markdown_content)
            )

            return markdown_content

        except Exception as e:
            _logger.error(
                "documentation_generation_failed",
                project_id=project_id,
                error=str(e)
            )
            raise

    def _load_project_artifacts(self, project_id: str) -> List[AnalysisArtifact]:
        """Load all analysis artifacts for a project."""
        # Get all completed artifacts for the project
        artifacts = self.artifact_manager.list_artifacts(
            status="completed",
            project_id=project_id
        )

        # Filter for analysis artifacts (not debug artifacts)
        analysis_artifacts = [
            artifact for artifact in artifacts
            if not artifact.analysis_type.startswith("debug_")
        ]

        _logger.info(
            "loaded_project_artifacts",
            project_id=project_id,
            total_artifacts=len(artifacts),
            analysis_artifacts=len(analysis_artifacts)
        )

        return analysis_artifacts

    def _generate_project_summary(self, artifacts: List[AnalysisArtifact]) -> ProjectSummary:
        """Generate high-level project summary from artifacts."""
        total_pages = len(artifacts)
        successful_analyses = len([a for a in artifacts if a.status == "completed"])

        # Calculate average quality scores
        quality_scores = []
        business_importance_scores = []
        total_features = 0
        total_apis = 0
        total_interactive_elements = 0

        for artifact in artifacts:
            if artifact.quality_metrics:
                quality_scores.append(artifact.quality_metrics.get("overall_quality_score", 0.0))

            if artifact.step1_result:
                business_importance_scores.append(
                    artifact.step1_result.get("business_importance", 0.5)
                )

            if artifact.step2_result:
                total_features += len(artifact.step2_result.get("functional_capabilities", []))
                total_apis += len(artifact.step2_result.get("api_integrations", []))
                total_interactive_elements += len(artifact.step2_result.get("interactive_elements", []))

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        avg_business_importance = (
            sum(business_importance_scores) / len(business_importance_scores)
            if business_importance_scores else 0.5
        )

        # Assess complexity
        if avg_quality > 0.8 and total_features > 50:
            complexity = "High"
            effort = "6-12 months"
        elif avg_quality > 0.6 and total_features > 20:
            complexity = "Medium"
            effort = "3-6 months"
        else:
            complexity = "Low"
            effort = "1-3 months"

        return ProjectSummary(
            total_pages_analyzed=total_pages,
            successful_analyses=successful_analyses,
            average_quality_score=avg_quality,
            total_features_identified=total_features,
            total_api_endpoints=total_apis,
            total_interactive_elements=total_interactive_elements,
            complexity_assessment=complexity,
            estimated_rebuild_effort=effort,
            business_importance_average=avg_business_importance
        )

    def _generate_executive_summary(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate executive summary section."""
        summary = self.project_summary

        content = f"""## Executive Summary

### Project Analysis Overview

This document presents a comprehensive analysis of the legacy web application, covering {summary.total_pages_analyzed} pages with {summary.successful_analyses} successful analyses. The analysis provides detailed insights into the application's structure, functionality, and technical requirements for modernization planning.

### Key Findings

- **Quality Assessment**: Average analysis quality score of {summary.average_quality_score:.1%}
- **Functional Complexity**: {summary.total_features_identified} functional capabilities identified
- **API Integration**: {summary.total_api_endpoints} API endpoints discovered
- **User Interface**: {summary.total_interactive_elements} interactive elements catalogued
- **Business Importance**: Average business importance rating of {summary.business_importance_average:.1%}

### Complexity Assessment

**Overall Complexity**: {summary.complexity_assessment}

The application demonstrates {summary.complexity_assessment.lower()} complexity based on the number of features, integration points, and technical depth of analysis. This assessment considers both the breadth of functionality and the sophistication of implementation patterns discovered.

### Rebuild Recommendations

**Estimated Effort**: {summary.estimated_rebuild_effort}

Based on the analysis findings, the recommended approach for modernization includes:

1. **Incremental Migration**: Priority-based feature migration starting with core business functionality
2. **API-First Design**: Leverage discovered API patterns for microservices architecture
3. **User Experience Modernization**: Rebuild interactive elements with modern frameworks
4. **Data Architecture Review**: Assess data flows and integration patterns for optimization

### Next Steps

1. **Detailed Planning**: Use per-page analysis sections for detailed sprint planning
2. **Architecture Design**: Reference technical specifications for system design
3. **API Strategy**: Review API integration summary for service decomposition
4. **Risk Assessment**: Consider business logic dependencies for migration sequencing
"""

        return DocumentationSection(
            title="Executive Summary",
            content=content,
            level=2,
            anchor="executive-summary"
        )

    def _generate_project_overview(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate project overview section."""
        # Aggregate site characteristics
        site_characteristics = defaultdict(int)
        page_types = defaultdict(int)
        workflows = set()

        for artifact in artifacts:
            if artifact.step1_result:
                # Collect workflows
                key_workflows = artifact.step1_result.get("key_workflows", [])
                workflows.update(key_workflows)

                # Categorize page types
                purpose = artifact.step1_result.get("purpose", "").lower()
                if "login" in purpose or "auth" in purpose:
                    page_types["Authentication"] += 1
                elif "dashboard" in purpose or "admin" in purpose:
                    page_types["Administration"] += 1
                elif "form" in purpose or "input" in purpose:
                    page_types["Data Entry"] += 1
                elif "list" in purpose or "search" in purpose:
                    page_types["Data Display"] += 1
                else:
                    page_types["General"] += 1

        content = f"""## Project Overview

### Application Structure

The analyzed application consists of {self.project_summary.total_pages_analyzed} pages with the following distribution:

"""

        # Add page type breakdown
        for page_type, count in sorted(page_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / self.project_summary.total_pages_analyzed) * 100
            content += f"- **{page_type}**: {count} pages ({percentage:.1f}%)\n"

        content += f"""

### Business Workflows Identified

The following key business workflows were identified across the application:

"""

        for i, workflow in enumerate(sorted(workflows), 1):
            content += f"{i}. {workflow.title().replace('_', ' ')}\n"

        content += f"""

### Technical Architecture Insights

- **Interactive Elements**: {self.project_summary.total_interactive_elements} UI components requiring implementation
- **API Endpoints**: {self.project_summary.total_api_endpoints} backend integrations identified
- **Functional Capabilities**: {self.project_summary.total_features_identified} distinct features documented

### Quality Metrics

- **Analysis Success Rate**: {(self.project_summary.successful_analyses / self.project_summary.total_pages_analyzed) * 100:.1f}%
- **Average Quality Score**: {self.project_summary.average_quality_score:.1%}
- **Business Importance**: {self.project_summary.business_importance_average:.1%} average priority rating
"""

        return DocumentationSection(
            title="Project Overview",
            content=content,
            level=2,
            anchor="project-overview"
        )

    def _generate_per_page_analysis(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate per-page analysis sections."""
        content = "## Per-Page Analysis\n\n"
        content += "This section provides detailed analysis for each page in the application, combining content summaries with feature analysis.\n\n"

        subsections = []

        for i, artifact in enumerate(artifacts, 1):
            page_section = self._generate_single_page_section(artifact, i)
            subsections.append(page_section)

        return DocumentationSection(
            title="Per-Page Analysis",
            content=content,
            level=2,
            anchor="per-page-analysis",
            subsections=subsections
        )

    def _generate_single_page_section(self, artifact: AnalysisArtifact, page_number: int) -> DocumentationSection:
        """Generate documentation section for a single page."""
        page_url = artifact.page_url
        safe_url = re.sub(r'[^\w\-_.]', '_', page_url.split('/')[-1] or 'root')
        anchor = f"page-{page_number}-{safe_url}"

        content = f"### Page {page_number}: {page_url}\n\n"

        # Content Summary
        if artifact.step1_result:
            step1 = artifact.step1_result
            content += f"""#### Content Summary

- **Purpose**: {step1.get('purpose', 'Not specified')}
- **User Context**: {step1.get('user_context', 'Not specified')}
- **Business Logic**: {step1.get('business_logic', 'Not specified')}
- **Navigation Role**: {step1.get('navigation_role', 'Not specified')}
- **Business Importance**: {step1.get('business_importance', 0.0):.1%}
- **Confidence Score**: {step1.get('confidence_score', 0.0):.1%}

"""

            # Workflows
            workflows = step1.get('key_workflows', [])
            if workflows:
                content += "**Key Workflows**:\n"
                for workflow in workflows:
                    content += f"- {workflow.replace('_', ' ').title()}\n"
                content += "\n"

        # Feature Analysis
        if artifact.step2_result:
            step2 = artifact.step2_result
            content += "#### Feature Analysis\n\n"

            # Interactive Elements
            interactive_elements = step2.get('interactive_elements', [])
            if interactive_elements:
                content += "**Interactive Elements**:\n\n"
                content += "| Type | Selector | Purpose |\n"
                content += "|------|----------|----------|\n"
                for element in interactive_elements:
                    elem_type = element.get('type', 'Unknown')
                    selector = element.get('selector', 'N/A')
                    purpose = element.get('purpose', 'Not specified')
                    content += f"| {elem_type} | `{selector}` | {purpose} |\n"
                content += "\n"

            # Functional Capabilities
            capabilities = step2.get('functional_capabilities', [])
            if capabilities:
                content += "**Functional Capabilities**:\n\n"
                for cap in capabilities:
                    name = cap.get('name', 'Unnamed')
                    description = cap.get('description', 'No description')
                    complexity = cap.get('complexity_score', 'Not rated')
                    content += f"- **{name}**: {description}"
                    if complexity != 'Not rated':
                        content += f" (Complexity: {complexity}/10)"
                    content += "\n"
                content += "\n"

            # API Integrations
            apis = step2.get('api_integrations', [])
            if apis:
                content += "**API Integrations**:\n\n"
                content += "| Method | Endpoint | Purpose |\n"
                content += "|--------|----------|----------|\n"
                for api in apis:
                    method = api.get('method', 'Unknown')
                    endpoint = api.get('endpoint', 'Not specified')
                    purpose = api.get('purpose', 'Not specified')
                    content += f"| {method} | `{endpoint}` | {purpose} |\n"
                content += "\n"

        # Quality Metrics
        if artifact.quality_metrics:
            quality = artifact.quality_metrics
            content += "#### Quality Metrics\n\n"
            content += f"- **Overall Quality**: {quality.get('overall_quality_score', 0.0):.1%}\n"
            content += f"- **Completeness**: {quality.get('completeness_score', 0.0):.1%}\n"
            content += f"- **Technical Depth**: {quality.get('technical_depth_score', 0.0):.1%}\n"

            if quality.get('needs_manual_review'):
                content += f"\n⚠️ **Manual Review Required**: {', '.join(quality.get('review_reasons', []))}\n"

            content += "\n"

        return DocumentationSection(
            title=f"Page {page_number}: {page_url}",
            content=content,
            level=3,
            anchor=anchor
        )

    def _generate_api_integration_summary(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate API integration summary section."""
        # Collect all API integrations
        all_apis = []
        for artifact in artifacts:
            if artifact.step2_result:
                apis = artifact.step2_result.get('api_integrations', [])
                for api in apis:
                    api_data = {
                        'page_url': artifact.page_url,
                        **api
                    }
                    all_apis.append(api_data)

        content = f"""## API Integration Summary

This section documents all API endpoints discovered during the analysis, providing a comprehensive view of backend integrations and data flows.

### Overview

- **Total API Endpoints**: {len(all_apis)}
- **Unique Endpoints**: {len(set(api.get('endpoint', '') for api in all_apis))}

"""

        if all_apis:
            # Group by method
            methods = defaultdict(list)
            for api in all_apis:
                method = api.get('method', 'Unknown')
                methods[method].append(api)

            content += "### Endpoints by Method\n\n"

            for method in sorted(methods.keys()):
                apis_for_method = methods[method]
                content += f"#### {method} Endpoints ({len(apis_for_method)})\n\n"
                content += "| Endpoint | Purpose | Page | Auth Type |\n"
                content += "|----------|---------|------|----------|\n"

                for api in apis_for_method:
                    endpoint = api.get('endpoint', 'Not specified')
                    purpose = api.get('purpose', 'Not specified')
                    page_url = api.get('page_url', 'Unknown')
                    auth_type = api.get('auth_type', 'Not specified')
                    content += f"| `{endpoint}` | {purpose} | {page_url} | {auth_type} |\n"

                content += "\n"

            # Data Flow Analysis
            content += "### Data Flow Patterns\n\n"

            data_flows = set()
            for api in all_apis:
                flow = api.get('data_flow', '')
                if flow:
                    data_flows.add(flow)

            if data_flows:
                content += "The following data flow patterns were identified:\n\n"
                for i, flow in enumerate(sorted(data_flows), 1):
                    content += f"{i}. {flow}\n"
            else:
                content += "No specific data flow patterns were documented in the analysis.\n"

            content += "\n"

        else:
            content += "No API integrations were discovered during the analysis.\n\n"

        return DocumentationSection(
            title="API Integration Summary",
            content=content,
            level=2,
            anchor="api-integration-summary"
        )

    def _generate_business_logic_documentation(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate business logic and workflows documentation."""
        # Collect business rules and workflows
        all_workflows = set()
        all_business_rules = []
        user_journeys = defaultdict(list)

        for artifact in artifacts:
            if artifact.step1_result:
                workflows = artifact.step1_result.get('key_workflows', [])
                all_workflows.update(workflows)

                journey_stage = artifact.step1_result.get('user_journey_stage', 'unknown')
                purpose = artifact.step1_result.get('purpose', 'Unknown purpose')
                user_journeys[journey_stage].append({
                    'url': artifact.page_url,
                    'purpose': purpose
                })

            if artifact.step2_result:
                business_rules = artifact.step2_result.get('business_rules', [])
                for rule in business_rules:
                    rule_data = {
                        'page_url': artifact.page_url,
                        **rule
                    }
                    all_business_rules.append(rule_data)

        content = f"""## Business Logic Documentation

This section captures the business workflows, user journeys, and functional requirements identified during the analysis.

### Business Workflows

{len(all_workflows)} distinct business workflows were identified across the application:

"""

        for i, workflow in enumerate(sorted(all_workflows), 1):
            content += f"{i}. **{workflow.replace('_', ' ').title()}**\n"

        content += "\n### User Journey Mapping\n\n"

        journey_order = ['entry', 'middle', 'conversion', 'exit', 'support', 'administration', 'unknown']
        for stage in journey_order:
            if stage in user_journeys:
                pages = user_journeys[stage]
                content += f"#### {stage.title()} Stage ({len(pages)} pages)\n\n"
                for page in pages:
                    content += f"- **{page['url']}**: {page['purpose']}\n"
                content += "\n"

        if all_business_rules:
            content += f"### Business Rules ({len(all_business_rules)})\n\n"
            content += "| Rule | Description | Validation Logic | Page |\n"
            content += "|------|-------------|------------------|------|\n"

            for rule in all_business_rules:
                name = rule.get('name', 'Unnamed Rule')
                description = rule.get('description', 'No description')
                validation = rule.get('validation_logic', 'Not specified')
                page_url = rule.get('page_url', 'Unknown')
                content += f"| {name} | {description} | {validation} | {page_url} |\n"

            content += "\n"
        else:
            content += "### Business Rules\n\nNo specific business rules were documented during the analysis.\n\n"

        return DocumentationSection(
            title="Business Logic Documentation",
            content=content,
            level=2,
            anchor="business-logic-documentation"
        )

    def _generate_technical_specifications(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate technical specifications section."""
        # Collect rebuild specifications
        all_rebuild_specs = []
        for artifact in artifacts:
            if artifact.step2_result:
                specs = artifact.step2_result.get('rebuild_specifications', [])
                for spec in specs:
                    spec_data = {
                        'page_url': artifact.page_url,
                        **spec
                    }
                    all_rebuild_specs.append(spec_data)

        content = f"""## Technical Specifications

This section provides technical specifications and rebuild recommendations suitable for architects and developers.

### Architecture Recommendations

Based on the analysis of {self.project_summary.total_pages_analyzed} pages, the following architectural patterns are recommended:

#### Frontend Architecture
- **Framework**: Modern JavaScript framework (React, Vue, or Angular)
- **Component Library**: Design system based on identified UI patterns
- **State Management**: Centralized state management for complex user workflows
- **Routing**: Client-side routing with authentication guards

#### Backend Architecture
- **API Design**: RESTful or GraphQL API based on discovered endpoint patterns
- **Microservices**: Service decomposition based on business workflow boundaries
- **Authentication**: Modern authentication system (OAuth2, JWT)
- **Data Layer**: Database design optimized for identified data flows

### Rebuild Specifications

"""

        if all_rebuild_specs:
            # Group by priority
            high_priority = [s for s in all_rebuild_specs if s.get('priority_score', 0) > 0.7]
            medium_priority = [s for s in all_rebuild_specs if 0.4 <= s.get('priority_score', 0) <= 0.7]
            low_priority = [s for s in all_rebuild_specs if s.get('priority_score', 0) < 0.4]

            for specs, title in [
                (high_priority, "High Priority"),
                (medium_priority, "Medium Priority"),
                (low_priority, "Low Priority")
            ]:
                if specs:
                    content += f"#### {title} ({len(specs)} items)\n\n"
                    content += "| Component | Description | Complexity | Dependencies |\n"
                    content += "|-----------|-------------|------------|-------------|\n"

                    for spec in specs:
                        name = spec.get('name', 'Unnamed Component')
                        description = spec.get('description', 'No description')
                        complexity = spec.get('complexity', 'Unknown')
                        dependencies = ', '.join(spec.get('dependencies', []))
                        content += f"| {name} | {description} | {complexity} | {dependencies} |\n"

                    content += "\n"

        else:
            content += "No specific rebuild specifications were generated during the analysis.\n\n"

        # Technology Stack Recommendations
        content += """### Recommended Technology Stack

#### Frontend
- **Framework**: React 18+ with TypeScript
- **Styling**: Tailwind CSS or Styled Components
- **Build Tool**: Vite or Next.js
- **Testing**: Jest + React Testing Library

#### Backend
- **Runtime**: Node.js with Express or FastAPI (Python)
- **Database**: PostgreSQL for relational data, Redis for caching
- **Authentication**: Auth0 or custom JWT implementation
- **API Documentation**: OpenAPI/Swagger

#### Infrastructure
- **Deployment**: Docker containers with Kubernetes
- **CI/CD**: GitHub Actions or GitLab CI
- **Monitoring**: Application and infrastructure monitoring
- **Security**: Security headers, input validation, rate limiting

"""

        return DocumentationSection(
            title="Technical Specifications",
            content=content,
            level=2,
            anchor="technical-specifications"
        )

    def _generate_debug_information(self, artifacts: List[AnalysisArtifact]) -> DocumentationSection:
        """Generate debug information section."""
        content = f"""## Debug Information

This section provides debugging and quality assurance information for the analysis process.

### Analysis Quality Overview

"""

        quality_distribution = {"High (>80%)": 0, "Medium (60-80%)": 0, "Low (<60%)": 0}
        total_retries = 0
        total_errors = 0

        for artifact in artifacts:
            if artifact.quality_metrics:
                quality_score = artifact.quality_metrics.get('overall_quality_score', 0.0)
                if quality_score > 0.8:
                    quality_distribution["High (>80%)"] += 1
                elif quality_score >= 0.6:
                    quality_distribution["Medium (60-80%)"] += 1
                else:
                    quality_distribution["Low (<60%)"] += 1

            total_retries += len(artifact.retry_history)
            total_errors += len(artifact.errors)

        content += "**Quality Score Distribution**:\n"
        for quality_level, count in quality_distribution.items():
            percentage = (count / len(artifacts)) * 100 if artifacts else 0
            content += f"- {quality_level}: {count} pages ({percentage:.1f}%)\n"

        content += f"""

### Analysis Statistics

- **Total Retries**: {total_retries}
- **Total Errors**: {total_errors}
- **Error Rate**: {(total_errors / len(artifacts) * 100):.1f}% per page

### Quality Issues Summary

"""

        # Collect quality issues
        all_issues = defaultdict(int)
        for artifact in artifacts:
            if artifact.quality_metrics:
                issues = artifact.quality_metrics.get('quality_issues', [])
                for issue in issues:
                    all_issues[issue] += 1

        if all_issues:
            content += "| Issue | Frequency |\n"
            content += "|-------|----------|\n"
            for issue, count in sorted(all_issues.items(), key=lambda x: x[1], reverse=True):
                content += f"| {issue} | {count} |\n"
        else:
            content += "No significant quality issues were identified during analysis.\n"

        content += "\n"

        return DocumentationSection(
            title="Debug Information",
            content=content,
            level=2,
            anchor="debug-information"
        )

    def _assemble_markdown_document(self, project_id: str) -> str:
        """Assemble final markdown document with TOC and cross-references."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Document header
        header = f"""# Legacy Web Application Analysis Report

**Project ID**: {project_id}
**Generated**: {timestamp}
**Analysis Tool**: Legacy Web MCP Server

---

"""

        # Table of Contents
        toc = "## Table of Contents\n\n"
        toc += self._generate_table_of_contents(self.sections)
        toc += "\n---\n\n"

        # Assemble sections
        content_sections = []
        for section in self.sections:
            content_sections.append(self._render_section(section))

        # Footer
        footer = f"""

---

## Document Information

- **Report Generated**: {timestamp}
- **Analysis Quality**: {self.project_summary.average_quality_score:.1%} average
- **Pages Analyzed**: {self.project_summary.total_pages_analyzed}
- **Features Identified**: {self.project_summary.total_features_identified}

*This report was generated by the Legacy Web MCP Server analysis system.*
"""

        return header + toc + "\n".join(content_sections) + footer

    def _generate_table_of_contents(self, sections: List[DocumentationSection], level: int = 0) -> str:
        """Generate table of contents with links."""
        toc = ""
        indent = "  " * level

        for section in sections:
            toc += f"{indent}- [{section.title}](#{section.anchor})\n"
            if section.subsections:
                toc += self._generate_table_of_contents(section.subsections, level + 1)

        return toc

    def _render_section(self, section: DocumentationSection) -> str:
        """Render a documentation section to markdown."""
        content = section.content

        # Add subsections
        for subsection in section.subsections:
            content += self._render_section(subsection)

        return content

    def generate_anchor(self, title: str) -> str:
        """Generate URL-safe anchor from title."""
        # Convert to lowercase and replace spaces/special chars with hyphens
        anchor = re.sub(r'[^\w\s-]', '', title.lower())
        anchor = re.sub(r'[-\s]+', '-', anchor)
        return anchor.strip('-')