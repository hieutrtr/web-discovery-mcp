import asyncio

from legacy_web_mcp.mcp.server import SERVER_NAME, SimpleMCPServer, create_mcp_server


def test_simple_server_ping_returns_status_ok() -> None:
    server = SimpleMCPServer()
    result = asyncio.run(server.ping())
    assert result == {"status": "ok"}


def test_create_mcp_server_returns_fallback_without_fastmcp() -> None:
    server = create_mcp_server()
    assert isinstance(server, SimpleMCPServer)
    assert server.name == SERVER_NAME
    result = asyncio.run(server.ping())
    assert result["status"] == "ok"
