from __future__ import annotations

import asyncio
import importlib
import os
import platform
import resource
from datetime import datetime, timezone
from typing import Any, Dict, Mapping

try:  # pragma: no cover - structlog may not be installed during early dev
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "STEP1_MODEL",
    "STEP2_MODEL",
    "FALLBACK_MODEL",
]


def _module_available(module_name: str) -> tuple[bool, str | None]:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        return False, str(exc)
    return True, None


async def health_check() -> Dict[str, Any]:
    """Return aggregated server health information."""
    fastmcp_available, fastmcp_error = _module_available("fastmcp")
    dependency_report = {
        "fastmcp": {
            "available": fastmcp_available,
            "detail": "FastMCP import successful" if fastmcp_available else fastmcp_error,
            "remediation": None
            if fastmcp_available
            else "Install fastmcp>=2.12.0 to enable full MCP capabilities.",
        }
    }
    configuration_report = validate_configuration()
    status = "ok" if fastmcp_available and configuration_report["valid"] else "degraded"
    logger.info(
        "health_check_executed",
        status=status,
        fastmcp_available=fastmcp_available,
        configuration_valid=configuration_report["valid"],
    )
    return {
        "server": {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "dependencies": dependency_report,
        "configuration": configuration_report,
    }


async def validate_dependencies() -> Dict[str, Any]:
    """Validate local runtime dependencies such as Playwright browsers."""
    playwright_available, playwright_error = _module_available("playwright")
    status = "ok" if playwright_available else "missing"
    logger.info(
        "validate_dependencies",
        playwright_available=playwright_available,
        status=status,
    )
    return {
        "playwright": {
            "status": status,
            "detail": "Playwright is installed." if playwright_available else playwright_error,
            "remediation": None
            if playwright_available
            else "Install playwright via 'uv pip install playwright' and run 'playwright install'.",
        }
    }


async def test_llm_connectivity(env: Mapping[str, str] | None = None) -> Dict[str, Any]:
    """Validate LLM configuration by ensuring API keys are present.

    Network calls are intentionally avoided in the base implementation to keep
    tests deterministic and offline-friendly. When keys are present the status
    is reported as ``configured``; otherwise ``missing_key``.
    """
    env = dict(os.environ if env is None else env)
    providers = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    report: Dict[str, Any] = {}
    for provider, key in providers.items():
        api_key = env.get(key)
        if api_key:
            status = "configured"
            detail = "API key detected. Connectivity test deferred to runtime diagnostics."
        else:
            status = "missing_key"
            detail = f"Set the {key} environment variable to enable connectivity checks."
        report[provider] = {
            "status": status,
            "detail": detail,
        }
        logger.info(
            "llm_connectivity_status",
            provider=provider,
            status=status,
        )
    return report


async def system_status() -> Dict[str, Any]:
    """Return lightweight runtime metrics for the current process."""
    loop = asyncio.get_running_loop()
    active_tasks = len([task for task in asyncio.all_tasks(loop) if not task.done()])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    if platform.system() == "Darwin":
        memory_mb = usage.ru_maxrss / (1024 * 1024)
    else:
        memory_mb = usage.ru_maxrss / 1024
    status = {
        "pid": os.getpid(),
        "active_tasks": active_tasks,
        "memory_mb": round(memory_mb, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("system_status_snapshot", **status)
    return status


def validate_configuration(env: Mapping[str, str] | None = None) -> Dict[str, Any]:
    """Ensure mandatory environment configuration is present."""
    env = dict(os.environ if env is None else env)
    missing = [key for key in REQUIRED_ENV_VARS if not env.get(key)]
    report = {
        "valid": not missing,
        "missing": missing,
        "remediation": "Populate missing environment variables in .env or deployment settings."
        if missing
        else None,
    }
    logger.info("configuration_validation", valid=report["valid"], missing=len(missing))
    return report
