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

- Copy `.env.template` to `.env` and populate your LLM provider keys and model names.
- Override non-secret defaults via `config/default.yaml` (or your own config file). Values in this file are merged on top of environment settings when the server boots.
- Inspect the active configuration (with secrets redacted) through the `show_config` MCP tool, for example:

  ```bash
  uv run python scripts/diagnostics_client.py health    # Shows health and config summary
  uv run python scripts/diagnostics_client.py list      # Lists available tools/resources
  uv run python scripts/diagnostics_client.py status    # Live system metrics
  ```

  The `show_config` tool backs the health summary and can be called directly in MCP-aware IDEs.

- Default output folders, concurrency limits, and timeouts are documented in `config/default.yaml` and `docs/stories/1.3.basic-configuration-management.md`.

## Continuous Integration

GitHub Actions workflow in `.github/workflows/ci.yml` runs linting, typing, and tests against Python 3.11 using uv. The workflow keeps dependencies consistent with the local development setup.

## License

Distributed under the MIT License. See `LICENSE` for details.
