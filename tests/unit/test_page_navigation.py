"""Unit tests for page navigation and content extraction."""
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from legacy_web_mcp.browser.navigation import PageContentData, PageNavigationError, PageNavigator


class TestPageContentData:
    """Test PageContentData model."""

    def test_content_data_creation(self):
        """Test creating PageContentData instance."""
        content_data = PageContentData(
            url="https://example.com",
            title="Example Page",
            html_content="<html><body>Test</body></html>",
            visible_text="Test",
            meta_data={"description": "Test page"},
            load_time=1.5,
            status_code=200,
            content_size=1000,
        )

        assert content_data.url == "https://example.com"
        assert content_data.title == "Example Page"
        assert content_data.status_code == 200
        assert content_data.load_time == 1.5
        assert content_data.content_size == 1000
        assert content_data.meta_data["description"] == "Test page"

    def test_content_data_to_dict(self):
        """Test converting PageContentData to dictionary."""
        content_data = PageContentData(
            url="https://example.com",
            title="Example Page",
            html_content="<html><body>Test</body></html>",
            visible_text="Test",
            meta_data={"description": "Test page"},
            load_time=1.5,
            status_code=200,
            content_size=1000,
        )

        data_dict = content_data.to_dict()

        assert data_dict["url"] == "https://example.com"
        assert data_dict["title"] == "Example Page"
        assert data_dict["status_code"] == 200
        assert data_dict["load_time"] == 1.5
        assert data_dict["content_size"] == 1000
        assert "extracted_at" in data_dict


class TestPageNavigator:
    """Test PageNavigator functionality."""

    @pytest.fixture
    def navigator(self):
        """Create a PageNavigator instance."""
        return PageNavigator(
            timeout=10.0,
            max_retries=2,
            wait_for_network_idle=True,
            enable_screenshots=True,
        )

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = Mock()
        page.goto = AsyncMock()
        page.title = AsyncMock(return_value="Test Page")
        page.content = AsyncMock(return_value="<html><body>Test content</body></html>")
        page.inner_text = AsyncMock(return_value="Test content")
        page.wait_for_load_state = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.query_selector_all = AsyncMock(return_value=[])
        page.query_selector = AsyncMock(return_value=None)
        page.screenshot = AsyncMock()
        return page

    @pytest.fixture
    def mock_response(self):
        """Create a mock HTTP response."""
        response = Mock()
        response.status = 200
        return response

    @pytest.mark.asyncio
    async def test_successful_navigation(self, navigator, mock_page, mock_response):
        """Test successful page navigation and content extraction."""
        mock_page.goto.return_value = mock_response

        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        assert content_data.url == "https://example.com"
        assert content_data.title == "Test Page"
        assert content_data.status_code == 200
        assert content_data.html_content == "<html><body>Test content</body></html>"
        assert content_data.visible_text == "Test content"
        assert content_data.load_time > 0

        # Verify page interactions
        mock_page.goto.assert_called_once()
        mock_page.wait_for_load_state.assert_called()
        mock_page.title.assert_called_once()
        mock_page.content.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_url(self, navigator, mock_page):
        """Test navigation with invalid URL."""
        with pytest.raises(PageNavigationError) as exc_info:
            await navigator.navigate_and_extract(
                page=mock_page,
                url="not-a-valid-url",
            )

        assert "Invalid URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_error_404(self, navigator, mock_page):
        """Test navigation with 404 error."""
        mock_response = Mock()
        mock_response.status = 404
        mock_page.goto.return_value = mock_response

        with pytest.raises(PageNavigationError) as exc_info:
            await navigator.navigate_and_extract(
                page=mock_page,
                url="https://example.com/not-found",
            )

        assert "Page not found (404)" in str(exc_info.value)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_http_error_403(self, navigator, mock_page):
        """Test navigation with 403 error."""
        mock_response = Mock()
        mock_response.status = 403
        mock_page.goto.return_value = mock_response

        with pytest.raises(PageNavigationError) as exc_info:
            await navigator.navigate_and_extract(
                page=mock_page,
                url="https://example.com/forbidden",
            )

        assert "Access denied (403)" in str(exc_info.value)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_navigation_timeout_with_retry(self, navigator, mock_page):
        """Test navigation timeout with retry mechanism."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        # First attempt times out, second succeeds
        mock_response = Mock()
        mock_response.status = 200
        mock_page.goto.side_effect = [
            PlaywrightTimeoutError("Navigation timeout"),
            mock_response,
        ]

        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        assert content_data.url == "https://example.com"
        assert mock_page.goto.call_count == 2

    @pytest.mark.asyncio
    async def test_navigation_max_retries_exceeded(self, navigator, mock_page):
        """Test navigation failing after max retries."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.side_effect = PlaywrightTimeoutError("Navigation timeout")

        with pytest.raises(PageNavigationError) as exc_info:
            await navigator.navigate_and_extract(
                page=mock_page,
                url="https://example.com",
            )

        assert "Navigation failed after 2 attempts" in str(exc_info.value)
        assert mock_page.goto.call_count == 2

    @pytest.mark.asyncio
    async def test_meta_data_extraction(self, navigator, mock_page, mock_response):
        """Test meta data extraction from page."""
        mock_page.goto.return_value = mock_response

        # Mock meta elements
        meta_name = Mock()
        meta_name.get_attribute = AsyncMock(side_effect=lambda attr: {
            "name": "description",
            "content": "Test description"
        }.get(attr))

        meta_property = Mock()
        meta_property.get_attribute = AsyncMock(side_effect=lambda attr: {
            "name": None,
            "property": "og:title",
            "content": "Test OG Title"
        }.get(attr))

        mock_page.query_selector_all.return_value = [meta_name, meta_property]

        # Mock HTML element for language
        html_element = Mock()
        html_element.get_attribute = AsyncMock(return_value="en")
        mock_page.query_selector.side_effect = lambda selector: {
            "link[rel='canonical']": None,
            "html": html_element,
            "meta[name='viewport']": None,
        }.get(selector)

        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        assert "meta_description" in content_data.meta_data
        assert content_data.meta_data["meta_description"] == "Test description"
        assert "property_og:title" in content_data.meta_data
        assert content_data.meta_data["property_og:title"] == "Test OG Title"
        assert content_data.meta_data["language"] == "en"

    @pytest.mark.asyncio
    async def test_screenshot_capture(self, navigator, mock_page, mock_response, tmp_path):
        """Test screenshot capture functionality."""
        mock_page.goto.return_value = mock_response

        project_root = Path(tmp_path)
        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com/test-page",
            project_root=project_root,
        )

        # Verify screenshot was attempted
        mock_page.screenshot.assert_called_once()

        # Check screenshot path format
        assert content_data.screenshot_path is not None
        assert "analysis/screenshots/" in content_data.screenshot_path
        assert content_data.screenshot_path.endswith(".png")

    @pytest.mark.asyncio
    async def test_visible_text_cleanup(self, navigator, mock_page, mock_response):
        """Test visible text whitespace cleanup."""
        mock_page.goto.return_value = mock_response
        mock_page.inner_text.return_value = "   Test   content   with   spaces   "

        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        assert content_data.visible_text == "Test content with spaces"

    @pytest.mark.asyncio
    async def test_content_size_calculation(self, navigator, mock_page, mock_response):
        """Test content size calculation."""
        mock_page.goto.return_value = mock_response
        html_content = "<html><body>Test content with unicode: ñáéíóú</body></html>"
        mock_page.content.return_value = html_content

        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        expected_size = len(html_content.encode('utf-8'))
        assert content_data.content_size == expected_size

    @pytest.mark.asyncio
    async def test_network_idle_timeout_handling(self, navigator, mock_page, mock_response):
        """Test handling of network idle timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page.goto.return_value = mock_response
        mock_page.wait_for_load_state.side_effect = [
            PlaywrightTimeoutError("Network idle timeout"),
            None,  # DOM content loaded succeeds
        ]

        # Should not raise exception, just log warning and continue
        content_data = await navigator.navigate_and_extract(
            page=mock_page,
            url="https://example.com",
        )

        assert content_data.url == "https://example.com"
        assert mock_page.wait_for_load_state.call_count == 2

    def test_navigator_configuration(self):
        """Test PageNavigator configuration options."""
        navigator = PageNavigator(
            timeout=45.0,
            max_retries=5,
            wait_for_network_idle=False,
            enable_screenshots=False,
        )

        assert navigator.timeout == 45.0
        assert navigator.max_retries == 5
        assert navigator.wait_for_network_idle is False
        assert navigator.enable_screenshots is False