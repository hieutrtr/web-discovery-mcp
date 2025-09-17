# Tech Stack Reference

This document summarizes the technology choices defined for the Legacy Web Application Analysis MCP Server. It is derived from `docs/architecture.md#tech-stack` and should guide dependency management, tooling, and operational decisions.

## Core Runtime
- **Language:** Python 3.11
- **Async Runtime:** `asyncio`
- **Package Manager:** `uv` (preferred) with `uvx` for execution
- **Packaging:** `setuptools`

## Frameworks & Libraries
- **MCP Framework:** FastMCP 2.12.0 (JSON-RPC 2.0 server)
- **Browser Automation:** Playwright 1.55.0 (Chromium, Firefox, WebKit support)
- **HTTP Client:** `aiohttp` 3.12.15 for async LLM integrations
- **Configuration:** `pydantic-settings` 2.10.1 for typed settings from environment/config files
- **Logging:** `structlog` 25.4.0 with JSON output
- **Retry/Backoff:** Use `tenacity` or custom retry per architecture error policy (exponential backoff)

## Quality & Tooling
- **Linting/Formatting:** `ruff` 0.13.0 (enforce PEP 8 + import sorting)
- **Static Typing:** `mypy` 1.18.1
- **Unit/Integration Testing:** `pytest` 8.4.2 with `pytest-asyncio` 1.2.0
- **Browser Testing:** Leverage Playwright testing fixtures for headless runs
- **Security Scanning:** `bandit` (per architecture security guidance)

## LLM Providers
- **Primary Providers:** OpenAI, Anthropic, Gemini
- **Provider Access:** Managed through the LLM Provider Facade (Story 3.1)
- **Model Configuration:** Environment-driven (`STEP1_MODEL`, `STEP2_MODEL`, `FALLBACK_MODEL`)

## Data & Storage
- **State Storage:** File-based (JSON/YAML, Markdown) in project-specific directories
- **Documentation Outputs:** Markdown reports (`docs/web_discovery/...`)
- **Checkpoints & Metadata:** JSON structures maintained via Progress/Checkpoint services

## Observability & Metrics
- **Logging:** Structured via `structlog`
- **Metrics/Telemetry:** Collected through logging and progress tracking; optional integration with external analytics can be added later

## Developer Experience
- **CLI Integration:** Designed to operate within Claude Code, Cursor, and Gemini CLI via MCP tooling
- **Documentation:** Generated markdown artifacts accessible through MCP resources
- **Recommended IDE Setup:** VS Code or JetBrains with Python 3.11, Playwright extensions, Ruff/Mypy integration

## Deployment & Distribution
- **Distribution Target:** Python package installable via `pip`/`pipx`
- **Supported OS:** Windows, macOS, Linux
- **Installation Expectation:** <15 minutes with documented prerequisites (Playwright browsers, environment variables)

Keep this document synchronized with changes in `pyproject.toml`, CI configuration, or architecture updates to maintain alignment across teams.
