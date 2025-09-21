"""MCP tools for comprehensive page analysis data collection."""

from __future__ import annotations

import json
from typing import Any, List

import structlog
from fastmcp import Context, FastMCP

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.analysis import PageAnalyzer
from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.storage.projects import create_project_store
from legacy_web_mcp.llm.analysis.step1_summarize import ContentSummarizer
from legacy_web_mcp.llm.analysis.step2_feature_analysis import FeatureAnalyzer
from legacy_web_mcp.llm.engine import LLMEngine
from legacy_web_mcp.llm.models import ContentSummary

_logger = structlog.get_logger("legacy_web_mcp.mcp.analysis_tools")


def register(mcp: FastMCP) -> None:
    """Register page analysis tools with the MCP server."""

    @mcp.tool()
    async def summarize_page_content(
        context: Context,
        url: str,
        project_id: str = "content-summary",
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Performs Step 1 Content Summarization analysis on a single page.

        Args:
            url: The target URL to summarize.
            project_id: A project identifier for the analysis session.
            browser_engine: The browser engine to use.

        Returns:
            A dictionary containing the structured content summary.
        """
        try:
            config = load_configuration()
            _logger.info("page_content_summarization_started", url=url, project_id=project_id)

            browser_service = BrowserAutomationService(config)
            project_store = create_project_store(config)
            llm_engine = LLMEngine(config)

            project_record = project_store.load_project(project_id)
            if not project_record:
                project_record = project_store.initialize_project(
                    url, configuration_snapshot={"analysis_type": "content-summary"}
                )

            analyzer = PageAnalyzer()
            await browser_service.initialize()
            page = await browser_service.navigate_page(project_id, url)
            page_data = await analyzer.analyze_page(page, url, project_record.paths.root)

            summarizer = ContentSummarizer(llm_engine)
            content_summary = await summarizer.summarize_page(page_data)

            _logger.info("page_content_summarization_completed", url=url)
            return {"status": "success", "summary": content_summary.model_dump()}

        except Exception as e:
            await context.error(f"Content summarization failed: {e}")
            _logger.error("page_content_summarization_failed", url=url, error=str(e))
            return {"status": "error", "error": str(e)}

    @mcp.tool()
    async def analyze_page_comprehensive(
        context: Context,
        url: str,
        project_id: str = "page-analysis",
        include_network_monitoring: bool = True,
        include_interaction_simulation: bool = True,
        include_performance_metrics: bool = True,
        save_analysis_data: bool = True,
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Perform comprehensive page analysis combining all data collection capabilities.

        Executes a complete page analysis pipeline that combines navigation, network monitoring,
        interaction simulation, DOM analysis, functionality categorization, accessibility evaluation,
        technology detection, CSS analysis, and performance metrics collection. This creates
        structured data optimized for LLM processing and human review.

        Args:
            url: Target URL to analyze comprehensively (required)
            project_id: Project identifier for organizing analysis results (default: "page-analysis")
            include_network_monitoring: Monitor network traffic during page load (default: True)
            include_interaction_simulation: Simulate user interactions to discover functionality (default: True)
            include_performance_metrics: Collect detailed performance and timing metrics (default: True)
            save_analysis_data: Save complete analysis data to project storage (default: True)
            browser_engine: Browser engine to use - "chromium", "firefox", or "webkit" (default: "chromium")

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - url: Analyzed URL
            - project_id: Project identifier used
            - analysis_summary: High-level analysis metrics and scores
            - page_classification: Page type and functionality categorization
            - technology_stack: Detected frameworks, libraries, and technologies
            - accessibility_score: Accessibility compliance and semantic structure assessment
            - performance_metrics: Load times, resource usage, and optimization opportunities
            - complexity_assessment: Technical complexity and modernization priority scoring
            - full_analysis_path: Path to complete JSON analysis data (if saved)
            - analysis_duration: Total time taken for comprehensive analysis

        Analysis Components:
            - DOM Structure: Element counts, semantic structure, interactive components
            - Page Functionality: Type classification, user workflows, business processes
            - Accessibility: ARIA usage, semantic elements, compliance issues
            - Technology Detection: JavaScript frameworks, CSS frameworks, libraries
            - CSS Analysis: Styling patterns, responsive design, framework usage
            - Performance Metrics: Navigation timing, resource analysis, optimization scores
            - Network Traffic: API endpoints, third-party services, request patterns (if enabled)
            - User Interactions: Form analysis, navigation discovery, workflow mapping (if enabled)

        Performance Considerations:
            - Analysis typically completes within 60-120 seconds per page
            - Network monitoring adds 10-20 seconds for traffic capture
            - Interaction simulation adds 20-40 seconds for workflow discovery
            - Results are cached and can be reused across LLM analysis sessions
        """
        try:
            config = load_configuration()

            _logger.info(
                "comprehensive_page_analysis_started",
                url=url,
                project_id=project_id,
                include_network_monitoring=include_network_monitoring,
                include_interaction_simulation=include_interaction_simulation,
                include_performance_metrics=include_performance_metrics,
                browser_engine=browser_engine,
            )

            # Initialize services
            browser_service = BrowserAutomationService(config)
            project_store = None
            project_root = None

            if save_analysis_data:
                project_store = create_project_store(config)
                # Get or create project
                project_metadata = project_store.get_project_metadata(project_id)
                if not project_metadata:
                    project_metadata = project_store.create_project(
                        project_id=project_id,
                        website_url=url,
                        config={"analysis_type": "comprehensive"},
                    )
                project_root = project_metadata.root_path

            # Initialize page analyzer
            analyzer = PageAnalyzer(
                include_network_analysis=include_network_monitoring,
                include_interaction_analysis=include_interaction_simulation,
                performance_budget_seconds=120.0,
            )

            async with browser_service.get_session(
                project_id=project_id,
                engine=BrowserEngine(browser_engine),
                headless=config.BROWSER_HEADLESS,
            ) as session:
                page = session.page

                # Perform comprehensive analysis
                analysis_result = await analyzer.analyze_page(
                    page=page,
                    url=url,
                    project_root=project_root,
                )

                # Save analysis data if requested
                analysis_file_path = None
                if save_analysis_data and project_root:
                    analysis_dir = project_root / "analysis" / "pages"
                    analysis_dir.mkdir(parents=True, exist_ok=True)

                    # Generate filename from URL
                    import hashlib
                    from urllib.parse import urlparse

                    parsed = urlparse(url)
                    clean_path = (
                        "".join(c for c in parsed.path if c.isalnum() or c in "-_")[:50] or "index"
                    )
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    filename = f"{clean_path}-{url_hash}.json"

                    analysis_file_path = analysis_dir / filename
                    with open(analysis_file_path, "w", encoding="utf-8") as f:
                        json.dump(analysis_result.to_dict(), f, indent=2, ensure_ascii=False)

                await context.info(f"Comprehensive analysis completed for {url}")

                # Generate analysis summary
                analysis_summary = {
                    "total_elements": analysis_result.dom_analysis.total_elements,
                    "interactive_elements": analysis_result.dom_analysis.interactive_elements,
                    "page_type": analysis_result.functionality_analysis.page_type.value,
                    "complexity_score": _calculate_complexity_score(analysis_result),
                    "modernization_priority": _determine_modernization_priority(analysis_result),
                    "accessibility_compliance": _assess_accessibility_compliance(analysis_result),
                    "performance_score": _calculate_performance_score(analysis_result),
                }

                # Technology stack summary
                technology_stack = {
                    "javascript_frameworks": [
                        fw.value for fw in analysis_result.technology_analysis.js_frameworks
                    ],
                    "javascript_libraries": analysis_result.technology_analysis.js_libraries,
                    "css_frameworks": analysis_result.technology_analysis.css_frameworks,
                    "cms_detected": analysis_result.technology_analysis.cms_detection,
                    "build_tools": analysis_result.technology_analysis.build_tools,
                }

                # Performance metrics summary
                performance_metrics = {
                    "load_time_seconds": analysis_result.performance_analysis.navigation_timing.get(
                        "total_load", 0
                    )
                    / 1000,
                    "total_resource_size_kb": analysis_result.performance_analysis.total_resource_size
                    / 1024,
                    "javascript_bundle_size_kb": analysis_result.performance_analysis.javascript_bundle_size
                    / 1024,
                    "css_bundle_size_kb": analysis_result.performance_analysis.css_bundle_size
                    / 1024,
                    "resource_count": analysis_result.performance_analysis.resource_timing.get(
                        "resource_count", 0
                    ),
                    "optimization_score": analysis_result.performance_analysis.image_optimization_score,
                }

                # Accessibility assessment
                accessibility_score = {
                    "semantic_elements": analysis_result.dom_analysis.semantic_elements,
                    "aria_usage_count": len(analysis_result.accessibility_analysis.aria_labels),
                    "heading_structure_quality": _assess_heading_structure(
                        analysis_result.accessibility_analysis
                    ),
                    "alt_text_coverage": len(analysis_result.accessibility_analysis.alt_texts),
                    "accessibility_violations": analysis_result.accessibility_analysis.accessibility_violations,
                }

                _logger.info(
                    "comprehensive_page_analysis_completed",
                    url=url,
                    project_id=project_id,
                    analysis_duration=analysis_result.analysis_duration,
                    page_type=analysis_result.functionality_analysis.page_type.value,
                    complexity_score=analysis_summary["complexity_score"],
                    performance_score=analysis_summary["performance_score"],
                    total_elements=analysis_result.dom_analysis.total_elements,
                    js_frameworks=len(analysis_result.technology_analysis.js_frameworks),
                )

                return {
                    "status": "success",
                    "url": url,
                    "project_id": project_id,
                    "analysis_summary": analysis_summary,
                    "page_classification": {
                        "page_type": analysis_result.functionality_analysis.page_type.value,
                        "primary_functions": analysis_result.functionality_analysis.primary_functions,
                        "navigation_complexity": analysis_result.functionality_analysis.navigation_complexity,
                        "content_density": analysis_result.functionality_analysis.content_density,
                        "form_complexity": analysis_result.functionality_analysis.form_complexity,
                    },
                    "technology_stack": technology_stack,
                    "accessibility_score": accessibility_score,
                    "performance_metrics": performance_metrics,
                    "complexity_assessment": {
                        "overall_score": analysis_summary["complexity_score"],
                        "modernization_priority": analysis_summary["modernization_priority"],
                        "technical_debt_indicators": _identify_technical_debt(analysis_result),
                    },
                    "full_analysis_path": str(analysis_file_path) if analysis_file_path else None,
                    "analysis_duration": analysis_result.analysis_duration,
                }

        except Exception as e:
            await context.error(f"Comprehensive page analysis failed: {e}")
            _logger.error(
                "comprehensive_page_analysis_failed",
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
    async def analyze_dom_structure(
        context: Context,
        url: str,
        focus_on_interactivity: bool = True,
        extract_form_details: bool = True,
        project_id: str = "dom-analysis",
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Analyze DOM structure focusing on element composition and interactive components.

        Performs detailed analysis of the Document Object Model structure, counting elements,
        analyzing semantic markup, and extracting detailed information about interactive
        components like forms, buttons, and input fields. Optimized for understanding
        page complexity and user interaction patterns.

        Args:
            url: Target URL to analyze DOM structure (required)
            focus_on_interactivity: Prioritize analysis of interactive elements and workflows (default: True)
            extract_form_details: Extract detailed form field information and validation patterns (default: True)
            project_id: Project identifier for session management (default: "dom-analysis")
            browser_engine: Browser engine to use - "chromium", "firefox", or "webkit" (default: "chromium")

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - url: Analyzed URL
            - dom_metrics: Element counts and structural analysis
            - semantic_structure: HTML5 semantic elements and landmarks
            - interactive_elements: Detailed analysis of user interface components
            - form_analysis: Form structures, input types, and validation patterns (if enabled)
            - accessibility_structure: Semantic roles and ARIA usage
            - complexity_indicators: Nesting depth, element distribution, structural complexity

        DOM Analysis Components:
            - Element Counting: Total elements, semantic elements, interactive components
            - Semantic Structure: HTML5 landmarks, heading hierarchy, document outline
            - Interactive Analysis: Forms, buttons, inputs, links with detailed metadata
            - Form Details: Input types, validation attributes, field organization
            - Accessibility: ARIA roles, semantic roles, assistive technology support
            - Structural Metrics: Nesting depth, element distribution, complexity scoring
        """
        try:
            config = load_configuration()

            _logger.info(
                "dom_structure_analysis_started",
                url=url,
                focus_on_interactivity=focus_on_interactivity,
                extract_form_details=extract_form_details,
                browser_engine=browser_engine,
            )

            # Initialize browser service
            browser_service = BrowserAutomationService(config)

            async with browser_service.get_session(
                project_id=project_id,
                engine=BrowserEngine(browser_engine),
                headless=config.BROWSER_HEADLESS,
            ) as session:
                page = session.page

                # Navigate to page
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")

                # Initialize analyzer and extract DOM analysis
                analyzer = PageAnalyzer(
                    include_network_analysis=False,
                    include_interaction_analysis=False,
                )

                dom_analysis = await analyzer._analyze_dom_structure(page)

                # Extract additional interactivity details if requested
                interactivity_details = {}
                if focus_on_interactivity:
                    interactivity_details = await page.evaluate("""
                        () => {
                            const result = {
                                clickable_elements: document.querySelectorAll('button, [onclick], [role="button"], input[type="submit"], input[type="button"]').length,
                                focusable_elements: document.querySelectorAll('input, select, textarea, button, a[href], [tabindex]').length,
                                hover_targets: document.querySelectorAll('[onmouseover], [onmouseenter], .hover\\:').length,
                                keyboard_shortcuts: document.querySelectorAll('[accesskey]').length,
                                dynamic_content: document.querySelectorAll('[data-*], [ng-*], [v-*], [data-react-*]').length,
                            };
                            return result;
                        }
                    """)

                # Extract detailed form information if requested
                form_details = {}
                if extract_form_details:
                    form_details = await page.evaluate("""
                        () => {
                            const forms = Array.from(document.querySelectorAll('form'));
                            return forms.map(form => {
                                const inputs = Array.from(form.querySelectorAll('input, select, textarea'));
                                return {
                                    action: form.action || '',
                                    method: form.method || 'GET',
                                    fields: inputs.map(input => ({
                                        type: input.type || input.tagName.toLowerCase(),
                                        name: input.name || '',
                                        required: input.required || false,
                                        placeholder: input.placeholder || '',
                                        pattern: input.pattern || '',
                                        minlength: input.minLength || null,
                                        maxlength: input.maxLength || null,
                                        min: input.min || '',
                                        max: input.max || '',
                                        step: input.step || '',
                                        autocomplete: input.autocomplete || '',
                                        validation_attributes: {
                                            required: input.required,
                                            pattern: !!input.pattern,
                                            min_max: !!(input.min || input.max),
                                            length_limits: !!(input.minLength || input.maxLength)
                                        }
                                    }))
                                };
                            });
                        }
                    """)

                await context.info(f"DOM structure analysis completed for {url}")

                # Calculate complexity indicators
                complexity_score = min(100, (dom_analysis.total_elements / 500) * 100)
                interactivity_ratio = (
                    dom_analysis.interactive_elements / max(dom_analysis.total_elements, 1)
                ) * 100

                result = {
                    "status": "success",
                    "url": url,
                    "dom_metrics": {
                        "total_elements": dom_analysis.total_elements,
                        "semantic_elements": dom_analysis.semantic_elements,
                        "interactive_elements": dom_analysis.interactive_elements,
                        "form_elements": dom_analysis.form_elements,
                        "link_elements": dom_analysis.link_elements,
                        "image_elements": dom_analysis.image_elements,
                        "video_elements": dom_analysis.video_elements,
                        "iframe_elements": dom_analysis.iframe_elements,
                        "script_elements": dom_analysis.script_elements,
                        "style_elements": dom_analysis.style_elements,
                    },
                    "semantic_structure": {
                        "heading_structure": dom_analysis.heading_structure,
                        "landmark_elements": dom_analysis.landmark_elements,
                        "max_nesting_depth": dom_analysis.max_nesting_depth,
                    },
                    "interactive_elements": {
                        "forms": dom_analysis.forms,
                        "buttons": dom_analysis.buttons,
                        "inputs": dom_analysis.inputs,
                        "links": dom_analysis.links[:20],  # Limit for performance
                        **interactivity_details,
                    },
                    "complexity_indicators": {
                        "structural_complexity": complexity_score,
                        "interactivity_ratio": interactivity_ratio,
                        "nesting_depth": dom_analysis.max_nesting_depth,
                        "form_complexity": len(dom_analysis.forms),
                        "modernization_needs": complexity_score > 70 and interactivity_ratio < 5,
                    },
                }

                if extract_form_details:
                    result["form_analysis"] = {
                        "total_forms": len(form_details),
                        "form_details": form_details,
                        "validation_patterns": _analyze_validation_patterns(form_details),
                    }

                _logger.info(
                    "dom_structure_analysis_completed",
                    url=url,
                    total_elements=dom_analysis.total_elements,
                    interactive_elements=dom_analysis.interactive_elements,
                    complexity_score=complexity_score,
                    forms_found=len(dom_analysis.forms),
                )

                return result

        except Exception as e:
            await context.error(f"DOM structure analysis failed: {e}")
            _logger.error(
                "dom_structure_analysis_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "url": url,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def detect_technologies(
        context: Context,
        url: str,
        deep_scan: bool = True,
        include_version_detection: bool = True,
        project_id: str = "tech-detection",
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Detect JavaScript frameworks, CSS frameworks, and web technologies used on a page.

        Performs comprehensive technology stack detection by analyzing JavaScript globals,
        DOM attributes, stylesheet references, meta tags, and script patterns. Identifies
        frameworks, libraries, build tools, CMS platforms, and analytics tools to understand
        the technical architecture and modernization requirements.

        Args:
            url: Target URL to analyze for technology stack (required)
            deep_scan: Perform deeper analysis including script content and DOM patterns (default: True)
            include_version_detection: Attempt to detect framework and library versions (default: True)
            project_id: Project identifier for session management (default: "tech-detection")
            browser_engine: Browser engine to use - "chromium", "firefox", or "webkit" (default: "chromium")

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - url: Analyzed URL
            - javascript_technologies: Detected JS frameworks, libraries, and versions
            - css_technologies: CSS frameworks, preprocessors, and methodologies
            - build_tools: Detected build tools, bundlers, and development frameworks
            - cms_platform: Content management system detection
            - analytics_tools: Analytics and tracking technologies
            - hosting_platform: Hosting and CDN detection
            - modernization_assessment: Technology age and upgrade recommendations

        Technology Detection Categories:
            - JavaScript Frameworks: React, Angular, Vue, Svelte, Alpine, etc.
            - JavaScript Libraries: jQuery, Lodash, D3, Chart.js, etc.
            - CSS Frameworks: Bootstrap, Tailwind, Bulma, Foundation, etc.
            - Build Tools: Webpack, Vite, Parcel, Rollup detection
            - CMS Platforms: WordPress, Drupal, Shopify, etc.
            - Analytics: Google Analytics, Mixpanel, Segment, etc.
            - Meta Frameworks: Next.js, Nuxt.js, SvelteKit detection
        """
        try:
            config = load_configuration()

            _logger.info(
                "technology_detection_started",
                url=url,
                deep_scan=deep_scan,
                include_version_detection=include_version_detection,
                browser_engine=browser_engine,
            )

            # Initialize browser service
            browser_service = BrowserAutomationService(config)

            async with browser_service.get_session(
                project_id=project_id,
                engine=BrowserEngine(browser_engine),
                headless=config.BROWSER_HEADLESS,
            ) as session:
                page = session.page

                # Navigate to page
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")

                # Initialize analyzer and get technology analysis
                analyzer = PageAnalyzer()
                tech_analysis = await analyzer._analyze_technology(page)

                # Perform deep scan if requested
                deep_scan_results = {}
                if deep_scan:
                    deep_scan_results = await page.evaluate("""
                        () => {
                            const result = {
                                meta_frameworks: [],
                                build_tools: [],
                                hosting_indicators: [],
                                analytics_tools: [],
                                performance_tools: [],
                                testing_tools: []
                            };

                            // Meta framework detection
                            if (window.__NEXT_DATA__ || document.querySelector('[data-nextjs-router]')) {
                                result.meta_frameworks.push('Next.js');
                            }
                            if (window.__NUXT__ || document.querySelector('#__nuxt')) {
                                result.meta_frameworks.push('Nuxt.js');
                            }
                            if (window.__sveltekit) {
                                result.meta_frameworks.push('SvelteKit');
                            }
                            if (window.Gatsby || window.___gatsby) {
                                result.meta_frameworks.push('Gatsby');
                            }

                            // Build tool indicators
                            const scripts = Array.from(document.querySelectorAll('script[src]'));
                            scripts.forEach(script => {
                                const src = script.src.toLowerCase();
                                if (src.includes('webpack')) result.build_tools.push('Webpack');
                                if (src.includes('vite')) result.build_tools.push('Vite');
                                if (src.includes('parcel')) result.build_tools.push('Parcel');
                                if (src.includes('rollup')) result.build_tools.push('Rollup');
                            });

                            // Analytics detection
                            if (window.gtag || window.ga || window.dataLayer) {
                                result.analytics_tools.push('Google Analytics');
                            }
                            if (window.mixpanel) result.analytics_tools.push('Mixpanel');
                            if (window.amplitude) result.analytics_tools.push('Amplitude');
                            if (window.heap) result.analytics_tools.push('Heap');
                            if (window.hotjar || window.hj) result.analytics_tools.push('Hotjar');

                            // Performance monitoring
                            if (window.Sentry) result.performance_tools.push('Sentry');
                            if (window.NewRelic) result.performance_tools.push('New Relic');

                            // Remove duplicates
                            Object.keys(result).forEach(key => {
                                result[key] = [...new Set(result[key])];
                            });

                            return result;
                        }
                    """)

                # Version detection if requested
                version_info = {}
                if include_version_detection:
                    version_info = await page.evaluate("""
                        () => {
                            const versions = {};

                            // React version
                            if (window.React && window.React.version) {
                                versions.React = window.React.version;
                            }

                            // Vue version
                            if (window.Vue && window.Vue.version) {
                                versions.Vue = window.Vue.version;
                            }

                            // jQuery version
                            if (window.jQuery && window.jQuery.fn && window.jQuery.fn.jquery) {
                                versions.jQuery = window.jQuery.fn.jquery;
                            }

                            // Angular version (simplified)
                            if (window.ng && window.ng.version) {
                                versions.Angular = window.ng.version.full;
                            }

                            return versions;
                        }
                    """)

                # CMS detection from meta tags and DOM patterns
                cms_detection = await page.evaluate("""
                    () => {
                        // Check meta generator
                        const generator = document.querySelector('meta[name="generator"]');
                        if (generator) {
                            const content = generator.content.toLowerCase();
                            if (content.includes('wordpress')) return 'WordPress';
                            if (content.includes('drupal')) return 'Drupal';
                            if (content.includes('joomla')) return 'Joomla';
                            if (content.includes('shopify')) return 'Shopify';
                            if (content.includes('wix')) return 'Wix';
                            if (content.includes('squarespace')) return 'Squarespace';
                        }

                        // Check for WordPress indicators
                        if (document.querySelector('link[href*="wp-content"]') ||
                            document.querySelector('script[src*="wp-content"]')) {
                            return 'WordPress';
                        }

                        // Check for other CMS indicators
                        if (document.querySelector('[data-shopify]')) return 'Shopify';
                        if (document.querySelector('.wix-page')) return 'Wix';

                        return null;
                    }
                """)

                await context.info(f"Technology detection completed for {url}")

                # Assess modernization needs
                modernization_assessment = _assess_technology_modernization(
                    tech_analysis, deep_scan_results, version_info
                )

                result = {
                    "status": "success",
                    "url": url,
                    "javascript_technologies": {
                        "frameworks": [fw.value for fw in tech_analysis.js_frameworks],
                        "libraries": tech_analysis.js_libraries,
                        "versions": version_info,
                        "meta_frameworks": deep_scan_results.get("meta_frameworks", []),
                    },
                    "css_technologies": {
                        "frameworks": tech_analysis.css_frameworks,
                        "detected_patterns": _detect_css_patterns(tech_analysis),
                    },
                    "build_tools": deep_scan_results.get("build_tools", []),
                    "cms_platform": cms_detection,
                    "analytics_tools": deep_scan_results.get("analytics_tools", []),
                    "performance_tools": deep_scan_results.get("performance_tools", []),
                    "modernization_assessment": modernization_assessment,
                }

                _logger.info(
                    "technology_detection_completed",
                    url=url,
                    js_frameworks=len(tech_analysis.js_frameworks),
                    css_frameworks=len(tech_analysis.css_frameworks),
                    cms_detected=cms_detection,
                    modernization_priority=modernization_assessment["priority"],
                )

                return result

        except Exception as e:
            await context.error(f"Technology detection failed: {e}")
            _logger.error(
                "technology_detection_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "status": "error",
                "url": url,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @mcp.tool()
    async def analyze_page_features(
        context: Context,
        url: str,
        page_content: str | None = None,
        include_step1_summary: bool = True,
        project_id: str = "feature-analysis",
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Performs Step 2 Feature Analysis on a single page to extract detailed technical specifications.

        Uses the sophisticated FeatureAnalyzer to identify interactive elements, API integrations,
        business rules, third-party services, and rebuild specifications. This provides the detailed
        technical analysis needed for comprehensive site rebuilding documentation.

        Args:
            url: Target URL to analyze for features (required)
            page_content: Optional page content JSON string. If not provided, will fetch from URL.
            include_step1_summary: Whether to perform Step 1 summary first for context (default: True)
            project_id: Project identifier for session management (default: "feature-analysis")
            browser_engine: Browser engine to use - "chromium", "firefox", or "webkit" (default: "chromium")

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - url: Analyzed URL
            - interactive_elements: List of interactive UI components with selectors and behaviors
            - functional_capabilities: Core features and services identified on the page
            - api_integrations: API endpoints and integration points discovered
            - business_rules: Business logic and validation rules found
            - third_party_integrations: External service integrations detected
            - rebuild_specifications: Technical specifications for rebuilding each component
            - confidence_score: Analysis confidence level (0.0-1.0)
            - quality_score: Analysis quality score based on completeness
            - step1_context: Content summary used for analysis context

        Feature Analysis Components:
            - Interactive Elements: Buttons, forms, inputs, navigation components with detailed metadata
            - Functional Capabilities: Core features like search, authentication, data processing
            - API Integrations: REST endpoints, GraphQL, WebSocket connections, authentication methods
            - Business Rules: Validation logic, user permissions, data constraints, error handling
            - Third-party Services: Analytics, payment, social media, CDN, external APIs
            - Rebuild Specifications: Priority-scored technical requirements for reconstruction

        Analysis Process:
            1. Optionally performs Step 1 content summarization for business context
            2. Analyzes page DOM structure for interactive elements
            3. Examines network traffic for API integrations
            4. Identifies JavaScript patterns for business logic
            5. Detects third-party service integrations
            6. Generates prioritized rebuild specifications
        """
        try:
            config = load_configuration()
            _logger.info(
                "feature_analysis_started",
                url=url,
                include_step1_summary=include_step1_summary,
                browser_engine=browser_engine,
            )

            # Initialize services
            browser_service = BrowserAutomationService(config)
            project_store = create_project_store(config)
            llm_engine = LLMEngine(config)

            # Get or create project
            project_record = project_store.load_project(project_id)
            if not project_record:
                project_record = project_store.initialize_project(
                    url, configuration_snapshot={"analysis_type": "feature-analysis"}
                )

            # Initialize browser if we need to fetch content
            page_analysis_data = None
            if not page_content:
                await browser_service.initialize()
                page = await browser_service.navigate_page(project_id, url)

                # Use PageAnalyzer to get comprehensive page data
                analyzer = PageAnalyzer()
                page_analysis_data = await analyzer.analyze_page(
                    page, url, project_record.paths.root
                )
            else:
                # Parse provided page content
                try:
                    content_data = (
                        json.loads(page_content) if isinstance(page_content, str) else page_content
                    )
                    # Extract title from content data or use URL as fallback
                    title = content_data.get("title", url.split("//")[-1].split("/")[0])
                    # Create minimal PageAnalysisData from provided content
                    from legacy_web_mcp.browser.analysis import PageAnalysisData

                    page_analysis_data = PageAnalysisData(
                        url=url,
                        title=title,
                        page_content=content_data,
                        analysis_duration=0.0,
                    )
                except Exception as e:
                    raise ValueError(f"Invalid page_content format: {e}") from e

            # Perform Step 1 summary if requested
            step1_context = None
            if include_step1_summary:
                summarizer = ContentSummarizer(llm_engine)
                step1_context = await summarizer.summarize_page(page_analysis_data)
            else:
                # Create minimal context for standalone analysis
                step1_context = ContentSummary(
                    purpose="Feature analysis without step 1 context",
                    user_context="General web page users",
                    business_logic="Standard web page functionality",
                    navigation_role="Standalone page",
                    confidence_score=0.5,
                )

            # Use FeatureAnalyzer for detailed analysis
            feature_analyzer = FeatureAnalyzer(llm_engine)
            feature_analysis = await feature_analyzer.analyze_features(
                page_analysis_data=page_analysis_data, step1_context=step1_context
            )

            _logger.info("feature_analysis_completed", url=url)

            return {
                "status": "success",
                "url": url,
                "interactive_elements": feature_analysis.interactive_elements,
                "functional_capabilities": feature_analysis.functional_capabilities,
                "api_integrations": feature_analysis.api_integrations,
                "business_rules": feature_analysis.business_rules,
                "third_party_integrations": feature_analysis.third_party_integrations,
                "rebuild_specifications": feature_analysis.rebuild_specifications,
                "confidence_score": feature_analysis.confidence_score,
                "quality_score": feature_analysis.quality_score,
                "step1_context": step1_context.model_dump() if step1_context else None,
            }

        except Exception as e:
            await context.error(f"Feature analysis failed: {e}")
            _logger.error(
                "feature_analysis_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"status": "error", "url": url, "error": str(e), "error_type": type(e).__name__}


def _calculate_complexity_score(analysis_result) -> int:
    """Calculate overall complexity score from analysis results."""
    score = 0

    # DOM complexity
    elements = analysis_result.dom_analysis.total_elements
    if elements > 500:
        score += 30
    elif elements > 200:
        score += 20
    elif elements > 100:
        score += 10

    # JavaScript complexity
    js_frameworks = len(analysis_result.technology_analysis.js_frameworks)
    if js_frameworks > 2:
        score += 25
    elif js_frameworks > 1:
        score += 15
    elif js_frameworks == 1:
        score += 10

    # Form complexity
    forms = analysis_result.dom_analysis.form_elements
    if forms > 5:
        score += 20
    elif forms > 2:
        score += 15
    elif forms > 0:
        score += 10

    # Interactive elements
    interactive = analysis_result.dom_analysis.interactive_elements
    if interactive > 50:
        score += 15
    elif interactive > 20:
        score += 10
    elif interactive > 10:
        score += 5

    # Performance impact
    load_time = analysis_result.performance_analysis.navigation_timing.get("total_load", 0)
    if load_time > 5000:  # 5 seconds
        score += 10

    return min(score, 100)


def _determine_modernization_priority(analysis_result) -> str:
    """Determine modernization priority based on analysis."""
    complexity = _calculate_complexity_score(analysis_result)
    js_frameworks = analysis_result.technology_analysis.js_frameworks
    page_type = analysis_result.functionality_analysis.page_type.value

    # High priority conditions
    if complexity > 70:
        return "high"
    if page_type in ["admin_panel", "dashboard"] and not js_frameworks:
        return "high"
    if analysis_result.dom_analysis.form_elements > 3 and not js_frameworks:
        return "high"

    # Medium priority conditions
    if complexity > 40:
        return "medium"
    if analysis_result.dom_analysis.interactive_elements > 20 and len(js_frameworks) < 2:
        return "medium"

    return "low"


def _assess_accessibility_compliance(analysis_result) -> dict[str, Any]:
    """Assess accessibility compliance from analysis results."""
    violations = []
    score = 100

    # Check for common accessibility issues
    if analysis_result.dom_analysis.image_elements > len(
        analysis_result.accessibility_analysis.alt_texts
    ):
        violations.append("missing_alt_text")
        score -= 20

    if not analysis_result.accessibility_analysis.aria_labels:
        violations.append("no_aria_labels")
        score -= 15

    if not analysis_result.accessibility_analysis.heading_hierarchy:
        violations.append("poor_heading_structure")
        score -= 15

    if (
        analysis_result.dom_analysis.form_elements > 0
        and not analysis_result.accessibility_analysis.semantic_roles
    ):
        violations.append("unlabeled_form_controls")
        score -= 25

    return {
        "compliance_score": max(score, 0),
        "violations": violations,
        "recommendations": _generate_accessibility_recommendations(violations),
    }


def _calculate_performance_score(analysis_result) -> int:
    """Calculate performance score from metrics."""
    score = 100

    # Load time impact
    load_time = analysis_result.performance_analysis.navigation_timing.get("total_load", 0) / 1000
    if load_time > 5:
        score -= 30
    elif load_time > 3:
        score -= 20
    elif load_time > 2:
        score -= 10

    # Resource size impact
    total_size = analysis_result.performance_analysis.total_resource_size / (1024 * 1024)  # MB
    if total_size > 5:
        score -= 25
    elif total_size > 3:
        score -= 15
    elif total_size > 1:
        score -= 10

    # JavaScript bundle size
    js_size = analysis_result.performance_analysis.javascript_bundle_size / (1024 * 1024)  # MB
    if js_size > 1:
        score -= 15
    elif js_size > 0.5:
        score -= 10

    return max(score, 0)


def _identify_technical_debt(analysis_result) -> List[str]:
    """Identify technical debt indicators."""
    debt_indicators = []

    # Legacy jQuery usage
    if "jquery" in analysis_result.technology_analysis.js_libraries:
        debt_indicators.append("legacy_jquery_usage")

    # No modern framework
    if not analysis_result.technology_analysis.js_frameworks:
        debt_indicators.append("no_modern_js_framework")

    # High DOM complexity
    if analysis_result.dom_analysis.total_elements > 500:
        debt_indicators.append("high_dom_complexity")

    # Poor performance
    load_time = analysis_result.performance_analysis.navigation_timing.get("total_load", 0)
    if load_time > 5000:
        debt_indicators.append("poor_performance")

    # Large JavaScript bundles
    if analysis_result.performance_analysis.javascript_bundle_size > 1024 * 1024:  # 1MB
        debt_indicators.append("large_javascript_bundles")

    return debt_indicators


def _assess_heading_structure(accessibility_analysis) -> str:
    """Assess heading structure quality."""
    headings = accessibility_analysis.heading_hierarchy
    if not headings:
        return "poor"

    # Check for logical hierarchy
    levels = [h.get("level", 0) for h in headings]
    if levels[0] != 1:  # Should start with h1
        return "poor"

    # Check for level skipping
    for i in range(1, len(levels)):
        if levels[i] - levels[i - 1] > 1:
            return "moderate"

    return "good"


def _analyze_validation_patterns(form_details) -> dict[str, Any]:
    """Analyze form validation patterns."""
    validation_summary = {
        "client_side_validation": False,
        "required_fields": 0,
        "pattern_validation": 0,
        "length_validation": 0,
        "range_validation": 0,
        "complexity_score": "simple",
    }

    total_fields = 0
    for form in form_details:
        for field in form.get("fields", []):
            total_fields += 1
            val_attrs = field.get("validation_attributes", {})

            if val_attrs.get("required"):
                validation_summary["required_fields"] += 1
            if val_attrs.get("pattern"):
                validation_summary["pattern_validation"] += 1
            if val_attrs.get("length_limits"):
                validation_summary["length_validation"] += 1
            if val_attrs.get("min_max"):
                validation_summary["range_validation"] += 1

    # Determine complexity
    validation_count = sum(
        [
            validation_summary["required_fields"],
            validation_summary["pattern_validation"],
            validation_summary["length_validation"],
            validation_summary["range_validation"],
        ]
    )

    if validation_count > total_fields * 0.7:
        validation_summary["complexity_score"] = "complex"
    elif validation_count > total_fields * 0.3:
        validation_summary["complexity_score"] = "moderate"

    validation_summary["client_side_validation"] = validation_count > 0

    return validation_summary


def _assess_technology_modernization(
    tech_analysis, deep_scan_results, version_info
) -> dict[str, Any]:
    """Assess technology modernization needs."""
    priority = "low"
    recommendations = []
    modern_score = 100

    # Check for modern frameworks
    if not tech_analysis.js_frameworks:
        priority = "high"
        modern_score -= 40
        recommendations.append("Adopt a modern JavaScript framework (React, Vue, Angular)")

    # Check for legacy jQuery
    if "jquery" in tech_analysis.js_libraries and not tech_analysis.js_frameworks:
        priority = "medium" if priority == "low" else priority
        modern_score -= 20
        recommendations.append("Migrate from jQuery to modern framework")

    # Check for build tools
    if not deep_scan_results.get("build_tools"):
        modern_score -= 15
        recommendations.append("Implement modern build tooling (Webpack, Vite, etc.)")

    # Check for outdated versions
    for tech, version in version_info.items():
        if tech == "jQuery" and version.startswith("1."):
            priority = "high"
            modern_score -= 30
            recommendations.append(f"Update {tech} from legacy version {version}")

    return {
        "priority": priority,
        "modernization_score": max(modern_score, 0),
        "recommendations": recommendations,
        "technology_age": "legacy"
        if modern_score < 50
        else "modern"
        if modern_score > 80
        else "mixed",
    }


def _detect_css_patterns(tech_analysis) -> List[str]:
    """Detect CSS patterns and methodologies."""
    patterns = []

    # Framework patterns
    frameworks = tech_analysis.css_frameworks
    if "bootstrap" in frameworks:
        patterns.append("component_based")
    if "tailwind" in frameworks:
        patterns.append("utility_first")
    if "bulma" in frameworks:
        patterns.append("flexbox_based")

    # Default patterns if no framework
    if not frameworks:
        patterns.append("custom_css")

    return patterns


def _generate_accessibility_recommendations(violations) -> List[str]:
    """Generate accessibility improvement recommendations."""
    recommendations = []

    if "missing_alt_text" in violations:
        recommendations.append("Add alt text to all images for screen reader accessibility")
    if "no_aria_labels" in violations:
        recommendations.append("Implement ARIA labels for complex UI components")
    if "poor_heading_structure" in violations:
        recommendations.append("Create logical heading hierarchy starting with h1")
    if "unlabeled_form_controls" in violations:
        recommendations.append("Add proper labels to all form controls")

    return recommendations


__all__ = ["register"]
