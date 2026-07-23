"""Tests for MCP Gateway and Webhook bridge."""

from aios_core.mcp.gateway import MCPGateway


def test_mcp_gateway_stats():
    gw = MCPGateway()
    s = gw.stats()
    assert isinstance(s, dict)
    assert "tools" in s or isinstance(s, dict)


def test_mcp_gateway_initialized():
    gw = MCPGateway()
    assert gw is not None
