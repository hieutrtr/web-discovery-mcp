from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, Sequence

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from legacy_web_mcp.analysis import PageAnalysis
from legacy_web_mcp.interaction import InteractionAction
from legacy_web_mcp.llm.client import LLMResponse, LLMRequest
from legacy_web_mcp.llm.summary import ContentSummary
from legacy_web_mcp.network import NetworkTrafficReport


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
) -> FeatureAnalysis:
    prompt = _build_prompt(page, summary, interactions, network_report)
    request = LLMRequest(model=model_alias, prompt=prompt)
    start = time.perf_counter()
    response = await llm_client.generate(request)
    duration = time.perf_counter() - start
    data = _parse_response(page.url, response.content)
    analysis = FeatureAnalysis(
        page_url=page.url,
        interactive_elements=[
            InteractiveElement(**item) for item in data.get("interactive_elements", [])
        ],
        functional_capabilities=data.get("functional_capabilities", []),
        api_integrations=[APIIntegration(**item) for item in data.get("api_integrations", [])],
        business_rules=data.get("business_rules", []),
        rebuild_requirements=[
            RebuildRequirement(
                priority=_normalise_priority(item.get("priority", "medium")),
                requirement=item.get("requirement", ""),
                dependencies=item.get("dependencies", []) or [],
            )
            for item in data.get("rebuild_requirements", [])
        ],
        integration_points=data.get("integration_points", []),
        processing_seconds=duration,
    )
    logger.info(
        "feature_analysis_generated",
        url=page.url,
        provider=response.provider,
        model=response.model,
        tokens=response.tokens_used,
        cost=response.cost_usd,
        seconds=round(duration, 3),
        interactive_elements=len(analysis.interactive_elements),
        api_integrations=len(analysis.api_integrations),
    )
    return analysis


def _build_prompt(
    page: PageAnalysis,
    summary: ContentSummary,
    interactions: Sequence[InteractionAction],
    network_report: NetworkTrafficReport,
) -> str:
    interaction_overview = [f"{action.action_type}:{action.selector}" for action in interactions[:20]]
    api_overview = [f"{event.method} {event.url}" for event in network_report.events[:20]]
    return (
        f"{ANALYSIS_INSTRUCTIONS}\n"
        f"Page Purpose: {summary.purpose}\n"
        f"Business Context: {summary.business_context}\n"
        f"User Journey: {summary.user_journey}\n"
        f"Navigation Role: {summary.navigation_role}\n"
        f"Known Functionalities: {', '.join(page.functionality.categories)}\n"
        f"Interactions Observed: {interaction_overview}\n"
        f"API Activity: {api_overview}\n"
        "Return JSON only."
    )


def _parse_response(page_url: str, content: str) -> dict[str, Any]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM feature analysis response for {page_url} is invalid JSON") from exc
    required_lists = [
        "interactive_elements",
        "functional_capabilities",
        "business_rules",
        "rebuild_requirements",
        "integration_points",
    ]
    for key in required_lists:
        data.setdefault(key, [])
    data.setdefault("api_integrations", [])
    return data


def _normalise_priority(priority: str) -> str:
    value = priority.lower()
    if value in {"high", "medium", "low"}:
        return value
    if value in {"critical", "p0"}:
        return "high"
    if value in {"p2", "moderate"}:
        return "medium"
    return "low"
