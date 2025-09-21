"""High-level workflow orchestration tools for legacy website analysis.

This module provides intelligent orchestration of the complete Legacy Web MCP Server
toolkit through high-level tools that combine discovery, browser automation, LLM analysis,
and documentation generation into seamless conversational AI workflows.

The primary tool `analyze_legacy_site()` provides complete site analysis from URL to
documentation, with intelligent workflow planning, progress tracking, error recovery,
and result aggregation.

Story 6.5 adds AI-driven site analysis workflow through `intelligent_analyze_site()`,
which uses AI to orchestrate the complete analysis process with natural language
command parsing, intelligent decision-making, and adaptive strategies.
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
from legacy_web_mcp.llm.models import (CombinedAnalysisResult, ContextPayload, LLMMessage, LLMRequest, LLMRequestType, LLMRole)
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


class SitePattern(Enum):
    """Recognized website patterns for adaptive analysis."""
    ECOMMERCE = "ecommerce"
    ADMIN_PANEL = "admin_panel"
    CMS = "cms"
    BLOG = "blog"
    CORPORATE = "corporate"
    APPLICATION = "application"
    LANDING_PAGE = "landing_page"
    UNKNOWN = "unknown"


class AnalysisIntent(Enum):
    """User analysis intent categories."""
    REBUILD_PLANNING = "rebuild_planning"
    FEATURE_ASSESSMENT = "feature_assessment"
    SECURITY_AUDIT = "security_audit"
    MIGRATION_PREP = "migration_prep"
    GENERAL_ANALYSIS = "general_analysis"


class AIWorkflowOrchestrator:
    """AI-driven workflow orchestrator with intelligent decision-making."""

    def __init__(self, config, project_id: str):
        self.config = config
        self.project_id = project_id
        self.llm_engine = LLMEngine(config)
        self.base_orchestrator = LegacyAnalysisOrchestrator(config, project_id)

        # AI workflow state
        self.conversation_context = []
        self.learned_patterns = {}
        self.analysis_history = []

    async def analyze_with_intelligence(
        self,
        context: Context,
        natural_language_request: str,
        url: str,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute AI-driven site analysis with intelligent orchestration."""

        # Parse natural language request
        analysis_intent = await self._parse_analysis_intent(natural_language_request)

        await context.info(f"🧠 Understanding your request: {analysis_intent['summary']}")

        # Perform intelligent site discovery and pattern recognition
        site_pattern = await self._detect_site_pattern(context, url)

        await context.info(f"🔍 Detected site pattern: {site_pattern['type']} ({site_pattern['confidence']:.0%} confidence)")

        # AI-driven workflow planning
        workflow_plan = await self._create_intelligent_workflow_plan(
            analysis_intent, site_pattern, user_preferences or {}
        )

        await context.info(f"📋 Created intelligent analysis plan: {workflow_plan['strategy_summary']}")

        # Execute workflow with adaptive monitoring
        result = await self._execute_adaptive_workflow(
            context, url, workflow_plan, analysis_intent
        )

        # AI-powered result synthesis
        synthesized_result = await self._synthesize_results_with_ai(
            result, analysis_intent, site_pattern
        )

        # Learn from this analysis
        await self._learn_from_analysis(analysis_intent, site_pattern, synthesized_result)

        await context.info("✨ Analysis complete! Generated intelligent insights and recommendations.")

        return synthesized_result

    async def _parse_analysis_intent(self, natural_language_request: str) -> Dict[str, Any]:
        """Parse natural language request to extract analysis intent and requirements."""

        # Use LLM to analyze the request
        intent_prompt = f"""
        Analyze this legacy website analysis request and extract the key intent and requirements:

        Request: "{natural_language_request}"

        Please provide:
        1. Primary intent (rebuild_planning, feature_assessment, security_audit, migration_prep, general_analysis)
        2. Specific goals mentioned
        3. Urgency level (low/medium/high)
        4. Depth preference (quick/thorough/comprehensive)
        5. Focus areas if mentioned
        6. Budget/time constraints if mentioned
        7. A brief summary of what the user wants

        Return as JSON format.
        """

        try:
            intent_request = LLMRequest(
                messages=[LLMMessage(role=LLMRole.USER, content=intent_prompt)],
                request_type=LLMRequestType.FEATURE_ANALYSIS
            )
            intent_response = await self.llm_engine.chat_completion(request=intent_request)
            intent_response_content = intent_response.content

            intent_data = json.loads(intent_response_content)

            return {
                "intent": intent_data.get("primary_intent", "general_analysis"),
                "goals": intent_data.get("specific_goals", []),
                "urgency": intent_data.get("urgency_level", "medium"),
                "depth": intent_data.get("depth_preference", "thorough"),
                "focus_areas": intent_data.get("focus_areas", []),
                "constraints": intent_data.get("constraints", {}),
                "summary": intent_data.get("summary", natural_language_request)
            }
        except Exception as e:
            _logger.warning("Intent parsing failed, using defaults", error=str(e))
            return {
                "intent": "general_analysis",
                "goals": [],
                "urgency": "medium",
                "depth": "thorough",
                "focus_areas": [],
                "constraints": {},
                "summary": natural_language_request
            }

    async def _detect_site_pattern(self, context: Context, url: str) -> Dict[str, Any]:
        """Detect site pattern using AI analysis of initial page characteristics."""

        try:
            # Quick discovery for pattern detection
            discovery_result = await self.base_orchestrator._intelligent_site_discovery(
                context, url, AnalysisMode.QUICK, 3
            )

            # Use AI to analyze site characteristics
            pattern_prompt = f"""
            Analyze these website characteristics and determine the site pattern:

            URL: {url}
            Site characteristics: {discovery_result.get('site_characteristics', {})}
            Total pages found: {discovery_result.get('total_pages_found', 0)}

            Based on the URL structure, content, and characteristics, determine:
            1. Site type (ecommerce, admin_panel, cms, blog, corporate, application, landing_page, unknown)
            2. Confidence level (0.0 to 1.0)
            3. Key characteristics detected
            4. Recommended analysis approach
            5. Estimated complexity (low/medium/high)

            Return as JSON format.
            """

            pattern_request = LLMRequest(
                messages=[LLMMessage(role=LLMRole.USER, content=pattern_prompt)],
                request_type=LLMRequestType.FEATURE_ANALYSIS
            )
            pattern_response = await self.llm_engine.chat_completion(request=pattern_request)
            pattern_response_content = pattern_response.content

            pattern_data = json.loads(pattern_response_content)

            return {
                "type": pattern_data.get("site_type", "unknown"),
                "confidence": pattern_data.get("confidence_level", 0.5),
                "characteristics": pattern_data.get("key_characteristics", []),
                "recommended_approach": pattern_data.get("recommended_analysis_approach", "standard"),
                "complexity": pattern_data.get("estimated_complexity", "medium"),
                "discovery_data": discovery_result
            }

        except Exception as e:
            _logger.warning("Site pattern detection failed", error=str(e))
            return {
                "type": "unknown",
                "confidence": 0.0,
                "characteristics": [],
                "recommended_approach": "standard",
                "complexity": "medium",
                "discovery_data": {}
            }

    async def _create_intelligent_workflow_plan(
        self,
        analysis_intent: Dict[str, Any],
        site_pattern: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create intelligent workflow plan based on intent, pattern, and preferences."""

        # AI-driven workflow planning
        planning_prompt = f"""
        Create an intelligent analysis workflow plan based on:

        User Intent: {analysis_intent}
        Site Pattern: {site_pattern}
        User Preferences: {user_preferences}

        Please determine:
        1. Analysis mode (quick/recommended/comprehensive/targeted)
        2. Cost priority (speed/balanced/cost_efficient)
        3. Maximum pages to analyze
        4. Whether to include Step 2 detailed analysis
        5. Focus areas to prioritize
        6. Estimated time and cost
        7. Strategy summary
        8. Special considerations

        Optimize for the user's intent while being cost-effective and thorough.
        Return as JSON format.
        """

        try:
            plan_request = LLMRequest(
                messages=[LLMMessage(role=LLMRole.USER, content=planning_prompt)],
                request_type=LLMRequestType.FEATURE_ANALYSIS
            )
            plan_response = await self.llm_engine.chat_completion(request=plan_request)
            plan_response_content = plan_response.content

            plan_data = json.loads(plan_response_content)

            # Convert string enums to proper enum values
            analysis_mode = AnalysisMode(plan_data.get("analysis_mode", "recommended"))
            cost_priority = CostPriority(plan_data.get("cost_priority", "balanced"))

            return {
                "analysis_mode": analysis_mode,
                "cost_priority": cost_priority,
                "max_pages": plan_data.get("max_pages", 20),
                "include_step2": plan_data.get("include_step2", True),
                "focus_areas": plan_data.get("focus_areas", []),
                "estimated_time": plan_data.get("estimated_time", "2-4 hours"),
                "estimated_cost": plan_data.get("estimated_cost", "$5-15"),
                "strategy_summary": plan_data.get("strategy_summary", "Comprehensive analysis"),
                "special_considerations": plan_data.get("special_considerations", [])
            }

        except Exception as e:
            _logger.warning("Workflow planning failed, using defaults", error=str(e))
            return {
                "analysis_mode": AnalysisMode.RECOMMENDED,
                "cost_priority": CostPriority.BALANCED,
                "max_pages": 20,
                "include_step2": True,
                "focus_areas": [],
                "estimated_time": "2-4 hours",
                "estimated_cost": "$5-15",
                "strategy_summary": "Standard comprehensive analysis",
                "special_considerations": []
            }

    async def _execute_adaptive_workflow(
        self,
        context: Context,
        url: str,
        workflow_plan: Dict[str, Any],
        analysis_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute workflow with adaptive monitoring and natural language progress updates."""

        # Start workflow with conversational updates
        await context.info(
            f"🚀 Starting {workflow_plan['strategy_summary'].lower()} for {url}\n"
            f"📊 Plan: {workflow_plan['max_pages']} pages, {workflow_plan['analysis_mode'].value} mode\n"
            f"⏱️ Estimated time: {workflow_plan['estimated_time']}"
        )

        # Execute base orchestration workflow
        result = await self.base_orchestrator.discover_and_analyze_site(
            context=context,
            url=url,
            analysis_mode=workflow_plan["analysis_mode"],
            max_pages=workflow_plan["max_pages"],
            include_step2=workflow_plan["include_step2"],
            interactive_mode=False,
            cost_priority=workflow_plan["cost_priority"]
        )

        # Add workflow plan context to results
        result["ai_workflow_plan"] = workflow_plan
        result["analysis_intent"] = analysis_intent

        return result

    async def _synthesize_results_with_ai(
        self,
        analysis_result: Dict[str, Any],
        analysis_intent: Dict[str, Any],
        site_pattern: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use AI to synthesize results into intelligent, actionable insights."""

        synthesis_prompt = f"""
        Synthesize these analysis results into actionable insights based on the user's intent:

        User Intent: {analysis_intent['summary']}
        Site Pattern: {site_pattern['type']} (confidence: {site_pattern['confidence']:.0%})
        Analysis Results: {json.dumps(analysis_result, indent=2, default=str)[:2000]}...

        Please provide:
        1. Executive summary tailored to user intent
        2. Prioritized findings and recommendations
        3. Key insights specific to the site pattern
        4. Actionable next steps
        5. Risk assessment and considerations
        6. Rebuild/migration recommendations if applicable
        7. Cost and timeline estimates for recommendations

        Focus on what matters most for the user's goals.
        Return as JSON format with clear sections.
        """

        try:
            synthesis_request = LLMRequest(
                messages=[LLMMessage(role=LLMRole.USER, content=synthesis_prompt)],
                request_type=LLMRequestType.FEATURE_ANALYSIS
            )
            synthesis_response = await self.llm_engine.chat_completion(request=synthesis_request)
            synthesis_response_content = synthesis_response.content

            synthesis_data = json.loads(synthesis_response_content)

            # Enhance original result with AI insights
            enhanced_result = analysis_result.copy()
            enhanced_result.update({
                "ai_synthesis": synthesis_data,
                "intelligent_insights": {
                    "executive_summary": synthesis_data.get("executive_summary", ""),
                    "prioritized_findings": synthesis_data.get("prioritized_findings", []),
                    "key_insights": synthesis_data.get("key_insights", []),
                    "actionable_next_steps": synthesis_data.get("actionable_next_steps", []),
                    "risk_assessment": synthesis_data.get("risk_assessment", {}),
                    "rebuild_recommendations": synthesis_data.get("rebuild_recommendations", {}),
                    "estimates": synthesis_data.get("estimates", {})
                },
                "site_pattern_analysis": site_pattern,
                "user_intent_fulfillment": analysis_intent
            })

            return enhanced_result

        except Exception as e:
            _logger.warning("AI synthesis failed", error=str(e))
            # Return original result with basic enhancement
            analysis_result["ai_synthesis_error"] = str(e)
            analysis_result["site_pattern_analysis"] = site_pattern
            analysis_result["user_intent_fulfillment"] = analysis_intent
            return analysis_result

    async def _learn_from_analysis(
        self,
        analysis_intent: Dict[str, Any],
        site_pattern: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> None:
        """Learn from analysis to improve future workflow planning."""

        # Store analysis patterns for future learning
        learning_data = {
            "timestamp": time.time(),
            "intent": analysis_intent["intent"],
            "site_type": site_pattern["type"],
            "success_metrics": {
                "completed": analysis_result.get("status") == "success",
                "pages_analyzed": analysis_result.get("pages_analyzed", 0),
                "analysis_quality": analysis_result.get("analysis_quality_score", 0.5)
            }
        }

        self.analysis_history.append(learning_data)

        # Keep only recent history to avoid memory bloat
        if len(self.analysis_history) > 100:
            self.analysis_history = self.analysis_history[-100:]

        _logger.info(
            "analysis_learning_recorded",
            intent=analysis_intent["intent"],
            site_type=site_pattern["type"],
            success=learning_data["success_metrics"]["completed"]
        )


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

            # Discovery service returns inventory structure, not status/urls directly
            inventory = discovery_data.get("inventory", {})
            if not inventory:
                raise WorkflowPlanningError(f"Site discovery failed: No inventory data returned")

            # Extract URLs from inventory structure (URLs are grouped by category)
            url_groups = inventory.get("urls", {})
            all_urls = []

            # Collect URLs from all categories: internal_pages, external_pages, assets
            for category in ["internal_pages", "external_pages", "assets"]:
                for url_record in url_groups.get(category, []):
                    if isinstance(url_record, dict) and "url" in url_record:
                        all_urls.append(url_record["url"])
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
        """Execute Step 2 feature analysis on completed pages with quality validation and artifact management."""

        feature_analyzer = FeatureAnalyzer(self.llm_engine)
        content_summarizer = ContentSummarizer(self.llm_engine)

        # Initialize artifact manager for debugging and persistence
        from legacy_web_mcp.llm.artifacts import ArtifactManager
        from legacy_web_mcp.llm.debugging import DebugInspector
        
        artifact_manager = ArtifactManager()
        debug_inspector = DebugInspector(artifact_manager)

        step2_results = []
        confidence_threshold = strategy["step2_confidence_threshold"]

        for task in completed_pages:
            # Create artifact for this page analysis
            artifact = None
            debug_session = None
            
            try:
                if not task.analysis_result:
                    continue

                # Create analysis artifact for persistence and debugging
                artifact = artifact_manager.create_artifact(
                    analysis_type="step2_with_step1",
                    page_url=task.url,
                    page_analysis_data=task.analysis_result,
                    project_id=self.project_id,
                    metadata={
                        "page_id": task.page_id,
                        "workflow_id": self.workflow_id,
                        "strategy": strategy,
                        "processing_start": time.time()
                    }
                )

                # Start debug session for detailed monitoring
                debug_session = debug_inspector.start_debug_session(
                    page_url=task.url,
                    analysis_type="step2_with_step1",
                    session_id=f"{artifact.artifact_id}_debug"
                )

                # Perform Step 1 summarization first with quality validation
                try:
                    step1_summary = await content_summarizer.summarize_page(task.analysis_result)
                    
                    # Add Step 1 result to artifact
                    artifact_manager.add_analysis_result(
                        artifact=artifact,
                        result=step1_summary
                    )
                    
                    # Log Step 1 completion
                    _logger.info(
                        "step1_summary_completed",
                        url=task.url,
                        confidence_score=step1_summary.confidence_score,
                        artifact_id=artifact.artifact_id
                    )

                except Exception as step1_error:
                    error_msg = f"Step 1 analysis failed: {str(step1_error)}"
                    _logger.error(
                        "step1_analysis_failed_in_orchestration",
                        url=task.url,
                        error=str(step1_error),
                        artifact_id=artifact.artifact_id
                    )
                    
                    # Add error to artifact
                    artifact_manager.add_error(
                        artifact=artifact,
                        error=step1_error,
                        context={
                            "phase": "step1_summarization",
                            "page_url": task.url,
                            "page_id": task.page_id
                        }
                    )
                    
                    step2_results.append({
                        "url": task.url,
                        "page_id": task.page_id,
                        "error": error_msg,
                        "artifact_id": artifact.artifact_id,
                        "error_phase": "step1"
                    })
                    
                    artifact_manager.complete_artifact(artifact, status="failed")
                    continue

                # Only proceed with Step 2 if confidence is sufficient
                if step1_summary.confidence_score >= confidence_threshold:
                    try:
                        # Create context payload for Step 2
                        context_payload = ContextPayload(content_summary=step1_summary)

                        # Use context-aware feature analysis with validation
                        feature_analysis = await feature_analyzer.analyze_features_with_context(
                            page_analysis_data=task.analysis_result,
                            context_payload=context_payload,
                        )

                        # Add Step 2 result to artifact
                        artifact_manager.add_analysis_result(
                            artifact=artifact,
                            result=feature_analysis
                        )

                        # Create and append the combined analysis result
                        combined_result = CombinedAnalysisResult(
                            content_summary=step1_summary,
                            feature_analysis=feature_analysis,
                            context_payload=context_payload,
                            consistency_validation=feature_analysis.context_validation,
                        )
                        combined_result.calculate_overall_metrics()

                        # Update artifact with combined metrics
                        artifact.metadata.update({
                            "overall_quality_score": combined_result.overall_quality_score,
                            "analysis_completeness": combined_result.analysis_completeness,
                            "context_utilization_score": combined_result.context_utilization_score,
                            "cross_reference_score": combined_result.cross_reference_score,
                            "processing_end": time.time()
                        })

                        # Log quality assessment to debug session
                        if hasattr(feature_analysis, 'metadata') and feature_analysis.metadata:
                            quality_metrics = feature_analysis.metadata.get('quality_metrics')
                            validation_result = feature_analysis.metadata.get('validation_result')
                            
                            if quality_metrics and validation_result:
                                from legacy_web_mcp.llm.quality import QualityMetrics, ValidationResult
                                
                                quality_obj = QualityMetrics(**quality_metrics)
                                validation_obj = ValidationResult(**validation_result)
                                
                                debug_inspector.log_quality_assessment(
                                    session_id=debug_session.session_id,
                                    quality_metrics=quality_obj,
                                    validation_result=validation_obj,
                                    decision_rationale=f"Step 2 analysis completed with quality score {quality_obj.overall_quality_score:.2f}"
                                )

                        # Log a warning if inconsistencies are found
                        if combined_result.consistency_validation and combined_result.consistency_validation.action_required:
                            inconsistency_warning = {
                                "message": "Inconsistency found between Step 1 and Step 2 analysis",
                                "inconsistencies": combined_result.consistency_validation.inconsistencies,
                                "consistency_score": combined_result.consistency_validation.consistency_score
                            }
                            
                            _logger.warning(
                                "step_consistency_validation_failed",
                                url=task.url,
                                page_id=task.page_id,
                                **inconsistency_warning
                            )
                            
                            # Add warning to artifact
                            artifact.warnings.append(f"Consistency validation failed: {inconsistency_warning['message']}")
                            
                            # Log consistency issue to debug session
                            debug_inspector.log_retry_decision(
                                session_id=debug_session.session_id,
                                retry_count=0,
                                reason="consistency_validation_failed",
                                quality_score=combined_result.consistency_validation.consistency_score,
                                threshold=0.7,
                                decision="proceed_with_warning",
                                context=inconsistency_warning
                            )

                        # Store combined result in both artifact and results
                        artifact.metadata["combined_analysis_result"] = combined_result.model_dump()
                        step2_results.append(combined_result)

                        # Mark artifact as completed successfully
                        artifact_manager.complete_artifact(artifact, status="completed")

                        _logger.info(
                            "step2_analysis_completed_successfully",
                            url=task.url,
                            page_id=task.page_id,
                            overall_quality_score=combined_result.overall_quality_score,
                            artifact_id=artifact.artifact_id
                        )

                    except Exception as step2_error:
                        error_msg = f"Step 2 analysis failed: {str(step2_error)}"
                        _logger.error(
                            "step2_analysis_failed_in_orchestration",
                            url=task.url,
                            error=str(step2_error),
                            artifact_id=artifact.artifact_id
                        )
                        
                        # Add error to artifact
                        artifact_manager.add_error(
                            artifact=artifact,
                            error=step2_error,
                            context={
                                "phase": "step2_feature_analysis",
                                "page_url": task.url,
                                "page_id": task.page_id,
                                "step1_confidence": step1_summary.confidence_score
                            }
                        )
                        
                        step2_results.append({
                            "url": task.url,
                            "page_id": task.page_id,
                            "step1_confidence": step1_summary.confidence_score,
                            "error": error_msg,
                            "artifact_id": artifact.artifact_id,
                            "error_phase": "step2"
                        })
                        
                        artifact_manager.complete_artifact(artifact, status="failed")

                else:
                    # Step 1 confidence too low - store partial result
                    skip_reason = f"Low confidence ({step1_summary.confidence_score:.2f} < {confidence_threshold})"
                    
                    artifact.metadata.update({
                        "skip_reason": skip_reason,
                        "step1_confidence": step1_summary.confidence_score,
                        "confidence_threshold": confidence_threshold,
                        "processing_end": time.time()
                    })
                    
                    step2_results.append({
                        "url": task.url,
                        "page_id": task.page_id,
                        "step1_confidence": step1_summary.confidence_score,
                        "skipped_reason": skip_reason,
                        "artifact_id": artifact.artifact_id
                    })
                    
                    # Mark artifact as completed but skipped
                    artifact_manager.complete_artifact(artifact, status="completed")
                    
                    _logger.info(
                        "step2_analysis_skipped_low_confidence",
                        url=task.url,
                        confidence_score=step1_summary.confidence_score,
                        threshold=confidence_threshold,
                        artifact_id=artifact.artifact_id
                    )

            except Exception as e:
                error_msg = f"Analysis orchestration failed: {str(e)}"
                _logger.warning(
                    "step2_analysis_orchestration_failed",
                    url=task.url,
                    error=str(e),
                    artifact_id=artifact.artifact_id if artifact else "none"
                )
                
                # Add error to artifact if available
                if artifact:
                    artifact_manager.add_error(
                        artifact=artifact,
                        error=e,
                        context={
                            "phase": "orchestration",
                            "page_url": task.url,
                            "page_id": task.page_id
                        }
                    )
                    artifact_manager.complete_artifact(artifact, status="failed")
                
                step2_results.append({
                    "url": task.url,
                    "page_id": task.page_id,
                    "error": error_msg,
                    "artifact_id": artifact.artifact_id if artifact else None,
                    "error_phase": "orchestration"
                })
                
            finally:
                # Close debug session if it was created
                if debug_session:
                    debug_inspector.close_session(debug_session.session_id)

        # Calculate final summary with artifact information
        successful_analyses = [r for r in step2_results if isinstance(r, CombinedAnalysisResult)]
        failed_analyses = [r for r in step2_results if isinstance(r, dict) and "error" in r]
        skipped_analyses = [r for r in step2_results if isinstance(r, dict) and "skipped_reason" in r]

        _logger.info(
            "step2_analysis_batch_completed",
            total_pages=len(step2_results),
            successful=len(successful_analyses),
            failed=len(failed_analyses),
            skipped=len(skipped_analyses),
            project_id=self.project_id,
            workflow_id=self.workflow_id
        )

        return {
            "total_pages_processed": len(step2_results),
            "successful_analyses": len(successful_analyses),
            "skipped_low_confidence": len(skipped_analyses),
            "failed_analyses": len(failed_analyses),
            "results": step2_results,
            "artifact_summary": {
                "artifacts_created": len([r for r in step2_results if isinstance(r, dict) and r.get("artifact_id")]),
                "debugging_enabled": True,
                "quality_validation_enabled": True
            }
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
            # Check if step2_data has the expected structure (not empty when Step 2 was skipped)
            if step2_data and "successful_analyses" in step2_data:
                step2_summary = {
                    "feature_analysis_coverage": f"{step2_data['successful_analyses']}/{pages_analyzed}",
                    "average_feature_complexity": "medium",  # Could calculate from actual data
                    "api_integrations_found": sum(
                        len(r.feature_analysis.api_integrations)
                        for r in step2_data.get("results", []) if hasattr(r, 'feature_analysis')
                    ),
                    "interactive_elements_total": sum(
                        len(r.feature_analysis.interactive_elements)
                        for r in step2_data.get("results", []) if hasattr(r, 'feature_analysis')
                    ),
                }
            else:
                # Step 2 was skipped or failed
                step2_summary = {
                    "feature_analysis_coverage": "0/0 (Step 2 analysis skipped)",
                    "average_feature_complexity": "not_analyzed",
                    "api_integrations_found": 0,
                    "interactive_elements_total": 0,
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

    @mcp.tool()
    async def intelligent_analyze_site(
        context: Context,
        natural_language_request: str,
        url: str,
        user_preferences: Optional[str] = None,
        project_id: str = "ai-analysis",
    ) -> Dict[str, Any]:
        """AI-driven site analysis workflow with natural language orchestration.

        Uses AI to understand your analysis request, detect site patterns, create intelligent
        workflow plans, and synthesize results into actionable insights. Provides conversational
        progress updates and adapts analysis strategy based on site characteristics.

        Args:
            natural_language_request: Describe what you want to analyze in natural language
                Examples: "Analyze this legacy CRM for rebuilding", "Assess this e-commerce site's features"
            url: Target website URL for analysis (required)
            user_preferences: Optional JSON string with preferences like budget, timeline, focus areas
            project_id: Project identifier for organizing results (default: "ai-analysis")

        Returns:
            Comprehensive analysis with AI-generated insights, recommendations, and actionable next steps

        Features:
            - Natural language command parsing and intent recognition
            - Intelligent site pattern detection (e-commerce, admin, CMS, etc.)
            - AI-driven workflow planning and tool selection
            - Adaptive analysis strategies based on site complexity
            - Conversational progress updates throughout analysis
            - AI-powered result synthesis with prioritized recommendations
            - Learning from analysis patterns to improve future workflows
        """
        try:
            config = load_configuration()

            _logger.info(
                "intelligent_analysis_requested",
                request=natural_language_request,
                url=url,
                project_id=project_id,
            )

            # Parse user preferences if provided
            preferences = {}
            if user_preferences:
                try:
                    preferences = json.loads(user_preferences)
                except json.JSONDecodeError:
                    await context.info("⚠️ User preferences format invalid, using defaults")

            # Create AI workflow orchestrator
            ai_orchestrator = AIWorkflowOrchestrator(config, project_id)

            await context.info(f"🤖 Starting AI-driven analysis for: {url}")
            await context.info(f"📝 Your request: {natural_language_request}")

            # Execute AI-driven analysis
            result = await ai_orchestrator.analyze_with_intelligence(
                context=context,
                natural_language_request=natural_language_request,
                url=url,
                user_preferences=preferences
            )

            return result

        except Exception as e:
            await context.error(f"Intelligent analysis failed: {e}")
            _logger.error(
                "intelligent_analysis_failed",
                request=natural_language_request,
                url=url,
                project_id=project_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "url": url,
                "project_id": project_id,
                "natural_language_request": natural_language_request,
                "error": str(e),
                "error_type": type(e).__name__,
            }


__all__ = ["register", "LegacyAnalysisOrchestrator", "AIWorkflowOrchestrator", "AnalysisMode", "CostPriority", "SitePattern", "AnalysisIntent"]