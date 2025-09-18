"""Structured debug information for LLM analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(slots=True, frozen=True)
class DebugAttempt:
    provider: str
    model: str
    tokens_used: int
    cost_usd: float
    response_preview: str
    error: str | None = None


@dataclass(slots=True, frozen=True)
class AnalysisDebug:
    prompt: str
    attempts: Tuple[DebugAttempt, ...]

