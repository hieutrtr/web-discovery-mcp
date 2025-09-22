# Publishing Guide for Legacy Web MCP Server

This guide explains how to publish the Legacy Web MCP Server package to PyPI for global access via `uvx`.

## Prerequisites

1. **PyPI Account**: Create an account at [pypi.org](https://pypi.org)
2. **API Token**: Generate an API token in your PyPI account settings
3. **uv**: Ensure you have `uv` installed for package building

## Publishing Steps

### 1. Prepare the Release

1. Update the version in `pyproject.toml`:
   ```toml
   version = "0.1.1"  # or your desired version
   ```

2. Update the version in `src/legacy_web_mcp/cli.py`:
   ```python
   version="legacy-web-mcp 0.1.1",
   ```

3. Update GitHub URLs in `pyproject.toml` to point to your actual repository:
   ```toml
   [project.urls]
   Homepage = "https://github.com/your-username/legacy-web-mcp"
   Repository = "https://github.com/your-username/legacy-web-mcp"
   Documentation = "https://github.com/your-username/legacy-web-mcp/docs"
   Issues = "https://github.com/your-username/legacy-web-mcp/issues"
   ```

### 2. Build the Package

```bash
# Clean previous builds
rm -rf dist/

# Build source distribution and wheel
uv build

# Verify the built files
ls -la dist/
```

### 3. Test Local Installation

```bash
# Test with uvx (recommended for end users)
uvx --from ./dist/legacy_web_mcp-*.whl legacy-web-mcp --version

# Test with uv run (for development)
uv run legacy-web-mcp --version
```

### 4. Publish to PyPI

#### Option A: Using uv (Recommended)

```bash
# Install twine if not available
uv add --dev twine

# Upload to PyPI (will prompt for credentials)
uv run twine upload dist/*
```

#### Option B: Using twine directly

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*
```

#### Option C: Using API Token

```bash
# Set your PyPI API token
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-your-api-token-here

# Upload
twine upload dist/*
```

### 5. Verify Publication

After publishing, test the installation from PyPI:

```bash
# Test global installation via uvx
uvx legacy-web-mcp --version

# Test help command
uvx legacy-web-mcp --help

# Test server startup (Ctrl+C to stop)
uvx legacy-web-mcp
```

## Usage After Publication

Once published to PyPI, users can install and run the MCP server globally:

### For End Users (Recommended)

```bash
# Install and run with uvx (creates isolated environment)
uvx legacy-web-mcp
```

### For Developers

```bash
# Add to project dependencies
uv add legacy-web-mcp

# Run in project environment
uv run legacy-web-mcp
```

### For Claude Desktop Integration

Add to Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "legacy-web-mcp": {
      "command": "uvx",
      "args": ["legacy-web-mcp"]
    }
  }
}
```

## Version Management

### Semantic Versioning

Follow semantic versioning (semver):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backward compatible
- **PATCH** (0.1.1): Bug fixes, backward compatible

### Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `src/legacy_web_mcp/cli.py`
- [ ] Update CHANGELOG.md (if exists)
- [ ] Test locally with uvx
- [ ] Build package: `uv build`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Test installation from PyPI
- [ ] Create GitHub release (optional)
- [ ] Update documentation

## Troubleshooting

### Common Issues

1. **Package already exists**: Increment version number
2. **Authentication failed**: Check PyPI credentials/token
3. **Build failures**: Check pyproject.toml syntax
4. **Import errors**: Verify package structure and dependencies

### Testing Before Release

```bash
# Test package build
uv build

# Test local wheel installation
uvx --from ./dist/legacy_web_mcp-*.whl legacy-web-mcp --version

# Test server startup
timeout 5s uvx --from ./dist/legacy_web_mcp-*.whl legacy-web-mcp || echo "Server started successfully"
```

## Post-Publication

After successful publication:

1. **Update Documentation**: Update README with PyPI installation instructions
2. **GitHub Release**: Create a release on GitHub matching the PyPI version
3. **Announce**: Share the package with the community
4. **Monitor**: Watch for issues and user feedback

## Security Notes

- Never commit API tokens to version control
- Use environment variables or secure credential storage
- Consider using GitHub Actions for automated publishing
- Regularly update dependencies for security patches

## Next Steps

Consider setting up:
- Automated testing with GitHub Actions
- Automated publishing on tag creation
- Documentation hosting (e.g., GitHub Pages)
- Issue templates and contribution guidelines