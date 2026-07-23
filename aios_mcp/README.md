# AIOS MCP Gateway

Standalone Model Context Protocol (MCP) Gateway — JSON-RPC 2.0
server for tools, resources, and prompts.

## Install
```bash
pip install aios-mcp
```

## Usage
```python
from aios_mcp import MCPGateway, GatewayConfig

gw = MCPGateway(GatewayConfig(name="my-gateway"))
gw.register_tool("search", lambda q: q)
gw.register_resource("config", {"key": "value"})
```
