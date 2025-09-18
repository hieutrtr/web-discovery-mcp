"""Application-wide exception hierarchy for the Legacy Web MCP server."""

from __future__ import annotations

from typing import Any, Mapping


class LegacyWebMCPError(Exception):
    """Base error carrying a machine-readable code and optional details."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "GENERIC_000",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class LLMAnalysisError(LegacyWebMCPError):
    """Raised when an LLM request fails or returns unusable content."""


class LLMValidationError(LLMAnalysisError):
    """Raised when an LLM response violates the expected schema."""

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message=message, code="LLM_002", details=details)


class LLMRetryExhaustedError(LLMAnalysisError):
    """Raised when all configured LLM fallbacks fail to produce a valid response."""

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message=message, code="LLM_003", details=details)
