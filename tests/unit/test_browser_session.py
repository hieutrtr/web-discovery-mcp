"""Unit tests for browser session management."""
import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from legacy_web_mcp.browser import (
    BrowserEngine,
    BrowserSessionConfig,
    BrowserSessionError,
    ConcurrencyController,
    SessionLimitExceededError,
    SessionStatus,
)
from legacy_web_mcp.browser.service import BrowserAutomationService
from legacy_web_mcp.browser.session import BrowserSession, BrowserSessionFactory
from legacy_web_mcp.config.settings import MCPSettings


class TestBrowserSessionConfig:
    """Test browser session configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserSessionConfig()
        assert config.engine == BrowserEngine.CHROMIUM
        assert config.headless is True
        assert config.viewport_width == 1280
        assert config.viewport_height == 720
        assert config.timeout == 30.0
        assert config.user_agent is None
        assert config.extra_args == []

    def test_custom_config(self):
        """Test custom configuration values."""
        config = BrowserSessionConfig(
            engine=BrowserEngine.FIREFOX,
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
            timeout=60.0,
            user_agent="Custom User Agent",
            extra_args=["--no-sandbox"],
        )
        assert config.engine == BrowserEngine.FIREFOX
        assert config.headless is False
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.timeout == 60.0
        assert config.user_agent == "Custom User Agent"
        assert config.extra_args == ["--no-sandbox"]


class TestConcurrencyController:
    """Test concurrency control functionality."""

    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """Test acquiring and releasing session slots."""
        controller = ConcurrencyController(max_concurrent=2)

        assert controller.available_slots == 2
        assert controller.active_count == 0

        # Acquire first slot
        await controller.acquire("session1")
        assert controller.available_slots == 1
        assert controller.active_count == 1

        # Acquire second slot
        await controller.acquire("session2")
        assert controller.available_slots == 0
        assert controller.active_count == 2

        # Release first slot
        controller.release("session1")
        assert controller.available_slots == 1
        assert controller.active_count == 1

        # Release second slot
        controller.release("session2")
        assert controller.available_slots == 2
        assert controller.active_count == 0

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test that concurrency is properly limited."""
        controller = ConcurrencyController(max_concurrent=1)

        # Acquire the only slot
        await controller.acquire("session1")
        assert controller.available_slots == 0

        # Try to acquire another slot - should block
        acquire_task = asyncio.create_task(controller.acquire("session2"))

        # Give it a small amount of time to potentially complete
        await asyncio.sleep(0.01)
        assert not acquire_task.done()

        # Release the first slot
        controller.release("session1")

        # Now the second acquire should complete
        await acquire_task
        assert controller.active_count == 1

        controller.release("session2")


class TestBrowserSession:
    """Test browser session functionality."""

    @pytest.fixture
    def mock_browser(self):
        """Create a mock browser."""
        browser = Mock()
        browser.close = AsyncMock()
        return browser

    @pytest.fixture
    def mock_context(self):
        """Create a mock browser context."""
        context = Mock()
        context.close = AsyncMock()
        context.new_page = AsyncMock()
        context.pages = []
        return context

    @pytest.fixture
    def mock_page(self):
        """Create a mock page."""
        page = Mock()
        page.goto = AsyncMock()
        page.title = AsyncMock(return_value="Test Page")
        return page

    @pytest.fixture
    def browser_session(self, mock_browser, mock_context):
        """Create a browser session with mocked dependencies."""
        config = BrowserSessionConfig()
        session = BrowserSession("test-session", mock_browser, mock_context, config)
        return session

    @pytest.mark.asyncio
    async def test_create_page(self, browser_session, mock_context, mock_page):
        """Test page creation."""
        mock_context.new_page.return_value = mock_page

        page = await browser_session.create_page()
        assert page == mock_page
        mock_context.new_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_navigate_page(self, browser_session, mock_page):
        """Test page navigation."""
        url = "https://example.com"

        await browser_session.navigate_page(mock_page, url)

        mock_page.goto.assert_called_once_with(url, timeout=30000)
        assert browser_session.metrics.pages_loaded == 1
        assert browser_session.metrics.total_load_time > 0
        assert browser_session.metrics.last_activity is not None

    @pytest.mark.asyncio
    async def test_session_metrics(self, browser_session):
        """Test session metrics tracking."""
        metrics = browser_session.metrics

        assert metrics.session_id == "test-session"
        assert metrics.engine == BrowserEngine.CHROMIUM
        assert metrics.status == SessionStatus.ACTIVE
        assert metrics.pages_loaded == 0
        assert metrics.total_load_time == 0.0
        assert metrics.crash_count == 0

    @pytest.mark.asyncio
    async def test_close_session(self, browser_session, mock_browser, mock_context):
        """Test session cleanup."""
        await browser_session.close()

        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        assert browser_session.metrics.status == SessionStatus.CLOSED
        assert not browser_session.is_active


class TestBrowserAutomationService:
    """Test browser automation service."""

    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return MCPSettings(
            BROWSER_ENGINE="chromium",
            MAX_CONCURRENT_PAGES=2,
            BROWSER_HEADLESS=True,
        )

    @pytest.fixture
    def service(self, settings):
        """Create browser automation service."""
        return BrowserAutomationService(settings)

    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.playwright is None
        assert service.session_factory is None

        await service.initialize()

        assert service.playwright is not None
        assert service.session_factory is not None

        await service.shutdown()

    @pytest.mark.asyncio
    async def test_concurrency_limits(self, service):
        """Test that service respects concurrency limits."""
        # Fill up all slots manually
        await service.concurrency_controller.acquire("project1")
        await service.concurrency_controller.acquire("project2")

        # Next attempt should fail
        with pytest.raises(SessionLimitExceededError):
            await service.create_session("project3")

        # Clean up
        service.concurrency_controller.release("project1")
        service.concurrency_controller.release("project2")

    @pytest.mark.asyncio
    async def test_get_service_metrics(self, service):
        """Test service metrics collection."""
        await service.initialize()

        metrics = await service.get_service_metrics()

        assert "active_sessions" in metrics
        assert "max_concurrent" in metrics
        assert "available_slots" in metrics
        assert "total_pages_loaded" in metrics
        assert "total_crashes" in metrics
        assert "sessions" in metrics

        assert metrics["active_sessions"] == 0
        assert metrics["max_concurrent"] == 2
        assert metrics["available_slots"] == 2

        await service.shutdown()


@pytest.mark.asyncio
async def test_managed_browser_session():
    """Test managed browser session context manager."""
    from legacy_web_mcp.browser.session import managed_browser_session

    # This test requires actual Playwright installation
    # In CI/CD, it should be skipped if browsers aren't installed
    pytest.skip("Requires Playwright browser installation")

    config = BrowserSessionConfig(headless=True)

    async with managed_browser_session(config) as session:
        assert session.is_active
        assert session.metrics.status == SessionStatus.ACTIVE

    # Session should be closed after context exit
    assert not session.is_active