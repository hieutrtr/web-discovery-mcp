# Coding Standards

These guidelines codify the implementation expectations for the Legacy Web Application Analysis MCP Server. They build on the architecture document (`docs/architecture.md`) and apply to all source code, tests, utilities, and automation scripts.

## General Principles
- **Readability over cleverness:** Favor clear, maintainable code. Explicitness, type annotations, and docstrings are preferred to implicit behavior.
- **Async-first mindset:** All I/O, browser automation, and LLM calls must use `asyncio` patterns. Blocking calls in async contexts are prohibited.
- **Pure modules, injectable services:** Follow the modular monolith boundaries—construct services via dependency injection so components remain testable in isolation.
- **Logging & observability:** Use `structlog` with JSON-serializable payloads. Include request IDs, page IDs, and session IDs to trace analysis flows.
- **Configuration hygiene:** Fetch configuration via the central settings module (see Story 1.3). Never read environment variables directly in feature code.
- **Immutability where practical:** Prefer dataclasses with `frozen=True` for domain models (ContentSummary, FeatureAnalysis, etc.) unless mutation is required.

## Python Style
- Target **Python 3.11** features (pattern matching, dataclass kwargs, improved typing).
- Follow **PEP 8** and **PEP 484**; enforce via `ruff` and `mypy` in CI.
- Use `typing` comprehensively; prefer `list[str]` syntax and `Annotated` types where clarity improves.
- Module layout:
  - Imports ordered: standard library, third-party, local.
  - Expose public APIs via `__all__` where a module is intended for import.
  - Keep module length manageable; refactor when files exceed ~400 lines.
- Docstrings:
  - Use Google-style docstrings for modules and public callables.
  - Document coroutines with expected awaitable behavior and side effects.

## Async & Concurrency
- Use `asyncio` tasks only at orchestration boundaries; avoid global task spawning.
- Protect shared state with `asyncio.Lock` or per-project isolation.
- For Playwright sessions:
  - Manage contexts via async context managers.
  - Always close pages/contexts in `finally` blocks to avoid leaks.
- LLM requests:
  - Funnel through the provider facade (Story 3.1) which applies retry/backoff.
  - Timeouts must be configurable; never rely on provider defaults.

## Error Handling
- Raise custom exceptions derived from `LegacyWebMCPError` (see architecture doc section “Error Handling Strategy”).
- Include actionable messages and remediation hints.
- Never swallow exceptions silently; log them with context and re-raise or convert to domain errors.

## Logging
- Use the shared `structlog` configuration. Log levels:
  - `info`: lifecycle events (analysis started, page complete).
  - `warning`: recoverable issues, retries triggered.
  - `error`: failures that abort processing for a page/session.
- Log dictionaries with keys `event`, `project_id`, `page_id`, `tool`.
- Avoid logging sensitive data (API keys, credential payloads, personally identifiable information).

## Testing Strategy
- **Unit tests:** place under `tests/unit/` mirroring the source tree; cover positive/negative/edge cases.
- **Integration tests:** under `tests/integration/`; use Playwright fixtures and mock LLM responses.
- **Performance regressions:** guard critical timing (Step 1 and Step 2 analysis) using benchmarks or thresholds.
- Tests must run idempotently and independently.

## File & Commit Hygiene
- Keep imports sorted (use `ruff --fix`).
- Commit messages should reference story IDs when available (e.g., `Story 3.1: Add provider interface`).
- Update relevant documentation (`docs/web_discovery`, READMEs) whenever functionality changes.

Adhering to these standards ensures consistency across the MCP server codebase and keeps the system aligned with the approved architecture.
