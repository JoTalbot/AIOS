from aios_core.mcp.gateway import MCPGateway
def test(): s = MCPGateway().stats(); assert isinstance(s, dict)
