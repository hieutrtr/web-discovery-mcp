"""MCP tools for network traffic monitoring during page navigation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from mcp.server.fastmcp import FastMCP

from legacy_web_mcp.browser import BrowserAutomationService
from legacy_web_mcp.browser.network import NetworkMonitor, NetworkMonitorConfig
from legacy_web_mcp.browser.navigation import PageNavigator
from legacy_web_mcp.config import get_config

_logger = structlog.get_logger("legacy_web_mcp.mcp.network_tools")


@FastMCP.tool()
async def monitor_network_traffic(
    url: str,
    capture_payloads: bool = True,
    filter_static_assets: bool = True,
    max_payload_size: int = 10000,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Monitor network traffic during page navigation.

    Navigates to a URL while capturing and analyzing all network requests.

    Args:
        url: Target URL to navigate to and monitor
        capture_payloads: Whether to capture request/response payloads
        filter_static_assets: Whether to filter out static asset requests
        max_payload_size: Maximum size of payloads to capture (in bytes)
        session_id: Optional browser session ID to reuse

    Returns:
        Dictionary containing navigation results and network traffic analysis
    """
    try:
        config = get_config()

        _logger.info(
            "network_monitoring_started",
            url=url,
            capture_payloads=capture_payloads,
            filter_static_assets=filter_static_assets,
            session_id=session_id,
        )

        # Configure network monitoring
        monitor_config = NetworkMonitorConfig(
            capture_request_payloads=capture_payloads,
            capture_response_payloads=capture_payloads,
            max_payload_size=max_payload_size,
            filter_static_assets=filter_static_assets,
            include_timing_data=True,
            redact_sensitive_data=True,
        )

        # Extract base domain for third-party detection
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc

        # Initialize components
        browser_service = BrowserAutomationService(config.browser)
        navigator = PageNavigator(
            timeout=30.0,
            max_retries=3,
            wait_for_network_idle=True,
            enable_screenshots=True,
        )
        network_monitor = NetworkMonitor(monitor_config, base_domain)

        async with browser_service.get_session(session_id=session_id) as session:
            page = session.page

            # Start network monitoring
            await network_monitor.start_monitoring(page)

            try:
                # Navigate and extract content
                project_root = Path.cwd()
                content_data = await navigator.navigate_and_extract(
                    page=page,
                    url=url,
                    project_root=project_root,
                )

                # Get network traffic summary
                traffic_summary = network_monitor.get_summary()
                detailed_requests = network_monitor.get_requests()

                _logger.info(
                    "network_monitoring_completed",
                    url=url,
                    total_requests=len(detailed_requests),
                    api_requests=traffic_summary.api_requests,
                    third_party_requests=traffic_summary.third_party_requests,
                    failed_requests=traffic_summary.failed_requests,
                )

                return {
                    "status": "success",
                    "url": url,
                    "session_id": session.session_id,
                    "page_content": content_data.to_dict(),
                    "network_summary": traffic_summary.to_dict(),
                    "detailed_requests": [req.to_dict() for req in detailed_requests],
                    "analysis": {
                        "total_requests": len(detailed_requests),
                        "unique_domains": len(traffic_summary.unique_domains),
                        "api_endpoints_discovered": len(traffic_summary.api_endpoints),
                        "third_party_services": traffic_summary.third_party_domains,
                        "performance_metrics": {
                            "page_load_time": content_data.load_time,
                            "average_response_time": traffic_summary.average_response_time,
                            "total_bytes_transferred": traffic_summary.total_bytes,
                        }
                    }
                }

            finally:
                # Stop network monitoring
                await network_monitor.stop_monitoring(page)

    except Exception as e:
        _logger.error(
            "network_monitoring_failed",
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "status": "error",
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@FastMCP.tool()
async def analyze_api_endpoints(
    url: str,
    include_payloads: bool = False,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze API endpoints discovered during page navigation.

    Focuses specifically on identifying and analyzing API calls made by the page.

    Args:
        url: Target URL to analyze
        include_payloads: Whether to include request/response payloads in analysis
        session_id: Optional browser session ID to reuse

    Returns:
        Dictionary containing detailed API endpoint analysis
    """
    try:
        _logger.info(
            "api_analysis_started",
            url=url,
            include_payloads=include_payloads,
            session_id=session_id,
        )

        # Run network monitoring with focus on APIs
        result = await monitor_network_traffic(
            url=url,
            capture_payloads=include_payloads,
            filter_static_assets=True,  # Always filter assets for API analysis
            session_id=session_id,
        )

        if result["status"] != "success":
            return result

        # Filter and analyze API requests
        api_requests = []
        for request in result["detailed_requests"]:
            request_type = request["request_type"]
            if request_type in ["rest_api", "graphql", "soap"]:
                api_requests.append(request)

        # Group by endpoint pattern
        endpoint_patterns = {}
        for request in api_requests:
            url_path = request["url"]
            method = request["method"]
            status = request["status_code"]

            # Extract path pattern (remove query params and IDs)
            import re
            from urllib.parse import urlparse
            parsed = urlparse(url_path)
            path = parsed.path

            # Replace numeric IDs with placeholder
            path_pattern = re.sub(r'/\d+', '/{id}', path)
            pattern_key = f"{method} {path_pattern}"

            if pattern_key not in endpoint_patterns:
                endpoint_patterns[pattern_key] = {
                    "pattern": pattern_key,
                    "method": method,
                    "path_pattern": path_pattern,
                    "requests": [],
                    "status_codes": set(),
                    "avg_response_time": 0,
                }

            endpoint_patterns[pattern_key]["requests"].append(request)
            endpoint_patterns[pattern_key]["status_codes"].add(status)

        # Calculate averages and finalize patterns
        for pattern_data in endpoint_patterns.values():
            requests = pattern_data["requests"]
            response_times = [
                req["timing"].get("response_time_ms", 0)
                for req in requests
                if req["timing"]
            ]
            pattern_data["avg_response_time"] = (
                sum(response_times) / len(response_times) if response_times else 0
            )
            pattern_data["status_codes"] = list(pattern_data["status_codes"])
            pattern_data["call_count"] = len(requests)

        _logger.info(
            "api_analysis_completed",
            url=url,
            total_api_requests=len(api_requests),
            unique_patterns=len(endpoint_patterns),
        )

        return {
            "status": "success",
            "url": url,
            "session_id": result["session_id"],
            "api_summary": {
                "total_api_requests": len(api_requests),
                "unique_endpoint_patterns": len(endpoint_patterns),
                "endpoint_patterns": list(endpoint_patterns.values()),
            },
            "detailed_api_requests": api_requests if include_payloads else [],
            "page_metadata": {
                "title": result["page_content"]["title"],
                "load_time": result["page_content"]["load_time"],
                "status_code": result["page_content"]["status_code"],
            }
        }

    except Exception as e:
        _logger.error(
            "api_analysis_failed",
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "status": "error",
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@FastMCP.tool()
async def monitor_third_party_services(
    url: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Monitor and analyze third-party services used by a webpage.

    Identifies external services, tracking scripts, CDNs, and other third-party integrations.

    Args:
        url: Target URL to analyze
        session_id: Optional browser session ID to reuse

    Returns:
        Dictionary containing third-party service analysis
    """
    try:
        _logger.info(
            "third_party_analysis_started",
            url=url,
            session_id=session_id,
        )

        # Run network monitoring
        result = await monitor_network_traffic(
            url=url,
            capture_payloads=False,  # Don't need payloads for service identification
            filter_static_assets=False,  # Include assets to detect CDNs
            session_id=session_id,
        )

        if result["status"] != "success":
            return result

        # Analyze third-party requests
        third_party_requests = [
            req for req in result["detailed_requests"]
            if req["is_third_party"]
        ]

        # Categorize third-party services
        service_categories = {
            "analytics": [],
            "advertising": [],
            "cdn": [],
            "social_media": [],
            "payment": [],
            "other": []
        }

        # Known service patterns
        service_patterns = {
            "analytics": [
                "google-analytics", "googletagmanager", "hotjar", "mixpanel",
                "segment", "amplitude", "heap", "fullstory"
            ],
            "advertising": [
                "doubleclick", "googlesyndication", "facebook.com", "twitter.com",
                "linkedin.com", "adsystem", "amazon-adsystem"
            ],
            "cdn": [
                "cloudflare", "amazonaws", "cloudfront", "jsdelivr", "unpkg",
                "cdnjs", "bootstrapcdn", "googleapis"
            ],
            "social_media": [
                "facebook", "twitter", "linkedin", "instagram", "youtube",
                "tiktok", "pinterest"
            ],
            "payment": [
                "stripe", "paypal", "square", "braintree", "klarna"
            ]
        }

        # Categorize requests
        for request in third_party_requests:
            domain = request["third_party_domain"].lower()
            categorized = False

            for category, patterns in service_patterns.items():
                if any(pattern in domain for pattern in patterns):
                    service_categories[category].append({
                        "domain": request["third_party_domain"],
                        "url": request["url"],
                        "request_type": request["request_type"],
                        "status_code": request["status_code"],
                    })
                    categorized = True
                    break

            if not categorized:
                service_categories["other"].append({
                    "domain": request["third_party_domain"],
                    "url": request["url"],
                    "request_type": request["request_type"],
                    "status_code": request["status_code"],
                })

        # Generate summary
        unique_domains = list(set(req["third_party_domain"] for req in third_party_requests))

        _logger.info(
            "third_party_analysis_completed",
            url=url,
            total_third_party_requests=len(third_party_requests),
            unique_third_party_domains=len(unique_domains),
        )

        return {
            "status": "success",
            "url": url,
            "session_id": result["session_id"],
            "third_party_summary": {
                "total_third_party_requests": len(third_party_requests),
                "unique_third_party_domains": len(unique_domains),
                "service_categories": {
                    category: len(services)
                    for category, services in service_categories.items()
                },
            },
            "service_details": service_categories,
            "all_third_party_domains": unique_domains,
            "page_metadata": {
                "title": result["page_content"]["title"],
                "load_time": result["page_content"]["load_time"],
                "status_code": result["page_content"]["status_code"],
            }
        }

    except Exception as e:
        _logger.error(
            "third_party_analysis_failed",
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "status": "error",
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def register(mcp: FastMCP) -> None:
    """Register network monitoring tools with the MCP server."""
    mcp.tool(monitor_network_traffic)
    mcp.tool(analyze_api_endpoints)
    mcp.tool(monitor_third_party_services)


__all__ = [
    "monitor_network_traffic",
    "analyze_api_endpoints",
    "monitor_third_party_services",
    "register",
]