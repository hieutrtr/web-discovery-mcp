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

### 5. `test_page_navigation.py` - Page Navigation and Content Extraction Testing

Tests the page navigation and content extraction functionality from Story 2.2, including successful navigation, content extraction, screenshot capture, and error handling.

**Usage:**
```bash
# Run all navigation and extraction tests
python scripts/test_page_navigation.py all

# Test specific components
python scripts/test_page_navigation.py navigation  # Test successful navigation and content extraction
python scripts/test_page_navigation.py screenshot # Test screenshot capture functionality
python scripts/test_page_navigation.py errors     # Test handling of HTTP 404 and 403 errors
python scripts/test_page_navigation.py timeout    # Test navigation timeout handling
```

**Examples:**
```bash
# Test basic navigation functionality
python scripts/test_page_navigation.py navigation

# Test error handling
python scripts/test_page_navigation.py errors
```

### 6. `test_network_monitoring.py` - Network Traffic Monitoring Testing

Tests the network traffic monitoring functionality from Story 2.3, including traffic analysis, API endpoint detection, and third-party service identification.

**Usage:**
```bash
# Run all network monitoring tests
python scripts/test_network_monitoring.py all

# Test specific components
python scripts/test_network_monitoring.py summary     # Test network traffic summary generation
python scripts/test_network_monitoring.py api        # Test API endpoint analysis
python scripts/test_network_monitoring.py third-party # Test third-party service detection
python scripts/test_network_monitoring.py filtering  # Test static asset filtering
```

**Examples:**
```bash
# Test network traffic analysis
python scripts/test_network_monitoring.py summary

# Test API endpoint detection
python scripts/test_network_monitoring.py api
```

### 7. `test_page_interaction.py` - Page Interaction Automation Testing

Tests the page interaction automation functionality from Story 2.4, including form interactions, scrolling, hover/focus events, and modal handling.

**Usage:**
```bash
# Run all page interaction tests
python scripts/test_page_interaction.py all

# Test specific components
python scripts/test_page_interaction.py form      # Test form interaction and submission
python scripts/test_page_interaction.py scrolling # Test page scrolling to reveal content
python scripts/test_page_interaction.py hover     # Test hover and focus interactions
```

**Examples:**
```bash
# Test form interactions
python scripts/test_page_interaction.py form

# Test scrolling functionality
python scripts/test_page_interaction.py scrolling
```

### 8. `diagnostics_client.py` - MCP Diagnostics Client

A utility client for manually exercising MCP diagnostics tools and listing available capabilities.

**Usage:**
```bash
# List all available tools with descriptions
python scripts/diagnostics_client.py list

# Run diagnostic tools
python scripts/diagnostics_client.py health  # Run health check
python scripts/diagnostics_client.py deps    # Validate dependencies
python scripts/diagnostics_client.py llm     # Test LLM connectivity
python scripts/diagnostics_client.py status  # Get system status

# Specify custom server command
python scripts/diagnostics_client.py list --command uv run legacy-web-mcp

# Use custom scope for status
python scripts/diagnostics_client.py status --scope config
```

**Examples:**
```bash
# See all available tools and their descriptions
python scripts/diagnostics_client.py list

# Check server health
python scripts/diagnostics_client.py health

# Validate all dependencies
python scripts/diagnostics_client.py deps
```

### 9. `check_env.py` - Environment Variable Validation

CLI utility to ensure required environment variables are present for proper MCP server operation.

**Usage:**
```bash
# Check all required environment variables
python scripts/check_env.py

# Check specific environment variables
python scripts/check_env.py --keys OPENAI_API_KEY ANTHROPIC_API_KEY

# Quiet mode (exit codes only)
python scripts/check_env.py --quiet
```

**Examples:**
```bash
# Validate environment setup
python scripts/check_env.py

# Check only API keys
python scripts/check_env.py --keys OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY
```

## Available MCP Tools

The server provides these tools that you can test:

### Core Diagnostic Tools
| Tool | Description | Arguments |
|------|-------------|-----------|
| `health_check` | Check server health and status | None |
| `validate_dependencies` | Validate Playwright and other dependencies | None |
| `test_llm_connectivity` | Test LLM provider connectivity | None |
| `show_config` | Show current configuration (redacted) | None |
| `ping` | Report MCP server status and runtime metadata | None |

### Discovery and Configuration Tools
| Tool | Description | Arguments |
|------|-------------|-----------|
| `discover_website` | Discover website structure | `url` (string) |
| `get_project_configuration` | Get configuration for a project | `project_id` (string) |
| `update_project_configuration` | Update project configuration | `project_id`, `settings` |
| `create_project` | Create a new project | `name`, `description` |
| `list_projects` | List all projects | None |

### Browser Session Management Tools (Story 2.1)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `create_browser_session` | Create new browser session | `engine` (optional), `session_config` (optional) |
| `get_session_info` | Get information about a browser session | `session_id` |
| `list_browser_sessions` | List all active browser sessions | None |
| `close_browser_session` | Close a specific browser session | `session_id` |
| `get_session_metrics` | Get performance metrics for sessions | None |

### Page Navigation and Content Tools (Story 2.2)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `navigate_to_page` | Navigate to URL and extract page content | `url`, `timeout` (optional), `session_id` (optional) |
| `extract_page_content` | Extract content from current page | `session_id` (optional) |

### Network Monitoring Tools (Story 2.3)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `monitor_network_traffic` | Monitor network traffic during page navigation | `url`, `capture_payloads` (optional), `session_id` (optional) |
| `analyze_api_endpoints` | Analyze API endpoints discovered during navigation | `url`, `include_payloads` (optional), `session_id` (optional) |
| `monitor_third_party_services` | Monitor third-party services used by webpage | `url`, `session_id` (optional) |

### Page Interaction Tools (Story 2.4)
| Tool | Description | Arguments |
|------|-------------|-----------|
| `interact_with_page` | Perform automated interactions with webpage | `url`, `enable_form_interactions` (optional), `session_id` (optional) |
| `explore_navigation_menu` | Explore navigation menus to discover pages | `url`, `max_depth` (optional), `session_id` (optional) |
| `test_form_interactions` | Test form interactions safely | `url`, `safe_mode` (optional), `session_id` (optional) |

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