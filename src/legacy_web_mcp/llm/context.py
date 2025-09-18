"""Utilities for bridging Step 1 and Step 2 LLM analyses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import hints only
    from .summary import ContentSummary

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging
    from typing import Any

    logging.basicConfig(level=logging.INFO)

    class _Shim:
        def __init__(self, base: logging.Logger) -> None:
            self._base = base

        def debug(self, event: str, **kwargs: Any) -> None:
            self._base.debug("%s %s", event, kwargs)

    logger = _Shim(logging.getLogger(__name__))


_DELIMITERS = re.compile(r"(?:\n|;|,|->|•|\.\s+)")


def _normalise_tokens(text: str) -> Tuple[str, ...]:
    parts = [segment.strip() for segment in _DELIMITERS.split(text) if segment and segment.strip()]
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        lowered = part.lower()
        if lowered not in seen:
            seen.add(lowered)
            unique.append(part)
    return tuple(unique)


@dataclass(slots=True, frozen=True)
class AnalysisContext:
    """Structured context passed from Step 1 summary into Step 2 analysis."""

    highlights: Tuple[str, ...] = field(default_factory=tuple)
    user_journey: Tuple[str, ...] = field(default_factory=tuple)
    business_drivers: Tuple[str, ...] = field(default_factory=tuple)
    workflow_dependencies: Tuple[str, ...] = field(default_factory=tuple)
    priority_bias: float = 0.5
    keywords: Tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_summary(cls, summary: "ContentSummary") -> "AnalysisContext":
        highlights = _normalise_tokens(summary.purpose)
        drivers = _normalise_tokens(summary.business_context)
        journey = _normalise_tokens(summary.user_journey)
        dependencies = _normalise_tokens(summary.business_logic)
        keywords = tuple({token.lower() for token in highlights + drivers + journey + dependencies})
        bias = max(0.2, min(summary.confidence, 0.95))
        logger.debug(
            "analysis_context_constructed",
            url=summary.page_url,
            highlights=len(highlights),
            journey=len(journey),
            drivers=len(drivers),
            dependencies=len(dependencies),
            bias=round(bias, 3),
        )
        return cls(
            highlights=highlights,
            user_journey=journey,
            business_drivers=drivers,
            workflow_dependencies=dependencies,
            priority_bias=bias,
            keywords=keywords,
        )

    def emphasis_lines(self) -> Tuple[str, ...]:
        """Return human-readable lines used inside downstream prompts."""

        return (
            f"Purpose Highlights: {', '.join(self.highlights) or 'unknown'}",
            f"User Journey Signals: {', '.join(self.user_journey) or 'not provided'}",
            f"Business Drivers: {', '.join(self.business_drivers) or 'unspecified'}",
            f"Workflow Dependencies: {', '.join(self.workflow_dependencies) or 'none detected'}",
        )

    def matches(self, text: str) -> bool:
        lower = text.lower()
        return any(keyword in lower for keyword in self.keywords)


def derive_priority_multiplier(requirement: str, context: AnalysisContext) -> float:
    """Boost requirement priority if it aligns with context keywords."""

    matches = 0
    lowered = requirement.lower()
    for keyword in context.keywords:
        if keyword and keyword in lowered:
            matches += 1
    if matches == 0:
        return 0.8 * context.priority_bias
    return min(1.0, context.priority_bias + 0.1 * matches)


def context_overlap_score(items: Iterable[str], context: AnalysisContext) -> float:
    matches = 0
    total = 0
    for value in items:
        cleaned = value.strip()
        if not cleaned:
            continue
        total += 1
        if context.matches(cleaned):
            matches += 1
    if total == 0:
        return 0.0
    return matches / total
