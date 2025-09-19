"""Unit tests for page interaction automation functionality."""
from unittest.mock import AsyncMock, Mock, patch

import pytest

from legacy_web_mcp.browser.interaction import (
    ElementInfo,
    InteractionConfig,
    InteractionLog,
    InteractionStatus,
    InteractionType,
    PageInteractionAutomator,
)


class TestElementInfo:
    """Test ElementInfo model."""

    def test_element_info_creation(self):
        """Test creating ElementInfo instance."""
        element = ElementInfo(
            selector="button.submit",
            element_type="button",
            tag_name="button",
            text_content="Submit Form",
            attributes={"class": "submit", "type": "submit"},
            is_visible=True,
            is_interactive=True,
            bounding_box={"x": 100, "y": 200, "width": 120, "height": 40},
        )

        assert element.selector == "button.submit"
        assert element.element_type == "button"
        assert element.tag_name == "button"
        assert element.text_content == "Submit Form"
        assert element.attributes["class"] == "submit"
        assert element.is_visible is True
        assert element.is_interactive is True
        assert element.bounding_box["width"] == 120


class TestInteractionLog:
    """Test InteractionLog model."""

    def test_interaction_log_creation(self):
        """Test creating InteractionLog instance."""
        element = ElementInfo(
            selector="input[name='email']",
            element_type="input_email",
            tag_name="input",
        )

        log = InteractionLog(
            interaction_id="test_001",
            interaction_type=InteractionType.FILL,
            element_info=element,
            status=InteractionStatus.SUCCESS,
            data_used={"value": "test@example.com"},
        )

        assert log.interaction_id == "test_001"
        assert log.interaction_type == InteractionType.FILL
        assert log.status == InteractionStatus.SUCCESS
        assert log.data_used["value"] == "test@example.com"
        assert log.timestamp is not None


class TestInteractionConfig:
    """Test InteractionConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = InteractionConfig()

        assert config.enable_form_interactions is True
        assert config.enable_navigation_clicks is True
        assert config.enable_modal_handling is True
        assert config.enable_scrolling is True
        assert config.max_scroll_attempts == 5
        assert config.interaction_timeout == 5.0
        assert config.sample_data_enabled is True
        assert "delete" in config.destructive_action_keywords
        assert config.safe_domains_only is True
        assert config.max_interactions_per_page == 50

    def test_custom_config(self):
        """Test custom configuration values."""
        config = InteractionConfig(
            enable_form_interactions=False,
            max_scroll_attempts=3,
            interaction_timeout=10.0,
            destructive_action_keywords=["custom_dangerous"],
            max_interactions_per_page=25,
        )

        assert config.enable_form_interactions is False
        assert config.max_scroll_attempts == 3
        assert config.interaction_timeout == 10.0
        assert config.destructive_action_keywords == ["custom_dangerous"]
        assert config.max_interactions_per_page == 25


class TestPageInteractionAutomator:
    """Test PageInteractionAutomator functionality."""

    @pytest.fixture
    def config(self):
        """Create an InteractionConfig instance."""
        return InteractionConfig(
            enable_form_interactions=True,
            enable_navigation_clicks=True,
            enable_scrolling=True,
            max_interactions_per_page=20,
        )

    @pytest.fixture
    def automator(self, config):
        """Create a PageInteractionAutomator instance."""
        return PageInteractionAutomator(config)

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = Mock()
        page.query_selector_all = AsyncMock()
        page.query_selector = AsyncMock()
        page.evaluate = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.keyboard = Mock()
        page.keyboard.press = AsyncMock()
        page.title = AsyncMock(return_value="Test Page")
        page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        page.url = "https://example.com/test"
        return page

    @pytest.fixture
    def mock_element(self):
        """Create a mock Playwright element."""
        element = Mock()
        element.evaluate = AsyncMock()
        element.text_content = AsyncMock(return_value="Click Me")
        element.get_attribute = AsyncMock()
        element.is_visible = AsyncMock(return_value=True)
        element.is_enabled = AsyncMock(return_value=True)
        element.bounding_box = AsyncMock(return_value={"x": 10, "y": 20, "width": 100, "height": 30})
        element.hover = AsyncMock()
        element.click = AsyncMock()
        element.fill = AsyncMock()
        element.focus = AsyncMock()
        return element

    @pytest.mark.asyncio
    async def test_discover_interactive_elements(self, automator, mock_page, mock_element):
        """Test discovery of interactive elements."""
        mock_element.evaluate.return_value = "button"
        mock_element.get_attribute.side_effect = lambda attr: {
            "id": "test-button",
            "class": "btn primary",
            "type": "button",
        }.get(attr)

        mock_page.query_selector_all.return_value = [mock_element]

        elements = await automator._discover_interactive_elements(mock_page)

        assert len(elements) > 0
        element = elements[0]
        assert element.tag_name == "button"
        assert element.element_type == "button"
        assert element.is_visible is True
        assert element.is_interactive is True

    @pytest.mark.asyncio
    async def test_element_classification(self, automator):
        """Test element type classification."""
        # Test button classification
        button_type = automator._classify_element_type(
            "button", {"type": "submit"}, "Submit"
        )
        assert button_type == "button"

        # Test link classification
        link_type = automator._classify_element_type(
            "a", {"href": "#"}, "Link"
        )
        assert link_type == "link"

        # Test input classification
        input_type = automator._classify_element_type(
            "input", {"type": "email"}, None
        )
        assert input_type == "input_email"

        # Test role-based classification
        role_button_type = automator._classify_element_type(
            "div", {"role": "button"}, "Custom Button"
        )
        assert role_button_type == "button"

    def test_navigation_element_detection(self, automator):
        """Test navigation element detection."""
        # Test menu element
        menu_element = ElementInfo(
            selector=".nav-item",
            element_type="link",
            tag_name="a",
            text_content="Home",
            attributes={"class": "nav-link"},
        )
        assert automator._is_navigation_element(menu_element) is True

        # Test regular button (not navigation)
        button_element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            text_content="Calculate",
            attributes={"type": "button"},
        )
        assert automator._is_navigation_element(button_element) is False

    def test_safe_interaction_detection(self, automator):
        """Test safe interaction detection."""
        # Test safe element
        safe_element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            text_content="Submit Form",
        )
        assert automator._is_safe_interaction(safe_element) is True

        # Test dangerous element
        dangerous_element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            text_content="Delete Account",
        )
        assert automator._is_safe_interaction(dangerous_element) is False

    def test_destructive_keyword_detection(self, automator):
        """Test destructive keyword detection."""
        assert automator._contains_destructive_keywords("Delete all data") is True
        assert automator._contains_destructive_keywords("Submit form") is False
        assert automator._contains_destructive_keywords("Reset password") is True
        assert automator._contains_destructive_keywords("Save changes") is False

    def test_sample_data_retrieval(self, automator):
        """Test sample data retrieval for different input types."""
        email_data = automator._get_sample_data("email")
        assert "@" in email_data
        assert email_data in automator.sample_data["email"]

        text_data = automator._get_sample_data("text")
        assert text_data in automator.sample_data["text"]

        # Test fallback for unknown type
        unknown_data = automator._get_sample_data("unknown_type")
        assert unknown_data in automator.sample_data["text"]

    @pytest.mark.asyncio
    async def test_scrolling_interactions(self, automator, mock_page):
        """Test page scrolling functionality."""
        # Set up multiple calls: initial height, after each scroll position, check for new content
        mock_page.evaluate.side_effect = [1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000]

        await automator._perform_scrolling_interactions(mock_page, "https://example.com")

        # Verify scrolling was attempted
        assert mock_page.evaluate.call_count >= 4
        assert mock_page.wait_for_timeout.called

        # Verify interaction was logged
        assert len(automator.interaction_logs) == 1
        log = automator.interaction_logs[0]
        assert log.interaction_type == InteractionType.SCROLL
        assert log.status == InteractionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_modal_handling(self, automator, mock_page):
        """Test modal and popup handling."""
        mock_modal = Mock()
        mock_modal.is_visible = AsyncMock(return_value=True)
        mock_modal.query_selector = AsyncMock(return_value=None)

        mock_page.query_selector_all.return_value = [mock_modal]

        await automator._handle_modals_and_popups(mock_page, "https://example.com")

        # Verify modal detection was attempted
        mock_page.query_selector_all.assert_called()
        mock_page.keyboard.press.assert_called_with("Escape")

        # Verify interaction was logged
        assert len(automator.interaction_logs) == 1
        log = automator.interaction_logs[0]
        assert log.interaction_type == InteractionType.CLICK
        assert log.element_info.element_type == "modal_handler"

    @pytest.mark.asyncio
    async def test_form_interaction_safety(self, automator, mock_page):
        """Test safe form interaction with destructive action blocking."""
        # Mock form with destructive content
        mock_form = Mock()
        mock_form.text_content = AsyncMock(return_value="Delete user account permanently")
        mock_form.query_selector_all = AsyncMock(return_value=[])

        mock_page.query_selector_all.return_value = [mock_form]

        elements = []  # Empty elements list for this test

        await automator._interact_with_forms(mock_page, "https://example.com", elements)

        # Verify no interactions were performed due to destructive keywords
        form_interactions = [
            log for log in automator.interaction_logs
            if log.interaction_type in [InteractionType.FILL, InteractionType.SELECT]
        ]
        assert len(form_interactions) == 0

    @pytest.mark.asyncio
    async def test_form_input_filling(self, automator, mock_page):
        """Test form input filling with sample data."""
        # Mock safe form
        mock_form = Mock()
        mock_form.text_content = AsyncMock(return_value="Contact form")

        # Mock input element
        mock_input = Mock()
        mock_input.evaluate = AsyncMock(return_value="input")
        mock_input.get_attribute = AsyncMock(side_effect=lambda attr: {
            "type": "email",
            "name": "email",
        }.get(attr))
        mock_input.fill = AsyncMock()

        mock_form.query_selector_all = AsyncMock(return_value=[mock_input])
        mock_page.query_selector_all.return_value = [mock_form]

        elements = []  # Empty elements list for this test

        await automator._interact_with_forms(mock_page, "https://example.com", elements)

        # Verify input was filled
        mock_input.fill.assert_called()

        # Verify interaction was logged
        fill_interactions = [
            log for log in automator.interaction_logs
            if log.interaction_type == InteractionType.FILL
        ]
        assert len(fill_interactions) == 1
        assert fill_interactions[0].status == InteractionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_hover_and_focus_interactions(self, automator, mock_page):
        """Test hover and focus interactions."""
        # Create test elements
        elements = [
            ElementInfo(
                selector="button",
                element_type="button",
                tag_name="button",
                text_content="Hover Me",
                is_visible=True,
                is_interactive=True,
            ),
            ElementInfo(
                selector="a",
                element_type="link",
                tag_name="a",
                text_content="Focus Me",
                is_visible=True,
                is_interactive=True,
            ),
        ]

        # Mock locator
        mock_locator = Mock()
        mock_locator.hover = AsyncMock()
        mock_locator.focus = AsyncMock()

        with patch.object(automator, '_create_locator', return_value=mock_locator):
            await automator._perform_hover_and_focus_interactions(
                mock_page, "https://example.com", elements
            )

        # Verify hover interactions were performed
        assert mock_locator.hover.call_count == 2
        assert mock_locator.focus.call_count == 2

        # Verify interactions were logged
        hover_interactions = [
            log for log in automator.interaction_logs
            if log.interaction_type == InteractionType.HOVER
        ]
        assert len(hover_interactions) == 2

    def test_interaction_id_generation(self, automator):
        """Test unique interaction ID generation."""
        id1 = automator._generate_interaction_id()
        id2 = automator._generate_interaction_id()

        assert id1 != id2
        assert id1.startswith("interaction_1_")
        assert id2.startswith("interaction_2_")

    def test_interaction_logging(self, automator):
        """Test interaction logging functionality."""
        element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            text_content="Test Button",
        )

        automator._log_interaction(
            interaction_id="test_001",
            interaction_type=InteractionType.CLICK,
            element_info=element,
            status=InteractionStatus.SUCCESS,
            data_used={"test": "data"},
            result={"success": True},
        )

        assert len(automator.interaction_logs) == 1
        log = automator.interaction_logs[0]
        assert log.interaction_id == "test_001"
        assert log.interaction_type == InteractionType.CLICK
        assert log.status == InteractionStatus.SUCCESS
        assert log.data_used["test"] == "data"
        assert log.result["success"] is True

    def test_interaction_summary(self, automator):
        """Test interaction summary generation."""
        # Add some test logs
        element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
        )

        # Successful interaction
        automator._log_interaction(
            "test_001", InteractionType.CLICK, element, InteractionStatus.SUCCESS
        )

        # Failed interaction
        automator._log_interaction(
            "test_002", InteractionType.FILL, element, InteractionStatus.FAILED
        )

        # Blocked interaction
        automator._log_interaction(
            "test_003", InteractionType.SUBMIT, element, InteractionStatus.BLOCKED
        )

        # Add some discovered URLs
        automator.discovered_urls.add("https://example.com/page1")
        automator.discovered_urls.add("https://example.com/page2")

        summary = automator.get_interaction_summary()

        assert summary["total_interactions"] == 3
        assert summary["successful_interactions"] == 1
        assert summary["failed_interactions"] == 1
        assert summary["blocked_interactions"] == 1
        assert summary["discovered_urls"] == 2
        assert summary["interaction_types"]["click"] == 1
        assert summary["interaction_types"]["fill"] == 1
        assert summary["interaction_types"]["submit"] == 1

    def test_empty_interaction_summary(self, automator):
        """Test interaction summary with no interactions."""
        summary = automator.get_interaction_summary()

        assert summary["total_interactions"] == 0
        assert summary["successful_interactions"] == 0
        assert summary["failed_interactions"] == 0
        assert summary["discovered_urls"] == 0
        assert summary["interaction_types"] == {}

    @pytest.mark.asyncio
    async def test_page_state_capture(self, automator, mock_page):
        """Test page state capture functionality."""
        state = await automator._capture_page_state(mock_page)

        assert "url" in state
        assert "title" in state
        assert "html_length" in state
        assert "timestamp" in state
        assert state["url"] == "https://example.com/test"
        assert state["title"] == "Test Page"

    def test_clear_logs(self, automator):
        """Test clearing interaction logs and discovered URLs."""
        # Add some test data
        element = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
        )

        # Generate an interaction ID to increment counter
        interaction_id = automator._generate_interaction_id()
        automator._log_interaction(
            interaction_id, InteractionType.CLICK, element, InteractionStatus.SUCCESS
        )
        automator.discovered_urls.add("https://example.com/test")

        # Verify data exists
        assert len(automator.interaction_logs) == 1
        assert len(automator.discovered_urls) == 1
        assert automator._interaction_counter == 1

        # Clear and verify
        automator.clear_logs()

        assert len(automator.interaction_logs) == 0
        assert len(automator.discovered_urls) == 0
        assert automator._interaction_counter == 0

    def test_create_locator_strategies(self, automator, mock_page):
        """Test different locator creation strategies."""
        mock_page.locator = Mock(return_value="mocked_locator")

        # Test with data-testid
        element_with_testid = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            attributes={"data-testid": "submit-btn"},
        )
        locator = automator._create_locator(mock_page, element_with_testid)
        mock_page.locator.assert_called_with("[data-testid='submit-btn']")

        # Test with id
        element_with_id = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            attributes={"id": "submit-button"},
        )
        locator = automator._create_locator(mock_page, element_with_id)
        mock_page.locator.assert_called_with("#submit-button")

        # Test with text content
        element_with_text = ElementInfo(
            selector="button",
            element_type="button",
            tag_name="button",
            text_content="Submit Form",
        )
        locator = automator._create_locator(mock_page, element_with_text)
        mock_page.locator.assert_called_with("button:has-text('Submit Form')")

        # Test fallback to selector
        element_basic = ElementInfo(
            selector="button.submit",
            element_type="button",
            tag_name="button",
        )
        locator = automator._create_locator(mock_page, element_basic)
        mock_page.locator.assert_called_with("button.submit")