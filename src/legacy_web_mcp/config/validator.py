"""Configuration validation utilities for environmental requirements."""
from __future__ import annotations

import os
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

import structlog

logger = structlog.get_logger(__name__)

MANDATORY_ENV_KEYS: Sequence[str] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "STEP1_MODEL",
    "STEP2_MODEL",
    "FALLBACK_MODEL",
)


@dataclass
class EnvIssue:
    """Represents a configuration validation finding."""

    key: str
    remediation: str


def validate_env_vars(required_keys: Iterable[str] | None = None) -> list[EnvIssue]:
    """Validate that required environment variables are present and non-empty.

    Args:
        required_keys: Iterable of environment variable names to validate. If ``None``
            the default :data:`MANDATORY_ENV_KEYS` list is used.
    """

    keys = list(required_keys or MANDATORY_ENV_KEYS)
    issues: list[EnvIssue] = []
    for key in keys:
        value = os.getenv(key)
        if value:
            continue
        issues.append(
            EnvIssue(
                key=key,
                remediation=f"Set the {key} environment variable or update .env.template",
            )
        )
    if issues:
        logger.warning("configuration_missing_env", missing=[issue.key for issue in issues])
    return issues


def summarize_env_validation(required_keys: Iterable[str] | None = None) -> dict[str, object]:
    """Return a structured summary suitable for diagnostic responses."""

    issues = validate_env_vars(required_keys)
    if not issues:
        return {"status": "ok", "details": []}
    return {
        "status": "warning",
        "details": [asdict(issue) for issue in issues],
    }


__all__ = [
    "MANDATORY_ENV_KEYS",
    "EnvIssue",
    "validate_env_vars",
    "summarize_env_validation",
]
