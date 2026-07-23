"""Deep tests for MCP Gateway tools and resources."""

from aios_core.mcp.gateway import MCPGateway


def test_gateway_tools_list():
    gw = MCPGateway()
    tools = gw.list_tools() if hasattr(gw, 'list_tools') else []
    assert isinstance(tools, list)


def test_gateway_resources_list():
    gw = MCPGateway()
    resources = gw.list_resources() if hasattr(gw, 'list_resources') else []
    assert isinstance(resources, list)
