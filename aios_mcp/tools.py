"""AIOS MCP Tool Registry v1.0.0

Registration, discovery, and execution of MCP tools.
Every tool call passes through the Constitution Guard before execution.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .protocol import MCPToolCall, MCPToolResult


@dataclass
class ToolDefinition:
    """Definition of an MCP tool."""

    name: str
    description: str
    input_schema: dict  # JSON Schema for parameters
    handler: Callable[[dict], Any]
    category: str = "general"  # general, memory, knowledge, evolution, constitution
    risk_level: str = "low"  # low, medium, high, critical
    requires_consent: bool = False


class ToolRegistry:
    """Registry for MCP tools with constitution-aware dispatch.

    Tools are registered with a name, description, JSON Schema input
    definition, and a handler callable. The registry supports listing
    tools for MCP discovery and executing tool calls.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition.

        Args:
            tool: The ToolDefinition to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: Tool name to remove.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name.

        Args:
            name: Tool name to look up.

        Returns:
            The ToolDefinition or None if not found.
        """
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """List all registered tools as MCP tool descriptors.

        Returns:
            List of dicts with keys: name, description, inputSchema.
        """
        return [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def call(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call (without constitution check).

        Finds the tool, validates that required parameters are present,
        invokes the handler, and wraps the result in an MCPToolResult.

        Args:
            tool_call: The MCPToolCall to execute.

        Returns:
            MCPToolResult with content list and is_error flag.

        Raises:
            RuntimeError: If the tool is not found.
        """
        tool_def = self._tools.get(tool_call.name)
        if tool_def is None:
            raise RuntimeError(f"Tool not found: {tool_call.name}")

        # Basic validation: check required fields from input_schema
        schema = tool_def.input_schema or {}
        required_fields = schema.get("required", [])
        missing = [f for f in required_fields if f not in tool_call.arguments]
        if missing:
            return MCPToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Missing required parameters: {', '.join(missing)}",
                    }
                ],
                is_error=True,
            )

        # Invoke handler
        try:
            raw_result = tool_def.handler(tool_call.arguments)
        except Exception as exc:
            return MCPToolResult(
                content=[
                    {
                        "type": "text",
                        "text": f"Tool execution error: {exc}",
                    }
                ],
                is_error=True,
            )

        # Normalize result into MCPToolResult
        if isinstance(raw_result, MCPToolResult):
            return raw_result

        # Convert dict/list/primitive to text content
        import json

        text = json.dumps(raw_result, ensure_ascii=False, default=str)
        return MCPToolResult(
            content=[{"type": "text", "text": text}],
            is_error=False,
        )

    def categories(self) -> dict[str, list[str]]:
        """Group tool names by category.

        Returns:
            Dict mapping category names to lists of tool names.
        """
        cats: dict[str, list[str]] = {}
        for name, tool in self._tools.items():
            cats.setdefault(tool.category, []).append(name)
        return cats

    def stats(self) -> dict:
        """Registry statistics.

        Returns:
            Dict with total count, category breakdown, and risk breakdown.
        """
        by_category: dict[str, int] = {}
        by_risk: dict[str, int] = {}
        for tool in self._tools.values():
            by_category[tool.category] = by_category.get(tool.category, 0) + 1
            by_risk[tool.risk_level] = by_risk.get(tool.risk_level, 0) + 1

        return {
            "total": len(self._tools),
            "by_category": by_category,
            "by_risk": by_risk,
        }
