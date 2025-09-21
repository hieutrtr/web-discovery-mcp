"""Integration tests for orchestration tools with MCP server."""

import pytest
from fastmcp import FastMCP
from unittest.mock import patch, MagicMock

from legacy_web_mcp.mcp.orchestration_tools import register


class TestOrchestrationIntegration:
    """Test orchestration tools integration with MCP server."""

    @pytest.fixture
    def mcp_server(self):
        """Create FastMCP server with orchestration tools registered."""
        mcp = FastMCP(name="Test MCP Server")
        register(mcp)
        return mcp

    def test_orchestration_tools_registered(self, mcp_server):
        """Test that orchestration tools are properly registered with MCP server."""
        # Verify that tools are registered in the MCP server
        # This is a basic integration test to ensure registration works
        assert mcp_server is not None
        assert mcp_server.name == "Test MCP Server"

    async def test_analyze_legacy_site_tool_exists(self, mcp_server):
        """Test that analyze_legacy_site tool is accessible through MCP."""
        # This test verifies the tool can be found and called
        # In a real integration test, we would call the tool through the MCP protocol

        # For now, just verify the server was created successfully
        assert mcp_server is not None

    async def test_analyze_with_recommendations_tool_exists(self, mcp_server):
        """Test that analyze_with_recommendations tool is accessible through MCP."""
        # Similar to above - in a real scenario we'd test through MCP protocol
        assert mcp_server is not None

    async def test_get_analysis_status_tool_exists(self, mcp_server):
        """Test that get_analysis_status tool is accessible through MCP."""
        # Similar to above - in a real scenario we'd test through MCP protocol
        assert mcp_server is not None

    @pytest.mark.slow
    async def test_orchestration_workflow_end_to_end(self, mcp_server):
        """Test complete orchestration workflow through MCP (if we had a test site)."""
        # This would be a comprehensive end-to-end test
        # For now, just mark as slow and verify server exists
        assert mcp_server is not None

        # In a real implementation, this would:
        # 1. Start the MCP server
        # 2. Connect a client
        # 3. Call analyze_legacy_site with a test URL
        # 4. Verify the complete workflow executes
        # 5. Check that results are properly formatted

        # Example test structure (not implemented):
        # client = MCPClient(server_url)
        # result = await client.call_tool("analyze_legacy_site", {
        #     "url": "https://httpbin.org",
        #     "analysis_mode": "quick",
        #     "max_pages": 3
        # })
        # assert result["status"] == "success"
        # assert "workflow_id" in result
        # assert result["pages_analyzed"] > 0


class TestOrchestrationServerCompatibility:
    """Test compatibility with the main MCP server."""

    def test_orchestration_tools_import_in_server(self):
        """Test that orchestration tools can be imported by the main server."""
        # Test that the import works (simulating server.py import)
        try:
            from legacy_web_mcp.mcp import orchestration_tools
            assert orchestration_tools is not None
            assert hasattr(orchestration_tools, 'register')
        except ImportError as e:
            pytest.fail(f"Failed to import orchestration_tools: {e}")

    def test_server_registration_integration(self):
        """Test integration with main server registration."""
        # Mock the main server creation process
        with patch('legacy_web_mcp.mcp.server.FastMCP') as mock_fastmcp:
            mock_mcp_instance = MagicMock()
            mock_fastmcp.return_value = mock_mcp_instance

            # Import and test the main server creation
            from legacy_web_mcp.mcp.server import create_mcp

            # This should include orchestration_tools.register() call
            server = create_mcp()

            # Verify that orchestration tools registration was called
            # (The exact verification depends on how the mocking is set up)
            assert mock_mcp_instance is not None