from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Sequence

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

        def debug(self, event: str, **kwargs: Any) -> None:
            self._base.debug("%s %s", event, kwargs)

    logger = _Shim(logging.getLogger(__name__))

from legacy_web_mcp.analysis import PageAnalysis
from legacy_web_mcp.errors import LLMValidationError
from legacy_web_mcp.interaction import InteractionAction
from legacy_web_mcp.llm.client import LLMResponse, LLMRequest
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.network import NetworkTrafficReport
from legacy_web_mcp.llm.context import (
    AnalysisContext,
    context_overlap_score,
    derive_priority_multiplier,
)
from legacy_web_mcp.llm.debug import AnalysisDebug, DebugAttempt


@dataclass(slots=True)
class InteractiveElement:
    selector: str
    purpose: str
    details: str


@dataclass(slots=True)
class APIIntegration:
    url: str
    method: str
    description: str


@dataclass(slots=True)
class RebuildRequirement:
    priority: str
    requirement: str
    dependencies: List[str]
    score: float = 0.0
    rationale: str = ""


@dataclass(slots=True)
class FeatureAnalysis:
    page_url: str
    interactive_elements: List[InteractiveElement]
    functional_capabilities: List[str]
    api_integrations: List[APIIntegration]
    business_rules: List[str]
    rebuild_requirements: List[RebuildRequirement]
    integration_points: List[str]
    processing_seconds: float
    quality_score: float = 0.0
    consistency_warnings: tuple[str, ...] = field(default_factory=tuple)
    context_links: tuple[str, ...] = field(default_factory=tuple)
    debug: AnalysisDebug | None = None


ANALYSIS_INSTRUCTIONS = (
    "You are producing a detailed feature analysis for rebuilding a legacy web page. "
    "Respond ONLY with JSON using keys: interactive_elements (list of objects with selector, purpose, details), "
    "functional_capabilities (list of strings), api_integrations (list of objects url, method, description), "
    "business_rules (list of strings), rebuild_requirements (list of objects priority, requirement, dependencies), "
    "integration_points (list of strings)."
)


async def analyse_features(
    page: PageAnalysis,
    summary: ContentSummary,
    interactions: Sequence[InteractionAction],
    network_report: NetworkTrafficReport,
    *,
    llm_client,
    model_alias: str = "step2",
    max_interactions: int = 20,
    max_api_events: int = 20,
    context: AnalysisContext | None = None,
) -> FeatureAnalysis:
    analysis_context = context or summary.to_context()
    prompt = _build_prompt(
        page,
        summary,
        analysis_context,
        interactions,
        network_report,
        max_interactions,
        max_api_events,
    )
    attempts: list[DebugAttempt] = []
    validation_messages: list[str] = []
    model_sequence = _model_attempt_order(model_alias)
    total_start = time.perf_counter()
    parsed: Mapping[str, Any] | None = None
    response_provider = ""
    response_model = ""
    duration = 0.0

    for alias in model_sequence:
        request = LLMRequest(model=alias, prompt=prompt)
        attempt_start = time.perf_counter()
        response = await llm_client.generate(request)
        duration = time.perf_counter() - attempt_start
        response_provider = response.provider
        response_model = response.model
        try:
            parsed, soft_issues = _validate_feature_schema(page.url, response.content)
            validation_messages.extend(soft_issues)
            attempts.append(
                DebugAttempt(
                    provider=response.provider,
                    model=response.model,
                    tokens_used=response.tokens_used,
                    cost_usd=response.cost_usd,
                    response_preview=response.content[:200],
                )
            )
            break
        except LLMValidationError as error:
            validation_messages.append(str(error))
            attempts.append(
                DebugAttempt(
                    provider=response.provider,
                    model=response.model,
                    tokens_used=response.tokens_used,
                    cost_usd=response.cost_usd,
                    response_preview=response.content[:200],
                    error=str(error),
                )
            )
            logger.warning(
                "feature_analysis_validation_failed",
                url=page.url,
                provider=response.provider,
                model=response.model,
                code=error.code,
                detail=str(error),
            )
            continue

    total_duration = time.perf_counter() - total_start

    if parsed is None:
        logger.error(
            "feature_analysis_fallback_used",
            url=page.url,
            attempts=len(attempts),
            issues=validation_messages,
        )
        return _fallback_analysis(
            page,
            summary,
            analysis_context,
            tuple(validation_messages),
            prompt,
            tuple(attempts),
            total_duration,
        )

    analysis = _build_feature_analysis(
        page,
        parsed,
        duration,
        summary,
        analysis_context,
        validation_messages,
        attempts,
        prompt,
    )

    logger.info(
        "feature_analysis_generated",
        url=page.url,
        provider=response_provider,
        model=response_model,
        tokens=attempts[-1].tokens_used if attempts else 0,
        cost=attempts[-1].cost_usd if attempts else 0.0,
        seconds=round(total_duration, 3),
        quality=round(analysis.quality_score, 3),
        warnings=len(analysis.consistency_warnings),
    )
    return analysis


def _build_prompt(
    page: PageAnalysis,
    summary: ContentSummary,
    context: AnalysisContext,
    interactions: Sequence[InteractionAction],
    network_report: NetworkTrafficReport,
    max_interactions: int = 20,
    max_api_events: int = 20,
) -> str:
    interaction_overview = [f"{action.action_type}:{action.selector}" for action in interactions[:max_interactions]]
    api_overview = [f"{event.method} {event.url}" for event in network_report.events[:max_api_events]]
    emphasis = "\n".join(context.emphasis_lines())
    return (
        f"{ANALYSIS_INSTRUCTIONS}\n"
        f"Page Purpose: {summary.purpose}\n"
        f"Business Context: {summary.business_context}\n"
        f"User Journey: {summary.user_journey}\n"
        f"Navigation Role: {summary.navigation_role}\n"
        f"Context Signals:\n{emphasis}\n"
        f"Known Functionalities: {', '.join(page.functionality.categories)}\n"
        f"Interactions Observed: {interaction_overview}\n"
        f"API Activity: {api_overview}\n"
        "Return JSON only."
    )


def _normalise_priority(priority: str) -> str:
    value = priority.lower()
    if value in {"high", "medium", "low"}:
        return value
    if value in {"critical", "p0"}:
        return "high"
    if value in {"p2", "moderate"}:
        return "medium"
    return "low"


def _validate_feature_schema(page_url: str, raw_content: str) -> tuple[dict[str, Any], list[str]]:
    if not raw_content.strip():
        raise LLMValidationError(
            f"Empty response for {page_url}", details={"stage": "feature_analysis"}
        )
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise LLMValidationError(
            f"Invalid JSON payload for {page_url}", details={"error": str(exc)}
        ) from exc
    if not isinstance(data, dict):
        raise LLMValidationError(
            f"Response must be JSON object for {page_url}", details={"type": type(data).__name__}
        )

    def ensure_list(field: str) -> list[Any]:
        value = data.get(field, [])
        if not isinstance(value, list):
            raise LLMValidationError(
                f"Field '{field}' must be a list for {page_url}",
                details={"field": field, "received": type(value).__name__},
            )
        return value

    interactive = ensure_list("interactive_elements")
    functional = ensure_list("functional_capabilities")
    integrations = ensure_list("api_integrations")
    business_rules = ensure_list("business_rules")
    requirements = ensure_list("rebuild_requirements")
    integration_points = ensure_list("integration_points")

    warnings: list[str] = []
    normalised_interactive: list[dict[str, Any]] = []
    for item in interactive:
        if not isinstance(item, dict):
            warnings.append("interactive element not object; skipped")
            continue
        selector = str(item.get("selector", "")).strip()
        purpose = str(item.get("purpose", "")).strip()
        details = str(item.get("details", "")).strip()
        if not selector or not purpose:
            warnings.append("interactive element missing selector/purpose")
            continue
        normalised_interactive.append({"selector": selector, "purpose": purpose, "details": details})

    normalised_integrations: list[dict[str, Any]] = []
    for item in integrations:
        if not isinstance(item, dict):
            warnings.append("api integration not object; skipped")
            continue
        url = str(item.get("url", "")).strip()
        method = str(item.get("method", "")).strip().upper() or "GET"
        description = str(item.get("description", "")).strip()
        if not url:
            warnings.append("api integration missing url")
            continue
        normalised_integrations.append({"url": url, "method": method, "description": description})

    normalised_requirements: list[dict[str, Any]] = []
    for item in requirements:
        if not isinstance(item, dict):
            warnings.append("rebuild requirement not object; skipped")
            continue
        priority = _normalise_priority(str(item.get("priority", "medium")))
        requirement = str(item.get("requirement", "")).strip()
        deps = item.get("dependencies") or []
        if not isinstance(deps, list):
            deps = [str(deps)]
        if not requirement:
            warnings.append("rebuild requirement missing description")
            continue
        normalised_requirements.append(
            {
                "priority": priority,
                "requirement": requirement,
                "dependencies": [str(dep).strip() for dep in deps if dep],
            }
        )

    return (
        {
            "interactive_elements": normalised_interactive,
            "functional_capabilities": [str(item).strip() for item in functional if str(item).strip()],
            "api_integrations": normalised_integrations,
            "business_rules": [str(item).strip() for item in business_rules if str(item).strip()],
            "rebuild_requirements": normalised_requirements,
            "integration_points": [str(item).strip() for item in integration_points if str(item).strip()],
        },
        warnings,
    )


def _model_attempt_order(initial_alias: str) -> list[str]:
    order = [initial_alias]
    if initial_alias != "fallback":
        order.append("fallback")
    return order


def _build_feature_analysis(
    page: PageAnalysis,
    parsed: Mapping[str, Any],
    last_duration: float,
    summary: ContentSummary,
    context: AnalysisContext,
    validation_messages: list[str],
    attempts: Sequence[DebugAttempt],
    prompt: str,
) -> FeatureAnalysis:
    interactive = [InteractiveElement(**item) for item in parsed["interactive_elements"]]
    api_integrations = [APIIntegration(**item) for item in parsed["api_integrations"]]
    requirements = [
        _score_requirement(item, context) for item in parsed["rebuild_requirements"]
    ]
    quality_score = _score_feature_quality(parsed, context, summary.confidence, validation_messages)
    overlap = context_overlap_score(parsed["functional_capabilities"], context)
    warnings: list[str] = []
    if overlap < 0.3:
        warnings.append(
            "Functional capabilities show weak alignment with Step 1 context (overlap < 30%)."
        )
    if not requirements:
        warnings.append("No rebuild requirements identified; manual review recommended.")
    context_links = tuple(
        cap for cap in parsed["functional_capabilities"] if context.matches(cap)
    )
    combined_warnings = tuple(warnings + list(validation_messages)) if warnings or validation_messages else tuple()
    return FeatureAnalysis(
        page_url=page.url,
        interactive_elements=interactive,
        functional_capabilities=list(parsed["functional_capabilities"]),
        api_integrations=api_integrations,
        business_rules=list(parsed["business_rules"]),
        rebuild_requirements=requirements,
        integration_points=list(parsed["integration_points"]),
        processing_seconds=last_duration,
        quality_score=quality_score,
        consistency_warnings=combined_warnings,
        context_links=context_links,
        debug=AnalysisDebug(prompt=prompt, attempts=tuple(attempts)),
    )


def _score_feature_quality(
    parsed: Mapping[str, Any],
    context: AnalysisContext,
    confidence: float,
    issues: Iterable[str],
) -> float:
    lists = [
        parsed["interactive_elements"],
        parsed["functional_capabilities"],
        parsed["api_integrations"],
        parsed["business_rules"],
        parsed["rebuild_requirements"],
        parsed["integration_points"],
    ]
    completeness = sum(1 for items in lists if items) / len(lists)
    overlap = context_overlap_score(parsed["functional_capabilities"], context)
    penalty = min(0.25, 0.05 * sum(1 for _ in issues))
    blended = 0.45 * completeness + 0.35 * overlap + 0.20 * confidence - penalty
    return max(0.0, min(1.0, round(blended, 3)))


def _score_requirement(item: Mapping[str, Any], context: AnalysisContext) -> RebuildRequirement:
    base_priority = item["priority"]
    base_score = {"high": 0.8, "medium": 0.55, "low": 0.3}.get(base_priority, 0.5)
    multiplier = derive_priority_multiplier(item["requirement"], context)
    score = min(1.0, round(base_score * multiplier, 3))
    rationale = (
        "Aligned with Step 1 context"
        if multiplier > context.priority_bias
        else "Limited alignment with Step 1 findings"
    )
    return RebuildRequirement(
        priority=base_priority,
        requirement=item["requirement"],
        dependencies=item.get("dependencies", []),
        score=score,
        rationale=rationale,
    )


def _fallback_analysis(
    page: PageAnalysis,
    summary: ContentSummary,
    context: AnalysisContext,
    issues: tuple[str, ...],
    prompt: str,
    attempts: tuple[DebugAttempt, ...],
    duration: float,
) -> FeatureAnalysis:
    warnings = issues + ("LLM responses invalid; produced empty analysis",)
    logger.warning(
        "feature_analysis_heuristic_fallback",
        url=page.url,
        warnings=warnings,
    )
    placeholder_requirement = RebuildRequirement(
        priority="medium",
        requirement="Review page manually; automated analysis unavailable",
        dependencies=[],
        score=0.2,
        rationale="Heuristic fallback",
    )
    return FeatureAnalysis(
        page_url=page.url,
        interactive_elements=[],
        functional_capabilities=[],
        api_integrations=[],
        business_rules=[],
        rebuild_requirements=[placeholder_requirement],
        integration_points=[],
        processing_seconds=duration,
        quality_score=0.1,
        consistency_warnings=warnings,
        context_links=(),
        debug=AnalysisDebug(prompt=prompt, attempts=attempts),
    )
