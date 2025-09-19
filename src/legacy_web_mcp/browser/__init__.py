"""Browser automation package with Playwright session management."""

from .models import (
    BrowserCrashError,
    BrowserEngine,
    BrowserSessionConfig,
    BrowserSessionError,
    ConcurrencyController,
    SessionLimitExceededError,
    SessionMetrics,
    SessionStatus,
)
from .service import BrowserAutomationService
from .navigation import PageContentData, PageNavigationError, PageNavigator
from .network import NetworkMonitor, NetworkMonitorConfig, NetworkRequestData, NetworkTrafficSummary, RequestType
from .session import BrowserSession, BrowserSessionFactory, managed_browser_session

__all__ = [
    # Models
    "BrowserEngine",
    "SessionStatus",
    "BrowserSessionConfig",
    "SessionMetrics",
    "ConcurrencyController",
    # Exceptions
    "BrowserSessionError",
    "BrowserCrashError",
    "SessionLimitExceededError",
    "PageNavigationError",
    # Core classes
    "BrowserSession",
    "BrowserSessionFactory",
    "BrowserAutomationService",
    "PageNavigator",
    "PageContentData",
    "NetworkMonitor",
    "NetworkMonitorConfig",
    "NetworkRequestData",
    "NetworkTrafficSummary",
    "RequestType",
    # Utilities
    "managed_browser_session",
]