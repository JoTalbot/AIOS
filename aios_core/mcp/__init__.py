"""AIOS MCP Gateway Package v1.0.0

Model Context Protocol gateway for AIOS, providing JSON-RPC 2.0 access
to constitution-guarded tools, resources, and prompt templates.
"""

from .gateway import ConstitutionGuard, GatewayConfig, MCPGateway
from .prompts import PromptDefinition, PromptRegistry
from .protocol import (
    JSONRPCError,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPPrompt,
    MCPPromptResult,
    MCPProtocol,
    MCPResource,
    MCPResourceContent,
    MCPToolCall,
    MCPToolResult,
)
from .resources import ResourceDefinition, ResourceRegistry
from .tools import ToolDefinition, ToolRegistry

__all__ = [
    # Protocol
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCNotification",
    "MCPProtocol",
    "MCPToolCall",
    "MCPToolResult",
    "MCPResource",
    "MCPResourceContent",
    "MCPPrompt",
    "MCPPromptResult",
    # Tools
    "ToolDefinition",
    "ToolRegistry",
    # Resources
    "ResourceDefinition",
    "ResourceRegistry",
    # Prompts
    "PromptDefinition",
    "PromptRegistry",
    # Gateway
    "ConstitutionGuard",
    "GatewayConfig",
    "MCPGateway",
]

__version__ = "1.0.0"
