from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence
from urllib.parse import urlparse

from legacy_web_mcp.network import NetworkTrafficReport
from legacy_web_mcp.storage import ProjectPaths


@dataclass(slots=True)
class ElementSummary:
    total: int
    forms: int
    inputs: int
    buttons: int
    links: int


@dataclass(slots=True)
class FunctionalitySummary:
    categories: List[str] = field(default_factory=list)


@dataclass(slots=True)
class AccessibilityNode:
    role: str
    label: str
    level: int | None = None


@dataclass(slots=True)
class FrameworkDetection:
    react: bool = False
    angular: bool = False
    vue: bool = False
    jquery: bool = False


@dataclass(slots=True)
class CssSummary:
    stylesheets: int
    inline_styles: int
    has_media_queries: bool
    responsive_meta: bool


@dataclass(slots=True)
class PerformanceSummary:
    load_seconds: float | None
    network_events: int
    total_transfer_bytes: int


@dataclass(slots=True)
class PageAnalysis:
    url: str
    title: str
    text_length: int
    element_summary: ElementSummary
    functionality: FunctionalitySummary
    accessibility_outline: List[AccessibilityNode]
    frameworks: FrameworkDetection
    css: CssSummary
    performance: PerformanceSummary
    generated_at: str
    analysis_path: Path


class _StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.total = 0
        self.forms = 0
        self.inputs = 0
        self.buttons = 0
        self.links = 0
        self.stylesheets = 0
        self.inline_styles = 0
        self.has_media_queries = False
        self.responsive_meta = False
        self.headings: List[AccessibilityNode] = []
        self.framework_markers: dict[str, bool] = {
            "react": False,
            "angular": False,
            "vue": False,
            "jquery": False,
        }

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, str | None]]) -> None:
        self.total += 1
        attrs_dict = {name.lower(): (value or "") for name, value in attrs}
        lower_tag = tag.lower()
        if lower_tag == "form":
            self.forms += 1
        if lower_tag == "input":
            if attrs_dict.get("type", "text").lower() not in {"hidden"}:
                self.inputs += 1
        if lower_tag == "button":
            self.buttons += 1
        if lower_tag == "a" and attrs_dict.get("href"):
            self.links += 1
        if lower_tag == "link" and attrs_dict.get("rel", "").lower() == "stylesheet":
            self.stylesheets += 1
        if lower_tag == "style":
            self.inline_styles += 1
        if lower_tag == "meta" and attrs_dict.get("name", "").lower() == "viewport":
            self.responsive_meta = True
        if lower_tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(lower_tag[1])
            label = attrs_dict.get("id") or attrs_dict.get("class") or ""
            self.headings.append(AccessibilityNode(role="heading", label=label, level=level))
        if lower_tag == "script":
            src = attrs_dict.get("src", "").lower()
            text = attrs_dict.get("data-framework", "").lower()
            self._flag_frameworks(src + " " + text)

    def handle_data(self, data: str) -> None:
        snippet = data.lower()
        if "react" in snippet and "render" in snippet:
            self.framework_markers["react"] = True
        if "angular" in snippet or "ng-" in snippet:
            self.framework_markers["angular"] = True
        if "vue" in snippet or "v-" in snippet:
            self.framework_markers["vue"] = True
        if "jquery" in snippet or "$(" in snippet:
            self.framework_markers["jquery"] = True
        if "@media" in snippet:
            self.has_media_queries = True

    def _flag_frameworks(self, text: str) -> None:
        lower = text.lower()
        if "react" in lower:
            self.framework_markers["react"] = True
        if "angular" in lower or "ng-" in lower:
            self.framework_markers["angular"] = True
        if "vue" in lower or "v-" in lower:
            self.framework_markers["vue"] = True
        if "jquery" in lower or "jquery" in lower:
            self.framework_markers["jquery"] = True


def collect_page_analysis(
    *,
    project: ProjectPaths,
    page_url: str,
    html: str,
    text_content: str,
    navigation_metadata: Mapping[str, Any],
    network_report: NetworkTrafficReport | None = None,
) -> PageAnalysis:
    parser = _StructureParser()
    parser.feed(html)

    element_summary = ElementSummary(
        total=parser.total,
        forms=parser.forms,
        inputs=parser.inputs,
        buttons=parser.buttons,
        links=parser.links,
    )

    functionality = FunctionalitySummary(categories=_derive_functionality(parser))

    frameworks = FrameworkDetection(
        react=parser.framework_markers["react"],
        angular=parser.framework_markers["angular"],
        vue=parser.framework_markers["vue"],
        jquery=parser.framework_markers["jquery"],
    )

    css = CssSummary(
        stylesheets=parser.stylesheets,
        inline_styles=parser.inline_styles,
        has_media_queries=parser.has_media_queries,
        responsive_meta=parser.responsive_meta,
    )

    performance = _build_performance_summary(navigation_metadata, network_report)

    generated_at = datetime.now(timezone.utc).isoformat()
    slug = _slugify(page_url)
    output_path = project.analysis_dir / f"{slug}-analysis.json"
    payload = {
        "url": page_url,
        "title": navigation_metadata.get("title", page_url),
        "text_length": len(text_content),
        "element_summary": asdict(element_summary),
        "functionality": asdict(functionality),
        "accessibility_outline": [asdict(node) for node in parser.headings],
        "frameworks": asdict(frameworks),
        "css": asdict(css),
        "performance": asdict(performance),
        "generated_at": generated_at,
    }
    output_path.write_text(json.dumps(payload, indent=2))

    return PageAnalysis(
        url=page_url,
        title=payload["title"],
        text_length=len(text_content),
        element_summary=element_summary,
        functionality=functionality,
        accessibility_outline=parser.headings,
        frameworks=frameworks,
        css=css,
        performance=performance,
        generated_at=generated_at,
        analysis_path=output_path,
    )


def _derive_functionality(parser: _StructureParser) -> List[str]:
    categories: set[str] = set()
    if parser.forms > 0:
        categories.add("form")
    if parser.links > 5:
        categories.add("navigation")
    if parser.buttons > 0:
        categories.add("interaction")
    if parser.total - parser.buttons - parser.inputs > 20:
        categories.add("content")
    return sorted(categories)


def _build_performance_summary(
    navigation_metadata: Mapping[str, Any],
    network_report: NetworkTrafficReport | None,
) -> PerformanceSummary:
    load_seconds = navigation_metadata.get("load_seconds")
    network_events = 0
    total_transfer = 0
    if network_report:
        network_events = len(network_report.events)
        for event in network_report.events:
            if event.body_size:
                total_transfer += event.body_size
    return PerformanceSummary(
        load_seconds=load_seconds,
        network_events=network_events,
        total_transfer_bytes=total_transfer,
    )


def _slugify(url: str) -> str:
    parsed = urlparse(url)
    parts = [parsed.netloc] + [segment for segment in parsed.path.split("/") if segment]
    slug = "-".join(parts) or parsed.netloc or "page"
    slug = slug.replace(":", "-")
    return slug or "page"

