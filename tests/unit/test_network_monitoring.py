"""Unit tests for network traffic monitoring functionality."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from legacy_web_mcp.browser.network import (
    NetworkMonitor,
    NetworkMonitorConfig,
    NetworkRequestData,
    NetworkTrafficSummary,
    RequestType,
)


class TestNetworkRequestData:
    """Test NetworkRequestData model."""

    def test_request_data_creation(self):
        """Test creating NetworkRequestData instance."""
        request_data = NetworkRequestData(
            url="https://api.example.com/users",
            method="GET",
            request_type=RequestType.REST_API,
            status_code=200,
            headers={"content-type": "application/json"},
            timing={"response_time_ms": 150.5},
            is_third_party=False,
        )

        assert request_data.url == "https://api.example.com/users"
        assert request_data.method == "GET"
        assert request_data.request_type == RequestType.REST_API
        assert request_data.status_code == 200
        assert not request_data.is_third_party
        assert request_data.timing["response_time_ms"] == 150.5

    def test_request_data_to_dict(self):
        """Test converting NetworkRequestData to dictionary."""
        request_data = NetworkRequestData(
            url="https://api.example.com/users",
            method="POST",
            request_type=RequestType.REST_API,
            status_code=201,
            request_payload='{"name": "test"}',
            response_payload='{"id": 123}',
        )

        data_dict = request_data.to_dict()

        assert data_dict["url"] == "https://api.example.com/users"
        assert data_dict["method"] == "POST"
        assert data_dict["request_type"] == "rest_api"
        assert data_dict["status_code"] == 201
        assert data_dict["request_payload"] == '{"name": "test"}'
        assert data_dict["response_payload"] == '{"id": 123}'
        assert "timestamp" in data_dict


class TestNetworkTrafficSummary:
    """Test NetworkTrafficSummary model."""

    def test_traffic_summary_creation(self):
        """Test creating NetworkTrafficSummary instance."""
        summary = NetworkTrafficSummary(
            total_requests=50,
            api_requests=10,
            asset_requests=35,
            third_party_requests=15,
            failed_requests=2,
            total_bytes=1024000,
            average_response_time=125.5,
            unique_domains=["example.com", "api.example.com"],
            api_endpoints=["https://api.example.com/users", "https://api.example.com/posts"],
            third_party_domains=["cdn.example.com", "analytics.google.com"],
        )

        assert summary.total_requests == 50
        assert summary.api_requests == 10
        assert summary.asset_requests == 35
        assert summary.third_party_requests == 15
        assert summary.failed_requests == 2
        assert summary.total_bytes == 1024000
        assert summary.average_response_time == 125.5
        assert len(summary.unique_domains) == 2
        assert len(summary.api_endpoints) == 2
        assert len(summary.third_party_domains) == 2

    def test_traffic_summary_to_dict(self):
        """Test converting NetworkTrafficSummary to dictionary."""
        summary = NetworkTrafficSummary(
            total_requests=25,
            api_requests=5,
            unique_domains=["example.com"],
        )

        data_dict = summary.to_dict()

        assert data_dict["total_requests"] == 25
        assert data_dict["api_requests"] == 5
        assert data_dict["unique_domains"] == ["example.com"]


class TestNetworkMonitorConfig:
    """Test NetworkMonitorConfig model."""

    def test_default_config(self):
        """Test default configuration values."""
        config = NetworkMonitorConfig()

        assert config.capture_request_payloads is True
        assert config.capture_response_payloads is True
        assert config.max_payload_size == 10000
        assert config.filter_static_assets is True
        assert config.include_timing_data is True
        assert config.redact_sensitive_data is True
        assert "password" in config.sensitive_patterns

    def test_custom_config(self):
        """Test custom configuration values."""
        config = NetworkMonitorConfig(
            capture_request_payloads=False,
            max_payload_size=5000,
            filter_static_assets=False,
            sensitive_patterns=["custom_secret"],
        )

        assert config.capture_request_payloads is False
        assert config.max_payload_size == 5000
        assert config.filter_static_assets is False
        assert config.sensitive_patterns == ["custom_secret"]


class TestNetworkMonitor:
    """Test NetworkMonitor functionality."""

    @pytest.fixture
    def config(self):
        """Create a NetworkMonitorConfig instance."""
        return NetworkMonitorConfig(
            capture_request_payloads=True,
            capture_response_payloads=True,
            max_payload_size=1000,
            filter_static_assets=True,
            redact_sensitive_data=True,
        )

    @pytest.fixture
    def monitor(self, config):
        """Create a NetworkMonitor instance."""
        return NetworkMonitor(config, base_domain="example.com")

    @pytest.fixture
    def mock_page(self):
        """Create a mock Playwright page."""
        page = Mock()
        page.on = Mock()
        page.remove_listener = Mock()
        return page

    @pytest.fixture
    def mock_request(self):
        """Create a mock Playwright request."""
        request = Mock()
        request.url = "https://api.example.com/users"
        request.method = "GET"
        request.headers = {"content-type": "application/json"}
        request.post_data = None
        return request

    @pytest.fixture
    def mock_response(self):
        """Create a mock Playwright response."""
        response = Mock()
        response.status = 200
        response.headers = {"content-type": "application/json"}
        response.text = AsyncMock(return_value='{"users": []}')
        return response

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor, mock_page):
        """Test starting network monitoring on a page."""
        await monitor.start_monitoring(mock_page)

        # Verify event handlers were registered
        assert mock_page.on.call_count == 3
        expected_events = ["request", "response", "requestfailed"]
        actual_events = [call[0][0] for call in mock_page.on.call_args_list]
        for event in expected_events:
            assert event in actual_events

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor, mock_page):
        """Test stopping network monitoring."""
        await monitor.start_monitoring(mock_page)
        await monitor.stop_monitoring(mock_page)

        # Verify event handlers were removed
        assert mock_page.remove_listener.call_count == 3

    @pytest.mark.asyncio
    async def test_request_classification_rest_api(self, monitor, mock_request, mock_response):
        """Test classification of REST API requests."""
        mock_request.url = "https://api.example.com/v1/users"
        mock_request.method = "GET"

        request_type = monitor._classify_request(mock_request, mock_response)
        assert request_type == RequestType.REST_API

    @pytest.mark.asyncio
    async def test_request_classification_graphql(self, monitor, mock_request, mock_response):
        """Test classification of GraphQL requests."""
        mock_request.url = "https://example.com/graphql"
        mock_request.method = "POST"

        request_type = monitor._classify_request(mock_request, mock_response)
        assert request_type == RequestType.GRAPHQL

    @pytest.mark.asyncio
    async def test_request_classification_static_asset(self, monitor, mock_request, mock_response):
        """Test classification of static asset requests."""
        mock_request.url = "https://example.com/styles.css"
        mock_request.method = "GET"

        request_type = monitor._classify_request(mock_request, mock_response)
        assert request_type == RequestType.STATIC_ASSET

    @pytest.mark.asyncio
    async def test_request_classification_html_page(self, monitor, mock_request, mock_response):
        """Test classification of HTML page requests."""
        mock_request.url = "https://example.com/about.html"
        mock_request.method = "GET"
        mock_response.headers = {"content-type": "text/html"}

        request_type = monitor._classify_request(mock_request, mock_response)
        assert request_type == RequestType.HTML_PAGE

    def test_third_party_detection_same_domain(self, monitor):
        """Test third-party detection for same domain requests."""
        is_third_party, domain = monitor._is_third_party_request("https://example.com/api/users")
        assert not is_third_party
        assert domain is None

    def test_third_party_detection_subdomain(self, monitor):
        """Test third-party detection for subdomain requests."""
        is_third_party, domain = monitor._is_third_party_request("https://api.example.com/users")
        assert not is_third_party
        assert domain is None

    def test_third_party_detection_external_domain(self, monitor):
        """Test third-party detection for external domain requests."""
        is_third_party, domain = monitor._is_third_party_request("https://cdn.other.com/script.js")
        assert is_third_party
        assert domain == "cdn.other.com"

    def test_third_party_detection_www_handling(self, monitor):
        """Test third-party detection with www prefix handling."""
        # Test with www in base domain
        monitor.base_domain = "www.example.com"
        is_third_party, domain = monitor._is_third_party_request("https://example.com/page")
        assert not is_third_party

        # Test with www in request domain
        monitor.base_domain = "example.com"
        is_third_party, domain = monitor._is_third_party_request("https://www.example.com/page")
        assert not is_third_party

    def test_payload_sanitization_truncation(self, monitor):
        """Test payload truncation for large payloads."""
        large_payload = "x" * 2000
        sanitized = monitor._sanitize_payload(large_payload)

        assert len(sanitized) <= monitor.config.max_payload_size + len("...[TRUNCATED]")
        assert sanitized.endswith("...[TRUNCATED]")

    def test_payload_sanitization_redaction(self, monitor):
        """Test sensitive data redaction in payloads."""
        payload = '{"password": "secret123", "name": "user"}'
        sanitized = monitor._sanitize_payload(payload)

        assert "secret123" not in sanitized
        assert "***REDACTED***" in sanitized
        assert "user" in sanitized

    def test_sensitive_header_detection(self, monitor):
        """Test sensitive header detection."""
        assert monitor._is_sensitive_header("authorization")
        assert monitor._is_sensitive_header("Authorization")
        assert monitor._is_sensitive_header("cookie")
        assert monitor._is_sensitive_header("x-api-key")
        assert not monitor._is_sensitive_header("content-type")
        assert not monitor._is_sensitive_header("user-agent")

    def test_content_length_parsing(self, monitor):
        """Test content-length header parsing."""
        assert monitor._parse_content_length("1024") == 1024
        assert monitor._parse_content_length("0") == 0
        assert monitor._parse_content_length("invalid") is None
        assert monitor._parse_content_length(None) is None

    @pytest.mark.asyncio
    async def test_response_handler_success(self, monitor, mock_request, mock_response):
        """Test successful response handling."""
        mock_response.request = mock_request

        # Set up timing data
        monitor._active_requests[id(mock_request)] = {
            "start_time": datetime.now(UTC),
            "request": mock_request,
        }

        await monitor._on_response(mock_response)

        assert len(monitor.requests) == 1
        request_data = monitor.requests[0]
        assert request_data.url == mock_request.url
        assert request_data.method == mock_request.method
        assert request_data.status_code == 200

    @pytest.mark.asyncio
    async def test_failed_request_handler(self, monitor, mock_request):
        """Test failed request handling."""
        monitor._active_requests[id(mock_request)] = {
            "start_time": datetime.now(UTC),
            "request": mock_request,
        }

        await monitor._on_request_failed(mock_request)

        assert len(monitor.requests) == 1
        request_data = monitor.requests[0]
        assert request_data.url == mock_request.url
        assert request_data.status_code is None

    def test_get_summary_empty(self, monitor):
        """Test summary generation with no requests."""
        summary = monitor.get_summary()

        assert summary.total_requests == 0
        assert summary.api_requests == 0
        assert summary.asset_requests == 0
        assert summary.third_party_requests == 0
        assert summary.failed_requests == 0
        assert summary.average_response_time == 0.0

    def test_get_summary_with_data(self, monitor):
        """Test summary generation with request data."""
        # Add some test requests
        api_request = NetworkRequestData(
            url="https://api.example.com/users",
            method="GET",
            request_type=RequestType.REST_API,
            status_code=200,
            timing={"response_time_ms": 100},
            content_length=500,
        )

        asset_request = NetworkRequestData(
            url="https://example.com/style.css",
            method="GET",
            request_type=RequestType.STATIC_ASSET,
            status_code=200,
            timing={"response_time_ms": 50},
            content_length=1000,
        )

        third_party_request = NetworkRequestData(
            url="https://cdn.other.com/script.js",
            method="GET",
            request_type=RequestType.STATIC_ASSET,
            status_code=200,
            is_third_party=True,
            third_party_domain="cdn.other.com",
            timing={"response_time_ms": 200},
            content_length=2000,
        )

        failed_request = NetworkRequestData(
            url="https://api.example.com/error",
            method="GET",
            request_type=RequestType.REST_API,
            status_code=404,
        )

        monitor.requests = [api_request, asset_request, third_party_request, failed_request]

        summary = monitor.get_summary()

        assert summary.total_requests == 4
        assert summary.api_requests == 2
        assert summary.asset_requests == 2
        assert summary.third_party_requests == 1
        assert summary.failed_requests == 1
        assert summary.total_bytes == 3500
        assert abs(summary.average_response_time - 116.67) < 0.01  # (100 + 50 + 200) / 3

        assert "api.example.com" in summary.unique_domains
        assert "example.com" in summary.unique_domains
        assert "cdn.other.com" in summary.unique_domains

        assert "https://api.example.com/users" in summary.api_endpoints
        assert "https://api.example.com/error" in summary.api_endpoints

        assert "cdn.other.com" in summary.third_party_domains

    def test_request_filtering_static_assets(self, monitor):
        """Test filtering of static asset requests."""
        asset_request = NetworkRequestData(
            url="https://example.com/image.png",
            method="GET",
            request_type=RequestType.STATIC_ASSET,
            status_code=200,
        )

        # With filtering enabled (default)
        assert not monitor._should_include_request(asset_request)

        # With filtering disabled
        monitor.config.filter_static_assets = False
        assert monitor._should_include_request(asset_request)

    def test_clear_requests(self, monitor):
        """Test clearing request data."""
        # Add some test data
        monitor.requests.append(NetworkRequestData(
            url="https://example.com/test",
            method="GET",
            request_type=RequestType.REST_API,
            status_code=200,
        ))
        monitor._active_requests["test"] = {"test": "data"}

        monitor.clear_requests()

        assert len(monitor.requests) == 0
        assert len(monitor._active_requests) == 0

    def test_get_requests_copy(self, monitor):
        """Test getting copy of requests."""
        original_request = NetworkRequestData(
            url="https://example.com/test",
            method="GET",
            request_type=RequestType.REST_API,
            status_code=200,
        )
        monitor.requests.append(original_request)

        requests_copy = monitor.get_requests()

        # Should be a copy, not the same list
        assert requests_copy is not monitor.requests
        assert len(requests_copy) == 1
        assert requests_copy[0] is original_request