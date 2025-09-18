"""Generate markdown documentation artifacts for analyses."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Mapping

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

        def info(self, event: str, **kwargs: Any) -> None:
            self._base.info("%s %s", event, kwargs)

        def warning(self, event: str, **kwargs: Any) -> None:
            self._base.warning("%s %s", event, kwargs)

        def error(self, event: str, **kwargs: Any) -> None:
            self._base.error("%s %s", event, kwargs)

    logger = _Shim(logging.getLogger(__name__))

from legacy_web_mcp.analysis import PageAnalysis
from legacy_web_mcp.llm.feature_analysis import FeatureAnalysis
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.progress import ProgressSnapshot
from legacy_web_mcp.storage import ProjectPaths


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _slugify(url: str) -> str:
    slug = url.lower().replace("https://", "").replace("http://", "")
    slug = slug.strip("/")
    slug = slug.replace("/", "-").replace("?", "-").replace("=", "-")
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "page"


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(content, encoding="utf-8")
    temp.replace(path)


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp.replace(path)


class DocumentationGenerator:
    """Produces structured markdown documentation for analysis results."""

    DATA_FILE = "analysis-data.json"

    def __init__(self, project: ProjectPaths) -> None:
        self.project = project
        self._data_path = project.docs_web_dir / self.DATA_FILE
        self._pages_dir = project.docs_pages_dir
        self._master_report = project.docs_master_report

    def update_page(
        self,
        *,
        page: PageAnalysis,
        summary: ContentSummary | None,
        feature: FeatureAnalysis | None,
        progress: ProgressSnapshot | None,
    ) -> None:
        slug = _slugify(page.url)
        data = self._load_data()
        page_entry = self._build_page_entry(page, summary, feature)
        data.setdefault("pages", {})
        pages: Dict[str, Mapping[str, object]] = data["pages"]  # type: ignore[assignment]
        pages[slug] = page_entry
        data["project_id"] = self.project.project_id
        data["updated_at"] = _utcnow().isoformat()
        data["totals"] = self._compute_totals(pages.values())
        _write_json_atomic(self._data_path, data)
        self._write_page_markdown(slug, page_entry)
        self._write_master_report(data, progress)
        logger.info(
            "documentation_updated",
            project_id=self.project.project_id,
            page=page.url,
            master_report=str(self._master_report),
        )

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------
    def _load_data(self) -> Dict[str, object]:
        if not self._data_path.exists():
            return {"pages": {}, "totals": {}}
        try:
            return json.loads(self._data_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "documentation_data_corrupted",
                project_id=self.project.project_id,
                path=str(self._data_path),
            )
            return {"pages": {}, "totals": {}}

    def _build_page_entry(
        self,
        page: PageAnalysis,
        summary: ContentSummary | None,
        feature: FeatureAnalysis | None,
    ) -> Dict[str, object]:
        entry: Dict[str, object] = {
            "url": page.url,
            "title": page.title,
            "generated_at": page.generated_at,
            "element_summary": asdict(page.element_summary),
            "functionality": list(page.functionality.categories),
            "frameworks": asdict(page.frameworks),
            "css": asdict(page.css),
            "performance": asdict(page.performance),
            "content_summary": {},
            "feature_analysis": {},
        }
        if summary:
            entry["content_summary"] = {
                "purpose": summary.purpose,
                "target_users": summary.target_users,
                "business_context": summary.business_context,
                "user_journey": summary.user_journey,
                "navigation_role": summary.navigation_role,
                "business_logic": summary.business_logic,
                "confidence": round(summary.confidence, 3),
                "quality_score": round(summary.quality_score, 3),
            }
        if feature:
            entry["feature_analysis"] = {
                "functional_capabilities": list(feature.functional_capabilities),
                "integration_points": list(feature.integration_points),
                "business_rules": list(feature.business_rules),
                "interactive_elements": [asdict(item) for item in feature.interactive_elements],
                "api_integrations": [asdict(item) for item in feature.api_integrations],
                "rebuild_requirements": [asdict(item) for item in feature.rebuild_requirements],
                "quality_score": round(feature.quality_score, 3),
                "consistency_warnings": list(feature.consistency_warnings),
            }
        return entry

    def _compute_totals(self, pages: Iterable[Mapping[str, object]]) -> Dict[str, int]:
        totals = {
            "pages": 0,
            "interactive_elements": 0,
            "functional_capabilities": 0,
            "api_integrations": 0,
            "rebuild_requirements": 0,
        }
        for page in pages:
            totals["pages"] += 1
            feature = page.get("feature_analysis", {})
            if isinstance(feature, Mapping):
                totals["interactive_elements"] += len(feature.get("interactive_elements", []))
                totals["functional_capabilities"] += len(feature.get("functional_capabilities", []))
                totals["api_integrations"] += len(feature.get("api_integrations", []))
                totals["rebuild_requirements"] += len(feature.get("rebuild_requirements", []))
        return totals

    # ------------------------------------------------------------------
    # Markdown rendering
    # ------------------------------------------------------------------
    def _write_page_markdown(self, slug: str, entry: Mapping[str, object]) -> None:
        path = self._pages_dir / f"page-{slug}.md"
        title = str(entry.get("title", slug) or slug)
        content_lines = [
            f"# Page Analysis: {title.strip() or slug}",
            "",
            f"- URL: {entry.get('url')}\n- Generated: {entry.get('generated_at')}",
            "",
        ]

        summary = entry.get("content_summary", {})
        if isinstance(summary, Mapping) and summary:
            content_lines.append("## Content Summary")
            content_lines.append("")
            content_lines.extend(
                [
                    f"- Purpose: {summary.get('purpose', 'n/a')}",
                    f"- Target Users: {summary.get('target_users', 'n/a')}",
                    f"- Business Context: {summary.get('business_context', 'n/a')}",
                    f"- User Journey: {summary.get('user_journey', 'n/a')}",
                    f"- Navigation Role: {summary.get('navigation_role', 'n/a')}",
                    f"- Business Logic: {summary.get('business_logic', 'n/a')}",
                    f"- Confidence: {summary.get('confidence', 'n/a')}",
                    f"- Quality Score: {summary.get('quality_score', 'n/a')}",
                ]
            )
            content_lines.append("")

        feature = entry.get("feature_analysis", {})
        if isinstance(feature, Mapping) and feature:
            content_lines.append("## Feature Analysis")
            content_lines.append("")
            content_lines.append("### Functional Capabilities")
            for capability in list(feature.get("functional_capabilities", [])):
                content_lines.append(f"- {capability}")
            if not feature.get("functional_capabilities"):
                content_lines.append("- None recorded")
            content_lines.append("")

            content_lines.append("### API Integrations")
            apis = list(feature.get("api_integrations", []))
            if apis:
                for api in apis:
                    content_lines.append(
                        f"- {api.get('method', 'GET')} {api.get('url')} — {api.get('description', 'n/a')}"
                    )
            else:
                content_lines.append("- None detected")
            content_lines.append("")

            content_lines.append("### Rebuild Requirements")
            requirements = list(feature.get("rebuild_requirements", []))
            if requirements:
                for requirement in requirements:
                    content_lines.append(
                        f"- ({requirement.get('priority', 'medium')}) {requirement.get('requirement', 'n/a')}"
                    )
            else:
                content_lines.append("- No explicit requirements captured")
            content_lines.append("")

            warnings = list(feature.get("consistency_warnings", []))
            if warnings:
                content_lines.append("### Consistency Warnings")
                for warning in warnings:
                    content_lines.append(f"- {warning}")
                content_lines.append("")

        _write_text_atomic(path, "\n".join(content_lines).strip() + "\n")

    def _write_master_report(
        self,
        data: Mapping[str, object],
        progress: ProgressSnapshot | None,
    ) -> None:
        pages = data.get("pages", {})
        if not isinstance(pages, Mapping):
            pages = {}
        totals = data.get("totals", {})
        title = "Legacy Web Analysis Report"
        generated_at = _utcnow().isoformat()
        lines = [f"# {title}", "", f"_Last updated: {generated_at}_", ""]

        totals_mapping = totals if isinstance(totals, Mapping) else {}
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(
            f"- Pages Analyzed: {totals_mapping.get('pages', 0)}"
            f"\n- Functional Capabilities Catalogued: {totals_mapping.get('functional_capabilities', 0)}"
            f"\n- API Integrations Detected: {totals_mapping.get('api_integrations', 0)}"
            f"\n- Rebuild Requirements Logged: {totals_mapping.get('rebuild_requirements', 0)}"
        )
        lines.append("")

        if progress:
            lines.append("## Progress Summary")
            lines.append("")
            lines.append(
                "- Status: completed" if progress.percentage == 100.0 else "- Status: in progress"
            )
            lines.append(f"- Completed Pages: {progress.completed}")
            lines.append(f"- Pending Pages: {progress.pending}")
            lines.append(f"- Failed Pages: {progress.failed}")
            lines.append(f"- Skipped Pages: {progress.skipped}")
            if progress.eta_seconds is not None:
                lines.append(f"- Estimated Time Remaining (s): {progress.eta_seconds}")
            if progress.average_seconds is not None:
                lines.append(f"- Average Page Duration (s): {progress.average_seconds}")
            lines.append("")

        lines.append("## Table of Contents")
        lines.append("")
        for slug, entry in sorted(
            pages.items(), key=lambda item: str(item[1].get("title", item[0]) if isinstance(item[1], Mapping) else item[0]).lower()
        ):
            heading = entry.get("title") if isinstance(entry, Mapping) else slug
            lines.append(f"- [{heading}](#page-{slug})")
        if not pages:
            lines.append("- _No pages analyzed yet_")
        lines.append("")

        lines.append("## Page Analyses")
        lines.append("")
        for slug, entry in sorted(
            pages.items(), key=lambda item: str(item[1].get("title", item[0]) if isinstance(item[1], Mapping) else item[0]).lower()
        ):
            if not isinstance(entry, Mapping):
                continue
            lines.append(f"### Page: {entry.get('title', slug)}")
            lines.append(f"<a id=\"page-{slug}\"></a>")
            lines.append("")
            lines.append(f"- URL: {entry.get('url')}")
            lines.append(f"- Generated: {entry.get('generated_at')}")
            summary = entry.get("content_summary", {})
            if isinstance(summary, Mapping) and summary:
                lines.append("- Purpose: " + str(summary.get("purpose", "n/a")))
                lines.append("- Business Logic: " + str(summary.get("business_logic", "n/a")))
            feature = entry.get("feature_analysis", {})
            if isinstance(feature, Mapping) and feature:
                capabilities = feature.get("functional_capabilities", [])
                if capabilities:
                    lines.append("- Functional Capabilities: " + ", ".join(str(cap) for cap in capabilities))
                else:
                    lines.append("- Functional Capabilities: none")
                api_count = len(feature.get("api_integrations", []))
                lines.append(f"- API Integrations: {api_count}")
                requirement_count = len(feature.get("rebuild_requirements", []))
                lines.append(f"- Rebuild Requirements: {requirement_count}")
            lines.append("")

        # API Appendix
        lines.append("## API Integration Appendix")
        lines.append("")
        for slug, entry in sorted(pages.items(), key=lambda item: item[0]):
            if not isinstance(entry, Mapping):
                continue
            feature = entry.get("feature_analysis", {})
            if not isinstance(feature, Mapping):
                continue
            apis = feature.get("api_integrations", [])
            if not apis:
                continue
            lines.append(f"### {entry.get('title', slug)}")
            for api in apis:
                lines.append(
                    f"- {api.get('method', 'GET')} {api.get('url')} — {api.get('description', 'n/a')}"
                )
            lines.append("")

        _write_text_atomic(self._master_report, "\n".join(lines).strip() + "\n")


__all__ = ["DocumentationGenerator"]
