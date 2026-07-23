"""Backward-compatibility re-export.

The canonical MCP package is now ``aios_mcp``.  This module forwards
all public names so that existing imports keep working.
"""

from aios_mcp.gateway import GatewayConfig, MCPGateway  # noqa: F401
from aios_mcp.tools import ToolRegistry  # noqa: F401
from aios_mcp.resources import ResourceRegistry  # noqa: F401
from aios_mcp.prompts import PromptRegistry  # noqa: F401
from aios_mcp.protocol import MCPProtocol, MCPRequest, MCPResponse  # noqa: F401

__all__ = [
    "GatewayConfig", "MCPGateway", "MCPProtocol",
    "MCPRequest", "MCPResponse", "PromptRegistry",
    "ResourceRegistry", "ToolRegistry",
]
