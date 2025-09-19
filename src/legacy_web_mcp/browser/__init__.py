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
    # Core classes
    "BrowserSession",
    "BrowserSessionFactory",
    "BrowserAutomationService",
    # Utilities
    "managed_browser_session",
]