"""Browser session management with Playwright."""
from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .models import (
    BrowserCrashError,
    BrowserEngine,
    BrowserLaunchError,
    BrowserSessionConfig,
    SessionMetrics,
    SessionStatus,
)

_logger = structlog.get_logger("legacy_web_mcp.browser.session")


class BrowserSession:
    """Manages a single browser session with context isolation."""

    def __init__(
        self,
        session_id: str,
        browser: Browser,
        context: BrowserContext,
        config: BrowserSessionConfig,
    ):
        self.session_id = session_id
        self.browser = browser
        self.context = context
        self.config = config
        self.metrics = SessionMetrics(
            session_id=session_id,
            engine=config.engine,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )
        self._closed = False

    async def create_page(self) -> Page:
        """Create a new page in this session's context."""
        if self._closed:
            raise BrowserCrashError("Session is closed", self.session_id)

        try:
            page = await self.context.new_page()
            _logger.debug(
                "page_created",
                session_id=self.session_id,
                page_url="about:blank",
            )
            return page
        except Exception as e:
            _logger.error(
                "page_creation_failed",
                session_id=self.session_id,
                error=str(e),
            )
            await self._handle_crash()
            raise BrowserCrashError(f"Failed to create page: {e}", self.session_id) from e

    async def navigate_page(self, page: Page, url: str) -> None:
        """Navigate a page to URL and track metrics."""
        start_time = time.time()

        try:
            await page.goto(url, timeout=self.config.timeout * 1000)
            load_time = time.time() - start_time

            # Update metrics
            self.metrics.pages_loaded += 1
            self.metrics.total_load_time += load_time
            self.metrics.last_activity = datetime.now(UTC)

            _logger.info(
                "page_navigated",
                session_id=self.session_id,
                url=url,
                load_time=load_time,
                total_pages=self.metrics.pages_loaded,
            )

        except Exception as e:
            _logger.error(
                "navigation_failed",
                session_id=self.session_id,
                url=url,
                error=str(e),
            )
            await self._handle_crash()
            raise BrowserCrashError(f"Navigation failed: {e}", self.session_id) from e

    async def get_memory_usage(self) -> float | None:
        """Get current memory usage in MB."""
        try:
            # This is a simplified implementation
            # In a real scenario, you might use browser debugging APIs
            return None  # Placeholder for now
        except Exception:
            return None

    async def _handle_crash(self) -> None:
        """Handle browser crash detection and cleanup."""
        self.metrics.status = SessionStatus.CRASHED
        self.metrics.crash_count += 1
        self._closed = True

        _logger.error(
            "browser_session_crashed",
            session_id=self.session_id,
            crash_count=self.metrics.crash_count,
        )

    async def close(self) -> None:
        """Close the browser session and cleanup resources."""
        if self._closed:
            return

        self.metrics.status = SessionStatus.CLOSING

        try:
            await self.context.close()
            await self.browser.close()
            self.metrics.status = SessionStatus.CLOSED
            self._closed = True

            _logger.info(
                "session_closed",
                session_id=self.session_id,
                pages_loaded=self.metrics.pages_loaded,
                session_duration=self.metrics.session_duration,
            )

        except Exception as e:
            _logger.error(
                "session_close_failed",
                session_id=self.session_id,
                error=str(e),
            )
            self._closed = True
            self.metrics.status = SessionStatus.CRASHED

    @property
    def is_active(self) -> bool:
        """Check if session is still active."""
        return not self._closed and self.metrics.status == SessionStatus.ACTIVE


class BrowserSessionFactory:
    """Factory for creating and managing browser sessions."""

    def __init__(self, playwright: Playwright):
        self.playwright = playwright
        self._active_sessions: dict[str, BrowserSession] = {}

    async def create_session(self, config: BrowserSessionConfig) -> BrowserSession:
        """Create a new browser session with the given configuration."""
        session_id = str(uuid.uuid4())

        _logger.info(
            "creating_browser_session",
            session_id=session_id,
            engine=config.engine.value,
            headless=config.headless,
        )

        try:
            # Launch browser based on engine
            browser = await self._launch_browser(config)

            # Create isolated context
            context = await browser.new_context(
                viewport={"width": config.viewport_width, "height": config.viewport_height},
                user_agent=config.user_agent,
            )

            session = BrowserSession(session_id, browser, context, config)
            self._active_sessions[session_id] = session

            _logger.info(
                "browser_session_created",
                session_id=session_id,
                engine=config.engine.value,
            )

            return session

        except Exception as e:
            _logger.error(
                "browser_session_creation_failed",
                session_id=session_id,
                engine=config.engine.value,
                error=str(e),
            )
            raise BrowserLaunchError(f"Failed to create session: {e}", session_id) from e

    async def _launch_browser(self, config: BrowserSessionConfig) -> Browser:
        """Launch browser based on configuration."""
        launch_options = {
            "headless": config.headless,
            "args": config.extra_args,
        }

        if config.engine == BrowserEngine.CHROMIUM:
            return await self.playwright.chromium.launch(**launch_options)
        elif config.engine == BrowserEngine.FIREFOX:
            return await self.playwright.firefox.launch(**launch_options)
        elif config.engine == BrowserEngine.WEBKIT:
            return await self.playwright.webkit.launch(**launch_options)
        else:
            raise BrowserLaunchError(f"Unsupported browser engine: {config.engine}")

    async def get_session(self, session_id: str) -> BrowserSession | None:
        """Get an active session by ID."""
        return self._active_sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Close and remove a session."""
        session = self._active_sessions.get(session_id)
        if session:
            await session.close()
            del self._active_sessions[session_id]

    async def close_all_sessions(self) -> None:
        """Close all active sessions."""
        for session_id in list(self._active_sessions.keys()):
            await self.close_session(session_id)

    def get_metrics(self) -> dict[str, SessionMetrics]:
        """Get metrics for all active sessions."""
        return {
            session_id: session.metrics
            for session_id, session in self._active_sessions.items()
        }

    @property
    def active_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._active_sessions)


@asynccontextmanager
async def managed_browser_session(
    config: BrowserSessionConfig,
) -> AsyncGenerator[BrowserSession, None]:
    """Context manager for automatic browser session lifecycle management."""
    async with async_playwright() as playwright:
        factory = BrowserSessionFactory(playwright)
        session = await factory.create_session(config)

        try:
            yield session
        finally:
            await session.close()


__all__ = [
    "BrowserSession",
    "BrowserSessionFactory",
    "managed_browser_session",
]