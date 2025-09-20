"""MCP tools for page navigation and content extraction."""
from __future__ import annotations

from typing import Any

from fastmcp import Context, FastMCP

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.browser.navigation import PageNavigationError, PageNavigator
from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.storage.projects import create_project_store


def register(mcp: FastMCP) -> None:
    """Register navigation tools with the MCP instance."""

    @mcp.tool()
    async def navigate_to_page(
        context: Context,
        url: str,
        project_id: str = "navigation-test",
        timeout: float = 30.0,
        max_retries: int = 3,
        take_screenshot: bool = True,
        wait_for_network_idle: bool = True,
        browser_engine: str = "chromium",
    ) -> dict[str, Any]:
        """Navigate to a URL and extract comprehensive page content.

        Performs full page navigation with content extraction including HTML source,
        page metadata, visible text, and optional screenshot capture. Handles timeouts,
        retries, and error scenarios gracefully while maintaining session isolation.

        Args:
            url: Target URL to navigate to (required)
            project_id: Project identifier for organizing extracted content (default: "navigation-test")
            timeout: Maximum time in seconds to wait for page load (default: 30.0)
            max_retries: Number of retry attempts for failed navigation (default: 3)
            take_screenshot: Whether to capture a full-page screenshot (default: True)
            wait_for_network_idle: Wait for network requests to complete (default: True)
            browser_engine: Browser engine to use - "chromium", "firefox", or "webkit" (default: "chromium")

        Returns:
            Dictionary containing:
            - url: Final URL after redirects
            - title: Page title
            - html_content: Complete HTML source
            - visible_text: Cleaned visible text content
            - meta_data: Meta tags and page metadata
            - screenshot_path: Path to captured screenshot (if enabled)
            - load_time: Time taken to load the page
            - status_code: HTTP response status code
            - content_size: Size of HTML content in bytes
            - session_id: Browser session identifier for potential reuse

        Raises:
            PageNavigationError: When navigation fails after retries or encounters HTTP errors
            BrowserSessionError: When browser session creation or management fails
        """
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

    @mcp.tool()
    async def extract_page_content(
        context: Context,
        project_id: str,
        capture_screenshot: bool = False,
    ) -> dict[str, Any]:
        """Extract content from an already loaded page without performing navigation.

        Extracts comprehensive page content from an existing browser session that has
        already navigated to a page. Useful for re-extracting content after page
        interactions or when you want to capture content changes without re-navigation.

        Args:
            project_id: Project identifier of existing browser session (required)
            capture_screenshot: Whether to capture a fresh screenshot (default: False)

        Returns:
            Dictionary containing:
            - success: Whether extraction was successful
            - title: Current page title
            - html_content: Complete HTML source
            - visible_text: Cleaned visible text content
            - meta_data: Meta tags and page metadata
            - url: Current page URL (may differ from original if redirected)
            - content_size: Size of HTML content in bytes
            - screenshot_path: Path to captured screenshot (if requested)
            - extracted_at: ISO timestamp of extraction
            - session_id: Browser session identifier

        Raises:
            BrowserSessionError: When no active session exists for the project_id
            RuntimeError: When page content extraction fails
        """
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