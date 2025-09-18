from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol

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
from legacy_web_mcp.llm.client import LLMClient, LLMRequest, LLMResponse
from legacy_web_mcp.llm.context import AnalysisContext
from legacy_web_mcp.llm.debug import AnalysisDebug, DebugAttempt


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
    quality_score: float = 0.0
    validation_issues: tuple[str, ...] = field(default_factory=tuple)
    context_highlights: tuple[str, ...] = field(default_factory=tuple)
    debug: AnalysisDebug | None = None

    def to_context(self) -> AnalysisContext:
        """Return the derived context payload used by Step 2 analysis."""

        return AnalysisContext.from_summary(self)


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
    attempts: list[DebugAttempt] = []
    validation_messages: list[str] = []
    model_sequence = _model_attempt_order(model_alias)
    total_start = time.perf_counter()
    last_duration = 0.0
    summary_payload: dict[str, Any] | None = None
    confidence: float | None = None
    response_provider = ""
    response_model = ""

    for alias in model_sequence:
        request = LLMRequest(model=alias, prompt=prompt)
        attempt_start = time.perf_counter()
        response = await llm_client.generate(request)
        last_duration = time.perf_counter() - attempt_start
        response_provider = response.provider
        response_model = response.model
        try:
            summary_payload, soft_issues = _validate_summary_schema(page.url, response.content)
            validation_messages.extend(soft_issues)
            confidence = summary_payload.pop("confidence", None)
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
                "content_summary_validation_failed",
                url=page.url,
                provider=response.provider,
                model=response.model,
                code=error.code,
                detail=str(error),
            )
            continue

    total_duration = time.perf_counter() - total_start
    if summary_payload is None:
        logger.error(
            "content_summary_fallback_used",
            url=page.url,
            attempts=len(attempts),
            issues=validation_messages,
        )
        fallback = _fallback_summary(
            page,
            tuple(validation_messages),
            prompt,
            tuple(attempts),
            total_duration,
        )
        return fallback

    if confidence is None:
        validation_messages.append("confidence missing from LLM response; heuristic applied")
        confidence = _heuristic_confidence(page)
    else:
        confidence = max(0.0, min(float(confidence), 1.0))

    quality_score = _score_summary_quality(summary_payload.values(), confidence, validation_messages)
    context_highlights = _context_snippets(summary_payload)
    logger.info(
        "content_summary_generated",
        url=page.url,
        provider=response_provider,
        model=response_model,
        tokens=attempts[-1].tokens_used if attempts else 0,
        cost=attempts[-1].cost_usd if attempts else 0.0,
        seconds=round(total_duration, 3),
        confidence=round(confidence, 3),
        quality=round(quality_score, 3),
    )
    summary = ContentSummary(
        page_url=page.url,
        purpose=summary_payload["purpose"],
        target_users=summary_payload["target_users"],
        business_context=summary_payload["business_context"],
        user_journey=summary_payload["user_journey"],
        navigation_role=summary_payload["navigation_role"],
        business_logic=summary_payload["business_logic"],
        confidence=confidence,
        processing_seconds=total_duration,
        quality_score=quality_score,
        validation_issues=tuple(validation_messages),
        context_highlights=context_highlights,
        debug=AnalysisDebug(prompt=prompt, attempts=tuple(attempts)),
    )
    return summary


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


def _validate_summary_schema(page_url: str, raw_content: str) -> tuple[dict[str, str | None], list[str]]:
    try:
        payload = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise LLMValidationError(
            f"Response is not valid JSON for {page_url}", details={"error": str(exc)}
        ) from exc
    if not isinstance(payload, dict):
        raise LLMValidationError(
            f"LLM response for {page_url} must be a JSON object", details={"type": type(payload).__name__}
        )

    required = (
        "purpose",
        "target_users",
        "business_context",
        "user_journey",
        "navigation_role",
        "business_logic",
    )
    normalized: dict[str, str | None] = {}
    for field in required:
        value = payload.get(field)
        if not isinstance(value, str):
            raise LLMValidationError(
                f"Field '{field}' missing or not a string for {page_url}",
                details={"field": field, "received": value},
            )
        cleaned = value.strip()
        if not cleaned:
            raise LLMValidationError(
                f"Field '{field}' is empty for {page_url}",
                details={"field": field},
            )
        normalized[field] = cleaned

    issues: list[str] = []
    confidence_value = payload.get("confidence")
    if confidence_value is None:
        issues.append("confidence field missing")
    else:
        try:
            numeric = float(confidence_value)
        except (TypeError, ValueError):
            issues.append("confidence value not numeric")
            numeric = None
        else:
            if not 0.0 <= numeric <= 1.0:
                issues.append("confidence outside expected range")
                numeric = max(0.0, min(numeric, 1.0))
        normalized["confidence"] = numeric
    return normalized, issues


def _heuristic_confidence(page: PageAnalysis) -> float:
    score = 0.5
    if page.text_length > 500:
        score += 0.1
    if page.element_summary.forms > 0 and "form" in page.functionality.categories:
        score += 0.1
    return min(score, 0.9)


def _score_summary_quality(values: Iterable[str | None], confidence: float, issues: Iterable[str]) -> float:
    strings = [value for value in values if isinstance(value, str)]
    completeness = len(strings) / 6
    penalty = min(0.3, 0.05 * sum(1 for _ in issues))
    blended = 0.6 * completeness + 0.4 * confidence - penalty
    return max(0.0, min(1.0, round(blended, 3)))


def _context_snippets(payload: Mapping[str, str | None]) -> tuple[str, ...]:
    highlights = [
        payload.get("purpose"),
        payload.get("business_context"),
        payload.get("user_journey"),
    ]
    return tuple(value for value in highlights if isinstance(value, str))


def _model_attempt_order(initial_alias: str) -> list[str]:
    order = [initial_alias]
    if initial_alias != "fallback":
        order.append("fallback")
    return order


def _fallback_summary(
    page: PageAnalysis,
    issues: tuple[str, ...],
    prompt: str,
    attempts: tuple[DebugAttempt, ...],
    duration: float,
) -> ContentSummary:
    heuristic_confidence = _heuristic_confidence(page)
    highlights = (
        f"Heuristic purpose derived from title: {page.title}",
        "LLM summary unavailable; using structural heuristics",
    )
    validation = issues + ("LLM responses invalid; heuristic fallback used",)
    logger.warning(
        "content_summary_heuristic_fallback",
        url=page.url,
        confidence=heuristic_confidence,
        issues=validation,
    )
    return ContentSummary(
        page_url=page.url,
        purpose=page.title or page.url,
        target_users="Unknown user segments",
        business_context="Context inferred from page metadata",
        user_journey="Unable to determine due to invalid LLM responses",
        navigation_role=", ".join(page.functionality.categories) or "unspecified",
        business_logic="Not captured",
        confidence=heuristic_confidence,
        processing_seconds=duration,
        quality_score=0.2,
        validation_issues=validation,
        context_highlights=highlights,
        debug=AnalysisDebug(prompt=prompt, attempts=attempts),
    )
