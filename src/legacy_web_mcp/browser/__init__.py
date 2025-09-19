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
from .interaction import InteractionConfig, InteractionLog, InteractionStatus, InteractionType, PageInteractionAutomator, ElementInfo
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
    "InteractionConfig",
    "InteractionLog",
    "InteractionStatus",
    "InteractionType",
    "PageInteractionAutomator",
    "ElementInfo",
    # Utilities
    "managed_browser_session",
]