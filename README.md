# Legacy Web MCP Server

[![PyPI version](https://badge.fury.io/py/legacy-web-mcp.svg)](https://pypi.org/project/legacy-web-mcp/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Legacy Web MCP Server implements the Model Context Protocol (MCP) to power automated discovery and analysis of legacy web applications. This AI-powered tool helps development teams automatically crawl websites, analyze site structure, and generate comprehensive documentation artifacts for modernization planning.

**🚀 Now available on PyPI!** Install and run globally with `uvx legacy-web-mcp`

## Getting Started

## Quick Start

### For Most Users (Recommended)

```bash
# Install uvx (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run the MCP server directly from PyPI
uvx legacy-web-mcp
```

That's it! The server is ready for MCP connections.

## Detailed Installation Steps

### Step 1: Install uvx

The Legacy Web MCP Server uses `uvx` for isolation and easy installation. Install it if you haven't already:

#### On macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### On Windows:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Verify Installation:
```bash
uvx --version
```

### Step 2: Install Legacy Web MCP Server

#### Option A: Direct Execution (Recommended)
```bash
# Run directly from PyPI - no installation required
uvx legacy-web-mcp
```

#### Option B: Global Installation
```bash
# Install globally and run
uvx install legacy-web-mcp
legacy-web-mcp
```

#### Option C: Specific Version
```bash
# Install specific version
uvx --from legacy-web-mcp==0.1.1 legacy-web-mcp
```

### Step 3: Verify Installation

```bash
# Check version
uvx legacy-web-mcp --version

# Show help
uvx legacy-web-mcp --help

# Test server startup (Ctrl+C to stop)
uvx legacy-web-mcp
```

## Claude Desktop Configuration

### Step 1: Locate Configuration File

**📍 Find your Claude Desktop configuration file:**

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/claude-desktop/config.json`

### Step 2: Add MCP Server Configuration

**📝 Edit the configuration file** and add the Legacy Web MCP Server:

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["legacy-web-mcp"],
      "env": {
        "OPENAI_API_KEY": "your_openai_key_here",
        "ANTHROPIC_API_KEY": "your_anthropic_key_here",
        "GEMINI_API_KEY": "your_gemini_key_here",
        "STEP1_MODEL": "gpt-4o-mini",
        "STEP2_MODEL": "gpt-4o-mini",
        "FALLBACK_MODEL": "gpt-4o-mini",
        "OPENAI_CHAT_MODEL": "gpt-4o-mini",
        "ANTHROPIC_CHAT_MODEL": "claude-3-haiku-20240307",
        "GEMINI_CHAT_MODEL": "gemini-1.5-flash",
        "PLAYWRIGHT_HEADLESS": "true",
        "MAX_CONCURRENT_PAGES": "3",
        "OUTPUT_ROOT": "docs/web_discovery"
      }
    }
  }
}
```

**If you already have other MCP servers configured:**

```json
{
  "mcpServers": {
    "existing-server": {
      "command": "existing-command",
      "args": ["existing-args"]
    },
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["legacy-web-mcp"],
      "env": {
        "OPENAI_API_KEY": "your_openai_key_here",
        "ANTHROPIC_API_KEY": "your_anthropic_key_here",
        "GEMINI_API_KEY": "your_gemini_key_here",
        "STEP1_MODEL": "gpt-4o-mini",
        "STEP2_MODEL": "gpt-4o-mini",
        "FALLBACK_MODEL": "gpt-4o-mini",
        "OPENAI_CHAT_MODEL": "gpt-4o-mini",
        "ANTHROPIC_CHAT_MODEL": "claude-3-haiku-20240307",
        "GEMINI_CHAT_MODEL": "gemini-1.5-flash",
        "PLAYWRIGHT_HEADLESS": "true",
        "MAX_CONCURRENT_PAGES": "3",
        "OUTPUT_ROOT": "docs/web_discovery"
      }
    }
  }
}
```

### Step 3: Configure Environment Variables

**🔐 Important:** Replace the placeholder values with your actual API keys and desired configuration.

**Security Note:** For better security, you can use environment variable references instead:

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["legacy-web-mcp"],
      "env": {
        "OPENAI_API_KEY": "${OPENAI_API_KEY}",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}",
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "STEP1_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

Then set the environment variables in your shell profile:

```bash
export OPENAI_API_KEY="your_openai_key_here"
export ANTHROPIC_API_KEY="your_anthropic_key_here"
export GEMINI_API_KEY="your_gemini_key_here"
```

### Step 4: Restart Claude Desktop

1. **Quit Claude Desktop completely**
2. **Restart Claude Desktop**
3. **Look for the MCP connection indicator** (🔌 icon)
4. **Verify connection** - you should see "legacy-web-mcp" in the MCP panel

## Environment Configuration (Optional)

For AI-powered analysis features, configure LLM providers:

### Step 1: Create Environment File

```bash
# If using development version, copy template
cp .env.template .env
```

### Step 2: Configure LLM Providers

Edit `.env` with your API keys:

```bash
# LLM Providers (choose one or more)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here

# Model Configuration (Required if using LLMs)
STEP1_MODEL=gpt-4o-mini
STEP2_MODEL=gpt-4o-mini
FALLBACK_MODEL=gpt-4o-mini

# Provider-specific chat models
OPENAI_CHAT_MODEL=gpt-4o-mini
ANTHROPIC_CHAT_MODEL=claude-3-haiku-20240307
GEMINI_CHAT_MODEL=gemini-1.5-flash

# Browser & Concurrency Settings
PLAYWRIGHT_HEADLESS=true
MAX_CONCURRENT_PAGES=3

# Output Directory
OUTPUT_ROOT=docs/web_discovery
```


### Step 3: Install Browser Dependencies (Optional)

For enhanced website crawling:

```bash
# Install Playwright browsers
uvx --from legacy-web-mcp playwright install
```

## Available MCP Tools

The server provides comprehensive website analysis and documentation tools:

### 🔍 **Discovery & Analysis Tools**
- **`discover_website`** - Comprehensive website structure discovery via sitemap/crawling
- **`analyze_legacy_site`** - Complete automated analysis workflow for legacy applications
- **`intelligent_analyze_site`** - AI-driven website analysis with natural language insights
- **`analyze_with_recommendations`** - Analysis with AI-powered modernization recommendations

### 📊 **System & Health Tools**
- **`ping`** - Server health and status information
- **`health_check`** - Comprehensive system health report with diagnostics
- **`validate_dependencies`** - Check Playwright browser installations
- **`test_llm_connectivity`** - Verify LLM provider connections and API health
- **`show_config`** - Display current configuration (redacted for security)

### 📁 **File Management & Documentation**
- **`setup_project_documentation_structure`** - Create project documentation folders
- **`organize_project_artifacts`** - Organize analysis results into project structure
- **`generate_master_analysis_report`** - Create comprehensive analysis reports
- **`generate_url_slug`** - Convert URLs to safe filenames
- **`create_gitignore_for_web_discovery`** - Generate version control guidance

### 🔧 **Browser & Workflow Tools**
- **`validate_browser_dependencies`** - Detailed browser installation status
- **`get_browser_metrics`** - Performance metrics for browser sessions
- **`execute_sequential_workflow`** - Multi-page analysis workflows
- **`capture_page_screenshot`** - Page screenshot capture
- **`simulate_page_interactions`** - Interactive element discovery and testing

### 🛠️ **Debugging & Development Tools**
- **`inspect_debug_session`** - Analysis debugging and quality inspection
- **`list_analysis_artifacts`** - View available analysis results
- **`export_analysis_artifacts`** - Export analysis data for external use
- **`validate_analysis_quality`** - Quality scoring and validation
- **`cleanup_old_artifacts`** - Maintenance and cleanup operations

## Testing Your Installation

### Basic Functionality Test

```bash
# Test server version
uvx legacy-web-mcp --version

# Test help command
uvx legacy-web-mcp --help
```

### MCP Integration Test

With Claude Desktop running and configured:

1. **Start a conversation in Claude Desktop**
2. **Look for the MCP connection indicator** (🔌)
3. **Try a simple command** like asking Claude to "check the health of the legacy web MCP server"

### Direct Tool Testing

```bash
# Clone the repository for testing scripts
git clone https://github.com/hieutrtr/web-discovery-mcp.git
cd web-discovery-mcp

# Test basic tools
uv run python scripts/test_mcp_client.py ping
uv run python scripts/test_mcp_client.py health_check

# Test website discovery
uv run python scripts/test_mcp_client.py discover_website https://example.com

# Test AI analysis (requires LLM configuration)
uv run python scripts/test_mcp_client.py analyze_legacy_site https://example.com
```

## Advanced Configuration Options

### Using Development Version

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uv",
      "args": ["run", "legacy-web-mcp"],
      "cwd": "/path/to/web-discovery-mcp"
    }
  }
}
```

### Using Local Build

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["--from", ".", "legacy-web-mcp"],
      "cwd": "/path/to/web-discovery-mcp"
    }
  }
}
```

### Using Specific Version

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["--from", "legacy-web-mcp==0.1.1", "legacy-web-mcp"]
    }
  }
}
```

## Troubleshooting

### MCP Connection Issues

**Problem:** Claude Desktop doesn't show MCP connection

**Solutions:**
1. **Check configuration file location and syntax**
   ```bash
   # Verify file exists and is valid JSON
   cat ~/.config/claude-desktop/config.json | jq .
   ```

2. **Test uvx installation**
   ```bash
   uvx --version
   uvx legacy-web-mcp --version
   ```

3. **Check Claude Desktop logs** (if available)

4. **Restart Claude Desktop completely**

### Server Startup Issues

**Problem:** Server fails to start

**Solutions:**
1. **Check Python version**
   ```bash
   python3 --version  # Should be 3.11+
   ```

2. **Reinstall the package**
   ```bash
   uvx uninstall legacy-web-mcp
   uvx install legacy-web-mcp
   ```

3. **Check for port conflicts**
   ```bash
   # Test basic startup
   uvx legacy-web-mcp --help
   ```

### Browser Dependencies Issues

**Problem:** Browser automation fails

**Solutions:**
1. **Install Playwright browsers**
   ```bash
   uvx --from legacy-web-mcp playwright install
   ```

2. **Validate installation**
   ```bash
   uv run python scripts/test_mcp_client.py validate_dependencies
   ```

3. **Check system requirements** for Playwright

### LLM Configuration Issues

**Problem:** AI analysis tools fail

**Solutions:**
1. **Verify API keys in environment**
   ```bash
   # For development setup
   grep -E "API_KEY|MODEL" .env
   ```

2. **Test LLM connectivity**
   ```bash
   uv run python scripts/test_mcp_client.py test_llm_connectivity
   ```

3. **Check model configuration**
   ```bash
   uv run python scripts/test_mcp_client.py show_config
   ```

## What It Does

The Legacy Web MCP Server automatically:

- **🔍 Discovers** website structure via sitemaps and intelligent crawling
- **🧠 Analyzes** legacy applications using AI-powered insights
- **📊 Documents** findings in comprehensive reports
- **🔧 Recommends** modernization strategies and technical approaches
- **📁 Organizes** results in structured project documentation

Perfect for development teams planning legacy application modernization, conducting technical audits, or understanding complex website architectures.

## Getting Help

### Support Resources

- **GitHub Issues:** [Report bugs or request features](https://github.com/hieutrtr/web-discovery-mcp/issues)
- **PyPI Package:** [View package details](https://pypi.org/project/legacy-web-mcp/)
- **Documentation:** Check the `docs/` directory for detailed guides

### Common Questions

**Q: Do I need to install Python separately?**
A: No, `uvx` manages Python environments automatically.

**Q: Can I use this with other MCP clients?**
A: Yes, any MCP-compatible client should work.

**Q: Do I need LLM API keys to use basic features?**
A: No, website discovery works without LLM configuration. AI analysis features require API keys.

**Q: How do I update to a newer version?**
A: Run `uvx install --force legacy-web-mcp` or use `uvx` directly which always uses the latest version.

## Next Steps

After successful installation:

1. **Try basic website discovery** with Claude Desktop
2. **Configure LLM providers** for AI-powered analysis
3. **Explore the available tools** in the MCP interface
4. **Check the documentation** for advanced usage patterns

Happy analyzing! 🚀

## License

Distributed under the MIT License. See `LICENSE` for details.
