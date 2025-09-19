"""Helpers for verifying required environment configuration."""
from __future__ import annotations

from collections.abc import Iterable, Sequence

from .validator import MANDATORY_ENV_KEYS, EnvIssue, validate_env_vars

__all__ = [
    "collect_missing_env_issues",
    "default_required_keys",
    "format_issue",
    "format_report",
    "check_required_env",
]


def default_required_keys() -> tuple[str, ...]:
    """Return the default set of environment keys required for deployment."""

    return tuple(MANDATORY_ENV_KEYS)


def collect_missing_env_issues(
    required_keys: Iterable[str] | None = None,
) -> list[EnvIssue]:
    """Return issues for environment keys that are unset or empty."""

    keys = tuple(required_keys) if required_keys is not None else None
    return validate_env_vars(keys)


def check_required_env(
    required_keys: Iterable[str] | None = None,
) -> tuple[bool, list[EnvIssue]]:
    """Return success flag and list of issues for required environment keys."""

    issues = collect_missing_env_issues(required_keys)
    return (not issues, issues)


def format_issue(issue: EnvIssue) -> str:
    """Return a human-friendly message for a missing environment key."""

    return f"{issue.key}: {issue.remediation}"


def format_report(issues: Sequence[EnvIssue]) -> list[str]:
    """Format a sequence of issues into string messages."""

    return [format_issue(issue) for issue in issues]
