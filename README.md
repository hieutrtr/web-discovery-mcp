# Legacy Web MCP Server

Legacy Web MCP Server implements the Model Context Protocol (MCP) to power automated analysis of legacy web applications. This repository provides the backend foundation for crawling websites, running multi-step LLM analysis, and generating documentation artifacts that help teams plan modernization efforts.

## Getting Started

### Prerequisites

- Python 3.11
- [uv](https://github.com/astral-sh/uv) for dependency management
- Playwright browsers (`uv run playwright install` will install them later stories)

### Installation

```bash
uv sync
```

The command creates a virtual environment under `.venv/` and installs runtime and development dependencies.

### Running the Server

```bash
uv run legacy-web-mcp
```

The entry point starts a FastMCP stdio server with a `ping` tool that reports status metadata.

## Development Tooling

- **Linting & Formatting:** `uv run ruff check` and `uv run ruff format`
- **Static Typing:** `uv run mypy`
- **Testing:** `uv run pytest`

CI runs these same commands on every push via GitHub Actions.

## Repository Layout

```
src/legacy_web_mcp/        # Application source code
└── mcp/                   # FastMCP bootstrap and core tools
└── shared/                # Cross-cutting utilities (logging, constants, ...)

tests/                    # pytest suites
├── unit/                  # Unit tests mirroring src modules
├── integration/           # Integration tests (future stories)
└── fixtures/              # Test assets

scripts/                   # Helper CLI scripts (reserved for later use)
```

Detailed architectural guidance lives in `docs/architecture.md` and related documents under `docs/`.

## Configuration

Secrets and settings are provided via environment variables. Copy `.env.template` to `.env` and fill in provider keys before running features that depend on them.

```bash
cp .env.template .env
```

Additional configuration layers (YAML/JSON files) arrive in Story 1.3.

## Continuous Integration

GitHub Actions workflow in `.github/workflows/ci.yml` runs linting, typing, and tests against Python 3.11 using uv. The workflow keeps dependencies consistent with the local development setup.

## License

Distributed under the MIT License. See `LICENSE` for details.
