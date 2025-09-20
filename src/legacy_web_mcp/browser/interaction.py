"""Page interaction automation for discovering hidden functionality."""
from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import structlog
from playwright.async_api import ElementHandle, Locator, Page
from pydantic import BaseModel, Field

_logger = structlog.get_logger("legacy_web_mcp.browser.interaction")


class InteractionType(str, Enum):
    """Types of page interactions."""

    CLICK = "click"
    HOVER = "hover"
    FOCUS = "focus"
    FILL = "fill"
    SELECT = "select"
    SCROLL = "scroll"
    SUBMIT = "submit"
    KEYBOARD = "keyboard"


class InteractionStatus(str, Enum):
    """Status of an interaction attempt."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class ElementInfo(BaseModel):
    """Information about a discovered page element."""

    selector: str
    element_type: str
    tag_name: str
    text_content: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    is_visible: bool = True
    is_interactive: bool = True
    bounding_box: dict[str, float] | None = None


class InteractionLog(BaseModel):
    """Log entry for a page interaction."""

    interaction_id: str
    interaction_type: InteractionType
    element_info: ElementInfo
    status: InteractionStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
    data_used: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    page_changes: dict[str, Any] | None = None


class InteractionConfig(BaseModel):
    """Configuration for page interactions."""

    enable_form_interactions: bool = True
    enable_navigation_clicks: bool = True
    enable_modal_handling: bool = True
    enable_scrolling: bool = True
    max_scroll_attempts: int = 5
    scroll_delay: float = 1.0
    interaction_timeout: float = 5.0
    sample_data_enabled: bool = True
    destructive_action_keywords: list[str] = Field(default_factory=lambda: [
        "delete", "remove", "clear", "reset", "cancel", "destroy",
        "purge", "wipe", "erase", "terminate", "disable", "deactivate"
    ])
    safe_domains_only: bool = True
    max_interactions_per_page: int = 50


class PageInteractionAutomator:
    """Automates basic page interactions to discover hidden functionality."""

    def __init__(self, config: InteractionConfig):
        self.config = config
        self.interaction_logs: list[InteractionLog] = []
        self.discovered_urls: set[str] = set()
        self._interaction_counter = 0

        # Sample data for form interactions
        self.sample_data = {
            "text": ["test", "sample", "example", "demo"],
            "email": ["test@example.com", "demo@test.com", "sample@demo.org"],
            "password": ["TestPassword123!", "Demo123!", "Sample456!"],
            "name": ["Test User", "John Doe", "Sample Name"],
            "phone": ["555-0123", "123-456-7890", "(555) 123-4567"],
            "url": ["https://example.com", "https://test.com", "https://demo.org"],
            "number": ["123", "42", "100"],
            "search": ["test", "sample", "demo", "example"],
        }

    async def discover_and_interact(
        self,
        page: Page,
        base_url: str,
    ) -> dict[str, Any]:
        """Discover page elements and perform safe interactions.

        Args:
            page: Playwright page instance
            base_url: Base URL for relative link resolution

        Returns:
            Dictionary containing interaction results and discovered content
        """
        _logger.info(
            "page_interaction_discovery_started",
            base_url=base_url,
            config=self.config.model_dump(),
        )

        try:
            # Clear previous state
            self.interaction_logs.clear()
            self.discovered_urls.clear()
            self._interaction_counter = 0

            # Get initial page state
            initial_state = await self._capture_page_state(page)

            # Discover interactive elements
            interactive_elements = await self._discover_interactive_elements(page)

            _logger.info(
                "interactive_elements_discovered",
                element_count=len(interactive_elements),
                base_url=base_url,
            )

            # Perform interactions
            if self.config.enable_scrolling:
                await self._perform_scrolling_interactions(page, base_url)

            if self.config.enable_modal_handling:
                await self._handle_modals_and_popups(page, base_url)

            if self.config.enable_navigation_clicks:
                await self._explore_navigation_elements(page, base_url, interactive_elements)

            if self.config.enable_form_interactions:
                await self._interact_with_forms(page, base_url, interactive_elements)

            await self._perform_hover_and_focus_interactions(page, base_url, interactive_elements)

            # Get final page state
            final_state = await self._capture_page_state(page)

            _logger.info(
                "page_interaction_discovery_completed",
                base_url=base_url,
                total_interactions=len(self.interaction_logs),
                discovered_urls=len(self.discovered_urls),
            )

            return {
                "base_url": base_url,
                "total_interactions": len(self.interaction_logs),
                "successful_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.SUCCESS]),
                "failed_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.FAILED]),
                "skipped_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.SKIPPED]),
                "discovered_urls": list(self.discovered_urls),
                "interaction_logs": [log.model_dump() for log in self.interaction_logs],
                "initial_page_state": initial_state,
                "final_page_state": final_state,
            }

        except Exception as e:
            _logger.error(
                "page_interaction_discovery_failed",
                base_url=base_url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def _discover_interactive_elements(self, page: Page) -> list[ElementInfo]:
        """Discover all interactive elements on the page."""
        elements = []

        # Define selectors for interactive elements
        selectors = [
            "button",
            "input",
            "select",
            "textarea",
            "a[href]",
            "[onclick]",
            "[role='button']",
            "[role='link']",
            "[role='menuitem']",
            "[tabindex]",
            ".btn",
            ".button",
            ".link",
            ".menu-item",
            ".tooltip",
            "[data-testid*='button']",
            "[data-testid*='link']",
        ]

        for selector in selectors:
            try:
                playwright_elements = await page.query_selector_all(selector)
                for element in playwright_elements:
                    element_info = await self._extract_element_info(element, selector)
                    if element_info and element_info.is_interactive:
                        elements.append(element_info)
            except Exception as e:
                _logger.warning(
                    "element_discovery_partial_failure",
                    selector=selector,
                    error=str(e),
                )

        return elements

    async def _extract_element_info(self, element: ElementHandle, selector: str) -> ElementInfo | None:
        """Extract information from a page element."""
        try:
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            text_content = await element.text_content()
            
            # Clean text content
            if text_content:
                text_content = text_content.strip()
                # Skip elements with only whitespace
                if not text_content or text_content.isspace():
                    text_content = None
            
            attributes = {}

            # Get common attributes
            for attr in ["id", "class", "type", "name", "href", "role", "data-testid"]:
                value = await element.get_attribute(attr)
                if value:
                    attributes[attr] = value

            # Check visibility and interactivity
            is_visible = await element.is_visible()
            is_enabled = await element.is_enabled()

            # Get bounding box if visible
            bounding_box = None
            if is_visible:
                try:
                    box = await element.bounding_box()
                    if box:
                        bounding_box = {
                            "x": box["x"],
                            "y": box["y"],
                            "width": box["width"],
                            "height": box["height"],
                        }
                except Exception:
                    pass

            # Determine element type
            element_type = self._classify_element_type(tag_name, attributes, text_content)

            return ElementInfo(
                selector=selector,
                element_type=element_type,
                tag_name=tag_name,
                text_content=text_content,
                attributes=attributes,
                is_visible=is_visible,
                is_interactive=is_visible and is_enabled,
                bounding_box=bounding_box,
            )

        except Exception as e:
            _logger.warning(
                "element_info_extraction_failed",
                selector=selector,
                error=str(e),
            )
            return None

    def _classify_element_type(self, tag_name: str, attributes: dict[str, str], text_content: str | None) -> str:
        """Classify the type of element based on its properties."""
        if tag_name == "button":
            return "button"
        elif tag_name == "a":
            return "link"
        elif tag_name == "input":
            input_type = attributes.get("type", "text")
            return f"input_{input_type}"
        elif tag_name == "select":
            return "select"
        elif tag_name == "textarea":
            return "textarea"
        elif attributes.get("role") == "button":
            return "button"
        elif attributes.get("role") == "link":
            return "link"
        elif attributes.get("onclick"):
            return "clickable"
        elif "btn" in attributes.get("class", "").lower():
            return "button"
        elif "menu" in attributes.get("class", "").lower():
            return "menu_item"
        else:
            return "interactive"

    async def _perform_scrolling_interactions(self, page: Page, base_url: str) -> None:
        """Perform scrolling to reveal lazy-loaded content."""
        interaction_id = self._generate_interaction_id()

        try:
            # Get initial page height
            initial_height = await page.evaluate("document.body.scrollHeight")

            for attempt in range(self.config.max_scroll_attempts):
                # Scroll to different positions
                positions = ["top", "middle", "bottom"]

                for position in positions:
                    if position == "top":
                        await page.evaluate("window.scrollTo(0, 0)")
                    elif position == "middle":
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    elif position == "bottom":
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                    await page.wait_for_timeout(int(self.config.scroll_delay * 1000))

                # Check if new content was loaded
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height > initial_height:
                    initial_height = new_height
                    _logger.info(
                        "lazy_content_detected",
                        attempt=attempt + 1,
                        new_height=new_height,
                    )
                else:
                    break

            self._log_interaction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.SCROLL,
                element_info=ElementInfo(
                    selector="body",
                    element_type="page",
                    tag_name="body",
                    text_content="Page scrolling",
                ),
                status=InteractionStatus.SUCCESS,
                result={"final_height": initial_height, "attempts": attempt + 1},
            )

        except Exception as e:
            self._log_interaction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.SCROLL,
                element_info=ElementInfo(
                    selector="body",
                    element_type="page",
                    tag_name="body",
                    text_content="Page scrolling",
                ),
                status=InteractionStatus.FAILED,
                error_message=str(e),
            )

    async def _handle_modals_and_popups(self, page: Page, base_url: str) -> None:
        """Handle modals and popups that might appear."""
        interaction_id = self._generate_interaction_id()

        try:
            # Common modal/popup selectors
            modal_selectors = [
                "[role='dialog']",
                ".modal",
                ".popup",
                ".overlay",
                ".dialog",
                "[data-testid*='modal']",
                "[data-testid*='popup']",
                "[data-testid*='dialog']",
            ]

            modals_found = 0

            for selector in modal_selectors:
                try:
                    modals = await page.query_selector_all(selector)
                    for modal in modals:
                        if await modal.is_visible():
                            modals_found += 1

                            # Try to find close buttons
                            close_selectors = [
                                "button[aria-label*='close']",
                                ".close",
                                ".close-button",
                                "[data-testid*='close']",
                                "button:has-text('Close')",
                                "button:has-text('×')",
                                "button:has-text('X')",
                            ]

                            closed = False
                            for close_selector in close_selectors:
                                try:
                                    close_button = await modal.query_selector(close_selector)
                                    if close_button and await close_button.is_visible():
                                        await close_button.click(timeout=self.config.interaction_timeout * 1000)
                                        closed = True
                                        break
                                except Exception:
                                    continue

                            if not closed:
                                # Try pressing Escape key
                                await page.keyboard.press("Escape")

                except Exception as e:
                    _logger.warning(
                        "modal_handling_partial_failure",
                        selector=selector,
                        error=str(e),
                    )

            self._log_interaction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.CLICK,
                element_info=ElementInfo(
                    selector="modals",
                    element_type="modal_handler",
                    tag_name="modal",
                    text_content="Modal and popup handling",
                ),
                status=InteractionStatus.SUCCESS,
                result={"modals_found": modals_found},
            )

        except Exception as e:
            self._log_interaction(
                interaction_id=interaction_id,
                interaction_type=InteractionType.CLICK,
                element_info=ElementInfo(
                    selector="modals",
                    element_type="modal_handler",
                    tag_name="modal",
                    text_content="Modal and popup handling",
                ),
                status=InteractionStatus.FAILED,
                error_message=str(e),
            )

    async def _explore_navigation_elements(self, page: Page, base_url: str, elements: list[ElementInfo]) -> None:
        """Explore navigation menus and links to discover additional pages."""
        nav_elements = [
            elem for elem in elements
            if elem.element_type in ["link", "menu_item", "button"] and
            self._is_navigation_element(elem)
        ]

        for element in nav_elements[:10]:  # Limit to avoid excessive navigation
            if self._interaction_counter >= self.config.max_interactions_per_page:
                break

            interaction_id = self._generate_interaction_id()

            try:
                # Check if it's a safe navigation element
                if not self._is_safe_interaction(element):
                    self._log_interaction(
                        interaction_id=interaction_id,
                        interaction_type=InteractionType.CLICK,
                        element_info=element,
                        status=InteractionStatus.BLOCKED,
                        error_message="Potentially destructive action blocked",
                    )
                    continue

                # Try to interact with the element
                locator = self._create_locator(page, element)
                if await locator.is_visible():
                    if element.element_type == "link":
                        href = element.attributes.get("href")
                        if href:
                            full_url = urljoin(base_url, href)
                            self.discovered_urls.add(full_url)

                    # Perform hover to see if it reveals submenu
                    await locator.hover(timeout=self.config.interaction_timeout * 1000)
                    await page.wait_for_timeout(500)  # Brief pause to let content appear

                    self._log_interaction(
                        interaction_id=interaction_id,
                        interaction_type=InteractionType.HOVER,
                        element_info=element,
                        status=InteractionStatus.SUCCESS,
                    )

            except Exception as e:
                self._log_interaction(
                    interaction_id=interaction_id,
                    interaction_type=InteractionType.HOVER,
                    element_info=element,
                    status=InteractionStatus.FAILED,
                    error_message=str(e),
                )

    async def _interact_with_forms(self, page: Page, base_url: str, elements: list[ElementInfo]) -> None:
        """Safely interact with forms using sample data."""
        # Filter form-related elements from the discovered elements
        form_related_elements = [
            elem for elem in elements
            if elem.element_type.startswith("input_") or elem.element_type in ["select", "textarea"]
        ]

        # Group elements by form
        forms = await page.query_selector_all("form")

        for form in forms:
            if self._interaction_counter >= self.config.max_interactions_per_page:
                break

            try:
                # Check if form is safe to interact with
                form_text = await form.text_content()
                if self._contains_destructive_keywords(form_text or ""):
                    _logger.info(
                        "form_interaction_skipped",
                        reason="Contains destructive keywords",
                    )
                    continue

                # Get form elements
                form_inputs = await form.query_selector_all("input, select, textarea")

                for input_element in form_inputs[:5]:  # Limit interactions per form
                    if self._interaction_counter >= self.config.max_interactions_per_page:
                        break

                    interaction_id = self._generate_interaction_id()
                    
                    try:
                        # Check if element is actually interactive first
                        is_visible = await input_element.is_visible()
                        is_enabled = await input_element.is_enabled()
                        
                        if not is_visible or not is_enabled:
                            continue
                        
                        tag_name = await input_element.evaluate("el => el.tagName.toLowerCase()")
                        input_type = await input_element.get_attribute("type") or "text"

                        if tag_name == "input" and input_type in ["text", "email", "password", "search", "tel", "url"]:
                            sample_value = self._get_sample_data(input_type)
                            await input_element.fill(sample_value, timeout=self.config.interaction_timeout * 1000)

                            self._log_interaction(
                                interaction_id=interaction_id,
                                interaction_type=InteractionType.FILL,
                                element_info=ElementInfo(
                                    selector=f"form input[type='{input_type}']",
                                    element_type=f"input_{input_type}",
                                    tag_name=tag_name,
                                ),
                                status=InteractionStatus.SUCCESS,
                                data_used={"value": sample_value},
                            )

                        elif tag_name == "select":
                            options = await input_element.query_selector_all("option")
                            if len(options) > 1:  # Skip if only placeholder option
                                # Select the second option (skip first which is often placeholder)
                                await options[1].click()

                                self._log_interaction(
                                    interaction_id=interaction_id,
                                    interaction_type=InteractionType.SELECT,
                                    element_info=ElementInfo(
                                        selector="form select",
                                        element_type="select",
                                        tag_name=tag_name,
                                    ),
                                    status=InteractionStatus.SUCCESS,
                                )

                        elif tag_name == "textarea":
                            sample_value = self._get_sample_data("text")
                            await input_element.fill(sample_value, timeout=self.config.interaction_timeout * 1000)

                            self._log_interaction(
                                interaction_id=interaction_id,
                                interaction_type=InteractionType.FILL,
                                element_info=ElementInfo(
                                    selector="form textarea",
                                    element_type="textarea",
                                    tag_name=tag_name,
                                ),
                                status=InteractionStatus.SUCCESS,
                                data_used={"value": sample_value},
                            )

                    except Exception as e:
                        self._log_interaction(
                            interaction_id=interaction_id,
                            interaction_type=InteractionType.FILL,
                            element_info=ElementInfo(
                                selector="form input",
                                element_type="form_element",
                                tag_name=tag_name,
                            ),
                            status=InteractionStatus.FAILED,
                            error_message=str(e),
                        )

            except Exception as e:
                _logger.warning(
                    "form_interaction_error",
                    error=str(e),
                )

    async def _perform_hover_and_focus_interactions(self, page: Page, base_url: str, elements: list[ElementInfo]) -> None:
        """Perform hover and focus interactions to reveal hidden elements."""
        hover_elements = [
            elem for elem in elements
            if elem.element_type in ["button", "link", "menu_item", "interactive"] and
            elem.is_visible and elem.is_interactive
        ]

        for element in hover_elements[:15]:  # Limit hover interactions
            if self._interaction_counter >= self.config.max_interactions_per_page:
                break

            interaction_id = self._generate_interaction_id()

            try:
                locator = self._create_locator(page, element)

                # Hover over element
                await locator.hover(timeout=self.config.interaction_timeout * 1000)
                await page.wait_for_timeout(300)  # Brief pause for content to appear

                # Focus on element if it's focusable
                if element.tag_name in ["input", "select", "textarea", "button", "a"]:
                    await locator.focus(timeout=self.config.interaction_timeout * 1000)
                    await page.wait_for_timeout(200)

                self._log_interaction(
                    interaction_id=interaction_id,
                    interaction_type=InteractionType.HOVER,
                    element_info=element,
                    status=InteractionStatus.SUCCESS,
                )

            except Exception as e:
                self._log_interaction(
                    interaction_id=interaction_id,
                    interaction_type=InteractionType.HOVER,
                    element_info=element,
                    status=InteractionStatus.FAILED,
                    error_message=str(e),
                )

    def _is_navigation_element(self, element: ElementInfo) -> bool:
        """Check if element is likely a navigation element."""
        text = (element.text_content or "").lower()
        class_name = element.attributes.get("class", "").lower()

        nav_keywords = [
            "menu", "nav", "link", "home", "about", "contact", "services",
            "products", "blog", "news", "help", "support", "login", "register"
        ]

        return any(keyword in text or keyword in class_name for keyword in nav_keywords)

    def _is_safe_interaction(self, element: ElementInfo) -> bool:
        """Check if interaction with element is safe."""
        text = (element.text_content or "").lower()

        if self._contains_destructive_keywords(text):
            return False

        # Check for specific dangerous patterns
        dangerous_patterns = [
            r"delete\s+account",
            r"permanently\s+remove",
            r"close\s+account",
            r"deactivate",
        ]

        return not any(re.search(pattern, text) for pattern in dangerous_patterns)

    def _contains_destructive_keywords(self, text: str) -> bool:
        """Check if text contains destructive action keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.config.destructive_action_keywords)

    def _get_sample_data(self, input_type: str) -> str:
        """Get appropriate sample data for input type."""
        import random

        if input_type in self.sample_data:
            return random.choice(self.sample_data[input_type])
        else:
            return random.choice(self.sample_data["text"])

    def _create_locator(self, page: Page, element: ElementInfo) -> Locator:
        """Create a Playwright locator for the element."""
        # Use the most specific selector available
        if element.attributes.get("data-testid"):
            return page.locator(f"[data-testid='{element.attributes['data-testid']}']")
        elif element.attributes.get("id"):
            return page.locator(f"#{element.attributes['id']}")
        elif element.text_content and len(element.text_content.strip()) >= 3:
            # Use text-based selector for meaningful content
            text_content = element.text_content[:50].replace('\n', ' ')
            return page.locator(f"{element.tag_name}:has-text('{text_content}')")
        elif element.selector and '.' in element.selector:
            # Use original selector if it contains class information
            return page.locator(element.selector)
        else:
            # Fallback to basic tag name selector
            return page.locator(element.tag_name)

    def _generate_interaction_id(self) -> str:
        """Generate a unique interaction ID."""
        self._interaction_counter += 1
        return f"interaction_{self._interaction_counter}_{int(time.time())}"

    def _log_interaction(
        self,
        interaction_id: str,
        interaction_type: InteractionType,
        element_info: ElementInfo,
        status: InteractionStatus,
        error_message: str | None = None,
        data_used: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Log an interaction attempt."""
        log_entry = InteractionLog(
            interaction_id=interaction_id,
            interaction_type=interaction_type,
            element_info=element_info,
            status=status,
            error_message=error_message,
            data_used=data_used,
            result=result,
        )

        self.interaction_logs.append(log_entry)

        _logger.info(
            "interaction_logged",
            interaction_id=interaction_id,
            interaction_type=interaction_type.value,
            element_type=element_info.element_type,
            status=status.value,
            error=error_message,
        )

    async def _capture_page_state(self, page: Page) -> dict[str, Any]:
        """Capture current page state for comparison."""
        try:
            return {
                "url": page.url,
                "title": await page.title(),
                "html_length": len(await page.content()),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            _logger.warning(
                "page_state_capture_failed",
                error=str(e),
            )
            return {}

    def get_interaction_summary(self) -> dict[str, Any]:
        """Get summary of all interactions performed."""
        if not self.interaction_logs:
            return {
                "total_interactions": 0,
                "successful_interactions": 0,
                "failed_interactions": 0,
                "skipped_interactions": 0,
                "blocked_interactions": 0,
                "discovered_urls": 0,
                "interaction_types": {},
            }

        interaction_types = {}
        for log in self.interaction_logs:
            interaction_type = log.interaction_type.value
            if interaction_type not in interaction_types:
                interaction_types[interaction_type] = 0
            interaction_types[interaction_type] += 1

        return {
            "total_interactions": len(self.interaction_logs),
            "successful_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.SUCCESS]),
            "failed_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.FAILED]),
            "skipped_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.SKIPPED]),
            "blocked_interactions": len([log for log in self.interaction_logs if log.status == InteractionStatus.BLOCKED]),
            "discovered_urls": len(self.discovered_urls),
            "interaction_types": interaction_types,
        }

    def clear_logs(self) -> None:
        """Clear interaction logs and discovered URLs."""
        self.interaction_logs.clear()
        self.discovered_urls.clear()
        self._interaction_counter = 0


__all__ = [
    "InteractionType",
    "InteractionStatus",
    "ElementInfo",
    "InteractionLog",
    "InteractionConfig",
    "PageInteractionAutomator",
]