import asyncio
import time

from legacy_web_mcp.browser import BrowserSessionManager
from legacy_web_mcp.config import Settings


def test_session_stub_respects_engine_and_headless():
    manager = BrowserSessionManager(Settings(max_concurrent_browsers=1, headless=False))

    async def run() -> None:
        async with manager.session("project", engine="firefox") as session:
            assert session.engine == "firefox"
            assert session.headless is False
            assert session.context.engine == "firefox"
            assert session.context.headless is False
        await manager.shutdown()

    asyncio.run(run())


def test_concurrency_limit_enforced():
    manager = BrowserSessionManager(Settings(max_concurrent_browsers=1))

    async def worker(delay: float) -> float:
        async with manager.session(f"project-{delay}"):
            start = time.perf_counter()
            await asyncio.sleep(delay)
            return time.perf_counter() - start

    async def run() -> None:
        durations = await asyncio.gather(worker(0.01), worker(0.01))
        assert manager.metrics.sessions_created == 2
        assert manager.metrics.sessions_closed == 2
        assert manager.metrics.active_sessions == 0
        assert all(duration >= 0.01 for duration in durations)
        await manager.shutdown()

    asyncio.run(run())


def test_restart_updates_metrics():
    manager = BrowserSessionManager(Settings(max_concurrent_browsers=1))

    async def run() -> None:
        async with manager.session("project") as session:
            await session.restart()
            assert manager.metrics.restarts == 1
        assert manager.metrics.sessions_closed == 2
        await manager.shutdown()

    asyncio.run(run())
