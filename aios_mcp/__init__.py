"""AIOS MCP — Model Context Protocol Gateway.

JSON-RPC 2.0 gateway for tools, resources and prompts.
Now a standalone package installable via ``pip install aios-mcp``.

Re-exports the public API from the sub-modules.
"""

from aios_mcp.gateway import GatewayConfig, MCPGateway
from aios_mcp.tools import ToolRegistry
from aios_mcp.resources import ResourceRegistry
from aios_mcp.prompts import PromptRegistry
from aios_mcp.protocol import MCPProtocol, MCPRequest, MCPResponse

__all__ = [
    "GatewayConfig",
    "MCPGateway",
    "MCPProtocol",
    "MCPRequest",
    "MCPResponse",
    "PromptRegistry",
    "ResourceRegistry",
    "ToolRegistry",
]
