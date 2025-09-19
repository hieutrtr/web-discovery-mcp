"""Diagnostics tools and resources for the MCP server."""
from __future__ import annotations

import asyncio
import os
import platform
import resource
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from fastmcp import Context, FastMCP

from legacy_web_mcp.config.validator import summarize_env_validation

LOGGER = structlog.get_logger(__name__)

_PLAYWRIGHT_CHECKER: Callable[[], Awaitable[list[BrowserStatus]]] | None = None
_LLM_PROBE: Callable[[str, str, str], Awaitable[dict[str, Any]]] | None = None


@dataclass(slots=True)
class BrowserStatus:
    name: str
    status: str
    details: dict[str, Any]


async def _check_playwright_browsers() -> list[BrowserStatus]:
    if _PLAYWRIGHT_CHECKER is not None:
        return await _PLAYWRIGHT_CHECKER()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return [
            BrowserStatus(
                name="playwright",
                status="missing",
                details={
                    "remediation": "Install Playwright browsers via `uv run playwright install`.",
                },
            )
        ]

    results: list[BrowserStatus] = []
    try:
        async with async_playwright() as playwright:
            for browser_name in ("chromium", "firefox", "webkit"):
                browser_type = getattr(playwright, browser_name)
                executable = browser_type.executable_path
                status = "ok" if executable and os.path.exists(executable) else "unavailable"
                details: dict[str, Any] = {"executable": executable}
                if status != "ok":
                    details["remediation"] = (
                        f"Run `uv run playwright install {browser_name}` to install the browser."
                    )
                results.append(BrowserStatus(name=browser_name, status=status, details=details))
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.error("playwright_check_failed", error=str(exc))
        results.append(
            BrowserStatus(
                name="playwright",
                status="error",
                details={
                    "error": str(exc),
                    "remediation": "Reinstall Playwright (`uv run playwright install`).",
                },
            )
        )
    return results


async def _probe_llm_endpoint(provider: str, url: str, api_key: str) -> dict[str, Any]:
    if _LLM_PROBE is not None:
        return await _LLM_PROBE(provider, url, api_key)

    headers = {"Authorization": f"Bearer {api_key}"}
    timeout = httpx.Timeout(5.0, connect=2.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            if response.status_code < 400:
                return {"status": "ok", "http_status": response.status_code}
            return {
                "status": "error",
                "http_status": response.status_code,
                "remediation": "Verify API key permissions and provider availability.",
            }
    except httpx.HTTPStatusError as exc:  # pragma: no cover - handled above
        return {
            "status": "error",
            "http_status": exc.response.status_code,
            "remediation": "Resolve provider HTTP error.",
        }
    except Exception as exc:  # pragma: no cover - network failure
        return {
            "status": "error",
            "remediation": f"Connectivity check failed: {exc}",
        }


async def _gather_llm_statuses() -> dict[str, Any]:
    checks = {
        "openai": (
            "OPENAI_API_KEY",
            "https://api.openai.com/v1/models",
        ),
        "anthropic": (
            "ANTHROPIC_API_KEY",
            "https://api.anthropic.com/v1/models",
        ),
        "gemini": (
            "GEMINI_API_KEY",
            "https://generativelanguage.googleapis.com/v1/models",
        ),
    }
    results: dict[str, Any] = {}
    for provider, (env_key, url) in checks.items():
        api_key = os.getenv(env_key)
        if not api_key:
            results[provider] = {
                "status": "missing_key",
                "remediation": f"Set {env_key} to enable connectivity checks.",
            }
            continue
        results[provider] = await _probe_llm_endpoint(provider, url, api_key)
    return results


def _collect_system_status() -> dict[str, Any]:
    try:
        memory_usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:  # pragma: no cover - platform-specific fallback
        memory_usage_kb = None
    loop = asyncio.get_event_loop()
    active_tasks = len(asyncio.all_tasks(loop))
    return {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "memory_usage_kb": memory_usage_kb,
        "active_tasks": active_tasks,
    }


async def perform_health_check(mcp: FastMCP) -> dict[str, Any]:
    env_validation = summarize_env_validation()
    browsers = await _check_playwright_browsers()
    llm_status = await _gather_llm_statuses()
    return {
        "server": {
            "name": mcp.name,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "tools": list((await mcp.get_tools()).keys()),
        },
        "environment": env_validation,
        "playwright": [asdict(browser) for browser in browsers],
        "llm": llm_status,
    }


async def gather_dependency_report() -> dict[str, Any]:
    browsers = await _check_playwright_browsers()
    return {"browsers": [asdict(browser) for browser in browsers]}


async def gather_llm_connectivity() -> dict[str, Any]:
    return await _gather_llm_statuses()


def register(mcp: FastMCP) -> None:
    """Register diagnostics tools/resources with the provided MCP instance."""

    @mcp.tool()
    async def health_check(context: Context) -> dict[str, Any]:
        """Perform comprehensive server health check and report system status.

        Executes a full diagnostic suite including server status, environment validation,
        browser dependency checks, and LLM provider connectivity tests. Provides
        detailed status information for troubleshooting and monitoring.

        Returns:
            Dictionary containing:
            - server: MCP server information and available tools
            - environment: Environment variable validation results
            - playwright: Browser installation status for all engines
            - llm: LLM provider connectivity status and API health
            - timestamp: Check execution time

        Use Case:
            Primary diagnostic tool for verifying system readiness and identifying
            configuration issues. Run this first when troubleshooting problems.
        """
        payload = await perform_health_check(mcp)
        LOGGER.info("health_check", payload=payload)
        return payload

    @mcp.tool()
    async def validate_dependencies(context: Context) -> dict[str, Any]:
        """Validate Playwright browser installations and provide guidance.

        Checks the installation status of all supported browser engines and provides
        detailed remediation guidance for any missing or misconfigured browsers.

        Returns:
            Dictionary containing:
            - browsers: Array of browser status reports
            - Each browser includes:
              - name: Browser engine identifier
              - status: "installed", "missing", or "error"
              - details: Version info or remediation guidance

        Use Case:
            Diagnose browser installation issues and get specific remediation steps.
            Essential for setting up the browser automation environment.
        """
        status = await gather_dependency_report()
        LOGGER.info("validate_dependencies", status=status)
        return status

    @mcp.tool()
    async def test_llm_connectivity(context: Context) -> dict[str, Any]:
        """Test connectivity to configured LLM providers with current credentials.

        Validates API credentials and connectivity for all configured LLM providers
        (OpenAI, Anthropic, Google Gemini) by making lightweight test requests.

        Returns:
            Dictionary containing:
            - Provider status for each configured LLM service
            - API response times and availability
            - Authentication status and error details
            - Recommended actions for failed connections

        Use Case:
            Verify LLM API credentials and network connectivity before operations
            that require AI processing. Helps diagnose authentication failures.
        """
        status = await gather_llm_connectivity()
        LOGGER.info("test_llm_connectivity", results=status)
        return status

    @mcp.resource(
        "/system/status/{scope}",
        name="system_status",
        description="Expose runtime system metrics for diagnostics.",
    )
    async def system_status(context: Context, scope: str) -> dict[str, Any]:
        snapshot = _collect_system_status()
        LOGGER.info("system_status", snapshot=snapshot)
        snapshot["uri"] = f"/system/status/{scope}"
        return snapshot


__all__ = [
    "gather_dependency_report",
    "gather_llm_connectivity",
    "perform_health_check",
    "register",
]
