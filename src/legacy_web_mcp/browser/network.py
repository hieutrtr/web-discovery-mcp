"""Network traffic monitoring and analysis for browser sessions."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import structlog
from playwright.async_api import Page, Request, Response
from pydantic import BaseModel, Field

_logger = structlog.get_logger("legacy_web_mcp.browser.network")


class RequestType(str, Enum):
    """Types of network requests."""

    REST_API = "rest_api"
    GRAPHQL = "graphql"
    SOAP = "soap"
    STATIC_ASSET = "static_asset"
    HTML_PAGE = "html_page"
    WEBSOCKET = "websocket"
    UNKNOWN = "unknown"


class NetworkRequestData(BaseModel):
    """Data model for captured network requests."""

    url: str
    method: str
    request_type: RequestType
    status_code: int | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    request_payload: str | None = None
    response_payload: str | None = None
    timing: dict[str, float] = Field(default_factory=dict)
    is_third_party: bool = False
    third_party_domain: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "method": self.method,
            "request_type": self.request_type.value,
            "status_code": self.status_code,
            "headers": self.headers,
            "request_payload": self.request_payload,
            "response_payload": self.response_payload,
            "timing": self.timing,
            "is_third_party": self.is_third_party,
            "third_party_domain": self.third_party_domain,
            "content_type": self.content_type,
            "content_length": self.content_length,
            "timestamp": self.timestamp.isoformat(),
        }


class NetworkTrafficSummary(BaseModel):
    """Summary of network traffic for a page."""

    total_requests: int = 0
    api_requests: int = 0
    asset_requests: int = 0
    third_party_requests: int = 0
    failed_requests: int = 0
    total_bytes: int = 0
    average_response_time: float = 0.0
    unique_domains: list[str] = Field(default_factory=list)
    api_endpoints: list[str] = Field(default_factory=list)
    third_party_domains: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_requests": self.total_requests,
            "api_requests": self.api_requests,
            "asset_requests": self.asset_requests,
            "third_party_requests": self.third_party_requests,
            "failed_requests": self.failed_requests,
            "total_bytes": self.total_bytes,
            "average_response_time": self.average_response_time,
            "unique_domains": self.unique_domains,
            "api_endpoints": self.api_endpoints,
            "third_party_domains": self.third_party_domains,
        }


class NetworkMonitorConfig(BaseModel):
    """Configuration for network monitoring."""

    capture_request_payloads: bool = True
    capture_response_payloads: bool = True
    max_payload_size: int = Field(default=10000)  # 10KB
    filter_static_assets: bool = True
    include_timing_data: bool = True
    redact_sensitive_data: bool = True
    sensitive_patterns: list[str] = Field(default_factory=lambda: [
        r'password',
        r'token',
        r'key',
        r'secret',
        r'auth',
        r'bearer',
        r'session',
        r'cookie',
    ])


class NetworkMonitor:
    """Monitors and captures network traffic during page navigation."""

    def __init__(self, config: NetworkMonitorConfig, base_domain: str | None = None):
        self.config = config
        self.base_domain = base_domain
        self.requests: list[NetworkRequestData] = []
        self._active_requests: dict[str, dict[str, Any]] = {}

    async def start_monitoring(self, page: Page) -> None:
        """Start monitoring network traffic on a page."""
        _logger.info(
            "network_monitoring_started",
            base_domain=self.base_domain,
            config=self.config.model_dump(),
        )

        # Set up request/response handlers
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)

    async def stop_monitoring(self, page: Page) -> None:
        """Stop monitoring network traffic."""
        # Remove event handlers
        page.remove_listener("request", self._on_request)
        page.remove_listener("response", self._on_response)
        page.remove_listener("requestfailed", self._on_request_failed)

        _logger.info(
            "network_monitoring_stopped",
            total_requests=len(self.requests),
            base_domain=self.base_domain,
        )

    async def _on_request(self, request: Request) -> None:
        """Handle outgoing request."""
        try:
            request_id = id(request)
            start_time = datetime.now(UTC)

            # Store request timing
            self._active_requests[request_id] = {
                "start_time": start_time,
                "request": request,
            }

            _logger.debug(
                "network_request_started",
                url=request.url,
                method=request.method,
                request_id=request_id,
            )

        except Exception as e:
            _logger.error(
                "network_request_handler_error",
                error=str(e),
                url=getattr(request, 'url', 'unknown'),
            )

    async def _on_response(self, response: Response) -> None:
        """Handle incoming response."""
        try:
            request = response.request
            request_id = id(request)

            # Get timing data
            timing_data = {}
            if request_id in self._active_requests:
                start_time = self._active_requests[request_id]["start_time"]
                response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
                timing_data["response_time_ms"] = response_time

            # Classify request type
            request_type = self._classify_request(request, response)

            # Check if third-party
            is_third_party, third_party_domain = self._is_third_party_request(request.url)

            # Capture payloads if enabled
            request_payload = None
            response_payload = None

            if self.config.capture_request_payloads and request.post_data:
                request_payload = self._sanitize_payload(request.post_data)

            if self.config.capture_response_payloads:
                try:
                    response_text = await response.text()
                    response_payload = self._sanitize_payload(response_text)
                except Exception:
                    # Some responses can't be read as text
                    response_payload = None

            # Extract headers (sanitized)
            headers = {}
            for name, value in request.headers.items():
                if self._is_sensitive_header(name):
                    headers[name] = "***REDACTED***"
                else:
                    headers[name] = value

            # Create request data
            request_data = NetworkRequestData(
                url=request.url,
                method=request.method,
                request_type=request_type,
                status_code=response.status,
                headers=headers,
                request_payload=request_payload,
                response_payload=response_payload,
                timing=timing_data,
                is_third_party=is_third_party,
                third_party_domain=third_party_domain,
                content_type=response.headers.get("content-type"),
                content_length=self._parse_content_length(response.headers.get("content-length")),
            )

            # Apply filtering
            if self._should_include_request(request_data):
                self.requests.append(request_data)

            # Clean up tracking
            if request_id in self._active_requests:
                del self._active_requests[request_id]

            _logger.debug(
                "network_response_captured",
                url=request.url,
                status=response.status,
                request_type=request_type.value,
                is_third_party=is_third_party,
            )

        except Exception as e:
            _logger.error(
                "network_response_handler_error",
                error=str(e),
                url=getattr(response, 'url', 'unknown'),
            )

    async def _on_request_failed(self, request: Request) -> None:
        """Handle failed request."""
        try:
            request_id = id(request)

            # Create failed request data
            request_data = NetworkRequestData(
                url=request.url,
                method=request.method,
                request_type=self._classify_request(request, None),
                status_code=None,  # Failed request has no status
                is_third_party=self._is_third_party_request(request.url)[0],
            )

            if self._should_include_request(request_data):
                self.requests.append(request_data)

            # Clean up tracking
            if request_id in self._active_requests:
                del self._active_requests[request_id]

            _logger.warning(
                "network_request_failed",
                url=request.url,
                method=request.method,
            )

        except Exception as e:
            _logger.error(
                "network_failed_handler_error",
                error=str(e),
                url=getattr(request, 'url', 'unknown'),
            )

    def _classify_request(self, request: Request, response: Response | None) -> RequestType:
        """Classify the type of network request."""
        url = request.url.lower()
        method = request.method.upper()
        content_type = ""

        if response:
            content_type = response.headers.get("content-type", "").lower()

        # Check for GraphQL
        if "/graphql" in url or "graphql" in url:
            return RequestType.GRAPHQL

        # Check for SOAP (usually POST with XML content)
        if method == "POST" and ("xml" in content_type or "soap" in content_type):
            return RequestType.SOAP

        # Check for WebSocket
        if url.startswith("ws://") or url.startswith("wss://"):
            return RequestType.WEBSOCKET

        # Check for static assets
        static_extensions = [
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.mp3', '.pdf',
            '.zip', '.tar', '.gz'
        ]
        if any(url.endswith(ext) for ext in static_extensions):
            return RequestType.STATIC_ASSET

        # Check for HTML pages
        if method == "GET" and ("text/html" in content_type or url.endswith(".html")):
            return RequestType.HTML_PAGE

        # Check for API endpoints (common patterns)
        api_patterns = [
            r'/api/',
            r'/v\d+/',
            r'/rest/',
            r'/service/',
            r'\.json',
            r'/json',
            r'/graphql',
        ]
        if any(re.search(pattern, url) for pattern in api_patterns):
            return RequestType.REST_API

        # Default for data-bearing requests
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return RequestType.REST_API

        return RequestType.UNKNOWN

    def _is_third_party_request(self, url: str) -> tuple[bool, str | None]:
        """Check if request is to a third-party domain."""
        if not self.base_domain:
            return False, None

        try:
            parsed = urlparse(url)
            request_domain = parsed.netloc.lower()

            # Remove 'www.' prefix for comparison
            base_clean = self.base_domain.lower().replace('www.', '')
            request_clean = request_domain.replace('www.', '')

            is_third_party = not (request_clean == base_clean or request_clean.endswith(f'.{base_clean}'))
            third_party_domain = request_domain if is_third_party else None

            return is_third_party, third_party_domain

        except Exception:
            return False, None

    def _should_include_request(self, request_data: NetworkRequestData) -> bool:
        """Determine if request should be included based on filtering rules."""
        if self.config.filter_static_assets and request_data.request_type == RequestType.STATIC_ASSET:
            return False

        return True

    def _sanitize_payload(self, payload: str) -> str | None:
        """Sanitize payload data, removing sensitive information."""
        if not payload:
            return None

        # Limit payload size
        if len(payload) > self.config.max_payload_size:
            payload = payload[:self.config.max_payload_size] + "...[TRUNCATED]"

        # Redact sensitive data if enabled
        if self.config.redact_sensitive_data:
            for pattern in self.config.sensitive_patterns:
                # Simple pattern-based redaction
                payload = re.sub(
                    f'"{pattern}"\\s*:\\s*"[^"]*"',
                    f'"{pattern}": "***REDACTED***"',
                    payload,
                    flags=re.IGNORECASE
                )

        return payload

    def _is_sensitive_header(self, header_name: str) -> bool:
        """Check if header contains sensitive information."""
        sensitive_headers = [
            'authorization', 'cookie', 'set-cookie', 'x-api-key',
            'x-auth-token', 'x-csrf-token', 'authentication'
        ]
        return header_name.lower() in sensitive_headers

    def _parse_content_length(self, content_length_header: str | None) -> int | None:
        """Parse content-length header."""
        if not content_length_header:
            return None
        try:
            return int(content_length_header)
        except ValueError:
            return None

    def get_summary(self) -> NetworkTrafficSummary:
        """Generate summary of captured network traffic."""
        if not self.requests:
            return NetworkTrafficSummary()

        api_requests = [r for r in self.requests if r.request_type in [
            RequestType.REST_API, RequestType.GRAPHQL, RequestType.SOAP
        ]]
        asset_requests = [r for r in self.requests if r.request_type == RequestType.STATIC_ASSET]
        third_party_requests = [r for r in self.requests if r.is_third_party]
        failed_requests = [r for r in self.requests if r.status_code is None or r.status_code >= 400]

        # Calculate total bytes
        total_bytes = sum(r.content_length or 0 for r in self.requests)

        # Calculate average response time
        response_times = [
            r.timing.get("response_time_ms", 0) for r in self.requests
            if "response_time_ms" in r.timing
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0

        # Extract unique domains
        unique_domains = list(set(
            urlparse(r.url).netloc for r in self.requests
            if urlparse(r.url).netloc
        ))

        # Extract API endpoints
        api_endpoints = list(set(r.url for r in api_requests))

        # Extract third-party domains
        third_party_domains = list(set(
            r.third_party_domain for r in third_party_requests
            if r.third_party_domain
        ))

        return NetworkTrafficSummary(
            total_requests=len(self.requests),
            api_requests=len(api_requests),
            asset_requests=len(asset_requests),
            third_party_requests=len(third_party_requests),
            failed_requests=len(failed_requests),
            total_bytes=total_bytes,
            average_response_time=avg_response_time,
            unique_domains=unique_domains,
            api_endpoints=api_endpoints,
            third_party_domains=third_party_domains,
        )

    def get_requests(self) -> list[NetworkRequestData]:
        """Get all captured requests."""
        return self.requests.copy()

    def clear_requests(self) -> None:
        """Clear captured requests."""
        self.requests.clear()
        self._active_requests.clear()


__all__ = [
    "RequestType",
    "NetworkRequestData",
    "NetworkTrafficSummary",
    "NetworkMonitorConfig",
    "NetworkMonitor",
]