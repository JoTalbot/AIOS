"""Backward-compatibility re-export.

The canonical MCP package is now ``aios_mcp``.  This module forwards
all public names so that existing imports keep working.
"""

from aios_mcp.gateway import GatewayConfig, MCPGateway
from aios_mcp.prompts import PromptRegistry
from aios_mcp.protocol import JSONRPCRequest, JSONRPCResponse, MCPProtocol
from aios_mcp.resources import ResourceRegistry
from aios_mcp.tools import ToolRegistry

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
