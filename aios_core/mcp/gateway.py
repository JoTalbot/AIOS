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

import os
import sys
from dataclasses import dataclass

# Ensure AIOS core is importable
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from aios_core.runtime_policy import RuntimePolicy
from aios_core.storage import Database

from .prompts import PromptDefinition, PromptRegistry
from .protocol import (
    JSONRPCError,
    JSONRPCNotification,
    JSONRPCParseError,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPProtocol,
    MCPToolCall,
)
from .resources import ResourceDefinition, ResourceRegistry
from .tools import ToolDefinition, ToolRegistry

import requests  # Added for POST requests with authorization

# Default constitution/policy dirs relative to project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class _MCPError(Exception):
    """Internal error carrying a JSON-RPC error code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = message


class ConstitutionGuard:
    """Wraps every MCP tool call with constitutional evaluation.

    Converts an MCPToolCall into an agent_action for RuntimePolicy,
    then allows/denies/reviews based on the 7-phase evaluation.
    """

    def __init__(self, runtime_policy: RuntimePolicy):
        """Initialize ConstitutionGuard."""
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

        self._call_log.append(
            {
                "tool_name": tool_call.name,
                "request_id": tool_call.request_id,
                "decision": result.get("decision"),
                "allowed": result.get("allowed", False),
            }
        )

        return {
            "allowed": result.get("allowed", False),
            "decision": result.get("decision", "DENY"),
            "evaluation_id": result.get("evaluation_id", ""),
            "approval_id": result.get("approval_id"),
            "reason": result.get("reason", ""),
        }

    def approve(self, approval_id: str) -> dict | None:
        """Approve a pending action."""
        return self.policy.approve(approval_id)

    def deny(self, approval_id: str) -> dict | None:
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
    # Added for authorization token for POST requests
    auth_token: str = ""


class MCPGateway:
    def __init__(self, config: GatewayConfig | None = None, db: Database | None = None):
        """Initialize MCPGateway."""
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

        # Gateway identity / version
        self.version = "1.0.0"

    # ------------------------------------------------------------------
    # JSON-RPC 2.0 dispatcher (MCP protocol)
    # ------------------------------------------------------------------

    def handle_request(self, raw: str) -> str | None:
        """Handle a JSON-RPC 2.0 request/notification string.

        Returns the response JSON string, or ``None`` for notifications
        (which must not produce a response per the MCP spec).
        """
        import json as _json

        if not raw or not raw.strip():
            return _json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": JSONRPCError.PARSE_ERROR, "message": "Parse error"},
            })
        try:
            data = _json.loads(raw)
        except Exception:
            return _json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": JSONRPCError.PARSE_ERROR, "message": "Parse error"},
            })
        if not isinstance(data, dict) or data.get("jsonrpc") != "2.0" or "method" not in data:
            return _json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": JSONRPCError.INVALID_REQUEST, "message": "Invalid Request"},
            })

        method = data["method"]
        params = data.get("params") or {}
        request_id = data.get("id")

        if request_id is None:  # notification — no response
            self._request_log.append({"method": method, "notification": True})
            return None

        try:
            result = self._dispatch(method, params)
        except _MCPError as exc:
            return _json.dumps({
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": exc.code, "message": exc.message},
            })
        except Exception as exc:  # noqa: BLE001 — JSON-RPC errors go to the client
            return _json.dumps({
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": JSONRPCError.INTERNAL_ERROR, "message": str(exc)[:300]},
            })

        self._request_log.append({"method": method, "id": request_id})
        return _json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _dispatch(self, method: str, params: dict) -> dict:
        """Route an MCP method to its handler."""
        if method == "initialize":
            self._initialized = True
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "aios-mcp-gateway", "version": self.version},
            }
        if method == "ping":
            return {"pong": True}
        if method == "tools/list":
            return {"tools": self.tools.list_tools()}
        if method == "tools/call":
            return self._tools_call(params)
        if method == "resources/list":
            return {"resources": self.resources.list_resources()}
        if method == "resources/read":
            return self._resources_read(params)
        if method == "prompts/list":
            return {"prompts": self.prompts.list_prompts()}
        if method == "prompts/get":
            return self._prompts_get(params)
        if method == "aios/evaluate":
            return self._aios_evaluate(params)
        if method == "aios/approvals":
            approvals = list(self.runtime.approvals.history())
            return {"count": len(approvals), "approvals": approvals}
        if method == "aios/stats":
            return self.stats()
        raise _MCPError(JSONRPCError.METHOD_NOT_FOUND, f"Method not found: {method}")

    def _tools_call(self, params: dict) -> dict:
        """Execute a tool call through the constitution guard."""
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        tool_def = self.tools.get(name)
        if tool_def is None:
            raise _MCPError(JSONRPCError.METHOD_NOT_FOUND, f"Tool not found: {name}")

        verdict = self.guard.check(MCPToolCall(name=name, arguments=arguments), tool_def)
        if not verdict.get("allowed"):
            code = (JSONRPCError.CONSTITUTION_REVIEW
                    if verdict.get("decision") == "REVIEW"
                    else JSONRPCError.CONSTITUTION_DENIED)
            raise _MCPError(code, verdict.get("reason") or verdict.get("decision") or "Denied")

        result = self.tools.call(MCPToolCall(name=name, arguments=arguments))
        return {"content": result.content, "isError": result.is_error}

    def _resources_read(self, params: dict) -> dict:
        uri = params.get("uri", "")
        content = self.resources.read(uri)
        if content is None:
            raise _MCPError(JSONRPCError.RESOURCE_NOT_FOUND, f"Resource not found: {uri}")
        return {"contents": [{
            "uri": content.uri,
            "mimeType": getattr(content, "mime_type", "text/plain"),
            "text": content.text,
        }]}

    def _prompts_get(self, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        result = self.prompts.render(name, arguments)
        if result is None:
            raise _MCPError(JSONRPCError.METHOD_NOT_FOUND, f"Prompt not found: {name}")
        return {"description": result.description, "messages": result.messages}

    def _aios_evaluate(self, params: dict) -> dict:
        action = {
            "goal": params.get("goal", ""),
            "scope": params.get("scope", "general"),
            "risk": params.get("risk", "low"),
            "audit_log": True,
            "agent_id": "mcp-gateway",
            "authority": "user",
        }
        evaluation = self.runtime.request_execution(action)
        return {
            "decision": evaluation.get("decision", "DENY"),
            "allowed": evaluation.get("allowed", False),
            "evaluation_id": evaluation.get("evaluation_id", ""),
            "reason": evaluation.get("reason", ""),
        }

    def stats(self) -> dict:
        """Gateway statistics across all subsystems."""
        return {
            "gateway": {
                "initialized": self._initialized,
                "version": self.version,
                "requests": len(self._request_log),
            },
            "tools": self.tools.stats(),
            "resources": self.resources.stats(),
            "prompts": self.prompts.stats(),
            "constitution_guard": self.guard.stats(),
            "runtime": self.runtime.stats(),
            "database": self.runtime.db.stats(),
        }

    def close(self) -> None:
        """Close the underlying database connection."""
        try:
            self.runtime.db.close()
        except Exception:  # noqa: BLE001
            pass

    def _register_builtin_resources(self):
        """Register built-in AIOS resources (constitution/policies overview)."""
        self.resources.register(
            ResourceDefinition(
                uri="aios://constitution/overview",
                name="Constitution Overview",
                description="Summary of the AIOS constitutional articles and principles",
                mime_type="text/plain",
                provider=lambda: str(self.runtime.engine.constitution.stats()),
            )
        )
        self.resources.register(
            ResourceDefinition(
                uri="aios://policies/summary",
                name="Policy Summary",
                description="Summary of active AIOS policies",
                mime_type="text/plain",
                provider=lambda: str(self.runtime.engine.policies.stats()),
            )
        )

    def _register_builtin_prompts(self):
        """Register built-in AIOS prompt templates."""
        self.prompts.register(
            PromptDefinition(
                name="evaluate_action",
                description="Template for evaluating a proposed action against the AIOS constitution",
                arguments=[
                    {"name": "goal", "description": "The action's goal", "required": True},
                    {"name": "scope", "description": "The action's scope", "required": True},
                    {"name": "risk", "description": "Risk level", "required": True},
                ],
                template=(
                    "Evaluate the following proposed action against the AIOS constitution:\n\n"
                    "Goal: {goal}\nScope: {scope}\nRisk Level: {risk}\n\n"
                    "Provide your assessment of constitutional compliance."
                ),
            )
        )
        self.prompts.register(
            PromptDefinition(
                name="evolution_proposal",
                description="Template for proposing a system evolution change",
                arguments=[
                    {"name": "component", "description": "Component to evolve", "required": True},
                    {"name": "change", "description": "Description of the change", "required": True},
                    {"name": "rationale", "description": "Why this change is needed", "required": True},
                ],
                template=(
                    "Evolution Proposal for AIOS:\n\n"
                    "Component: {component}\nProposed Change: {change}\nRationale: {rationale}\n\n"
                    "This proposal must comply with ARTICLE-XXXVI (Controlled Evolution) "
                    "and pass all constitutional checks before deployment."
                ),
            )
        )

    def _register_builtin_tools(self):
        """Register built-in AIOS tools that expose core functionality through MCP."""

        # Tool: aios_evaluate — evaluate an action against constitution
        self.tools.register(
            ToolDefinition(
                name="aios_evaluate",
                description="Evaluate a proposed action against the AIOS constitution and policies. Returns ALLOW/DENY/REVIEW decision with full evaluation details.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "goal": {
                            "type": "string",
                            "description": "What the action intends to achieve",
                        },
                        "scope": {
                            "type": "string",
                            "description": "Scope of the action",
                        },
                        "risk": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Risk level",
                        },
                        "action_type": {
                            "type": "string",
                            "description": "Type of action (optional)",
                        },
                    },
                    "required": ["goal", "scope", "risk"],
                },
                handler=lambda params: self.runtime.request_execution(
                    {
                        **params,
                        "audit_log": True,
                        "agent_id": "mcp-gateway",
                        "authority": "system",
                    }
                ),
                category="constitution",
                risk_level="low",
            )
        )

        # Tool: aios_memory_store — store a memory item
        self.tools.register(
            ToolDefinition(
                name="aios_memory_store",
                description="Store an item in AIOS memory. Category can be: personal, operational, constitutional.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Memory content to store",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["personal", "operational", "constitutional"],
                            "description": "Memory category",
                        },
                        "tags": {
                            "type": "string",
                            "description": "Comma-separated tags",
                        },
                    },
                    "required": ["content", "category"],
                },
                handler=self._handle_memory_store,
                category="memory",
                risk_level="low",
            )
        )

        # Tool: aios_memory_search — search memories
        self.tools.register(
            ToolDefinition(
                name="aios_memory_search",
                description="Search AIOS memory by category and/or text query.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                        },
                        "query": {"type": "string", "description": "Text search query"},
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 20)",
                        },
                    },
                },
                handler=self._handle_memory_search,
                category="memory",
                risk_level="low",
            )
        )

        # Tool: aios_knowledge_query — query the knowledge graph
        self.tools.register(
            ToolDefinition(
                name="aios_knowledge_query",
                description="Query the AIOS knowledge graph for nodes and edges.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for nodes",
                        },
                        "node_type": {
                            "type": "string",
                            "description": "Filter by node type",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max results (default 20)",
                        },
                    },
                },
                handler=self._handle_knowledge_query,
                category="knowledge",
                risk_level="low",
            )
        )

        # Tool: aios_approve — approve a pending action
        self.tools.register(
            ToolDefinition(
                name="aios_approve",
                description="Approve a pending REVIEW action by its approval ID.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "approval_id": {
                            "type": "string",
                            "description": "UUID of the pending approval",
                        },
                    },
                    "required": ["approval_id"],
                },
                handler=lambda p: self.guard.approve(p["approval_id"]),
                category="constitution",
                risk_level="high",
            )
        )

        # Tool: aios_deny — deny a pending action
        self.tools.register(
            ToolDefinition(
                name="aios_deny",
                description="Deny a pending REVIEW action by its approval ID.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "approval_id": {
                            "type": "string",
                            "description": "UUID of the pending approval",
                        },
                    },
                    "required": ["approval_id"],
                },
                handler=lambda p: self.guard.deny(p["approval_id"]),
                category="constitution",
                risk_level="high",
            )
        )

        # Tool: aios_stats — get gateway/runtime statistics
        self.tools.register(
            ToolDefinition(
                name="aios_stats",
                description="Get comprehensive AIOS statistics including constitution, policies, and runtime metrics.",
                input_schema={"type": "object", "properties": {}},
                handler=lambda p: self.stats(),
                category="constitution",
                risk_level="low",
            )
        )

        self._register_olx_tools()

    def _olx_store(self, profile: str | None = None):
        """OLX Parser Agent storage, optionally profile-scoped.

        Без ``profile`` — общее хранилище (AIOS_OLX_DB env). С ``profile``
        хранилище разрешается через платформенный реестр профилей
        (``AIOS_PROFILES_DB``) и кэшируется по имени.
        """
        import os

        from aios_core.modules.olx import OLXStorage

        if getattr(self, "_olx_storages", None) is None:
            self._olx_storages = {}
        key = profile or ""
        if key not in self._olx_storages:
            if not profile:
                storage = OLXStorage(os.environ.get("AIOS_OLX_DB", ":memory:"))
            else:
                from aios_core.platforms import resolve_profile
                from aios_core.platforms.store import ProfileStore

                resolved = resolve_profile("olx", profile, store=ProfileStore.default())
                storage = OLXStorage(resolved.db_path)
            self._olx_storages[key] = storage
        return self._olx_storages[key]

    def _register_olx_tools(self):
        """Register read-only OLX Parser Agent tools (market intelligence)."""

        self.tools.register(
            ToolDefinition(
                name="olx_market_stats",
                description="Competitor market statistics for an OLX search query: price min/max/mean/median, TOP share, top cities.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query filter (optional — whole store)",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name — storage is resolved from the profiles registry",
                        },
                    },
                },
                handler=lambda p: self._olx_market_stats(p),
                category="olx",
                risk_level="low",
            )
        )

        self.tools.register(
            ToolDefinition(
                name="olx_listing_recommend",
                description="Listing advice for a draft OLX ad: suggested price, market verdict, title keywords, TOP promotion decision.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query of competitors",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Draft listing title",
                        },
                        "price": {
                            "type": "number",
                            "description": "Draft listing price",
                        },
                    },
                },
                handler=lambda p: self._olx_listing_recommend(p),
                category="olx",
                risk_level="low",
            )
        )

        self.tools.register(
            ToolDefinition(
                name="olx_price_drops",
                description="OLX ads with a detected price drop plus listings that left the feed (sold/removed).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query filter (optional)",
                        },
                        "profile": {
                            "type": "string",
                            "description": "Platform profile (account) name",
                        },
                    },
                },
                handler=lambda p: self._olx_price_drops(p),
                category="olx",
                risk_level="low",
            )
        )

    def _olx_market_stats(self, params: dict) -> dict:
        from aios_core.modules.olx import CompetitorAnalyzer

        store = self._olx_store(params.get("profile"))
        query = params.get("query")
        ads = store.get_ads(query=query)
        return CompetitorAnalyzer().analyze(ads, query=query).to_dict()

    def _olx_listing_recommend(self, params: dict) -> dict:
        from dataclasses import asdict

        from aios_core.modules.olx import AdCard, RecommendationEngine

        store = self._olx_store(params.get("profile"))
        query = params.get("query")
        ads = store.get_ads(query=query)
        my_ad = None
        if params.get("title") is not None or params.get("price") is not None:
            my_ad = AdCard(
                title=params.get("title") or "",
                price=params.get("price"),
                currency="UAH",
                query=query,
            )
        advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
        payload = asdict(advice)
        payload["text"] = advice.to_text()
        return payload

    def _olx_price_drops(self, params: dict) -> dict:
        from aios_core.modules.olx import PriceTracker

        store = self._olx_store(params.get("profile"))
        tracker = PriceTracker(store)
        query = params.get("query")
        return {
            "drops": [change.to_dict() for change in tracker.price_drops(query=query)],
            "gone": [ad.to_dict() for ad in tracker.gone_from_feed(query=query)],
        }

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
        return

# Compatibility alias

