"""Page navigation and content extraction functionality."""
from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from legacy_web_mcp.discovery.utils import normalize_url

_logger = structlog.get_logger("legacy_web_mcp.browser.navigation")


class PageNavigationError(Exception):
    """Exception raised during page navigation."""

    def __init__(self, message: str, url: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class PageContentData:
    """Container for extracted page content and metadata."""

    def __init__(
        self,
        url: str,
        title: str,
        html_content: str,
        visible_text: str,
        meta_data: dict[str, Any],
        load_time: float,
        status_code: int,
        content_size: int,
        screenshot_path: str | None = None,
        extracted_at: datetime | None = None,
    ):
        self.url = url
        self.title = title
        self.html_content = html_content
        self.visible_text = visible_text
        self.meta_data = meta_data
        self.load_time = load_time
        self.status_code = status_code
        self.content_size = content_size
        self.screenshot_path = screenshot_path
        self.extracted_at = extracted_at or datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "title": self.title,
            "html_content": self.html_content,
            "visible_text": self.visible_text,
            "meta_data": self.meta_data,
            "load_time": self.load_time,
            "status_code": self.status_code,
            "content_size": self.content_size,
            "screenshot_path": self.screenshot_path,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
        }


class PageNavigator:
    """Handles page navigation and content extraction."""

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
        wait_for_network_idle: bool = True,
        enable_screenshots: bool = True,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.wait_for_network_idle = wait_for_network_idle
        self.enable_screenshots = enable_screenshots

    async def navigate_and_extract(
        self,
        page: Page,
        url: str,
        project_root: Path | None = None,
    ) -> PageContentData:
        """Navigate to URL and extract complete page content."""
        # Validate and normalize URL
        try:
            normalized = normalize_url(url)
            target_url = normalized.url
        except Exception as e:
            raise PageNavigationError(f"Invalid URL: {e}", url) from e

        _logger.info(
            "page_navigation_started",
            url=target_url,
            timeout=self.timeout,
            wait_for_network_idle=self.wait_for_network_idle,
        )

        # Attempt navigation with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await self._attempt_navigation(page, target_url, project_root, attempt + 1)
            except (PlaywrightTimeoutError, PageNavigationError) as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    _logger.error(
                        "page_navigation_failed_final",
                        url=target_url,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    # Preserve status code from original error if it's a PageNavigationError
                    status_code = getattr(e, 'status_code', None) if isinstance(e, PageNavigationError) else None
                    raise PageNavigationError(
                        f"Navigation failed after {self.max_retries} attempts: {e}",
                        target_url,
                        status_code,
                    ) from e

                _logger.warning(
                    "page_navigation_retry",
                    url=target_url,
                    attempt=attempt + 1,
                    error=str(e),
                    next_attempt=attempt + 2,
                )
                # Wait before retry
                await page.wait_for_timeout(1000 * (attempt + 1))

        raise PageNavigationError("Unexpected error during navigation", target_url)

    async def _attempt_navigation(
        self,
        page: Page,
        url: str,
        project_root: Path | None,
        attempt: int,
    ) -> PageContentData:
        """Single navigation attempt."""
        start_time = time.time()

        try:
            # Navigate to page
            response = await page.goto(url, timeout=self.timeout * 1000)

            if not response:
                raise PageNavigationError("No response received", url)

            status_code = response.status

            # Check for error status codes
            if status_code >= 400:
                if status_code == 404:
                    raise PageNavigationError("Page not found (404)", url, status_code)
                elif status_code == 403:
                    raise PageNavigationError("Access denied (403)", url, status_code)
                elif status_code >= 500:
                    raise PageNavigationError(f"Server error ({status_code})", url, status_code)
                else:
                    raise PageNavigationError(f"HTTP error ({status_code})", url, status_code)

            # Wait for content to load
            if self.wait_for_network_idle:
                try:
                    await page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
                except PlaywrightTimeoutError:
                    _logger.warning(
                        "network_idle_timeout",
                        url=url,
                        timeout=self.timeout,
                    )
                    # Continue anyway, just log the warning

            # Wait for DOM ready
            await page.wait_for_load_state("domcontentloaded")

            # Calculate load time
            load_time = time.time() - start_time

            # Extract content
            content_data = await self._extract_page_content(page, url, load_time, status_code)

            # Take screenshot if enabled
            if self.enable_screenshots and project_root:
                screenshot_path = await self._capture_screenshot(page, url, project_root)
                content_data.screenshot_path = screenshot_path

            _logger.info(
                "page_navigation_successful",
                url=url,
                attempt=attempt,
                load_time=load_time,
                status_code=status_code,
                content_size=content_data.content_size,
                title=content_data.title,
            )

            return content_data

        except PlaywrightTimeoutError as e:
            raise PageNavigationError(f"Navigation timeout: {e}", url) from e

    async def _extract_page_content(
        self,
        page: Page,
        url: str,
        load_time: float,
        status_code: int,
    ) -> PageContentData:
        """Extract all relevant content from the page."""
        # Get basic page information
        title = await page.title()
        html_content = await page.content()

        # Extract visible text (remove excessive whitespace)
        visible_text = await page.inner_text("body")
        visible_text = re.sub(r'\s+', ' ', visible_text).strip()

        # Extract meta tags
        meta_data = await self._extract_meta_data(page)

        # Calculate content size
        content_size = len(html_content.encode('utf-8'))

        return PageContentData(
            url=url,
            title=title,
            html_content=html_content,
            visible_text=visible_text,
            meta_data=meta_data,
            load_time=load_time,
            status_code=status_code,
            content_size=content_size,
        )

    async def _extract_meta_data(self, page: Page) -> dict[str, Any]:
        """Extract meta tags and other page metadata."""
        meta_data = {}

        try:
            # Extract meta tags
            meta_elements = await page.query_selector_all("meta")
            for meta in meta_elements:
                name = await meta.get_attribute("name")
                property_attr = await meta.get_attribute("property")
                content = await meta.get_attribute("content")

                if name and content:
                    meta_data[f"meta_{name}"] = content
                elif property_attr and content:
                    meta_data[f"property_{property_attr}"] = content

            # Extract canonical URL
            canonical = await page.query_selector("link[rel='canonical']")
            if canonical:
                canonical_href = await canonical.get_attribute("href")
                if canonical_href:
                    meta_data["canonical_url"] = canonical_href

            # Extract language
            html_element = await page.query_selector("html")
            if html_element:
                lang = await html_element.get_attribute("lang")
                if lang:
                    meta_data["language"] = lang

            # Extract viewport
            viewport = await page.query_selector("meta[name='viewport']")
            if viewport:
                viewport_content = await viewport.get_attribute("content")
                if viewport_content:
                    meta_data["viewport"] = viewport_content

        except Exception as e:
            _logger.warning(
                "meta_extraction_partial_failure",
                error=str(e),
            )

        return meta_data

    async def _capture_screenshot(
        self,
        page: Page,
        url: str,
        project_root: Path,
    ) -> str:
        """Capture screenshot and save to project directory."""
        try:
            # Create screenshots directory
            screenshots_dir = project_root / "analysis" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from URL
            parsed_url = urlparse(url)
            safe_filename = re.sub(r'[^\w\-_.]', '_', parsed_url.path or 'index')
            if safe_filename.startswith('_'):
                safe_filename = safe_filename[1:]
            if not safe_filename or safe_filename == '_':
                safe_filename = 'index'

            # Add timestamp to avoid collisions
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"{safe_filename}_{timestamp}.png"
            screenshot_path = screenshots_dir / screenshot_filename

            # Take screenshot
            await page.screenshot(
                path=str(screenshot_path),
                full_page=True,
                type="png",
            )

            _logger.info(
                "screenshot_captured",
                url=url,
                screenshot_path=str(screenshot_path),
            )

            return str(screenshot_path.relative_to(project_root))

        except Exception as e:
            _logger.error(
                "screenshot_capture_failed",
                url=url,
                error=str(e),
            )
            return None


__all__ = [
    "PageNavigationError",
    "PageContentData",
    "PageNavigator",
]