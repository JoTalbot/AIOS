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

    # ------------------------------------------------------------------
    # Built-in tool registration
    # ------------------------------------------------------------------

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