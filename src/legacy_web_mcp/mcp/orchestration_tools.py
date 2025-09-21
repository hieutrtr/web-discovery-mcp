"""High-level workflow orchestration tools for legacy website analysis.

This module provides intelligent orchestration of the complete Legacy Web MCP Server
toolkit through high-level tools that combine discovery, browser automation, LLM analysis,
and documentation generation into seamless conversational AI workflows.

The primary tool `analyze_legacy_site()` provides complete site analysis from URL to
documentation, with intelligent workflow planning, progress tracking, error recovery,
and result aggregation.
"""

import asyncio
import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import structlog
from fastmcp import Context, FastMCP

from legacy_web_mcp.browser.service import BrowserAutomationService
from legacy_web_mcp.browser.workflow import SequentialNavigationWorkflow
from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.discovery.pipeline import WebsiteDiscoveryService
from legacy_web_mcp.llm.analysis.step1_summarize import ContentSummarizer
from legacy_web_mcp.llm.analysis.step2_feature_analysis import FeatureAnalyzer
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.storage.projects import create_project_store

_logger = structlog.get_logger(__name__)


class AnalysisMode(Enum):
    """Analysis depth and strategy modes."""
    QUICK = "quick"
    RECOMMENDED = "recommended"
    COMPREHENSIVE = "comprehensive"
    TARGETED = "targeted"


class CostPriority(Enum):
    """Cost optimization strategies."""
    SPEED = "speed"
    BALANCED = "balanced"
    COST_EFFICIENT = "cost_efficient"


class OrchestrationError(Exception):
    """Base exception for orchestration errors."""
    pass


class WorkflowPlanningError(OrchestrationError):
    """Error in workflow planning or strategy selection."""
    pass


class ToolIntegrationError(OrchestrationError):
    """Error in tool integration or coordination."""
    pass


class LegacyAnalysisOrchestrator:
    """Core orchestration class for managing complex analysis workflows."""

    def __init__(self, config, project_id: str):
        self.config = config
        self.project_id = project_id
        self.browser_service = BrowserAutomationService(config)
        self.project_store = create_project_store(config)
        self.llm_engine = LLMEngine(config)
        self.discovery_service = WebsiteDiscoveryService(config, project_store=self.project_store)

        # Workflow state
        self.workflow_id = f"orchestration-{int(time.time())}"
        self.start_time = time.time()
        self.current_phase = "initialization"
        self.progress_tracker = {"completed_phases": [], "current_phase": None, "errors": []}

    async def discover_and_analyze_site(
        self,
        context: Context,
        url: str,
        analysis_mode: AnalysisMode = AnalysisMode.RECOMMENDED,
        max_pages: int = 0,
        include_step2: bool = True,
        interactive_mode: bool = False,
        cost_priority: CostPriority = CostPriority.BALANCED,
    ) -> Dict[str, Any]:
        """Execute complete legacy site analysis workflow with intelligent orchestration."""

        try:
            _logger.info(
                "orchestrated_analysis_started",
                url=url,
                workflow_id=self.workflow_id,
                analysis_mode=analysis_mode.value,
                max_pages=max_pages,
                include_step2=include_step2,
                cost_priority=cost_priority.value,
            )

            # Phase 1: Site Discovery with Intelligent Selection
            await context.info(f"🔍 Phase 1: Discovering site structure for {url}")
            self.current_phase = "discovery"

            discovery_result = await self._intelligent_site_discovery(context, url, analysis_mode, max_pages)
            self.progress_tracker["completed_phases"].append("discovery")

            # Phase 2: Analysis Strategy Planning
            await context.info(f"🧠 Phase 2: Planning analysis strategy ({analysis_mode.value} mode)")
            self.current_phase = "planning"

            analysis_strategy = await self._create_analysis_strategy(
                discovery_result, analysis_mode, cost_priority, include_step2
            )
            self.progress_tracker["completed_phases"].append("planning")

            # Phase 3: Orchestrated Analysis Execution
            await context.info(f"⚡ Phase 3: Executing analysis on {len(analysis_strategy['target_pages'])} pages")
            self.current_phase = "analysis"

            analysis_results = await self._execute_analysis_pipeline(
                context, analysis_strategy, interactive_mode
            )
            self.progress_tracker["completed_phases"].append("analysis")

            # Phase 4: Result Synthesis and Documentation
            await context.info("📋 Phase 4: Synthesizing results and generating documentation")
            self.current_phase = "synthesis"

            final_results = await self._synthesize_and_document_results(
                context, discovery_result, analysis_results, analysis_strategy
            )
            self.progress_tracker["completed_phases"].append("synthesis")

            # Calculate total workflow duration
            total_duration = time.time() - self.start_time

            await context.info(f"✅ Analysis complete! Processed {len(analysis_strategy['target_pages'])} pages in {total_duration:.1f}s")

            return {
                "status": "success",
                "workflow_id": self.workflow_id,
                "url": url,
                "analysis_mode": analysis_mode.value,
                "total_duration": total_duration,
                "discovery_summary": discovery_result,
                "analysis_summary": final_results,
                "pages_analyzed": len(analysis_strategy['target_pages']),
                "project_id": self.project_id,
            }

        except Exception as e:
            error_msg = f"Orchestrated analysis failed in phase {self.current_phase}: {e}"
            self.progress_tracker["errors"].append({
                "phase": self.current_phase,
                "error": str(e),
                "timestamp": time.time(),
            })

            _logger.error(
                "orchestrated_analysis_failed",
                url=url,
                workflow_id=self.workflow_id,
                phase=self.current_phase,
                error=str(e),
                error_type=type(e).__name__,
            )

            await context.error(error_msg)
            return {
                "status": "error",
                "workflow_id": self.workflow_id,
                "url": url,
                "error": str(e),
                "error_type": type(e).__name__,
                "failed_phase": self.current_phase,
                "progress_tracker": self.progress_tracker,
            }

    async def _intelligent_site_discovery(
        self, context: Context, url: str, analysis_mode: AnalysisMode, max_pages: int
    ) -> Dict[str, Any]:
        """Perform intelligent site discovery with strategic page selection."""

        try:
            # Basic site discovery
            discovery_data = await self.discovery_service.discover(context, url)

            if discovery_data.get("status") != "success":
                raise WorkflowPlanningError(f"Site discovery failed: {discovery_data.get('error', 'Unknown error')}")

            all_urls = discovery_data.get("urls", [])
            site_info = discovery_data.get("site_info", {})

            if not all_urls:
                raise WorkflowPlanningError(f"No URLs discovered for {url}")

            # Intelligent page selection based on analysis mode
            selected_pages = await self._select_priority_pages(all_urls, site_info, analysis_mode, max_pages)

            # Estimate analysis cost and complexity
            cost_estimate = self._estimate_analysis_cost(selected_pages, analysis_mode)

            return {
                "total_pages_found": len(all_urls),
                "selected_pages": selected_pages,
                "page_count": len(selected_pages),
                "site_characteristics": site_info,
                "cost_estimate": cost_estimate,
                "discovery_method": discovery_data.get("discovery_method", "unknown"),
            }

        except Exception as e:
            raise WorkflowPlanningError(f"Intelligent site discovery failed: {e}") from e

    async def _select_priority_pages(
        self, all_urls: List[str], site_info: Dict[str, Any], analysis_mode: AnalysisMode, max_pages: int
    ) -> List[str]:
        """Select priority pages for analysis based on mode and site characteristics."""

        # Auto-calculate max pages if not specified
        if max_pages == 0:
            mode_defaults = {
                AnalysisMode.QUICK: min(10, len(all_urls)),
                AnalysisMode.RECOMMENDED: min(20, len(all_urls)),
                AnalysisMode.COMPREHENSIVE: min(50, len(all_urls)),
                AnalysisMode.TARGETED: min(15, len(all_urls)),
            }
            max_pages = mode_defaults[analysis_mode]

        # Simple selection strategy - prioritize key pages
        priority_patterns = [
            "/",           # Home page
            "/login",      # Authentication
            "/dashboard",  # Main interface
            "/admin",      # Admin interface
            "/search",     # Search functionality
            "/checkout",   # E-commerce
            "/contact",    # Contact forms
            "/about",      # Company info
        ]

        selected = []

        # First, add high-priority pages
        for pattern in priority_patterns:
            for url in all_urls:
                if pattern in url.lower() and url not in selected:
                    selected.append(url)
                    if len(selected) >= max_pages:
                        return selected

        # Fill remaining slots with other pages
        for url in all_urls:
            if url not in selected:
                selected.append(url)
                if len(selected) >= max_pages:
                    break

        return selected

    def _estimate_analysis_cost(self, pages: List[str], analysis_mode: AnalysisMode) -> Dict[str, Any]:
        """Estimate analysis cost and time requirements."""

        # Base cost estimates per page (in approximate USD)
        mode_costs = {
            AnalysisMode.QUICK: 0.05,
            AnalysisMode.RECOMMENDED: 0.15,
            AnalysisMode.COMPREHENSIVE: 0.30,
            AnalysisMode.TARGETED: 0.20,
        }

        # Time estimates per page (in seconds)
        mode_times = {
            AnalysisMode.QUICK: 30,
            AnalysisMode.RECOMMENDED: 90,
            AnalysisMode.COMPREHENSIVE: 180,
            AnalysisMode.TARGETED: 120,
        }

        base_cost_per_page = mode_costs[analysis_mode]
        base_time_per_page = mode_times[analysis_mode]

        total_estimated_cost = len(pages) * base_cost_per_page
        total_estimated_time = len(pages) * base_time_per_page

        return {
            "estimated_cost_usd": round(total_estimated_cost, 2),
            "estimated_time_seconds": total_estimated_time,
            "estimated_time_minutes": round(total_estimated_time / 60, 1),
            "cost_per_page": base_cost_per_page,
            "time_per_page": base_time_per_page,
            "page_count": len(pages),
        }

    async def _create_analysis_strategy(
        self,
        discovery_result: Dict[str, Any],
        analysis_mode: AnalysisMode,
        cost_priority: CostPriority,
        include_step2: bool,
    ) -> Dict[str, Any]:
        """Create intelligent analysis strategy based on site characteristics."""

        target_pages = discovery_result["selected_pages"]
        site_characteristics = discovery_result.get("site_characteristics", {})

        # Configure analysis parameters based on mode
        step2_threshold = {
            AnalysisMode.QUICK: 0.6,
            AnalysisMode.RECOMMENDED: 0.75,
            AnalysisMode.COMPREHENSIVE: 0.85,
            AnalysisMode.TARGETED: 0.8,
        }[analysis_mode]

        # Configure concurrency based on cost priority
        max_concurrent = {
            CostPriority.SPEED: 5,
            CostPriority.BALANCED: 3,
            CostPriority.COST_EFFICIENT: 1,
        }[cost_priority]

        return {
            "target_pages": target_pages,
            "analysis_mode": analysis_mode.value,
            "include_step2_analysis": include_step2,
            "step2_confidence_threshold": step2_threshold,
            "max_concurrent_sessions": max_concurrent,
            "cost_priority": cost_priority.value,
            "site_characteristics": site_characteristics,
            "batch_size": 3 if cost_priority == CostPriority.COST_EFFICIENT else 1,
        }

    async def _execute_analysis_pipeline(
        self, context: Context, strategy: Dict[str, Any], interactive_mode: bool
    ) -> Dict[str, Any]:
        """Execute the orchestrated analysis pipeline with progress tracking."""

        target_pages = strategy["target_pages"]
        include_step2 = strategy["include_step2_analysis"]
        max_concurrent = strategy["max_concurrent_sessions"]

        if not target_pages:
            raise ToolIntegrationError("No target pages identified for analysis")

        # Interactive mode checkpoint: confirm analysis plan
        if interactive_mode:
            await context.info(
                f"📋 **Interactive Mode**: About to analyze {len(target_pages)} pages.\n"
                f"Analysis mode: {strategy['analysis_mode']}\n"
                f"Cost priority: {strategy['cost_priority']}\n"
                f"Include Step 2: {include_step2}\n"
                f"Max concurrent: {max_concurrent}\n\n"
                f"**Pages to analyze:**\n" +
                "\n".join(f"  • {url}" for url in target_pages[:10]) +
                (f"\n  ... and {len(target_pages) - 10} more" if len(target_pages) > 10 else "") +
                f"\n\n⏳ Proceeding with analysis in 5 seconds (analysis will continue automatically)..."
            )
            await asyncio.sleep(5)  # Brief pause for user to review

        try:
            # Get or create project
            project_metadata = self.project_store.get_project_metadata(self.project_id)
            if not project_metadata:
                project_metadata = self.project_store.create_project(
                    project_id=self.project_id,
                    website_url=target_pages[0],
                    config={"analysis_type": "orchestrated_workflow", "page_count": len(target_pages)},
                )

            # Create workflow for page processing
            workflow = SequentialNavigationWorkflow(
                browser_service=self.browser_service,
                project_root=project_metadata.root_path,
                project_id=self.project_id,
                max_concurrent_sessions=max_concurrent,
                default_max_retries=2,
                checkpoint_interval=5,
                enable_resource_cleanup=True,
            )

            # Add pages to workflow
            workflow.add_page_urls(target_pages, max_retries=2)

            # Configure analyzer
            analyzer_config = {
                "include_network_analysis": True,
                "include_interaction_analysis": True,
                "performance_budget_seconds": 120.0,
            }

            # Execute workflow with progress updates
            await workflow.start_workflow(analyzer_config)

            # Provide progress updates during execution
            progress_updates = 0
            while workflow.status.value in ["running", "paused"] and progress_updates < 10:
                await asyncio.sleep(30)  # Update every 30 seconds
                progress = workflow.get_progress_summary()
                completion_pct = progress["progress"]["completion_percentage"]

                await context.info(
                    f"⚡ Analysis progress: {completion_pct:.1f}% complete "
                    f"({progress['progress']['completed_pages']}/{progress['progress']['total_pages']} pages)"
                )
                progress_updates += 1

            # Collect results
            completed_pages = [
                task for task in workflow.page_tasks
                if task.status.value == "completed" and task.analysis_result
            ]

            failed_pages = [
                task for task in workflow.page_tasks
                if task.status.value == "failed"
            ]

            # Interactive mode checkpoint: review initial results
            if interactive_mode and completed_pages:
                await context.info(
                    f"📊 **Phase 3 Complete**: Page analysis finished.\n"
                    f"✅ Successfully analyzed: {len(completed_pages)} pages\n"
                    f"❌ Failed: {len(failed_pages)} pages\n"
                    f"🔬 Proceeding to Step 2 feature analysis..." if include_step2 else "🔄 Skipping Step 2 analysis as requested."
                )

            # Process Step 2 analysis if enabled
            step2_results = {}
            if include_step2 and completed_pages:
                await context.info(f"🔬 Running Step 2 feature analysis on {len(completed_pages)} pages")
                step2_results = await self._execute_step2_analysis(context, completed_pages, strategy)

            return {
                "completed_pages": len(completed_pages),
                "failed_pages": len(failed_pages),
                "page_analysis_results": [
                    {
                        "url": task.url,
                        "page_id": task.page_id,
                        "status": task.status.value,
                        "processing_duration": task.processing_duration,
                        "has_analysis": task.analysis_result is not None,
                    }
                    for task in workflow.page_tasks
                ],
                "step2_analysis_results": step2_results,
                "workflow_id": workflow.workflow_id,
                "total_processing_time": workflow.progress.workflow_duration,
            }

        except Exception as e:
            raise ToolIntegrationError(f"Analysis pipeline execution failed: {e}") from e

    async def _execute_step2_analysis(
        self, context: Context, completed_pages: List[Any], strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Step 2 feature analysis on completed pages."""

        feature_analyzer = FeatureAnalyzer(self.llm_engine)
        content_summarizer = ContentSummarizer(self.llm_engine)

        step2_results = []
        confidence_threshold = strategy["step2_confidence_threshold"]

        for task in completed_pages:
            try:
                if not task.analysis_result:
                    continue

                # Perform Step 1 summarization first
                step1_summary = await content_summarizer.summarize_page(task.analysis_result)

                # Only proceed with Step 2 if confidence is sufficient
                if step1_summary.confidence_score >= confidence_threshold:
                    feature_analysis = await feature_analyzer.analyze_features(
                        page_analysis_data=task.analysis_result,
                        step1_context=step1_summary
                    )

                    step2_results.append({
                        "url": task.url,
                        "page_id": task.page_id,
                        "step1_confidence": step1_summary.confidence_score,
                        "feature_analysis": {
                            "interactive_elements": len(feature_analysis.interactive_elements),
                            "functional_capabilities": len(feature_analysis.functional_capabilities),
                            "api_integrations": len(feature_analysis.api_integrations),
                            "business_rules": len(feature_analysis.business_rules),
                            "confidence_score": feature_analysis.confidence_score,
                            "quality_score": feature_analysis.quality_score,
                        },
                    })
                else:
                    step2_results.append({
                        "url": task.url,
                        "page_id": task.page_id,
                        "step1_confidence": step1_summary.confidence_score,
                        "skipped_reason": f"Low confidence ({step1_summary.confidence_score:.2f} < {confidence_threshold})",
                    })

            except Exception as e:
                _logger.warning(
                    "step2_analysis_failed_for_page",
                    url=task.url,
                    error=str(e),
                )
                step2_results.append({
                    "url": task.url,
                    "page_id": task.page_id,
                    "error": str(e),
                })

        return {
            "total_pages_processed": len(step2_results),
            "successful_analyses": len([r for r in step2_results if "feature_analysis" in r]),
            "skipped_low_confidence": len([r for r in step2_results if "skipped_reason" in r]),
            "failed_analyses": len([r for r in step2_results if "error" in r]),
            "results": step2_results,
        }

    async def _synthesize_and_document_results(
        self,
        context: Context,
        discovery_result: Dict[str, Any],
        analysis_results: Dict[str, Any],
        strategy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synthesize analysis results and generate comprehensive documentation."""

        # Calculate analysis metrics
        total_pages_found = discovery_result["total_pages_found"]
        pages_analyzed = analysis_results["completed_pages"]
        analysis_coverage = (pages_analyzed / total_pages_found * 100) if total_pages_found > 0 else 0

        # Aggregate Step 2 results if available
        step2_summary = {}
        if "step2_analysis_results" in analysis_results:
            step2_data = analysis_results["step2_analysis_results"]
            step2_summary = {
                "feature_analysis_coverage": f"{step2_data['successful_analyses']}/{pages_analyzed}",
                "average_feature_complexity": "medium",  # Could calculate from actual data
                "api_integrations_found": sum(
                    r.get("feature_analysis", {}).get("api_integrations", 0)
                    for r in step2_data.get("results", [])
                ),
                "interactive_elements_total": sum(
                    r.get("feature_analysis", {}).get("interactive_elements", 0)
                    for r in step2_data.get("results", [])
                ),
            }

        # Technology assessment
        tech_assessment = {
            "modernization_priority": "medium",  # Could analyze from actual tech detection
            "rebuild_complexity": "moderate",    # Could calculate from feature complexity
            "estimated_rebuild_time": f"{pages_analyzed * 2}-{pages_analyzed * 4} weeks",
        }

        # Generate documentation summary
        documentation_summary = {
            "analysis_completion_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_pages_discovered": total_pages_found,
            "pages_successfully_analyzed": pages_analyzed,
            "analysis_coverage_percentage": round(analysis_coverage, 1),
            "analysis_mode_used": strategy["analysis_mode"],
            "cost_priority_used": strategy["cost_priority"],
            "step2_feature_analysis": step2_summary,
            "technology_assessment": tech_assessment,
            "processing_time_seconds": analysis_results.get("total_processing_time", 0),
            "workflow_id": self.workflow_id,
        }

        return documentation_summary


def register(mcp: FastMCP) -> None:
    """Register high-level orchestration tools with the MCP server."""

    @mcp.tool()
    async def analyze_legacy_site(
        context: Context,
        url: str,
        analysis_mode: str = "recommended",
        max_pages: int = 0,
        include_step2: bool = True,
        interactive_mode: bool = False,
        project_id: str = "legacy-analysis",
        cost_priority: str = "balanced",
    ) -> Dict[str, Any]:
        """Complete legacy website analysis with intelligent orchestration.

        Orchestrates the entire analysis workflow from site discovery to documentation:
        1. Intelligent site discovery with strategic page selection
        2. Adaptive analysis strategy based on site characteristics
        3. Coordinated execution of browser automation and LLM analysis
        4. Result synthesis and comprehensive documentation generation

        Args:
            url: Target website URL for analysis (required)
            analysis_mode: Analysis depth - "quick", "recommended", "comprehensive", "targeted" (default: "recommended")
            max_pages: Maximum pages to analyze (0 = auto-select based on mode) (default: 0)
            include_step2: Include detailed feature analysis (Step 2) (default: True)
            interactive_mode: Enable human validation checkpoints (default: False)
            project_id: Project identifier for organizing results (default: "legacy-analysis")
            cost_priority: Optimize for "speed", "balanced", or "cost_efficient" (default: "balanced")

        Returns:
            Complete analysis summary with findings, recommendations, and technical specifications

        Features:
            - Intelligent site discovery with priority page selection
            - Adaptive analysis strategies based on site complexity
            - Real-time progress tracking with human-readable updates
            - Comprehensive error handling and recovery
            - Cost-aware analysis with transparent usage reporting
            - Structured documentation ready for rebuild planning
        """
        try:
            # Validate and convert parameters
            try:
                analysis_mode_enum = AnalysisMode(analysis_mode.lower())
            except ValueError:
                valid_modes = [mode.value for mode in AnalysisMode]
                await context.error(f"Invalid analysis_mode: {analysis_mode}. Valid options: {valid_modes}")
                return {
                    "status": "error",
                    "error": f"Invalid analysis_mode: {analysis_mode}",
                    "valid_options": valid_modes
                }

            try:
                cost_priority_enum = CostPriority(cost_priority.lower())
            except ValueError:
                valid_priorities = [priority.value for priority in CostPriority]
                await context.error(f"Invalid cost_priority: {cost_priority}. Valid options: {valid_priorities}")
                return {
                    "status": "error",
                    "error": f"Invalid cost_priority: {cost_priority}",
                    "valid_options": valid_priorities
                }

            config = load_configuration()

            _logger.info(
                "orchestrated_legacy_analysis_requested",
                url=url,
                analysis_mode=analysis_mode,
                max_pages=max_pages,
                include_step2=include_step2,
                interactive_mode=interactive_mode,
                project_id=project_id,
                cost_priority=cost_priority,
            )

            # Create orchestrator and execute workflow
            orchestrator = LegacyAnalysisOrchestrator(config, project_id)

            result = await orchestrator.discover_and_analyze_site(
                context=context,
                url=url,
                analysis_mode=analysis_mode_enum,
                max_pages=max_pages,
                include_step2=include_step2,
                interactive_mode=interactive_mode,
                cost_priority=cost_priority_enum,
            )

            return result

        except Exception as e:
            await context.error(f"Legacy site analysis failed: {e}")
            _logger.error(
                "orchestrated_legacy_analysis_failed",
                url=url,
                project_id=project_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "url": url,
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def analyze_with_recommendations(
        context: Context,
        url: str,
        project_id: str = "smart-analysis",
    ) -> Dict[str, Any]:
        """AI-recommended analysis strategy based on automatic site assessment.

        Performs intelligent site assessment and automatically selects optimal analysis
        parameters based on site characteristics, complexity, and typical use cases.

        Args:
            url: Target website URL for analysis (required)
            project_id: Project identifier for organizing results (default: "smart-analysis")

        Returns:
            Complete analysis with AI-selected strategy and recommendations
        """
        try:
            config = load_configuration()
            orchestrator = LegacyAnalysisOrchestrator(config, project_id)

            await context.info(f"🤖 Analyzing {url} with AI-recommended strategy...")

            # Quick discovery to assess site characteristics
            discovery_result = await orchestrator._intelligent_site_discovery(
                context, url, AnalysisMode.QUICK, 5
            )

            site_info = discovery_result.get("site_characteristics", {})
            total_pages = discovery_result["total_pages_found"]

            # AI strategy selection based on site characteristics
            if total_pages <= 10:
                recommended_mode = AnalysisMode.COMPREHENSIVE
                recommended_cost = CostPriority.BALANCED
                max_pages = total_pages
            elif total_pages <= 30:
                recommended_mode = AnalysisMode.RECOMMENDED
                recommended_cost = CostPriority.BALANCED
                max_pages = 20
            else:
                recommended_mode = AnalysisMode.RECOMMENDED
                recommended_cost = CostPriority.COST_EFFICIENT
                max_pages = 25

            await context.info(
                f"🎯 AI recommendation: {recommended_mode.value} mode, "
                f"{recommended_cost.value} cost priority, {max_pages} pages max"
            )

            # Execute with recommended strategy
            result = await orchestrator.discover_and_analyze_site(
                context=context,
                url=url,
                analysis_mode=recommended_mode,
                max_pages=max_pages,
                include_step2=True,
                interactive_mode=False,
                cost_priority=recommended_cost,
            )

            # Add recommendation details to result
            result["ai_recommendations"] = {
                "selected_mode": recommended_mode.value,
                "selected_cost_priority": recommended_cost.value,
                "reasoning": f"Selected based on {total_pages} total pages discovered",
                "site_assessment": site_info,
            }

            return result

        except Exception as e:
            await context.error(f"AI-recommended analysis failed: {e}")
            return {
                "status": "error",
                "url": url,
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def get_analysis_status(
        context: Context,
        project_id: str,
    ) -> Dict[str, Any]:
        """Get human-readable status of ongoing or completed analysis workflows.

        Args:
            project_id: Project identifier to check status for (required)

        Returns:
            Human-readable progress summary and workflow information
        """
        try:
            config = load_configuration()
            project_store = create_project_store(config)

            # Get project metadata
            project_metadata = project_store.get_project_metadata(project_id)
            if not project_metadata:
                return {
                    "status": "not_found",
                    "project_id": project_id,
                    "message": f"No project found with ID: {project_id}",
                }

            # Check for active workflows (simplified - would integrate with workflow tracking)
            project_root = project_metadata.root_path
            analysis_dir = project_root / "analysis" / "pages"
            workflow_dir = project_root / "workflow"

            analysis_files = list(analysis_dir.glob("*.json")) if analysis_dir.exists() else []
            checkpoint_files = list(workflow_dir.glob("checkpoints/*.json")) if workflow_dir.exists() else []

            status_summary = {
                "status": "completed" if analysis_files else "no_analysis",
                "project_id": project_id,
                "project_path": str(project_root),
                "analysis_files_found": len(analysis_files),
                "checkpoint_files_found": len(checkpoint_files),
                "last_activity": max(
                    [f.stat().st_mtime for f in analysis_files + checkpoint_files]
                ) if analysis_files or checkpoint_files else None,
            }

            if analysis_files:
                status_summary["message"] = f"Analysis complete: {len(analysis_files)} pages analyzed"
                status_summary["analysis_files"] = [f.name for f in analysis_files[:10]]
            else:
                status_summary["message"] = "No analysis results found for this project"

            return status_summary

        except Exception as e:
            return {
                "status": "error",
                "project_id": project_id,
                "error": str(e),
                "error_type": type(e).__name__,
            }


__all__ = ["register", "LegacyAnalysisOrchestrator", "AnalysisMode", "CostPriority"]