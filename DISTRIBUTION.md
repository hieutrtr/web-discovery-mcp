# Distribution Guide for Legacy Web MCP Server

This guide explains how to package and distribute the Legacy Web MCP Server for execution with `uvx`.

## Package Structure

The project is already configured for uvx distribution with:

- ✅ **`pyproject.toml`** - Modern Python packaging configuration
- ✅ **`fastmcp.json`** - FastMCP CLI configuration
- ✅ **Entry points** - Console scripts for `legacy-web-mcp` and `legacy-web-mcp-server`
- ✅ **Dependencies** - FastMCP 2.12.0 and required packages

## Local Testing

### Verify Local uvx Execution

```bash
# Test version command
uvx --from . legacy-web-mcp --version

# Test help command  
uvx --from . legacy-web-mcp --help

# Test configuration check
uvx --from . legacy-web-mcp --config-check
```

### Test MCP Server Functionality

```bash
# Start the server (Ctrl+C to stop)
uvx --from . legacy-web-mcp

# Test with MCP client
python scripts/test_mcp_client.py ping
```

## Distribution Methods

### 1. GitHub Repository Distribution

Users can run directly from your GitHub repository:

```bash
# Run from GitHub (replace with your actual repository URL)
uvx --from git+https://github.com/your-username/web-discovery-mcp-claude-1.git legacy-web-mcp
```

**Requirements:**
- Public GitHub repository
- Tagged releases (recommended)
- Updated repository URL in `pyproject.toml`

### 2. PyPI Distribution

For wider distribution, publish to PyPI:

#### Build and Upload

```bash
# Install build tools
uv add --dev build twine

# Build distribution packages
uv run python -m build

# Upload to PyPI (requires PyPI account and API token)
uv run twine upload dist/*
```

#### User Installation

Once published on PyPI:

```bash
# Users can run directly
uvx legacy-web-mcp
```

### 3. Private Package Index

For enterprise environments:

```bash
# Upload to private index
uv run twine upload --repository-url https://your-private-index.com/simple/ dist/*

# Users install from private index
uvx --index-url https://your-private-index.com/simple/ legacy-web-mcp
```

## MCP Client Configuration Examples

### Claude Desktop

Add to `~/.config/claude-desktop/config.json`:

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/your-username/web-discovery-mcp-claude-1.git",
        "legacy-web-mcp"
      ],
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

### Generic MCP Client

```json
{
  "servers": {
    "legacy-web-mcp": {
      "command": ["uvx", "legacy-web-mcp"],
      "transport": "stdio",
      "env": {
        "OPENAI_API_KEY": "your_openai_key_here",
        "ANTHROPIC_API_KEY": "your_anthropic_key_here",
        "GEMINI_API_KEY": "your_gemini_key_here",
        "STEP1_MODEL": "gpt-4o-mini",
        "STEP2_MODEL": "gpt-4o-mini",
        "FALLBACK_MODEL": "gpt-4o-mini",
        "OUTPUT_ROOT": "docs/web_discovery"
      }
    }
  }
}
```

## Version Management

### Semantic Versioning

Update version in both files when releasing:

1. **`pyproject.toml`**: `version = "0.2.0"`
2. **`fastmcp.json`**: `"version": "0.2.0"`
3. **`src/legacy_web_mcp/cli.py`**: `version="legacy-web-mcp 0.2.0"`

### Git Tags

Create tags for releases:

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

Users can pin to specific versions:

```bash
uvx --from git+https://github.com/your-username/web-discovery-mcp-claude-1.git@v0.1.0 legacy-web-mcp
```

## Environment Requirements

### System Requirements

- Python 3.11+
- `uv`/`uvx` installed
- Optional: Playwright browsers for enhanced crawling

### Dependencies

All dependencies are automatically installed by uvx:

- `fastmcp==2.12.0`
- `playwright==1.55.0` 
- `aiohttp==3.12.15`
- `pydantic-settings==2.10.1`
- `structlog==25.4.0`
- `tenacity==9.0.0`
- `pyyaml==6.0.2`

## Troubleshooting

### Common Issues

1. **Missing Entry Point**
   ```bash
   # Verify entry points are configured
   uvx --from . --help
   ```

2. **Dependency Conflicts**
   ```bash
   # Clean uvx cache
   uvx cache clean
   ```

3. **Version Mismatch**
   ```bash
   # Force reinstall
   uvx --force --from . legacy-web-mcp
   ```

### Debug Mode

For debugging packaging issues:

```bash
# Verbose uvx output
uvx --verbose --from . legacy-web-mcp --version

# Check installed packages
uvx --from . python -c "import pkg_resources; print([d.project_name for d in pkg_resources.working_set])"
```

## Security Considerations

### Package Integrity

- Use tagged releases for production
- Verify checksums for critical deployments
- Pin dependency versions in `pyproject.toml`

### Secrets Management

- Never include API keys in the package
- Use environment variables for configuration
- Document required environment setup

### Environment Variable Security

**⚠️ Important Security Notes:**

1. **Never commit API keys** to version control
2. **Use secure storage** for API keys in production:
   - macOS: Keychain Access
   - Windows: Windows Credential Store
   - Linux: Secret Service API or encrypted files
3. **Alternative to hardcoded values** in MCP config:
   ```json
   {
     "mcpServers": {
       "legacy-web-mcp": {
         "command": "uvx",
         "args": ["legacy-web-mcp"],
         "env": {
           "OPENAI_API_KEY": "${OPENAI_API_KEY}",
           "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
         }
       }
     }
   }
   ```
   Then set environment variables in your shell profile.

## Publishing Checklist

Before distributing:

- [ ] Update version numbers in all files
- [ ] Test uvx execution locally
- [ ] Update README with actual repository URLs
- [ ] Create git tag for release
- [ ] Test installation from GitHub
- [ ] Verify MCP client configuration works
- [ ] Update documentation

## Support

For distribution issues:

1. Check this guide for common solutions
2. Test with minimal MCP client setup
3. Verify uvx and Python versions
4. Report issues with full error logs
