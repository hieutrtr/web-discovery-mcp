# Source Tree Conventions

This guide outlines the expected repository layout for the MCP server. Use it to keep new modules, tests, and documentation consistent.

## Top-Level Structure
```
/ (repo root)
├── docs/                     # Product, architecture, and analysis artifacts
│   ├── architecture.md       # Master architecture reference
│   ├── architecture/         # Developer standards (coding, tech stack, source tree)
│   ├── prd.md                # Product requirements
│   ├── stories/              # Approved story documents
│   └── qa/                   # QA gate outputs and reports
├── src/legacy_web_mcp/       # Application source code (package name TBD)
│   ├── __init__.py
│   ├── config/               # Configuration models & loaders
│   ├── llm/                  # Provider facade, prompts, analysis pipeline
│   ├── browser/              # Playwright session & interaction services
│   ├── progress/             # Progress tracking, checkpointing
│   ├── documentation/        # Markdown generation utilities
│   ├── storage/              # File system abstractions, metadata handling
│   ├── mcp/                  # FastMCP tool/resource registration & handlers
│   └── shared/               # Common utilities, domain models, error types
├── tests/
│   ├── unit/                 # Unit tests mirroring src structure
│   ├── integration/          # Cross-service tests (Playwright, MCP, LLM)
│   └── fixtures/             # Sample HTML, network logs, LLM responses
├── scripts/                  # Optional dev scripts, tooling helpers
├── pyproject.toml            # Project configuration (dependencies, tooling)
├── uv.lock / requirements/   # Dependency lockfile (if applicable)
├── README.md                 # Setup + usage instructions
└── .github/workflows/        # CI definitions (lint, type-check, tests)
```

## Module Guidelines
- Package name should remain stable (`legacy_web_mcp` recommended). Avoid deep relative imports; use absolute package imports.
- Domain models (ContentSummary, FeatureAnalysis, etc.) live in `src/legacy_web_mcp/shared/models.py` or a dedicated models package.
- Keep MCP tool/resource registration centralized under `src/legacy_web_mcp/mcp/`.
- Shared constants (e.g., default timeouts, directory names) belong in `shared/constants.py` to prevent duplication.

## Tests
- Mirror `src` modules under `tests/unit/` (e.g., `src/legacy_web_mcp/llm/provider.py` → `tests/unit/llm/test_provider.py`).
- Integration tests may use lightweight fixture services; mark long-running Playwright tests with `@pytest.mark.slow`.
- Store HTML and JSON fixtures under `tests/fixtures/` with descriptive names (`page_login.html`, `network_checkout.json`).

## Documentation Outputs
- Analysis artifacts are written to `<project>/docs/web_discovery/...` at runtime (see Story 4.4).
- Ensure generation utilities accept a root path parameter to support multi-project scenarios.

## Tooling & Scripts
- Place maintenance scripts under `scripts/` with executable shebangs and short usage docs.
- Scripts should rely on project configuration modules rather than re-parsing environment variables.

Keeping the repository aligned with this structure ensures the developer experience remains predictable and supports the workflows defined in the architecture and PRD.
