# Legacy Web Application Analysis MCP Server

This repository implements the Legacy Web Application Analysis MCP Server. The project is built with
Python 3.11, FastMCP, and Playwright to automate discovery and analysis of legacy web sites and
produce documentation ready for modernization efforts.

## Getting Started

1. **Install dependencies** using [uv](https://github.com/astral-sh/uv) (recommended) or `pip`:

   ```bash
   uv pip install -e .[dev]
   uv pip install playwright
   playwright install
   ```

2. **Configure environment variables** by copying the template:

   ```bash
   cp .env.template .env
   ```

   Populate your LLM provider API keys and default model preferences.

3. **Run the server** (once the FastMCP entrypoint is fully implemented):

   ```bash
   python -m legacy_web_mcp.mcp.server
   ```

4. **Execute quality checks**:

   ```bash
   ruff check src tests
   mypy src
   pytest
   ```

## Repository Layout

- `src/legacy_web_mcp/` – Production source code, following the modular monolith structure
- `tests/` – Unit and integration test suites
- `docs/` – PRD, architecture guidance, developer standards, and story documents
- `scripts/` – Utility scripts (if needed)

Refer to `docs/architecture/source-tree.md` for the canonical repository structure and naming
conventions.

## Contributing

1. Branch from `main`
2. Implement the assigned story and ensure tests pass
3. Update documentation as needed
4. Submit a pull request with a clear summary referencing the story id

## License

This project is released under the MIT License.
