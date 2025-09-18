"""Interaction automation helpers."""

from .actions import InteractionAction, InteractionLogEntry, discover_interactions, perform_interactions
from .interactive import (
    InteractiveAnalysisResult,
    InteractiveAnalysisSession,
    InteractiveConfig,
    InteractiveIO,
    InteractivePageContext,
    SimpleConsoleIO,
)

__all__ = [
    "InteractionAction",
    "InteractionLogEntry",
    "discover_interactions",
    "perform_interactions",
    "InteractiveAnalysisSession",
    "InteractiveAnalysisResult",
    "InteractivePageContext",
    "InteractiveConfig",
    "InteractiveIO",
    "SimpleConsoleIO",
]
