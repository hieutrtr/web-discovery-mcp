"""MCP tools for documentation generation functionality.

This module provides MCP tools to expose the documentation assembler functionality,
allowing users to generate comprehensive analysis documentation from analysis artifacts.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastmcp import FastMCP, Context

from ..documentation.assembler import DocumentationAssembler
from ..config.loader import load_configuration
from ..llm.artifacts import ArtifactManager


async def generate_project_documentation(
    context: Context,
    project_name: str,
    output_path: Optional[str] = None,
    include_technical_specs: bool = True,
    include_api_docs: bool = True,
    include_business_logic: bool = True,
    quality_threshold: float = 0.7
) -> Dict[str, Any]:
    """Generate comprehensive project documentation from analysis artifacts.

    Args:
        project_name: Name of the project for documentation
        output_path: Optional file path to save the documentation
        include_technical_specs: Whether to include technical specifications
        include_api_docs: Whether to include API integration documentation
        include_business_logic: Whether to include business logic documentation
        quality_threshold: Minimum quality score for artifacts to include

    Returns:
        Dict containing documentation content and metadata
    """
    try:
        await context.info(f"Generating documentation for project: {project_name}")

        # Initialize components
        config = load_configuration()
        from ..config.settings import load_settings
        settings = load_settings()
        artifact_manager = ArtifactManager(settings=settings)
        assembler = DocumentationAssembler(artifact_manager)

        # Use the DocumentationAssembler to generate real documentation
        try:
            documentation_content = assembler.generate_project_documentation(
                project_id=project_name,
                output_path=output_path,
                include_technical_specs=include_technical_specs,
                include_debug_info=False
            )

            # Extract metadata from assembler
            project_summary = assembler.project_summary
            if project_summary:
                metadata = {
                    "total_pages": project_summary.total_pages_analyzed,
                    "successful_analyses": project_summary.successful_analyses,
                    "average_quality": project_summary.average_quality_score,
                    "features_identified": project_summary.total_features_identified,
                    "api_endpoints": project_summary.total_api_endpoints,
                    "complexity": project_summary.complexity_assessment,
                    "estimated_effort": project_summary.estimated_rebuild_effort
                }
            else:
                metadata = {
                    "total_pages": 0,
                    "successful_analyses": 0,
                    "average_quality": 0.0,
                    "features_identified": 0
                }

            return {
                "status": "success",
                "project_name": project_name,
                "documentation_content": documentation_content,
                "word_count": len(documentation_content.split()),
                "sections_generated": len(assembler.sections) if assembler.sections else 0,
                "output_path": output_path,
                "metadata": metadata
            }

        except ValueError as ve:
            # Handle case where no artifacts found - provide helpful message
            await context.info(f"No artifacts found for project '{project_name}'. Checking available artifacts...")

            # List all available artifacts to help user understand
            all_artifacts = artifact_manager.list_artifacts()
            if not all_artifacts:
                error_msg = "No analysis artifacts found in the system. Please run some web analysis first using the analysis tools."
            else:
                project_ids = set(a.project_id for a in all_artifacts if a.project_id)
                if not project_ids:
                    error_msg = f"Found {len(all_artifacts)} artifacts but none have project_id set. Available artifacts are not associated with any project."
                else:
                    error_msg = f"No artifacts found for project '{project_name}'. Available project IDs: {', '.join(sorted(project_ids))}"

            return {
                "status": "error",
                "error": error_msg,
                "project_name": project_name,
                "available_artifacts": len(all_artifacts),
                "available_projects": list(set(a.project_id for a in all_artifacts if a.project_id))
            }

    except Exception as e:
        await context.error(f"Documentation generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_name": project_name
        }


async def generate_executive_summary(
    context: Context,
    project_name: str,
    quality_threshold: float = 0.7
) -> Dict[str, Any]:
    """Generate executive summary from analysis artifacts.

    Args:
        project_name: Name of the project for documentation
        quality_threshold: Minimum quality score for artifacts to include

    Returns:
        Dict containing executive summary content and metrics
    """
    try:
        await context.info(f"Generating executive summary for: {project_name}")

        # Initialize components
        config = load_configuration()
        from ..config.settings import load_settings
        settings = load_settings()
        artifact_manager = ArtifactManager(settings=settings)
        assembler = DocumentationAssembler(artifact_manager)

        try:
            # Load project artifacts and generate summary
            artifacts = assembler._load_project_artifacts(project_name)
            if not artifacts:
                # Check for available artifacts/projects
                all_artifacts = artifact_manager.list_artifacts()
                if not all_artifacts:
                    return {
                        "status": "error",
                        "error": "No analysis artifacts found. Please run web analysis first.",
                        "project_name": project_name
                    }
                else:
                    available_projects = list(set(a.project_id for a in all_artifacts if a.project_id))
                    return {
                        "status": "error",
                        "error": f"No artifacts found for project '{project_name}'. Available projects: {available_projects}",
                        "project_name": project_name,
                        "available_projects": available_projects
                    }

            # Generate project summary using real data
            project_summary = assembler._generate_project_summary(artifacts)
            # Set the project summary on the assembler so _generate_executive_summary can access it
            assembler.project_summary = project_summary
            executive_section = assembler._generate_executive_summary(artifacts)

            return {
                "status": "success",
                "project_name": project_name,
                "executive_summary": executive_section.content,
                "project_metrics": {
                    "total_pages": project_summary.total_pages_analyzed,
                    "successful_analyses": project_summary.successful_analyses,
                    "average_quality": project_summary.average_quality_score,
                    "features_identified": project_summary.total_features_identified,
                    "api_endpoints": project_summary.total_api_endpoints,
                    "complexity": project_summary.complexity_assessment,
                    "estimated_effort": project_summary.estimated_rebuild_effort,
                    "business_importance": project_summary.business_importance_average
                }
            }

        except Exception as inner_e:
            await context.error(f"Failed to process artifacts: {inner_e}")
            return {
                "status": "error",
                "error": f"Failed to process artifacts: {str(inner_e)}",
                "project_name": project_name
            }

    except Exception as e:
        await context.error(f"Executive summary generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_name": project_name
        }


async def list_available_artifacts(
    context: Context,
    quality_threshold: Optional[float] = None,
    artifact_type: Optional[str] = None
) -> Dict[str, Any]:
    """List available analysis artifacts for documentation generation.

    Args:
        quality_threshold: Optional minimum quality score filter
        artifact_type: Optional artifact type filter (e.g., 'content_summary', 'feature_analysis')

    Returns:
        Dict containing list of available artifacts with metadata
    """
    try:
        await context.info("Listing available analysis artifacts")

        # Initialize artifact manager
        config = load_configuration()
        from ..config.settings import load_settings
        settings = load_settings()
        artifact_manager = ArtifactManager(settings=settings)

        # Get all artifacts
        artifacts = artifact_manager.list_artifacts()

        # Apply filters
        filtered_artifacts = []
        for artifact in artifacts:
            # Quality threshold filter
            if quality_threshold and artifact.metadata.get('quality_score', 0) < quality_threshold:
                continue

            # Artifact type filter
            if artifact_type and artifact.artifact_type != artifact_type:
                continue

            filtered_artifacts.append(artifact)

        # Prepare artifact summaries
        artifact_summaries = []
        for artifact in filtered_artifacts:
            artifact_summaries.append({
                "artifact_id": artifact.artifact_id,
                "url": artifact.url,
                "artifact_type": artifact.artifact_type,
                "timestamp": artifact.timestamp.isoformat(),
                "quality_score": artifact.metadata.get('quality_score'),
                "page_title": artifact.metadata.get('page_title'),
                "analysis_status": artifact.metadata.get('analysis_status')
            })

        return {
            "status": "success",
            "total_artifacts": len(artifacts),
            "filtered_artifacts": len(filtered_artifacts),
            "artifacts": artifact_summaries,
            "filters_applied": {
                "quality_threshold": quality_threshold,
                "artifact_type": artifact_type
            }
        }

    except Exception as e:
        await context.error(f"Artifact listing failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def generate_api_documentation(
    context: Context,
    project_name: str,
    quality_threshold: float = 0.7
) -> Dict[str, Any]:
    """Generate API integration documentation from analysis artifacts.

    Args:
        project_name: Name of the project for documentation
        quality_threshold: Minimum quality score for artifacts to include

    Returns:
        Dict containing API documentation content
    """
    try:
        await context.info(f"Generating API documentation for: {project_name}")

        # Initialize components
        config = load_configuration()
        from ..config.settings import load_settings
        settings = load_settings()
        artifact_manager = ArtifactManager(settings=settings)
        assembler = DocumentationAssembler(artifact_manager)

        try:
            # Load project artifacts
            artifacts = assembler._load_project_artifacts(project_name)
            if not artifacts:
                all_artifacts = artifact_manager.list_artifacts()
                available_projects = list(set(a.project_id for a in all_artifacts if a.project_id))
                return {
                    "status": "error",
                    "error": f"No artifacts found for project '{project_name}'. Available projects: {available_projects}",
                    "project_name": project_name,
                    "available_projects": available_projects
                }

            # Filter by quality threshold
            filtered_artifacts = [
                a for a in artifacts
                if a.quality_metrics and a.quality_metrics.get('overall_quality_score', 0) >= quality_threshold
            ]

            # Generate API integration summary using real data
            api_section = assembler._generate_api_integration_summary(filtered_artifacts)

            return {
                "status": "success",
                "project_name": project_name,
                "api_documentation": api_section.content,
                "artifacts_analyzed": len(filtered_artifacts),
                "total_artifacts": len(artifacts),
                "quality_threshold": quality_threshold
            }

        except Exception as inner_e:
            await context.error(f"Failed to process artifacts: {inner_e}")
            return {
                "status": "error",
                "error": f"Failed to process artifacts: {str(inner_e)}",
                "project_name": project_name
            }

    except Exception as e:
        await context.error(f"API documentation generation failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "project_name": project_name
        }


async def validate_documentation_artifacts(
    context: Context,
    quality_threshold: float = 0.7
) -> Dict[str, Any]:
    """Validate analysis artifacts for documentation generation readiness.

    Args:
        quality_threshold: Minimum quality score for valid artifacts

    Returns:
        Dict containing validation results and recommendations
    """
    try:
        await context.info("Validating artifacts for documentation generation")

        # Initialize artifact manager
        config = load_configuration()
        from ..config.settings import load_settings
        settings = load_settings()
        artifact_manager = ArtifactManager(settings=settings)

        # Get all artifacts
        artifacts = artifact_manager.list_artifacts()

        # Analyze artifact quality and completeness
        validation_results = {
            "total_artifacts": len(artifacts),
            "high_quality_artifacts": 0,
            "medium_quality_artifacts": 0,
            "low_quality_artifacts": 0,
            "missing_content_summaries": 0,
            "missing_feature_analyses": 0,
            "incomplete_artifacts": 0,
            "recommendations": []
        }

        content_summaries = 0
        feature_analyses = 0

        for artifact in artifacts:
            quality_score = artifact.metadata.get('quality_score', 0)

            # Quality categorization
            if quality_score >= quality_threshold:
                validation_results["high_quality_artifacts"] += 1
            elif quality_score >= 0.5:
                validation_results["medium_quality_artifacts"] += 1
            else:
                validation_results["low_quality_artifacts"] += 1

            # Artifact type tracking
            if artifact.analysis_type == "step1":
                content_summaries += 1
            elif artifact.analysis_type == "step2":
                feature_analyses += 1

            # Completeness check
            if not (artifact.step1_result or artifact.step2_result):
                validation_results["incomplete_artifacts"] += 1

        # Generate recommendations
        if validation_results["low_quality_artifacts"] > 0:
            validation_results["recommendations"].append(
                f"Consider regenerating {validation_results['low_quality_artifacts']} low-quality artifacts"
            )

        if content_summaries == 0:
            validation_results["recommendations"].append(
                "No content summary artifacts found - run Step 1 analysis first"
            )

        if feature_analyses == 0:
            validation_results["recommendations"].append(
                "No feature analysis artifacts found - run Step 2 analysis first"
            )

        if content_summaries > feature_analyses:
            validation_results["recommendations"].append(
                f"Missing feature analyses for {content_summaries - feature_analyses} pages"
            )

        validation_results["content_summaries"] = content_summaries
        validation_results["feature_analyses"] = feature_analyses
        validation_results["documentation_ready"] = (
            validation_results["high_quality_artifacts"] > 0 and
            content_summaries > 0 and
            feature_analyses > 0
        )

        return {
            "status": "success",
            "validation_results": validation_results
        }

    except Exception as e:
        await context.error(f"Artifact validation failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


def register(mcp: FastMCP) -> None:
    """Register documentation tools with the MCP server."""
    mcp.tool(generate_project_documentation)
    mcp.tool(generate_executive_summary)
    mcp.tool(list_available_artifacts)
    mcp.tool(generate_api_documentation)
    mcp.tool(validate_documentation_artifacts)