"""AIOS MCP Gateway v1.0.0

Main MCP Gateway server that routes JSON-RPC 2.0 requests through
the constitutional evaluation pipeline. Implements the full MCP protocol:

Methods:
- initialize: Protocol handshake
- tools/list, tools/call: Tool discovery and execution
- resources/list, resources/read: Resource access
- prompts/list, prompts/get: Prompt template access
- aios/evaluate: Direct constitution evaluation
- aios/approvals: Manage approval queue
- aios/stats: Gateway statistics

Every tools/call passes through ConstitutionGuard (7-phase evaluation).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# Ensure AIOS core is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from aios_core.runtime_policy import RuntimePolicy
from aios_core.storage import Database
from aios_core.config import AIOSConfig, load_config

from .protocol import (
    MCPProtocol,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCNotification,
    JSONRPCError,
    JSONRPCParseError,
    MCPToolCall,
    MCPToolResult,
    MCPResourceContent,
)
from .tools import ToolRegistry, ToolDefinition
from .resources import ResourceRegistry, ResourceDefinition
from .prompts import PromptRegistry, PromptDefinition


# Default constitution/policy dirs relative to project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConstitutionGuard:
    """Wraps every MCP tool call with constitutional evaluation.

    Converts an MCPToolCall into an agent_action for RuntimePolicy,
    then allows/denies/reviews based on the 7-phase evaluation.
    """

    def __init__(self, runtime_policy: RuntimePolicy):
        self.policy = runtime_policy
        self._call_log: list[dict] = []

    def check(self, tool_call: MCPToolCall, tool_def: ToolDefinition | None = None) -> dict:
        """Evaluate a tool call against the constitution.

        Args:
            tool_call: The tool call to evaluate.
            tool_def: Optional tool definition for metadata (category, risk).

        Returns:
            Dict with keys:
                - allowed (bool)
                - decision (str): ALLOW/DENY/REVIEW
                - evaluation_id (str)
                - approval_id (str|None)
                - reason (str)
        """
        risk_level = tool_def.risk_level if tool_def else "low"
        scope = tool_def.category if tool_def else "general"

        agent_action = {
            "goal": f"Execute tool: {tool_call.name}",
            "scope": scope,
            "risk": risk_level,
            "audit_log": True,
            "agent_id": "mcp-gateway",
            "authority": "system",
        }

        result = self.policy.request_execution(agent_action)

        self._call_log.append({
            "tool_name": tool_call.name,
            "request_id": tool_call.request_id,
            "decision": result.get("decision"),
            "allowed": result.get("allowed", False),
        })

        return {
            "allowed": result.get("allowed", False),
            "decision": result.get("decision", "DENY"),
            "evaluation_id": result.get("evaluation_id", ""),
            "approval_id": result.get("approval_id"),
            "reason": result.get("reason", ""),
        }

    def approve(self, approval_id: str) -> Optional[dict]:
        """Approve a pending action."""
        return self.policy.approve(approval_id)

    def deny(self, approval_id: str) -> Optional[dict]:
        """Deny a pending action."""
        return self.policy.deny(approval_id)

    def stats(self) -> dict:
        """Constitution guard statistics."""
        decisions: dict[str, int] = {}
        for entry in self._call_log:
            d = entry.get("decision", "UNKNOWN")
            decisions[d] = decisions.get(d, 0) + 1

        return {
            "total_checks": len(self._call_log),
            "outcomes": decisions,
        }


@dataclass
class GatewayConfig:
    """MCP Gateway configuration."""

    host: str = "127.0.0.1"
    port: int = 8471  # Default MCP port
    constitution_dir: str = ""
    policies_dir: str = ""
    db_path: str = ":memory:"
    server_name: str = "aios-mcp-gateway"
    server_version: str = "1.0.0"


class MCPGateway:
    """Main MCP Gateway that routes JSON-RPC 2.0 requests.

    Usage (programmatic, no HTTP server — that's for Phase 2.7):
        gateway = MCPGateway(gateway_config)
        response = gateway.handle_request(
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
        )
        response = gateway.handle_request(
            '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
        )
    """

    def __init__(self, config: Optional[GatewayConfig] = None, db: Optional[Database] = None):
        self.config = config or GatewayConfig()
        self.protocol = MCPProtocol()

        # A gateway embedded in the REST API must share its Database instance.
        # Creating a second ``:memory:`` connection silently creates a different
        # database and splits audit/approval/memory state.
        db = db or Database(db_path=self.config.db_path)
        self.runtime = RuntimePolicy(
            constitution_dir=self.config.constitution_dir or os.path.join(_PROJECT_ROOT, "docs/constitution"),
            policies_dir=self.config.policies_dir or os.path.join(_PROJECT_ROOT, "policies"),
            db=db,
        )

        # Registries
        self.tools = ToolRegistry()
        self.resources = ResourceRegistry()
        self.prompts = PromptRegistry()

        # Constitution guard
        self.guard = ConstitutionGuard(self.runtime)

        # Register built-in AIOS tools, resources, prompts
        self._register_builtin_tools()
        self._register_builtin_resources()
        self._register_builtin_prompts()

        # State
        self._initialized = False
        self._request_log: list[dict] = []

    # ------------------------------------------------------------------
    # Built-in tool registration
    # ------------------------------------------------------------------

    def _register_builtin_tools(self):
        """Register built-in AIOS tools that expose core functionality through MCP."""

        # Tool: aios_evaluate — evaluate an action against constitution
        self.tools.register(ToolDefinition(
            name="aios_evaluate",
            description="Evaluate a proposed action against the AIOS constitution and policies. Returns ALLOW/DENY/REVIEW decision with full evaluation details.",
            input_schema={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "What the action intends to achieve"},
                    "scope": {"type": "string", "description": "Scope of the action"},
                    "risk": {"type": "string", "enum": ["low", "medium", "high", "critical"], "description": "Risk level"},
                    "action_type": {"type": "string", "description": "Type of action (optional)"},
                },
                "required": ["goal", "scope", "risk"],
            },
            handler=lambda params: self.runtime.request_execution({
                **params, "audit_log": True,
                "agent_id": "mcp-gateway", "authority": "system",
            }),
            category="constitution",
            risk_level="low",
        ))

        # Tool: aios_memory_store — store a memory item
        self.tools.register(ToolDefinition(
            name="aios_memory_store",
            description="Store an item in AIOS memory. Category can be: personal, operational, constitutional.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "category": {"type": "string", "enum": ["personal", "operational", "constitutional"], "description": "Memory category"},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                },
                "required": ["content", "category"],
            },
            handler=self._handle_memory_store,
            category="memory",
            risk_level="low",
        ))

        # Tool: aios_memory_search — search memories
        self.tools.register(ToolDefinition(
            name="aios_memory_search",
            description="Search AIOS memory by category and/or text query.",
            input_schema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"},
                    "query": {"type": "string", "description": "Text search query"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
            },
            handler=self._handle_memory_search,
            category="memory",
            risk_level="low",
        ))

        # Tool: aios_knowledge_query — query the knowledge graph
        self.tools.register(ToolDefinition(
            name="aios_knowledge_query",
            description="Query the AIOS knowledge graph for nodes and edges.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for nodes"},
                    "node_type": {"type": "string", "description": "Filter by node type"},
                    "limit": {"type": "integer", "description": "Max results (default 20)"},
                },
            },
            handler=self._handle_knowledge_query,
            category="knowledge",
            risk_level="low",
        ))

        # Tool: aios_approve — approve a pending action
        self.tools.register(ToolDefinition(
            name="aios_approve",
            description="Approve a pending REVIEW action by its approval ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "approval_id": {"type": "string", "description": "UUID of the pending approval"},
                },
                "required": ["approval_id"],
            },
            handler=lambda p: self.guard.approve(p["approval_id"]),
            category="constitution",
            risk_level="high",
        ))

        # Tool: aios_deny — deny a pending action
        self.tools.register(ToolDefinition(
            name="aios_deny",
            description="Deny a pending REVIEW action by its approval ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "approval_id": {"type": "string", "description": "UUID of the pending approval"},
                },
                "required": ["approval_id"],
            },
            handler=lambda p: self.guard.deny(p["approval_id"]),
            category="constitution",
            risk_level="high",
        ))

        # Tool: aios_stats — get gateway/runtime statistics
        self.tools.register(ToolDefinition(
            name="aios_stats",
            description="Get comprehensive AIOS statistics including constitution, policies, and runtime metrics.",
            input_schema={"type": "object", "properties": {}},
            handler=lambda p: self.stats(),
            category="constitution",
            risk_level="low",
        ))

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _handle_memory_store(self, params: dict) -> dict:
        """Handler for memory store tool."""
        from aios_core.memory_manager import MemoryManager

        if params.get("category") == "personal":
            raise PermissionError("Personal memory is available only through the authenticated REST API")

        mm = MemoryManager(db=self.runtime.db)
        tags = params.get("tags", "")
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # MemoryManager.store() expects content as a dict
        return mm.store(
            content={"text": params["content"]},
            category=params["category"],
            tags=tag_list,
        )

    def _handle_memory_search(self, params: dict) -> dict:
        """Handler for memory search tool."""
        from aios_core.memory_manager import MemoryManager

        if params.get("category") == "personal":
            raise PermissionError("Personal memory is available only through the authenticated REST API")

        mm = MemoryManager(db=self.runtime.db)
        results = mm.search(
            query=params.get("query", ""),
            category=params.get("category"),
            limit=params.get("limit", 20),
        )
        return {"results": results, "count": len(results)}

    def _handle_knowledge_query(self, params: dict) -> dict:
        """Handler for knowledge graph query tool."""
        from aios_core.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph(db=self.runtime.db)
        results = kg.find_nodes(
            label=params.get("query", ""),
            node_type=params.get("node_type"),
            limit=params.get("limit", 20),
        )
        return {"results": results, "count": len(results)}

    # ------------------------------------------------------------------
    # Built-in resource registration
    # ------------------------------------------------------------------

    def _register_builtin_resources(self):
        """Register built-in AIOS resources."""

        # Resource: constitution overview
        self.resources.register(ResourceDefinition(
            uri="aios://constitution/overview",
            name="Constitution Overview",
            description="Summary of the AIOS constitutional articles and principles",
            mime_type="text/plain",
            provider=lambda: str(self.runtime.engine.constitution.stats()),
        ))

        # Resource: policies summary
        self.resources.register(ResourceDefinition(
            uri="aios://policies/summary",
            name="Policy Summary",
            description="Summary of active AIOS policies",
            mime_type="text/plain",
            provider=lambda: str(self.runtime.engine.policies.stats()),
        ))

        # Audit and approval records deliberately are not exposed as generic MCP
        # resources. They contain operational metadata and require the REST API
        # role checks (admin/approver) instead.

    # ------------------------------------------------------------------
    # Built-in prompt registration
    # ------------------------------------------------------------------

    def _register_builtin_prompts(self):
        """Register built-in AIOS prompt templates."""

        self.prompts.register(PromptDefinition(
            name="evaluate_action",
            description="Template for evaluating a proposed action against the AIOS constitution",
            arguments=[
                {"name": "goal", "description": "The action's goal", "required": True},
                {"name": "scope", "description": "The action's scope", "required": True},
                {"name": "risk", "description": "Risk level", "required": True},
            ],
            template=(
                "Evaluate the following proposed action against the AIOS constitution:\n\n"
                "Goal: {goal}\n"
                "Scope: {scope}\n"
                "Risk Level: {risk}\n\n"
                "Provide your assessment of constitutional compliance."
            ),
        ))

        self.prompts.register(PromptDefinition(
            name="evolution_proposal",
            description="Template for proposing a system evolution change",
            arguments=[
                {"name": "component", "description": "Component to evolve", "required": True},
                {"name": "change", "description": "Description of the change", "required": True},
                {"name": "rationale", "description": "Why this change is needed", "required": True},
            ],
            template=(
                "Evolution Proposal for AIOS:\n\n"
                "Component: {component}\n"
                "Proposed Change: {change}\n"
                "Rationale: {rationale}\n\n"
                "This proposal must comply with ARTICLE-XXXVI (Controlled Evolution) "
                "and pass all constitutional checks before deployment."
            ),
        ))

    # ------------------------------------------------------------------
    # Request handling
    # ------------------------------------------------------------------

    def handle_request(self, raw: str) -> Optional[str]:
        """Handle a single JSON-RPC 2.0 request string.

        Args:
            raw: Raw JSON-RPC 2.0 message string.

        Returns:
            JSON-RPC response string, or None for notifications.
        """
        # 1. Parse the JSON-RPC message
        try:
            message = self.protocol.parse(raw)
        except JSONRPCParseError as exc:
            return self.protocol.encode_error(
                id=None,
                code=exc.code,
                message=exc.message,
                data=exc.data,
            )

        # 2. Handle notification — process but return no response
        if isinstance(message, JSONRPCNotification):
            self._request_log.append({
                "type": "notification",
                "method": message.method,
            })
            return None

        # 3. Handle response (echo back) — should not happen in server mode
        if isinstance(message, JSONRPCResponse):
            self._request_log.append({
                "type": "response",
                "id": message.id,
            })
            return self.protocol.encode_response(
                id=message.id,
                result={"echoed": True},
            )

        # 4. Route request to handler
        if not isinstance(message, JSONRPCRequest):
            return self.protocol.encode_error(
                id=None,
                code=JSONRPCError.INTERNAL_ERROR,
                message="Unexpected message type",
            )

        self._request_log.append({
            "type": "request",
            "method": message.method,
            "id": message.id,
        })

        response = self._route(message)
        return self.protocol.encode_response(
            id=response.id,
            result=response.result,
            error=response.error,
        )

    def _route(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Route a parsed request to the appropriate handler.

        Args:
            request: Parsed JSONRPCRequest.

        Returns:
            JSONRPCResponse.
        """
        method = request.method

        # Protocol methods
        if method == "initialize":
            return self._handle_initialize(request)
        if method == "ping":
            return JSONRPCResponse(id=request.id, result={"pong": True})

        # Tool methods (with constitution guard)
        if method == "tools/list":
            return self._handle_tools_list(request)
        if method == "tools/call":
            return self._handle_tools_call(request)

        # Resource methods
        if method == "resources/list":
            return self._handle_resources_list(request)
        if method == "resources/read":
            return self._handle_resources_read(request)

        # Prompt methods
        if method == "prompts/list":
            return self._handle_prompts_list(request)
        if method == "prompts/get":
            return self._handle_prompts_get(request)

        # AIOS-specific methods
        if method == "aios/evaluate":
            return self._handle_aios_evaluate(request)
        if method == "aios/approvals":
            return self._handle_aios_approvals(request)
        if method == "aios/stats":
            return self._handle_aios_stats(request)

        # Unknown method
        return JSONRPCResponse(
            id=request.id,
            error={"code": JSONRPCError.METHOD_NOT_FOUND, "message": f"Unknown method: {method}"},
        )

    # ------------------------------------------------------------------
    # Method handlers
    # ------------------------------------------------------------------

    def _handle_initialize(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle MCP initialize handshake."""
        self._initialized = True
        return JSONRPCResponse(id=request.id, result={
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": False, "listChanged": True},
                "prompts": {"listChanged": True},
            },
            "serverInfo": {
                "name": self.config.server_name,
                "version": self.config.server_version,
            },
        })

    def _handle_tools_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tools/list."""
        return JSONRPCResponse(id=request.id, result={"tools": self.tools.list_tools()})

    def _handle_tools_call(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle tools/call — with constitution guard."""
        params = request.params
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        tool_def = self.tools.get(name)
        if not tool_def:
            return JSONRPCResponse(
                id=request.id,
                error={"code": JSONRPCError.METHOD_NOT_FOUND, "message": f"Tool not found: {name}"},
            )

        # Constitution check
        tool_call = MCPToolCall(name=name, arguments=arguments, request_id=str(request.id))
        guard_result = self.guard.check(tool_call, tool_def)

        if not guard_result["allowed"]:
            if guard_result["decision"] == "REVIEW":
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": JSONRPCError.CONSTITUTION_REVIEW,
                        "message": "Tool call requires human approval",
                        "data": guard_result,
                    },
                )
            else:
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": JSONRPCError.CONSTITUTION_DENIED,
                        "message": "Tool call denied by constitution",
                        "data": guard_result,
                    },
                )

        # Execute the tool
        try:
            result = self.tools.call(tool_call)
            return JSONRPCResponse(id=request.id, result={
                "content": result.content,
                "isError": result.is_error,
            })
        except Exception as e:
            return JSONRPCResponse(
                id=request.id,
                error={"code": JSONRPCError.TOOL_EXECUTION_ERROR, "message": str(e)},
            )

    def _handle_resources_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle resources/list."""
        return JSONRPCResponse(id=request.id, result={"resources": self.resources.list_resources()})

    def _handle_resources_read(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle resources/read."""
        params = request.params
        uri = params.get("uri", "")
        content = self.resources.read(uri)
        if content is None:
            return JSONRPCResponse(
                id=request.id,
                error={"code": JSONRPCError.RESOURCE_NOT_FOUND, "message": f"Resource not found: {uri}"},
            )
        return JSONRPCResponse(id=request.id, result={
            "contents": [{
                "uri": content.uri,
                "mimeType": content.mime_type,
                "text": content.text,
            }],
        })

    def _handle_prompts_list(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle prompts/list."""
        return JSONRPCResponse(id=request.id, result={"prompts": self.prompts.list_prompts()})

    def _handle_prompts_get(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle prompts/get."""
        params = request.params
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = self.prompts.render(name, arguments)
        if result is None:
            return JSONRPCResponse(
                id=request.id,
                error={"code": JSONRPCError.METHOD_NOT_FOUND, "message": f"Prompt not found: {name}"},
            )
        return JSONRPCResponse(id=request.id, result={
            "description": result.description,
            "messages": result.messages,
        })

    def _handle_aios_evaluate(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Direct constitution evaluation without going through tool dispatch."""
        params = request.params
        result = self.runtime.request_execution({
            **params,
            "audit_log": True,
            "agent_id": params.get("agent_id", "mcp-direct"),
            "authority": params.get("authority", "user"),
        })
        return JSONRPCResponse(id=request.id, result=result)

    def _handle_aios_approvals(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle aios/approvals."""
        pending = self.runtime.get_pending_approvals()
        return JSONRPCResponse(id=request.id, result={"approvals": pending, "count": len(pending)})

    def _handle_aios_stats(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """Handle aios/stats."""
        return JSONRPCResponse(id=request.id, result=self.stats())

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Comprehensive gateway statistics."""
        return {
            "gateway": {
                "version": self.config.server_version,
                "initialized": self._initialized,
                "server_name": self.config.server_name,
            },
            "tools": self.tools.stats(),
            "resources": self.resources.stats(),
            "prompts": self.prompts.stats(),
            "constitution_guard": self.guard.stats(),
            "runtime": self.runtime.stats(),
            "database": self.runtime.db.stats(),
        }

    def close(self):
        """Cleanup resources."""
        self.runtime.db.close()