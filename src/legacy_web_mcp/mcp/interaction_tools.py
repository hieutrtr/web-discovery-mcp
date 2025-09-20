"""MCP tools for page interaction automation and discovery."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from fastmcp import FastMCP

from legacy_web_mcp.browser import BrowserAutomationService
from legacy_web_mcp.browser.interaction import InteractionConfig, PageInteractionAutomator
from legacy_web_mcp.browser.navigation import PageNavigator
from legacy_web_mcp.config.loader import load_configuration

_logger = structlog.get_logger("legacy_web_mcp.mcp.interaction_tools")

def register(mcp: FastMCP) -> None:
    """Register page interaction tools with the MCP server."""

    @mcp.tool()
    async def interact_with_page(
        url: str,
        enable_form_interactions: bool = True,
        enable_navigation_clicks: bool = True,
        enable_scrolling: bool = True,
        max_interactions: int = 50,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Perform automated, safe interactions with a webpage to discover hidden functionality.

        Intelligently explores page elements including forms, navigation menus, interactive
        components, and dynamic content. Uses sample data for form filling and implements
        safety guardrails to prevent destructive actions. Reveals functionality that's
        only visible after user interactions like hover states, modal dialogs, and
        lazy-loaded content.

        Args:
            url: Target URL to interact with (required)
            enable_form_interactions: Fill forms with safe sample data (default: True)
            enable_navigation_clicks: Explore navigation elements and menus (default: True)
            enable_scrolling: Scroll page to reveal lazy-loaded content (default: True)
            max_interactions: Maximum number of interactions to perform (default: 50)
            session_id: Reuse existing browser session ID (optional)

        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - url: Target URL
            - session_id: Browser session identifier
            - initial_page_content: Content before interactions
            - final_page_content: Content after interactions
            - interaction_results: Detailed interaction log
            - interaction_summary: Statistics and metrics
            - content_changes: Comparison of before/after content
            - discovered_functionality: New URLs, forms, and interactive elements found

        Safety Features:
            - Destructive action detection and blocking
            - Sample data for form testing without real submissions
            - Configurable interaction limits
            - Session isolation and cleanup
        """
        try:
            config = load_configuration()

            _logger.info(
                "page_interaction_started",
                url=url,
                enable_form_interactions=enable_form_interactions,
                enable_navigation_clicks=enable_navigation_clicks,
                enable_scrolling=enable_scrolling,
                max_interactions=max_interactions,
                session_id=session_id,
            )

            # Configure interaction automation
            interaction_config = InteractionConfig(
                enable_form_interactions=enable_form_interactions,
                enable_navigation_clicks=enable_navigation_clicks,
                enable_modal_handling=True,
                enable_scrolling=enable_scrolling,
                max_interactions_per_page=max_interactions,
                safe_domains_only=True,
            )

            # Initialize components
            browser_service = BrowserAutomationService(config)
            navigator = PageNavigator(
                timeout=30.0,
                max_retries=2,
                wait_for_network_idle=True,
                enable_screenshots=True,
            )
            automator = PageInteractionAutomator(interaction_config)

            async with browser_service.get_session(session_id=session_id) as session:
                page = session.page

                # First navigate to the page and get initial content
                project_root = Path.cwd()
                initial_content = await navigator.navigate_and_extract(
                    page=page,
                    url=url,
                    project_root=project_root,
                )

                # Perform automated interactions
                interaction_results = await automator.discover_and_interact(
                    page=page,
                    base_url=url,
                )

                # Get final page content after interactions
                final_content = await navigator.navigate_and_extract(
                    page=page,
                    url=url,
                    project_root=project_root,
                )

                # Get interaction summary
                interaction_summary = automator.get_interaction_summary()

                _logger.info(
                    "page_interaction_completed",
                    url=url,
                    total_interactions=interaction_summary["total_interactions"],
                    successful_interactions=interaction_summary["successful_interactions"],
                    discovered_urls=interaction_summary["discovered_urls"],
                )

                return {
                    "status": "success",
                    "url": url,
                    "session_id": session.session_id,
                    "initial_page_content": initial_content.to_dict(),
                    "final_page_content": final_content.to_dict(),
                    "interaction_results": interaction_results,
                    "interaction_summary": interaction_summary,
                    "content_changes": {
                        "html_size_before": initial_content.content_size,
                        "html_size_after": final_content.content_size,
                        "title_changed": initial_content.title != final_content.title,
                        "url_changed": initial_content.url != final_content.url,
                    },
                    "discovered_functionality": {
                        "new_urls_found": list(automator.discovered_urls),
                        "forms_discovered": len([
                            log for log in automator.interaction_logs
                            if log.interaction_type.value in ["fill", "select", "submit"]
                        ]),
                        "navigation_elements": len([
                            log for log in automator.interaction_logs
                            if log.element_info.element_type in ["link", "menu_item", "button"]
                        ]),
                        "interactive_elements": len([
                            log for log in automator.interaction_logs
                            if log.status.value == "success"
                        ]),
                    }
                }

        except Exception as e:
            _logger.error(
                "page_interaction_failed",
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
    async def explore_navigation_menu(
        url: str,
        max_depth: int = 1,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Explore navigation menus to discover additional pages and workflows.

        Focuses specifically on navigation elements like menus, nav bars, and
        internal links to map out the complete site structure.

        Args:
            url: Target URL to start navigation exploration
            max_depth: Maximum depth of navigation to explore (1 = hover only, 2 = click and explore)
            session_id: Optional browser session ID to reuse

        Returns:
            Dictionary containing discovered navigation structure and URLs
        """
        try:
            _logger.info(
                "navigation_exploration_started",
                url=url,
                max_depth=max_depth,
                session_id=session_id,
            )

            # Configure for navigation-focused exploration
            interaction_config = InteractionConfig(
                enable_form_interactions=False,  # Skip forms for navigation focus
                enable_navigation_clicks=True,
                enable_modal_handling=True,
                enable_scrolling=False,  # Skip scrolling for focused exploration
                max_interactions_per_page=30,
            )

            config = load_configuration()
            browser_service = BrowserAutomationService(config)
            automator = PageInteractionAutomator(interaction_config)

            async with browser_service.get_session(session_id=session_id) as session:
                page = session.page

                # Navigate to target page
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")

                # Perform navigation-focused interactions
                interaction_results = await automator.discover_and_interact(
                    page=page,
                    base_url=url,
                )

                # Analyze discovered navigation structure
                navigation_elements = []
                for log in automator.interaction_logs:
                    if log.element_info.element_type in ["link", "menu_item", "button"]:
                        navigation_elements.append({
                            "element_type": log.element_info.element_type,
                            "text": log.element_info.text_content,
                            "attributes": log.element_info.attributes,
                            "interaction_status": log.status.value,
                        })

                # Categorize discovered URLs
                internal_urls = []
                external_urls = []
                from urllib.parse import urlparse

                base_domain = urlparse(url).netloc

                for discovered_url in automator.discovered_urls:
                    parsed = urlparse(discovered_url)
                    if parsed.netloc == base_domain or not parsed.netloc:
                        internal_urls.append(discovered_url)
                    else:
                        external_urls.append(discovered_url)

                _logger.info(
                    "navigation_exploration_completed",
                    url=url,
                    internal_urls_found=len(internal_urls),
                    external_urls_found=len(external_urls),
                    navigation_elements_found=len(navigation_elements),
                )

                return {
                    "status": "success",
                    "url": url,
                    "session_id": session.session_id,
                    "navigation_structure": {
                        "total_navigation_elements": len(navigation_elements),
                        "navigation_elements": navigation_elements,
                        "internal_urls": internal_urls,
                        "external_urls": external_urls,
                        "menu_depth_explored": max_depth,
                    },
                    "site_mapping": {
                        "base_url": url,
                        "discovered_pages": len(internal_urls),
                        "external_dependencies": len(external_urls),
                        "navigation_coverage": len(navigation_elements),
                    },
                    "interaction_summary": automator.get_interaction_summary(),
                }

        except Exception as e:
            _logger.error(
                "navigation_exploration_failed",
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
    async def test_form_interactions(
        url: str,
        safe_mode: bool = True,
        custom_sample_data: dict[str, list[str]] | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Test form interactions to discover validation rules and workflow behaviors.

        Safely fills forms with sample data to trigger validation messages,
        discover required fields, and understand form workflows without
        causing any destructive actions.

        Args:
            url: Target URL containing forms to test
            safe_mode: Whether to use extra safety checks (recommended: True)
            custom_sample_data: Optional custom sample data to use instead of defaults
            session_id: Optional browser session ID to reuse

        Returns:
            Dictionary containing form analysis and validation discoveries
        """
        try:
            _logger.info(
                "form_interaction_testing_started",
                url=url,
                safe_mode=safe_mode,
                session_id=session_id,
            )

            # Configure for form-focused testing
            interaction_config = InteractionConfig(
                enable_form_interactions=True,
                enable_navigation_clicks=False,  # Skip navigation for form focus
                enable_modal_handling=True,
                enable_scrolling=True,  # Enable scrolling to find all forms
                max_interactions_per_page=100,  # Allow more form interactions
                safe_domains_only=safe_mode,
            )

            config = load_configuration()
            browser_service = BrowserAutomationService(config)
            automator = PageInteractionAutomator(interaction_config)

            # Update sample data if provided
            if custom_sample_data:
                automator.sample_data.update(custom_sample_data)

            async with browser_service.get_session(session_id=session_id) as session:
                page = session.page

                # Navigate to target page
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state("domcontentloaded")

                # Get initial form state
                forms = await page.query_selector_all("form")
                initial_form_count = len(forms)

                # Perform form interactions
                interaction_results = await automator.discover_and_interact(
                    page=page,
                    base_url=url,
                )

                # Analyze form interactions
                form_interactions = [
                    log for log in automator.interaction_logs
                    if log.interaction_type.value in ["fill", "select", "submit"]
                ]

                # Get validation messages that appeared
                validation_messages = []
                try:
                    # Common validation message selectors
                    validation_selectors = [
                        ".error", ".validation-error", ".field-error",
                        ".invalid-feedback", ".help-block", "[role='alert']",
                        ".form-error", ".input-error"
                    ]

                    for selector in validation_selectors:
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            if await element.is_visible():
                                text = await element.text_content()
                                if text and text.strip():
                                    validation_messages.append({
                                        "selector": selector,
                                        "message": text.strip(),
                                    })
                except Exception as e:
                    _logger.warning(
                        "validation_message_extraction_failed",
                        error=str(e),
                    )

                # Analyze form structure
                form_analysis = []
                for i, form in enumerate(forms):
                    try:
                        form_inputs = await form.query_selector_all("input, select, textarea")
                        form_data = {
                            "form_index": i,
                            "input_count": len(form_inputs),
                            "input_types": [],
                            "required_fields": 0,
                            "action": await form.get_attribute("action"),
                            "method": await form.get_attribute("method") or "GET",
                        }

                        for input_elem in form_inputs:
                            input_type = await input_elem.get_attribute("type") or "text"
                            form_data["input_types"].append(input_type)

                            if await input_elem.get_attribute("required"):
                                form_data["required_fields"] += 1

                        form_analysis.append(form_data)

                    except Exception as e:
                        _logger.warning(
                            "form_analysis_partial_failure",
                            form_index=i,
                            error=str(e),
                        )

                _logger.info(
                    "form_interaction_testing_completed",
                    url=url,
                    forms_found=initial_form_count,
                    form_interactions_performed=len(form_interactions),
                    validation_messages_found=len(validation_messages),
                )

                return {
                    "status": "success",
                    "url": url,
                    "session_id": session.session_id,
                    "form_analysis": {
                        "total_forms": initial_form_count,
                        "forms_analyzed": form_analysis,
                        "form_interactions_performed": len(form_interactions),
                        "validation_messages": validation_messages,
                    },
                    "interaction_details": {
                        "successful_fills": len([
                            log for log in form_interactions
                            if log.status.value == "success" and log.interaction_type.value == "fill"
                        ]),
                        "successful_selects": len([
                            log for log in form_interactions
                            if log.status.value == "success" and log.interaction_type.value == "select"
                        ]),
                        "blocked_interactions": len([
                            log for log in form_interactions
                            if log.status.value == "blocked"
                        ]),
                        "sample_data_used": list(automator.sample_data.keys()),
                    },
                    "validation_discovery": {
                        "validation_messages_found": len(validation_messages),
                        "client_side_validation": len(validation_messages) > 0,
                        "form_safety_checks": {
                            "safe_mode_enabled": safe_mode,
                            "destructive_actions_blocked": len([
                                log for log in automator.interaction_logs
                                if log.status.value == "blocked"
                            ]),
                        },
                    },
                    "interaction_summary": automator.get_interaction_summary(),
                }

        except Exception as e:
            _logger.error(
                "form_interaction_testing_failed",
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

__all__ = [
    "interact_with_page",
    "explore_navigation_menu",
    "test_form_interactions",
    "register",
]