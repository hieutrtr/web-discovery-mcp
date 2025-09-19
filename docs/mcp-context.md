# MCP Context in Legacy Web MCP Server

## Overview

The Model Context Protocol (MCP) Context is the communication bridge between MCP tools and clients. In the Legacy Web MCP Server, the Context provides essential functionality for tool execution, logging, progress reporting, and client interaction.

## What is MCP Context?

MCP Context is a wrapper around the underlying MCP session that provides:

1. **Bidirectional Communication** - Tools can send messages back to the client
2. **Structured Logging** - Standardized logging that clients can interpret
3. **Progress Reporting** - Real-time updates on long-running operations
4. **Error Handling** - Proper error propagation to the client
5. **Session Management** - Access to session-specific data and metadata

## Context Types

### 1. Production Context (Real MCP Client)

When running with a real MCP client (like Claude Desktop), the context provides full functionality:

```python
@mcp.tool(name="discover_website")
async def discover_website(context: Context, url: str) -> dict:
    # Full context functionality available
    await context.info(f"Starting discovery for {url}")
    await context.report_progress(0.5, 1.0, "Crawling pages...")
    # ... tool implementation
    return result
```

### 2. Test Context (Mock MCP Session)

For testing purposes, we create a mock context that simulates the MCP environment:

```python
class MockMCPSession:
    async def send_log_message(self, level: str, data: Any, logger: str = None, related_request_id: str = None):
        # Print to console instead of sending to client
        print(f"[{level.upper()}] {data}")

# Create mock context for testing
mock_context = RequestContext(
    request_id="test-request-123",
    meta=None,
    session=MockMCPSession(),
    lifespan_context=None,
    request=None
)
```

## Context Methods

### Logging Methods

The context provides structured logging that clients can interpret:

```python
# Information logging
await context.info("Discovery started")

# Error logging
await context.error("Invalid URL provided")

# Warning logging
await context.warning("Sitemap not found, using crawling")

# Debug logging (detailed technical information)
await context.debug("HTTP response: 200 OK")
```

### Progress Reporting

For long-running operations, report progress to keep clients informed:

```python
# Report progress with current/total values
await context.report_progress(25, 100, "Crawling pages...")

# Report progress as percentage
await context.report_progress(0.5, 1.0, "50% complete")
```

### Session Information

Access session metadata and identifiers:

```python
# Get session ID for tracking
session_id = context.session_id

# Access request-specific data
request_id = context.request_id
```

## Context Requirements

### Tools Requiring Context

Some tools need context for communication with the client:

- **`discover_website`** - Reports progress and logs discovery steps
- **Long-running operations** - Any tool that takes significant time
- **Interactive tools** - Tools that need to provide real-time feedback

### Tools Not Requiring Context

Simple tools that don't need client communication:

- **`ping`** - Simple status check
- **`show_config`** - Returns static configuration data

## Testing with Context

### Using Test Scripts

The Legacy Web MCP Server provides multiple ways to test tools:

1. **Direct MCP Testing** (with mock context):
   ```bash
   python scripts/test_mcp_client.py discover_website https://example.com
   ```

2. **Direct Service Testing** (bypasses MCP layer):
   ```bash
   python scripts/test_discovery_direct.py https://example.com
   ```

3. **Comprehensive Testing** (full test suite):
   ```bash
   python scripts/manual_test.py discover https://example.com
   ```

### Mock Context Implementation

The test client creates a mock context that simulates MCP functionality:

```python
class SimpleMCPClient:
    def __init__(self):
        self.mcp = create_mcp()
        self.context = Context(self.mcp)
        self.mock_request_context = create_mock_request_context()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        # Set up mock context for tools that need session
        token = request_ctx.set(self.mock_request_context)
        try:
            return await tool.fn(self.context, **arguments)
        finally:
            request_ctx.reset(token)
```

## Context Best Practices

### 1. Provide Meaningful Progress Updates

```python
await context.info("Validated target URL: {url}")
await context.info("Analyzed robots.txt directives")
await context.info("Manual crawl discovered {count} URLs")
await context.info("Persisted URL inventory to project storage")
```

### 2. Handle Errors Gracefully

```python
try:
    result = await some_operation()
except SomeException as e:
    await context.error(f"Operation failed: {e}")
    raise ValueError(f"Failed to complete operation") from e
```

### 3. Use Appropriate Log Levels

- **INFO**: Major steps and user-relevant information
- **DEBUG**: Technical details for debugging
- **WARNING**: Non-fatal issues that users should know about
- **ERROR**: Fatal errors that prevent operation completion

### 4. Report Progress for Long Operations

```python
total_urls = len(urls_to_process)
for i, url in enumerate(urls_to_process):
    await context.report_progress(i, total_urls, f"Processing {url}")
    await process_url(url)
```

## Troubleshooting

### "Context is not available outside of a request"

This error occurs when tools try to use context functionality without a proper MCP session:

**Solution**: Use the mock context implementation in test scripts, or test via a real MCP client.

### Mock Context Not Working

Ensure the mock context provides all required parameters:

```python
RequestContext(
    request_id="test-request-123",
    meta=None,
    session=MockMCPSession(),
    lifespan_context=None,
    request=None
)
```

### Tools Not Receiving Context

Check that tools are properly registered and accept context as first parameter:

```python
@mcp.tool(name="my_tool")
async def my_tool(context: Context, param: str) -> dict:
    # context is automatically injected by FastMCP
    await context.info("Tool started")
    return {"result": "success"}
```

## Architecture Integration

The MCP Context integrates with other system components:

- **Discovery Pipeline**: Uses context for progress reporting during website crawling
- **Storage Layer**: Logs project creation and data persistence
- **Configuration System**: Reports configuration validation results
- **Error Handling**: Provides structured error communication to clients

This design ensures that tools can provide rich, interactive experiences while maintaining compatibility with various MCP clients and testing environments.