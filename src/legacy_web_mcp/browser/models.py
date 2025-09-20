"""Data models for browser session management."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class BrowserEngine(str, Enum):
    """Supported browser engines."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class SessionStatus(str, Enum):
    """Browser session status."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    CRASHED = "crashed"
    CLOSING = "closing"
    CLOSED = "closed"


class BrowserSessionConfig(BaseModel):
    """Configuration for browser session creation."""

    engine: BrowserEngine = Field(default=BrowserEngine.CHROMIUM)
    headless: bool = Field(default=True)
    viewport_width: int = Field(default=1280)
    viewport_height: int = Field(default=720)
    timeout: float = Field(default=30.0)
    user_agent: str | None = Field(default=None)
    extra_args: list[str] = Field(default_factory=list)


class SessionMetrics(BaseModel):
    """Performance metrics for a browser session."""

    session_id: str
    engine: BrowserEngine
    status: SessionStatus
    created_at: datetime
    pages_loaded: int = Field(default=0)
    total_load_time: float = Field(default=0.0)
    memory_usage_mb: float | None = Field(default=None)
    crash_count: int = Field(default=0)
    last_activity: datetime | None = Field(default=None)

    @property
    def average_load_time(self) -> float:
        """Calculate average page load time."""
        if self.pages_loaded == 0:
            return 0.0
        return self.total_load_time / self.pages_loaded

    @property
    def session_duration(self) -> float:
        """Calculate session duration in seconds."""
        if self.last_activity:
            return (self.last_activity - self.created_at).total_seconds()
        return (datetime.now(UTC) - self.created_at).total_seconds()


class BrowserSessionError(Exception):
    """Base exception for browser session errors."""

    def __init__(self, message: str, session_id: str | None = None):
        super().__init__(message)
        self.session_id = session_id


class BrowserCrashError(BrowserSessionError):
    """Exception raised when browser crashes."""
    pass


class SessionLimitExceededError(BrowserSessionError):
    """Exception raised when concurrent session limit is exceeded."""
    pass


class BrowserLaunchError(BrowserSessionError):
    """Exception raised when browser fails to launch."""
    pass


class ConcurrencyController:
    """Controls concurrent browser session limits."""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_sessions: set[str] = set()

    async def acquire(self, session_id: str) -> None:
        """Acquire a session slot."""
        await self._semaphore.acquire()
        self._active_sessions.add(session_id)

    def release(self, session_id: str) -> None:
        """Release a session slot."""
        if session_id in self._active_sessions:
            self._active_sessions.remove(session_id)
            self._semaphore.release()

    @property
    def active_count(self) -> int:
        """Get number of active sessions."""
        return len(self._active_sessions)

    @property
    def available_slots(self) -> int:
        """Get number of available session slots."""
        return self.max_concurrent - self.active_count


__all__ = [
    "BrowserEngine",
    "SessionStatus",
    "BrowserSessionConfig",
    "SessionMetrics",
    "BrowserSessionError",
    "BrowserCrashError",
    "SessionLimitExceededError",
    "BrowserLaunchError",
    "ConcurrencyController",
]