# Legacy Web MCP Server - Developer Commands & Guidelines

## Essential Commands

```bash
# Setup (first time only)
uv sync --dev
uv run playwright install

# Linting & Formatting
uv run ruff check      # Check code style issues
uv run ruff format     # Auto-format code
uv run mypy src tests  # Type checking

# Testing
uv run pytest                                      # Run all tests
uv run pytest tests/unit/test_analysis.py         # Run single file
uv run pytest tests/unit/test_analysis.py::test_function  # Run single test
uv run pytest -k "test_name_pattern"              # Run tests matching pattern

# Development
uv run legacy-web-mcp  # Start MCP server
```

## Code Style Guidelines

**Async-First**: All I/O operations must use asyncio
**Type Hints**: Strict mypy mode enabled, use Python 3.11+ features
**Imports**: Standard lib → third party → local, ruff enforces order
**Naming**: snake_case for functions/variables, PascalCase for classes
**Docstrings**: Google style for modules and public callables
**Line Length**: 100 characters max (ruff configuration)
**Error Handling**: Use structured logging (structlog), never swallow exceptions blindly

## Testing Guidelines

**Structure**: Mirror source layout in `tests/unit/`
**Naming**: `test_*.py` for test files, descriptive test function names
**Coverage**: 90%+ target for unit tests
**Async**: Use `@pytest.mark.asyncio` for async functions
**Fixtures**: Place shared test data in `tests/fixtures/`
**Mock**: Always mock external APIs (LLM, browser) and I/O operations

## File Organization

- `src/legacy_web_mcp/` - Main package
- `mcp/` - MCP server and tool implementations
- `browser/` - Playwright automation
- `llm/` - Model providers (Anthropic, OpenAI, Gemini)
- `discovery/` - Web crawling and URL discovery
- `storage/` - File-based project persistence
- `shared/` - Reusable utilities

## Key Patterns

**Dependency Injection**: Use pure modules, import from `src/deps.ts`
**Configuration**: Load from `config/default.yaml`, override with env vars
**State**: File-based storage (JSON/YAML), no database dependency
**Testing**: Always test success and error paths, verify async/await usage