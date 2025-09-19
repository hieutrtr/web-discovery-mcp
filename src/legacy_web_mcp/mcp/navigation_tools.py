"""MCP tools for page navigation and content extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastmcp import Context, FastMCP

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.navigation import PageNavigator, PageNavigationError
from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.storage.projects import create_project_store


def register(mcp: FastMCP) -> None:
    """Register navigation tools with the MCP instance."""

    @mcp.tool(
        name="navigate_to_page",
        description="Navigate to a URL and extract complete page content including HTML, metadata, and screenshots."
    )
    async def navigate_to_page(
        context: Context,
        url: str,
        project_id: str = "navigation-test",
        timeout: float = 30.0,
        max_retries: int = 3,
        take_screenshot: bool = True,
        wait_for_network_idle: bool = True,
        browser_engine: str = "chromium",
    ) -> Dict[str, Any]:
        """Navigate to a page and extract content."""
        settings = load_configuration()
        browser_service = BrowserAutomationService(settings)
        project_store = create_project_store(settings)

        try:
            await browser_service.initialize()
            await context.info(f"Navigating to {url}")

            # Create browser session
            session = await browser_service.create_session(
                project_id=project_id,
                engine=BrowserEngine(browser_engine),
                headless=settings.BROWSER_HEADLESS,
            )

            # Create page navigator
            navigator = PageNavigator(
                timeout=timeout,
                max_retries=max_retries,
                wait_for_network_idle=wait_for_network_idle,
                enable_screenshots=take_screenshot,
            )

            # Create project directory for screenshots
            project_root = None
            if take_screenshot:
                project_metadata = project_store.get_project_metadata(project_id)
                if project_metadata:
                    project_root = project_metadata.root_path
                else:
                    # Create temporary project for navigation
                    temp_project = project_store.create_project(
                        project_id=project_id,
                        website_url=url,
                        config={}
                    )
                    project_root = temp_project.root_path

            # Create page and navigate
            page = await session.create_page()
            content_data = await navigator.navigate_and_extract(
                page=page,
                url=url,
                project_root=project_root,
            )

            await context.info(f"Successfully extracted content from {url}")

            # Convert to response format
            result = {
                "success": True,
                "url": content_data.url,
                "title": content_data.title,
                "status_code": content_data.status_code,
                "load_time": content_data.load_time,
                "content_size": content_data.content_size,
                "meta_data": content_data.meta_data,
                "visible_text_preview": content_data.visible_text[:500] + "..." if len(content_data.visible_text) > 500 else content_data.visible_text,
                "html_content_length": len(content_data.html_content),
                "screenshot_path": content_data.screenshot_path,
                "extracted_at": content_data.extracted_at.isoformat(),
                "navigation_details": {
                    "timeout": timeout,
                    "max_retries": max_retries,
                    "browser_engine": browser_engine,
                    "wait_for_network_idle": wait_for_network_idle,
                    "screenshot_enabled": take_screenshot,
                }
            }

            return result

        except PageNavigationError as e:
            await context.error(f"Navigation failed: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "status_code": getattr(e, 'status_code', None),
                "navigation_details": {
                    "timeout": timeout,
                    "max_retries": max_retries,
                    "browser_engine": browser_engine,
                }
            }

        except Exception as e:
            await context.error(f"Unexpected error during navigation: {e}")
            return {
                "success": False,
                "url": url,
                "error": f"Unexpected error: {e}",
                "navigation_details": {
                    "timeout": timeout,
                    "max_retries": max_retries,
                    "browser_engine": browser_engine,
                }
            }

        finally:
            # Always cleanup browser session
            try:
                await browser_service.close_session(project_id)
            except Exception:
                pass  # Ignore cleanup errors
            await browser_service.shutdown()

    @mcp.tool(
        name="extract_page_content",
        description="Extract content from an already loaded page without navigation."
    )
    async def extract_page_content(
        context: Context,
        project_id: str,
        capture_screenshot: bool = False,
    ) -> Dict[str, Any]:
        """Extract content from an existing page session."""
        settings = load_configuration()
        browser_service = BrowserAutomationService(settings)

        try:
            await browser_service.initialize()
            session = await browser_service.get_session(project_id)

            if not session:
                await context.error(f"No active session found for project {project_id}")
                return {
                    "success": False,
                    "error": f"No active session for project {project_id}",
                    "project_id": project_id,
                }

            # Get the current page (assuming first page)
            pages = session.context.pages
            if not pages:
                await context.error(f"No pages available in session {project_id}")
                return {
                    "success": False,
                    "error": f"No pages available in session {project_id}",
                    "project_id": project_id,
                }

            page = pages[0]
            current_url = page.url

            # Create navigator for content extraction
            navigator = PageNavigator(enable_screenshots=capture_screenshot)

            # Extract content from current page
            content_data = await navigator._extract_page_content(
                page=page,
                url=current_url,
                load_time=0.0,  # Not measured for existing page
                status_code=200,  # Assume success for existing page
            )

            # Capture screenshot if requested
            if capture_screenshot:
                project_store = create_project_store(settings)
                project_metadata = project_store.get_project_metadata(project_id)
                if project_metadata:
                    screenshot_path = await navigator._capture_screenshot(
                        page=page,
                        url=current_url,
                        project_root=project_metadata.root_path,
                    )
                    content_data.screenshot_path = screenshot_path

            await context.info(f"Extracted content from current page: {current_url}")

            return {
                "success": True,
                "url": content_data.url,
                "title": content_data.title,
                "content_size": content_data.content_size,
                "meta_data": content_data.meta_data,
                "visible_text_preview": content_data.visible_text[:500] + "..." if len(content_data.visible_text) > 500 else content_data.visible_text,
                "html_content_length": len(content_data.html_content),
                "screenshot_path": content_data.screenshot_path,
                "extracted_at": content_data.extracted_at.isoformat(),
                "project_id": project_id,
            }

        except Exception as e:
            await context.error(f"Content extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "project_id": project_id,
            }

        finally:
            await browser_service.shutdown()


__all__ = ["register"]