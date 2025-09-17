from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

try:  # pragma: no cover - optional dependency
    from playwright.async_api import async_playwright
except ModuleNotFoundError:  # pragma: no cover
    async_playwright = None  # type: ignore

from legacy_web_mcp.config import Settings, load_settings


@dataclass
class BrowserMetrics:
    sessions_created: int = 0
    sessions_closed: int = 0
    sessions_failed: int = 0
    restarts: int = 0
    active_sessions: int = 0
    last_error: str | None = None
    last_session_duration: float | None = None


class StubBrowserContext:
    def __init__(self, engine: str, headless: bool, project_id: str) -> None:
        self.engine = engine
        self.headless = headless
        self.project_id = project_id
        self.created_at = time.perf_counter()
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class BrowserSession:
    def __init__(
        self,
        manager: "BrowserSessionManager",
        project_id: str,
        *,
        engine: str | None = None,
        headless: bool | None = None,
    ) -> None:
        self._manager = manager
        self.project_id = project_id
        self.engine = engine or manager.engine
        self.headless = manager.headless if headless is None else headless
        self.context: Any | None = None
        self._start_time: float | None = None

    async def __aenter__(self) -> "BrowserSession":
        await self._manager._semaphore.acquire()
        try:
            self.context = await self._manager._create_context(self.engine, self.headless, self.project_id)
            self._start_time = time.perf_counter()
            self._manager.metrics.sessions_created += 1
            self._manager.metrics.active_sessions += 1
            return self
        except Exception as exc:  # pragma: no cover - defensive
            self._manager.metrics.sessions_failed += 1
            self._manager.metrics.last_error = str(exc)
            self._manager._semaphore.release()
            raise

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def restart(self) -> None:
        await self.close()
        await self._manager._semaphore.acquire()
        self._manager.metrics.restarts += 1
        self.context = await self._manager._create_context(self.engine, self.headless, self.project_id)
        self._start_time = time.perf_counter()
        self._manager.metrics.sessions_created += 1
        self._manager.metrics.active_sessions += 1

    async def close(self) -> None:
        if self.context is not None:
            try:
                await self._manager._close_context(self.context)
            finally:
                self.context = None
                self._manager.metrics.sessions_closed += 1
                self._manager.metrics.active_sessions = max(
                    0, self._manager.metrics.active_sessions - 1
                )
                self._manager._semaphore.release()
                if self._start_time is not None:
                    self._manager.metrics.last_session_duration = (
                        time.perf_counter() - self._start_time
                    )


class BrowserSessionManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.engine = self.settings.default_browser_engine
        self.headless = getattr(self.settings, "headless", True)
        limit = max(1, self.settings.max_concurrent_browsers)
        self._semaphore = asyncio.Semaphore(limit)
        self.metrics = BrowserMetrics()
        self._playwright = None
        self._browser_factories: Dict[str, Callable[[bool], Awaitable[Any]]] = {}

    def session(
        self,
        project_id: str,
        *,
        engine: str | None = None,
        headless: bool | None = None,
    ) -> BrowserSession:
        return BrowserSession(self, project_id, engine=engine, headless=headless)

    async def _create_context(self, engine: str, headless: bool, project_id: str) -> Any:
        if async_playwright is None:
            return StubBrowserContext(engine, headless, project_id=project_id)

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        factory = await self._get_browser_factory(engine)
        browser = await factory(headless)
        context = await browser.new_context()
        return _PlaywrightContext(browser, context)

    async def _get_browser_factory(self, engine: str) -> Callable[[bool], Awaitable[Any]]:
        if engine in self._browser_factories:
            return self._browser_factories[engine]
        if self._playwright is None:
            raise RuntimeError("Playwright is not initialized")
        playwright = await async_playwright().start()
        self._playwright = playwright

        async def factory(headless: bool) -> Any:
            browser_launcher = getattr(playwright, engine)
            return await browser_launcher.launch(headless=headless)

        self._browser_factories[engine] = factory
        return factory

    async def _close_context(self, context: Any) -> None:
        if isinstance(context, StubBrowserContext):
            await context.close()
            return
        await context.close()

    async def shutdown(self) -> None:
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self.metrics.active_sessions = 0


class _PlaywrightContext:
    def __init__(self, browser: Any, context: Any) -> None:
        self.browser = browser
        self.context = context

    async def close(self) -> None:
        await self.context.close()
        await self.browser.close()
