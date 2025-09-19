# Legacy Web MCP Server

Legacy Web MCP Server implements the Model Context Protocol (MCP) to power automated discovery and analysis of legacy web applications. This repository provides the backend foundation for crawling websites, analyzing site structure, and generating comprehensive documentation artifacts that help teams understand and plan modernization efforts.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management
- Optional: Playwright browsers for enhanced crawling (`uv run playwright install`)

### Installation

```bash
uv sync
```

The command creates a virtual environment under `.venv/` and installs runtime and development dependencies.

### Running the Server

```bash
uv run legacy-web-mcp
```

The entry point starts a FastMCP stdio server that provides comprehensive website discovery and analysis tools.

## Development Tooling

- **Linting & Formatting:** `uv run ruff check` and `uv run ruff format`
- **Static Typing:** `uv run mypy`
- **Testing:** `uv run pytest`

CI runs these same commands on every push via GitHub Actions.

## Available MCP Tools

The server provides the following tools:

- **`ping`** - Server health and status information
- **`health_check`** - Comprehensive system health report
- **`validate_dependencies`** - Check Playwright browser installations
- **`test_llm_connectivity`** - Verify LLM provider connections
- **`show_config`** - Display current configuration (redacted)
- **`discover_website`** - Discover and analyze website structure

## Testing and Development

### Manual Testing Scripts

The `scripts/` directory contains comprehensive testing tools with full MCP support:

```bash
# Interactive testing of all tools
python scripts/test_mcp_client.py

# Test ALL tools directly via MCP client (including discover_website!)
python scripts/test_mcp_client.py ping
python scripts/test_mcp_client.py health_check
python scripts/test_mcp_client.py show_config
python scripts/test_mcp_client.py validate_dependencies
python scripts/test_mcp_client.py test_llm_connectivity
python scripts/test_mcp_client.py discover_website https://context7.com

# Alternative direct testing (bypasses MCP layer)
python scripts/test_discovery_direct.py https://example.com
python scripts/test_discovery_direct.py https://github.com

# Comprehensive test suite
python scripts/manual_test.py all
python scripts/manual_test.py health
python scripts/manual_test.py discover https://context7.com
```

**✨ New Feature**: The MCP client script now supports **all tools including `discover_website`** with a mock MCP session context that provides full logging and progress reporting!

### Quick Demo

```bash
# Test website discovery via MCP client
uv run python scripts/test_mcp_client.py discover_website https://context7.com

# Output includes real-time MCP logging:
# [INFO] Validated target URL: https://context7.com
# [INFO] Initialized project context7-com_20250919-052810
# [INFO] Analyzed robots.txt directives
# [INFO] Manual crawl discovered 4 URLs
# ✅ Success! Full JSON result with discovered URLs
```

See `scripts/README.md` for detailed usage instructions.

## Repository Layout

```
src/legacy_web_mcp/        # Application source code
├── mcp/                   # FastMCP bootstrap and MCP tools
├── discovery/             # Website discovery and crawling engine
├── storage/              # Project and data persistence
├── config/               # Configuration management
└── shared/               # Cross-cutting utilities

docs/                     # Documentation and specifications
├── architecture.md       # System architecture overview
├── mcp-context.md        # MCP Context system documentation
├── stories/              # Epic and story documentation
└── web_discovery/        # Discovery output examples

scripts/                  # Manual testing and development tools
tests/                    # pytest test suites
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Architecture Overview](docs/architecture.md)** - System design and component interaction
- **[MCP Context Guide](docs/mcp-context.md)** - Understanding the MCP Context system, testing approaches, and best practices
- **[Story Documentation](docs/stories/)** - Epic and user story specifications
- **[Discovery Examples](docs/web_discovery/)** - Sample website discovery outputs

## Configuration

### Environment Setup

1. **Optional**: Copy `.env.template` to `.env` and configure your environment:
   ```bash
   # LLM API Keys (for future AI-powered analysis features)
   OPENAI_API_KEY=your_openai_key_here
   ANTHROPIC_API_KEY=your_anthropic_key_here
   GEMINI_API_KEY=your_gemini_key_here

   # Discovery settings
   DISCOVERY_TIMEOUT=60
   DISCOVERY_MAX_DEPTH=3
   OUTPUT_ROOT=docs/web_discovery
   ```

2. **Install Playwright browsers** (optional, for enhanced crawling):
   ```bash
   uv run playwright install
   ```

### Configuration Management

- **Check current configuration**: Use the `show_config` tool to inspect active settings
  ```bash
  python scripts/test_mcp_client.py show_config
  ```

- **Health monitoring**: Get comprehensive system status
  ```bash
  python scripts/test_mcp_client.py health_check
  ```

- **Validate dependencies**: Check Playwright browser installations
  ```bash
  python scripts/test_mcp_client.py validate_dependencies
  ```

Default settings and configuration documentation are in `docs/stories/1.3.basic-configuration-management.md`.

## Website Discovery Features

The server provides comprehensive website discovery capabilities:

### Discovery Methods
- **Sitemap parsing** - Automatically finds and parses XML sitemaps
- **Robots.txt analysis** - Extracts allowed/disallowed paths and additional sitemaps
- **Intelligent crawling** - Discovers internal pages, external links, and static assets

### Output Formats
- **JSON inventory** - Machine-readable site structure data
- **YAML inventory** - Human-readable site structure overview
- **Project metadata** - Discovery configuration and statistics

### Quick Start Examples

```bash
# Discover a website structure
python scripts/test_discovery_direct.py https://example.com

# Discover with comprehensive output
python scripts/manual_test.py discover https://context7.com
```

Discovery results are stored in `docs/web_discovery/` with timestamped project folders containing:
- `discovery/inventory.json` - Complete site structure
- `discovery/inventory.yaml` - Human-readable overview
- `metadata.json` - Project configuration and stats

## Continuous Integration

GitHub Actions workflow in `.github/workflows/ci.yml` runs linting, typing, and tests against Python 3.11 using uv. The workflow keeps dependencies consistent with the local development setup.

## License

Distributed under the MIT License. See `LICENSE` for details.
