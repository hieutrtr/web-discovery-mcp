"""MCP tools for browser session management."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from legacy_web_mcp.browser import BrowserAutomationService, BrowserEngine
from legacy_web_mcp.config.loader import load_configuration


def register(mcp: FastMCP) -> None:
    """Register browser management tools with the MCP instance."""

    @mcp.tool()
    async def validate_browser_dependencies(context: Context) -> dict[str, object]:
        """Validate Playwright browser installations and report detailed status.

        Checks the installation status and readiness of all supported browser engines
        (Chromium, Firefox, WebKit) for the current environment. Provides detailed
        information about browser versions, executable paths, and any missing components.

        Returns:
            Dictionary containing:
            - browsers: Array of browser engine status reports
            - Each browser report includes:
              - engine: Browser engine name ("chromium", "firefox", "webkit")
              - installed: Whether the browser is properly installed
              - version: Browser version if available
              - executable_path: Path to browser executable
              - error: Error message if installation issues detected

        Use Case:
            Run this before other browser operations to ensure proper environment setup.
            Helps diagnose browser installation issues and compatibility problems.
        """
        settings = load_configuration()
        service = BrowserAutomationService(settings)

        try:
            results = await service.validate_browser_installation()
            await context.info("Browser dependency validation completed")
            return {"browsers": list(results.values())}
        finally:
            await service.shutdown()

    @mcp.tool()
    async def get_browser_metrics(context: Context) -> dict[str, object]:
        """Retrieve comprehensive performance metrics for active browser sessions.

        Collects real-time metrics about browser session management, resource usage,
        and performance statistics across all active sessions and supported engines.

        Returns:
            Dictionary containing:
            - active_sessions: Number of currently active browser sessions
            - total_sessions_created: Lifetime count of sessions created
            - sessions_by_engine: Breakdown of sessions per browser engine
            - average_session_duration: Average session lifetime in seconds
            - memory_usage: Estimated memory consumption by browser processes
            - crash_count: Number of browser crashes detected
            - concurrent_session_limit: Maximum allowed concurrent sessions
            - uptime: Service uptime in seconds

        Use Case:
            Monitor browser service health and performance for optimization
            and troubleshooting. Useful for identifying resource leaks or limits.
        """
        settings = load_configuration()
        service = BrowserAutomationService(settings)

        try:
            await service.initialize()
            metrics = await service.get_service_metrics()
            await context.info(f"Retrieved metrics for {metrics['active_sessions']} sessions")
            return metrics
        finally:
            await service.shutdown()

    @mcp.tool(
        name="test_browser_session",
        description="Test browser session creation and basic navigation."
    )
    async def test_browser_session(
        context: Context,
        url: str = "https://example.com",
        engine: str = "chromium",
    ) -> dict[str, object]:
        """Test browser session functionality."""
        settings = load_configuration()
        service = BrowserAutomationService(settings)

        try:
            await service.initialize()
            await context.info(f"Testing browser session with {engine} engine")

            # Create session
            session = await service.create_session(
                project_id="test-session",
                engine=BrowserEngine(engine),
                headless=True,
            )

            # Test navigation
            page = await service.navigate_page("test-session", url)
            title = await page.title()

            # Get metrics
            metrics = session.metrics

            await context.info(f"Successfully navigated to {url}")

            return {
                "success": True,
                "url": url,
                "title": title,
                "engine": engine,
                "session_id": session.session_id,
                "metrics": {
                    "pages_loaded": metrics.pages_loaded,
                    "total_load_time": metrics.total_load_time,
                    "average_load_time": metrics.average_load_time,
                    "session_duration": metrics.session_duration,
                },
            }

        except Exception as e:
            await context.error(f"Browser session test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url,
                "engine": engine,
            }
        finally:
            await service.close_session("test-session")
            await service.shutdown()


__all__ = ["register"]