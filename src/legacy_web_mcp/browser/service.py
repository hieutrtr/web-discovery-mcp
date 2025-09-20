"""Browser automation service with session management and concurrency control."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog
from playwright.async_api import Page, Playwright, async_playwright

from legacy_web_mcp.config.settings import MCPSettings

from .models import (
    BrowserCrashError,
    BrowserEngine,
    BrowserSessionConfig,
    BrowserSessionError,
    ConcurrencyController,
    SessionLimitExceededError,
)
from .session import BrowserSession, BrowserSessionFactory

_logger = structlog.get_logger("legacy_web_mcp.browser.service")


class BrowserAutomationService:
    """Main service for browser automation with session management."""

    def __init__(self, settings: MCPSettings):
        self.settings = settings
        self.playwright: Playwright | None = None
        self.session_factory: BrowserSessionFactory | None = None
        self.concurrency_controller = ConcurrencyController(settings.MAX_CONCURRENT_PAGES)
        self._active_sessions: dict[str, BrowserSession] = {}
        self._recovery_attempts: dict[str, int] = {}
        self._max_recovery_attempts = 3

    async def initialize(self) -> None:
        """Initialize the browser automation service."""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            self.session_factory = BrowserSessionFactory(self.playwright)

            _logger.info(
                "browser_service_initialized",
                max_concurrent=self.settings.MAX_CONCURRENT_PAGES,
                default_engine=self.settings.BROWSER_ENGINE,
            )

    async def shutdown(self) -> None:
        """Shutdown the browser automation service."""
        if self.session_factory:
            await self.session_factory.close_all_sessions()

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            self.session_factory = None

        _logger.info("browser_service_shutdown")

    async def create_session(
        self,
        project_id: str,
        engine: BrowserEngine | None = None,
        headless: bool | None = None,
        **kwargs: Any,
    ) -> BrowserSession:
        """Create a new browser session with concurrency control."""
        if not self.session_factory:
            await self.initialize()

        # Check concurrency limits
        if self.concurrency_controller.available_slots <= 0:
            raise SessionLimitExceededError(
                f"Maximum concurrent sessions ({self.settings.MAX_CONCURRENT_PAGES}) exceeded"
            )

        # Build configuration
        config = BrowserSessionConfig(
            engine=engine or BrowserEngine(self.settings.BROWSER_ENGINE),
            headless=headless if headless is not None else True,
            **kwargs,
        )

        try:
            # Acquire concurrency slot
            await self.concurrency_controller.acquire(project_id)

            # Create session
            session = await self.session_factory.create_session(config)
            self._active_sessions[project_id] = session

            _logger.info(
                "session_created",
                project_id=project_id,
                session_id=session.session_id,
                engine=config.engine.value,
                active_sessions=self.concurrency_controller.active_count,
            )

            return session

        except Exception as e:
            # Release concurrency slot on failure
            self.concurrency_controller.release(project_id)
            _logger.error(
                "session_creation_failed",
                project_id=project_id,
                error=str(e),
            )
            raise

    async def get_session(self, project_id: str) -> BrowserSession | None:
        """Get an existing session by project ID."""
        return self._active_sessions.get(project_id)

    async def close_session(self, project_id: str) -> None:
        """Close a browser session and release resources."""
        session = self._active_sessions.get(project_id)
        if not session:
            return

        try:
            await session.close()
            _logger.info(
                "session_closed",
                project_id=project_id,
                session_id=session.session_id,
            )
        except Exception as e:
            _logger.error(
                "session_close_failed",
                project_id=project_id,
                error=str(e),
            )
        finally:
            # Always clean up tracking
            if project_id in self._active_sessions:
                del self._active_sessions[project_id]
            self.concurrency_controller.release(project_id)
            if project_id in self._recovery_attempts:
                del self._recovery_attempts[project_id]

    async def navigate_page(
        self,
        project_id: str,
        url: str,
        create_new_page: bool = True,
    ) -> Page:
        """Navigate to a URL, handling session recovery if needed."""
        session = await self._get_or_recover_session(project_id)

        try:
            if create_new_page:
                page = await session.create_page()
            else:
                # Use existing page if available
                pages = session.context.pages
                page = pages[0] if pages else await session.create_page()

            await session.navigate_page(page, url)
            return page

        except BrowserCrashError:
            # Attempt recovery
            await self._attempt_session_recovery(project_id)
            # Retry with recovered session
            session = await self._get_or_recover_session(project_id)
            page = await session.create_page()
            await session.navigate_page(page, url)
            return page

    async def _get_or_recover_session(self, project_id: str) -> BrowserSession:
        """Get session or recover if crashed."""
        session = self._active_sessions.get(project_id)

        if not session or not session.is_active:
            if session and session.metrics.status.value in ["crashed", "closed"]:
                await self._attempt_session_recovery(project_id)
                session = self._active_sessions.get(project_id)

            if not session:
                # Create new session if none exists
                session = await self.create_session(project_id)

        return session

    async def _attempt_session_recovery(self, project_id: str) -> None:
        """Attempt to recover a crashed session."""
        attempts = self._recovery_attempts.get(project_id, 0)

        if attempts >= self._max_recovery_attempts:
            _logger.error(
                "session_recovery_failed_max_attempts",
                project_id=project_id,
                attempts=attempts,
            )
            raise BrowserSessionError(
                f"Max recovery attempts ({self._max_recovery_attempts}) exceeded",
                project_id,
            )

        _logger.warning(
            "attempting_session_recovery",
            project_id=project_id,
            attempt=attempts + 1,
        )

        # Clean up old session
        await self.close_session(project_id)

        # Exponential backoff
        await asyncio.sleep(2 ** attempts)

        # Create new session
        try:
            await self.create_session(project_id)
            self._recovery_attempts[project_id] = attempts + 1

            _logger.info(
                "session_recovery_successful",
                project_id=project_id,
                attempt=attempts + 1,
            )

        except Exception as e:
            self._recovery_attempts[project_id] = attempts + 1
            _logger.error(
                "session_recovery_failed",
                project_id=project_id,
                attempt=attempts + 1,
                error=str(e),
            )
            raise

    async def get_service_metrics(self) -> dict[str, Any]:
        """Get comprehensive service metrics."""
        session_metrics = {}
        total_pages = 0
        total_crashes = 0

        for project_id, session in self._active_sessions.items():
            metrics = session.metrics
            session_metrics[project_id] = {
                "session_id": metrics.session_id,
                "engine": metrics.engine.value,
                "status": metrics.status.value,
                "pages_loaded": metrics.pages_loaded,
                "average_load_time": metrics.average_load_time,
                "session_duration": metrics.session_duration,
                "crash_count": metrics.crash_count,
                "memory_usage_mb": metrics.memory_usage_mb,
            }
            total_pages += metrics.pages_loaded
            total_crashes += metrics.crash_count

        return {
            "active_sessions": len(self._active_sessions),
            "max_concurrent": self.concurrency_controller.max_concurrent,
            "available_slots": self.concurrency_controller.available_slots,
            "total_pages_loaded": total_pages,
            "total_crashes": total_crashes,
            "sessions": session_metrics,
        }

    async def validate_browser_installation(self) -> dict[str, Any]:
        """Validate that browser engines are properly installed."""
        if not self.playwright:
            await self.initialize()

        results = {}

        for engine in BrowserEngine:
            try:
                config = BrowserSessionConfig(engine=engine, headless=True)
                browser = await self.session_factory._launch_browser(config)
                await browser.close()

                results[engine.value] = {
                    "status": "available",
                    "details": {"installed": True},
                }

            except Exception:
                executable_path = self._get_browser_executable_path(engine)
                results[engine.value] = {
                    "status": "unavailable",
                    "details": {
                        "executable": executable_path,
                        "remediation": f"Run `uv run playwright install {engine.value}` to install the browser.",
                    },
                }

        return results

    def _get_browser_executable_path(self, engine: BrowserEngine) -> str:
        """Get expected browser executable path."""
        from pathlib import Path

        home = Path.home()
        cache_dir = home / ".cache" / "ms-playwright"

        paths = {
            BrowserEngine.CHROMIUM: cache_dir / "chromium-1187" / "chrome-linux" / "chrome",
            BrowserEngine.FIREFOX: cache_dir / "firefox-1490" / "firefox" / "firefox",
            BrowserEngine.WEBKIT: cache_dir / "webkit-2203" / "pw_run.sh",
        }

        return str(paths.get(engine, "unknown"))


__all__ = ["BrowserAutomationService"]