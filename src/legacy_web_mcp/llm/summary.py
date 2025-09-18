from __future__ import annotations

import json
from pathlib import Path
import time
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Protocol

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from legacy_web_mcp.analysis import PageAnalysis
from legacy_web_mcp.llm.client import LLMClient, LLMRequest, LLMResponse


@dataclass(slots=True)
class ContentSummary:
    page_url: str
    purpose: str
    target_users: str
    business_context: str
    user_journey: str
    navigation_role: str
    business_logic: str
    confidence: float
    processing_seconds: float


class SupportsGenerate(Protocol):
    async def generate(self, request: LLMRequest, *, preferred: Mapping[str, Any] | None = None) -> LLMResponse:
        ...


SUMMARY_INSTRUCTIONS = (
    "You are summarizing legacy web pages for modernization. "
    "Given the supplied page detail, respond ONLY with JSON using the following schema: "
    "{\"purpose\": str, \"target_users\": str, \"business_context\": str, \"user_journey\": str, \"navigation_role\": str, \"business_logic\": str, \"confidence\": float}."
)


async def summarize_content(
    page: PageAnalysis,
    *,
    llm_client: SupportsGenerate | LLMClient,
    model_alias: str = "step1",
) -> ContentSummary:
    prompt = _build_prompt(page)
    request = LLMRequest(model=model_alias, prompt=prompt)
    start = time.perf_counter()
    response = await llm_client.generate(request)
    processing_seconds = time.perf_counter() - start
    summary = _parse_response(page.url, response)
    confidence = summary.get("confidence")
    if confidence is None:
        confidence = _heuristic_confidence(page)
    else:
        confidence = max(0.0, min(float(confidence), 1.0))
    logger.info(
        "content_summary_generated",
        url=page.url,
        provider=response.provider,
        model=response.model,
        tokens=response.tokens_used,
        cost=response.cost_usd,
        seconds=round(processing_seconds, 3),
        confidence=confidence,
    )
    return ContentSummary(
        page_url=page.url,
        purpose=summary["purpose"],
        target_users=summary["target_users"],
        business_context=summary["business_context"],
        user_journey=summary["user_journey"],
        navigation_role=summary["navigation_role"],
        business_logic=summary["business_logic"],
        confidence=confidence,
        processing_seconds=processing_seconds,
    )


def _build_prompt(page: PageAnalysis) -> str:
    content_preview = (Path(page.analysis_path).read_text(encoding="utf-8") if page.analysis_path.exists() else "")
    return (
        f"{SUMMARY_INSTRUCTIONS}\n"
        f"Page URL: {page.url}\n"
        f"Title: {page.title}\n"
        f"Functionality: {', '.join(page.functionality.categories) or 'unknown'}\n"
        f"Frameworks: {[name for name, value in asdict(page.frameworks).items() if value]}\n"
        f"Accessibility headings: {[node.role + ':' + (node.label or str(node.level)) for node in page.accessibility_outline[:10]]}\n"
        f"Content excerpt:\n{content_preview[:2000]}\n"
        "Return JSON only."
    )


def _parse_response(page_url: str, response: LLMResponse) -> dict[str, Any]:
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response for {page_url} is not valid JSON") from exc
    required = [
        "purpose",
        "target_users",
        "business_context",
        "user_journey",
        "navigation_role",
        "business_logic",
    ]
    for field in required:
        if field not in data or not isinstance(data[field], str):
            raise ValueError(f"LLM response missing field '{field}' for {page_url}")
    return data


def _heuristic_confidence(page: PageAnalysis) -> float:
    score = 0.5
    if page.text_length > 500:
        score += 0.1
    if page.element_summary.forms > 0 and "form" in page.functionality.categories:
        score += 0.1
    return min(score, 0.9)
