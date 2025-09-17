from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable, List, Mapping

SAFE_DESTRUCTIVE_KEYWORDS = {"delete", "remove", "destroy", "drop"}


@dataclass(slots=True)
class InteractionAction:
    action_type: str
    selector: str
    description: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class InteractionLogEntry:
    action: InteractionAction
    status: str
    detail: str | None = None


class _InteractionExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.actions: List[InteractionAction] = []
        self._form_depth = 0

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, str | None]]) -> None:
        attrs_dict = {name.lower(): (value or "") for name, value in attrs}
        selector = self._build_selector(tag, attrs_dict)
        if tag.lower() == "form":
            self._form_depth += 1
            if not self._is_safe(attrs_dict):
                return
            self.actions.append(
                InteractionAction(
                    action_type="submit_form",
                    selector=selector,
                    description="Submit form with sample data",
                    metadata={"method": attrs_dict.get("method", "get").upper()},
                )
            )
        elif tag.lower() in {"button", "a"}:
            if not self._is_safe(attrs_dict):
                return
            self.actions.append(
                InteractionAction(
                    action_type="click",
                    selector=selector,
                    description=attrs_dict.get("aria-label") or attrs_dict.get("title") or "Trigger element",
                    metadata={},
                )
            )
        elif tag.lower() == "input" and attrs_dict.get("type", "text") not in {"hidden", "submit"}:
            if not self._is_safe(attrs_dict):
                return
            self.actions.append(
                InteractionAction(
                    action_type="fill",
                    selector=selector,
                    description="Populate input for interaction",
                    metadata={"input_type": attrs_dict.get("type", "text")},
                )
            )

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self._form_depth > 0:
            self._form_depth -= 1

    def _build_selector(self, tag: str, attrs: Mapping[str, str]) -> str:
        if "id" in attrs and attrs["id"]:
            return f"{tag}#{attrs['id']}"
        if "class" in attrs and attrs["class"]:
            classes = attrs["class"].replace(" ", ".")
            return f"{tag}.{classes}"
        return tag

    def _is_safe(self, attrs: Mapping[str, str]) -> bool:
        text_values = " ".join(attrs.values()).lower()
        return not any(keyword in text_values for keyword in SAFE_DESTRUCTIVE_KEYWORDS)


def discover_interactions(html: str) -> List[InteractionAction]:
    extractor = _InteractionExtractor()
    extractor.feed(html)
    return extractor.actions


def perform_interactions(actions: Iterable[InteractionAction]) -> List[InteractionLogEntry]:
    logs: List[InteractionLogEntry] = []
    for action in actions:
        logs.append(
            InteractionLogEntry(
                action=action,
                status="simulated",
                detail="Action recorded for execution via Playwright in production",
            )
        )
    return logs
