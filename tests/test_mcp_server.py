"""Tests for MCP server runner."""
from aios_core.mcp.server import MCPServer
def test_mcp_server_init():
    s = MCPServer()
    assert s is not None
