# Scripts for Manual Testing

This folder contains scripts to help you manually test the Legacy Web MCP Server functionality.

## Prerequisites

Make sure you have the project dependencies installed:

```bash
uv sync
```

## Scripts

### 1. `manual_test.py` - Comprehensive Testing Suite

A comprehensive testing script that tests all major functionality of the MCP server.

**Usage:**
```bash
# Run all tests interactively
python scripts/manual_test.py all

# Test specific components
python scripts/manual_test.py health
python scripts/manual_test.py config
python scripts/manual_test.py projects
python scripts/manual_test.py discover [url]
```

**Examples:**
```bash
# Test health checks and diagnostics
python scripts/manual_test.py health

# Test configuration management
python scripts/manual_test.py config

# Test website discovery with a specific URL
python scripts/manual_test.py discover https://github.com

# Test project management
python scripts/manual_test.py projects
```

### 2. `test_mcp_client.py` - Direct MCP Tool Testing

Creates an MCP server context and enables direct testing of most tools without requiring an external MCP client.

**Usage:**
```bash
# Show available tools and usage guidance
python scripts/test_mcp_client.py

# Test specific tools directly
python scripts/test_mcp_client.py ping
python scripts/test_mcp_client.py health_check
python scripts/test_mcp_client.py show_config
python scripts/test_mcp_client.py validate_dependencies

# Note: discover_website requires full MCP session - use test_discovery_direct.py instead
```

### 3. `test_discovery_direct.py` - Direct Discovery Testing

Tests website discovery functionality directly without MCP context requirements.

**Usage:**
```bash
# Test discovery on any website
python scripts/test_discovery_direct.py [URL]
```

**Examples:**
```bash
# Test on example sites
python scripts/test_discovery_direct.py https://example.com
python scripts/test_discovery_direct.py https://github.com
python scripts/test_discovery_direct.py https://context7.com
python scripts/test_discovery_direct.py https://your-website.com
```

### 4. `test_browser_session.py` - Browser Session Management Testing

Tests the Playwright browser session management features from Story 2.1, including multi-engine support, concurrency control, crash recovery, and performance metrics.

**Usage:**
```bash
# Run all browser session tests
python scripts/test_browser_session.py all

# Test specific components
python scripts/test_browser_session.py engines      # Multi-engine support
python scripts/test_browser_session.py concurrency # Concurrent session limits
python scripts/test_browser_session.py lifecycle   # Session lifecycle management
python scripts/test_browser_session.py recovery    # Crash detection and recovery
python scripts/test_browser_session.py metrics     # Performance metrics collection
python scripts/test_browser_session.py install     # Browser installation validation
```

**Examples:**
```bash
# Validate browser installation
python scripts/test_browser_session.py install

# Test concurrency control
python scripts/test_browser_session.py concurrency

# Run complete test suite
python scripts/test_browser_session.py all
```

## Available MCP Tools

The server provides these tools that you can test:

| Tool | Description | Arguments |
|------|-------------|-----------|
| `health_check` | Check server health and status | None |
| `validate_dependencies` | Validate Playwright and other dependencies | None |
| `test_llm_connectivity` | Test LLM provider connectivity | None |
| `show_config` | Show current configuration (redacted) | None |
| `discover_website` | Discover website structure | `url` (string) |

## Environment Setup

### Required Environment Variables

For full functionality, set up these environment variables in `.env`:

```bash
# LLM API Keys (at least one required for LLM connectivity tests)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional: Output directory (defaults to current directory)
OUTPUT_ROOT=/path/to/output/directory

# Optional: Discovery settings
DISCOVERY_TIMEOUT=30
DISCOVERY_MAX_DEPTH=3
```

### Playwright Setup

For dependency validation tests, ensure Playwright browsers are installed:

```bash
uv run playwright install
```

## Expected Output

### Successful Health Check
```
✅ Health check passed: {'status': 'ok', 'server_name': 'Legacy Web MCP Server', ...}
```

### Successful Website Discovery
```
✅ Website discovery completed!
📊 Project ID: example-com_20250919-123456
🌐 Domain: example.com
📈 Total URLs: 15
📄 Internal pages: 8
🔗 External pages: 2
📎 Assets: 5
```

### Configuration Display
```
✅ Configuration retrieved:
{
  "OUTPUT_ROOT": "/current/directory",
  "DISCOVERY_TIMEOUT": 30,
  "DISCOVERY_MAX_DEPTH": 3,
  ...
}
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root and have installed dependencies with `uv sync`

2. **Permission Errors**: Ensure the output directory is writable

3. **Network Timeouts**: Check your internet connection for website discovery tests

4. **Missing Dependencies**: Run `uv run playwright install` to install browser dependencies

5. **API Key Errors**: Set up environment variables for LLM connectivity tests

### Debug Mode

For more detailed error information, you can modify the scripts to enable debug logging or run with Python's verbose mode:

```bash
python -v scripts/manual_test.py all
```

## Integration with Real MCP Clients

These scripts test the server functionality directly. To test with real MCP clients (like Claude Desktop), you would:

1. Start the server: `uv run python -m legacy_web_mcp`
2. Configure your MCP client to connect to the server
3. Use the tools through the client interface

The scripts in this folder help validate that the server works correctly before integrating with external clients.