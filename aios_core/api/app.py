"""AIOS REST API v1.0.0

HTTP/REST API layer for AIOS. Built on Starlette.
Provides RESTful access to all AIOS subsystems.

Endpoints:
  GET  /health                         — Health check
  GET  /api/v1/stats                   — System statistics

  POST /api/v1/evaluate                — Constitutional evaluation
  GET  /api/v1/constitution/stats      — Constitution stats

  # Tasks (Orchestrator)
  POST /api/v1/tasks                   — Create task
  GET  /api/v1/tasks                   — List tasks
  GET  /api/v1/tasks/{task_id}         — Get task
  POST /api/v1/tasks/{task_id}/execute — Execute task

  # Memory
  POST   /api/v1/memory                — Store memory
  GET    /api/v1/memory                — Search memory
  GET    /api/v1/memory/{id}           — Get memory item
  PUT    /api/v1/memory/{id}           — Update memory
  DELETE /api/v1/memory/{id}           — Delete memory
  GET    /api/v1/memory/stats          — Memory stats

  # Knowledge Graph
  POST /api/v1/knowledge/nodes         — Add node
  GET  /api/v1/knowledge/nodes         — Find nodes
  GET  /api/v1/knowledge/nodes/{id}    — Get node
  POST /api/v1/knowledge/edges         — Add relation
  GET  /api/v1/knowledge/nodes/{id}/neighbors — Get neighbors
  GET  /api/v1/knowledge/path          — Find path
  GET  /api/v1/knowledge/stats         — KG stats

  # Approvals
  GET  /api/v1/approvals               — List pending approvals
  POST /api/v1/approvals/{id}/approve  — Approve
  POST /api/v1/approvals/{id}/deny     — Deny

  # Evolution
  POST /api/v1/evolution/proposals          — Create proposal
  GET  /api/v1/evolution/proposals           — List proposals
  GET  /api/v1/evolution/proposals/{id}      — Get proposal
  POST /api/v1/evolution/proposals/{id}/advance — Advance stage
  POST /api/v1/evolution/proposals/{id}/approve — Approve
  POST /api/v1/evolution/proposals/{id}/reject — Reject
  GET  /api/v1/evolution/proposals/{id}/deploy-check — Can deploy?
  GET  /api/v1/evolution/stats               — Evolution stats

  # Tests
  GET  /api/v1/tests/suites             — List test suites
  POST /api/v1/tests/run                — Run all tests
  POST /api/v1/tests/run/{suite_name}   — Run specific suite
  GET  /api/v1/tests/last-report        — Last test report
  GET  /api/v1/tests/stats              — Test engine stats

  # Audit
  GET /api/v1/audit                     — Query audit log
  GET /api/v1/audit/stats               — Audit stats

  # JSON-RPC bridge
  POST /rpc                             — Forward to MCP Gateway
"""

import json
import os
import sys

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .security import APIKeyAuthMiddleware, Principal, load_api_keys

# Ensure project root is importable
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class AIOSAPI:
    """Central API state holder.

    Holds references to all AIOS subsystems and provides
    the Starlette application.
    """

    def __init__(self, db_path=":memory:", constitution_dir=None, policies_dir=None, *, auth_required=True, api_keys=None):
        from aios_core.storage import Database
        from aios_core.orchestrator import Orchestrator
        from aios_core.test_engine import TestEngine
        from aios_core.mcp.gateway import MCPGateway, GatewayConfig

        self.db = Database(db_path=db_path)
        self.auth_required = auth_required
        self.api_keys = load_api_keys(api_keys) if isinstance(api_keys, str) else api_keys

        _const_dir = constitution_dir or os.path.join(_PROJECT_ROOT, "docs/constitution")
        _pol_dir = policies_dir or os.path.join(_PROJECT_ROOT, "policies")

        self.orchestrator = Orchestrator(
            db=self.db, constitution_dir=_const_dir, policies_dir=_pol_dir
        )
        self.policy = self.orchestrator.policy
        self.memory = self.orchestrator.memory
        self.knowledge = self.orchestrator.knowledge
        self.evolution = self.orchestrator.evolution
        self.audit = self.orchestrator.policy.audit
        self.approvals = self.orchestrator.policy.approvals

        self.test_engine = TestEngine(
            constitution_dir=_const_dir, policies_dir=_pol_dir, db=self.db
        )

        self.mcp_gateway = MCPGateway(
            config=GatewayConfig(
                constitution_dir=_const_dir,
                policies_dir=_pol_dir,
                db_path=db_path,
            ),
            db=self.db,
        )

    def create_starlette_app(self) -> Starlette:
        """Build the Starlette application with all routes."""
        routes = [
            # Health
            Route("/health", self._health),

            # Stats
            Route("/api/v1/stats", self._stats),

            # Constitutional evaluation
            Route("/api/v1/evaluate", self._evaluate, methods=["POST"]),
            Route("/api/v1/constitution/stats", self._constitution_stats),

            # Tasks
            Route("/api/v1/tasks", self._tasks_list, methods=["GET"]),
            Route("/api/v1/tasks", self._tasks_create, methods=["POST"]),
            Route("/api/v1/tasks/{task_id}", self._tasks_get),
            Route("/api/v1/tasks/{task_id}/execute", self._tasks_execute, methods=["POST"]),

            # Memory (stats route must come before {item_id} to avoid capture)
            Route("/api/v1/memory", self._memory_search, methods=["GET"]),
            Route("/api/v1/memory", self._memory_store, methods=["POST"]),
            Route("/api/v1/memory/stats", self._memory_stats),
            Route("/api/v1/memory/{item_id}", self._memory_get),
            Route("/api/v1/memory/{item_id}", self._memory_update, methods=["PUT"]),
            Route("/api/v1/memory/{item_id}", self._memory_delete, methods=["DELETE"]),

            # Knowledge
            Route("/api/v1/knowledge/nodes", self._kg_add_node, methods=["POST"]),
            Route("/api/v1/knowledge/nodes", self._kg_find_nodes, methods=["GET"]),
            Route("/api/v1/knowledge/nodes/{node_id}", self._kg_get_node),
            Route("/api/v1/knowledge/edges", self._kg_add_edge, methods=["POST"]),
            Route("/api/v1/knowledge/nodes/{node_id}/neighbors", self._kg_neighbors),
            Route("/api/v1/knowledge/path", self._kg_path),
            Route("/api/v1/knowledge/stats", self._kg_stats),

            # Approvals
            Route("/api/v1/approvals", self._approvals_list),
            Route("/api/v1/approvals/{approval_id}/approve", self._approvals_approve, methods=["POST"]),
            Route("/api/v1/approvals/{approval_id}/deny", self._approvals_deny, methods=["POST"]),

            # Evolution
            Route("/api/v1/evolution/proposals", self._evo_list),
            Route("/api/v1/evolution/proposals", self._evo_propose, methods=["POST"]),
            Route("/api/v1/evolution/proposals/{proposal_id}", self._evo_get),
            Route("/api/v1/evolution/proposals/{proposal_id}/advance", self._evo_advance, methods=["POST"]),
            Route("/api/v1/evolution/proposals/{proposal_id}/approve", self._evo_approve, methods=["POST"]),
            Route("/api/v1/evolution/proposals/{proposal_id}/reject", self._evo_reject, methods=["POST"]),
            Route("/api/v1/evolution/proposals/{proposal_id}/deploy-check", self._evo_deploy_check),
            Route("/api/v1/evolution/stats", self._evo_stats),

            # Tests
            Route("/api/v1/tests/suites", self._tests_suites),
            Route("/api/v1/tests/run", self._tests_run_all, methods=["POST"]),
            Route("/api/v1/tests/run/{suite_name}", self._tests_run_suite, methods=["POST"]),
            Route("/api/v1/tests/last-report", self._tests_last_report),
            Route("/api/v1/tests/stats", self._tests_stats),

            # Audit
            Route("/api/v1/audit", self._audit_query),
            Route("/api/v1/audit/stats", self._audit_stats),

            # JSON-RPC bridge
            Route("/rpc", self._rpc, methods=["POST"]),
        ]

        app = Starlette(
            routes=routes,
            middleware=[
                Middleware(APIKeyAuthMiddleware, enabled=self.auth_required, api_keys=self.api_keys),
                # Same-origin by default. Configure a deliberate allow-list at the reverse proxy.
                Middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"]),
            ],
        )
        return app

    def _memory_actor(self, request: Request) -> tuple[str, bool]:
        """Return authenticated subject and administrative scope for memory ACLs."""
        principal: Principal = request.state.principal
        return principal.subject, "admin" in principal.roles

    @staticmethod
    def _bounded_int(value, *, default: int, maximum: int) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            return default
        return min(max(parsed, 1), maximum)

    # ---- Health & Stats ----

    async def _health(self, request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": "4.0.0"})

    async def _stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.orchestrator.stats())

    # ---- Evaluate ----

    async def _evaluate(self, request: Request) -> JSONResponse:
        body = await request.json()
        result = self.orchestrator.evaluate(body)
        return JSONResponse(result)

    async def _constitution_stats(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "constitution": self.policy.engine.constitution.stats(),
            "policies": self.policy.engine.policies.stats(),
        })

    # ---- Tasks ----

    async def _tasks_list(self, request: Request) -> JSONResponse:
        status = request.query_params.get("status")
        tasks = self.orchestrator.list_tasks(status=status)
        return JSONResponse({"tasks": tasks, "count": len(tasks)})

    async def _tasks_create(self, request: Request) -> JSONResponse:
        body = await request.json()
        task = self.orchestrator.create_task(
            name=body.get("name", "unnamed"),
            description=body.get("description", ""),
            agent_id=body.get("agent_id", "api-user"),
            authority=body.get("authority", "user"),
            risk_level=body.get("risk_level", "medium"),
            metadata=body.get("metadata"),
        )
        # Add steps if provided
        for step_data in body.get("steps", []):
            self.orchestrator.add_step(
                task,
                step_type=step_data.get("step_type", "tool"),
                params=step_data.get("params", {}),
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
            )
        return JSONResponse({
            "task_id": task.id,
            "name": task.name,
            "status": task.status.value,
            "steps": len(task.steps),
        })

    async def _tasks_get(self, request: Request) -> JSONResponse:
        task_id = request.path_params["task_id"]
        task = self.orchestrator.get_task(task_id)
        if task is None:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        return JSONResponse(self.orchestrator._task_summary(task))

    async def _tasks_execute(self, request: Request) -> JSONResponse:
        task_id = request.path_params["task_id"]
        task = self.orchestrator.get_task(task_id)
        if task is None:
            return JSONResponse({"error": "Task not found"}, status_code=404)
        result = self.orchestrator.execute_task(task)
        return JSONResponse(result)

    # ---- Memory ----

    async def _memory_search(self, request: Request) -> JSONResponse:
        subject, is_admin = self._memory_actor(request)
        results = self.memory.search(
            query=request.query_params.get("query", ""),
            category=request.query_params.get("category"),
            tag=request.query_params.get("tag"),
            limit=self._bounded_int(request.query_params.get("limit"), default=100, maximum=100),
            requester_id=subject,
            is_admin=is_admin,
        )
        return JSONResponse({"items": results, "count": len(results)})

    async def _memory_store(self, request: Request) -> JSONResponse:
        body = await request.json()
        subject, _ = self._memory_actor(request)
        result = self.memory.store(
            content=body.get("content", {}),
            category=body.get("category", "operational"),
            tags=body.get("tags"),
            source=body.get("source"),
            confidence=body.get("confidence", 1.0),
            owner_id=subject,
        )
        return JSONResponse(result, status_code=201)

    async def _memory_get(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        subject, is_admin = self._memory_actor(request)
        item = self.memory.retrieve(item_id, requester_id=subject, is_admin=is_admin)
        if item is None:
            return JSONResponse({"error": "Memory item not found"}, status_code=404)
        return JSONResponse(item)

    async def _memory_update(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        body = await request.json()
        subject, is_admin = self._memory_actor(request)
        result = self.memory.update(
            item_id,
            content=body.get("content"),
            tags=body.get("tags"),
            confidence=body.get("confidence"),
            requester_id=subject,
            is_admin=is_admin,
        )
        if result is None:
            return JSONResponse({"error": "Memory item not found or immutable"}, status_code=404)
        return JSONResponse(result)

    async def _memory_delete(self, request: Request) -> JSONResponse:
        item_id = request.path_params["item_id"]
        subject, is_admin = self._memory_actor(request)
        deleted = self.memory.delete(item_id, requester_id=subject, is_admin=is_admin)
        return JSONResponse({"deleted": deleted})

    async def _memory_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.memory.stats())

    # ---- Knowledge Graph ----

    async def _kg_add_node(self, request: Request) -> JSONResponse:
        body = await request.json()
        node = self.knowledge.add_node(
            label=body.get("label", ""),
            node_type=body.get("node_type", "concept"),
            properties=body.get("properties"),
        )
        return JSONResponse(node, status_code=201)

    async def _kg_find_nodes(self, request: Request) -> JSONResponse:
        nodes = self.knowledge.find_nodes(
            label=request.query_params.get("label"),
            node_type=request.query_params.get("node_type"),
            limit=int(request.query_params.get("limit", "100")),
        )
        return JSONResponse({"nodes": nodes, "count": len(nodes)})

    async def _kg_get_node(self, request: Request) -> JSONResponse:
        node_id = request.path_params["node_id"]
        node = self.knowledge.get_node(node_id)
        if node is None:
            return JSONResponse({"error": "Node not found"}, status_code=404)
        return JSONResponse(node)

    async def _kg_add_edge(self, request: Request) -> JSONResponse:
        body = await request.json()
        edge = self.knowledge.add_relation(
            source_id=body["source_id"],
            target_id=body["target_id"],
            relation=body["relation"],
            properties=body.get("properties"),
            weight=body.get("weight", 1.0),
        )
        return JSONResponse(edge, status_code=201)

    async def _kg_neighbors(self, request: Request) -> JSONResponse:
        node_id = request.path_params["node_id"]
        neighbors = self.knowledge.neighbors(
            node_id=node_id,
            relation=request.query_params.get("relation"),
            depth=int(request.query_params.get("depth", "1")),
        )
        return JSONResponse({"neighbors": neighbors, "count": len(neighbors)})

    async def _kg_path(self, request: Request) -> JSONResponse:
        source = request.query_params.get("source")
        target = request.query_params.get("target")
        if not source or not target:
            return JSONResponse({"error": "source and target query params required"}, status_code=400)
        path = self.knowledge.path(source, target)
        return JSONResponse({"path": path, "length": len(path)})

    async def _kg_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.knowledge.stats())

    # ---- Approvals ----

    async def _approvals_list(self, request: Request) -> JSONResponse:
        pending = self.approvals.get_pending()
        return JSONResponse({"approvals": pending, "count": len(pending)})

    async def _approvals_approve(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.approve(approval_id)
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    async def _approvals_deny(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.deny(approval_id)
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    # ---- Evolution ----

    async def _evo_list(self, request: Request) -> JSONResponse:
        status = request.query_params.get("status")
        proposals = self.evolution.list_proposals(status=status)
        return JSONResponse({"proposals": proposals, "count": len(proposals)})

    async def _evo_propose(self, request: Request) -> JSONResponse:
        body = await request.json()
        proposal = self.evolution.propose(
            change=body.get("change", {}),
            component=body.get("component", ""),
            reason=body.get("reason", ""),
        )
        return JSONResponse(proposal, status_code=201)

    async def _evo_get(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        proposal = self.evolution.get_proposal(proposal_id)
        if proposal is None:
            return JSONResponse({"error": "Proposal not found"}, status_code=404)
        return JSONResponse(proposal)

    async def _evo_advance(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            proposal = self.evolution.advance(proposal_id)
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_approve(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            proposal = self.evolution.approve(proposal_id)
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_reject(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        try:
            body = await request.json()
            proposal = self.evolution.reject(
                proposal_id, reason=body.get("reason", "")
            )
            return JSONResponse(proposal)
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _evo_deploy_check(self, request: Request) -> JSONResponse:
        proposal_id = request.path_params["proposal_id"]
        can = self.evolution.can_deploy(proposal_id)
        return JSONResponse({"proposal_id": proposal_id, "can_deploy": can})

    async def _evo_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.evolution.stats())

    # ---- Tests ----

    async def _tests_suites(self, request: Request) -> JSONResponse:
        return JSONResponse({"suites": self.test_engine.list_suites()})

    async def _tests_run_all(self, request: Request) -> JSONResponse:
        report = self.test_engine.run_all()
        return JSONResponse(self.test_engine.reporter.to_dict(report))

    async def _tests_run_suite(self, request: Request) -> JSONResponse:
        suite_name = request.path_params["suite_name"]
        try:
            suite_result = self.test_engine.run_suite(suite_name)
            return JSONResponse({
                "suite_name": suite_result.suite_name,
                "status": suite_result.status.value,
                "total": suite_result.total,
                "passed": suite_result.passed,
                "failed": suite_result.failed,
                "errors": suite_result.errors,
                "duration_ms": suite_result.duration_ms,
            })
        except ValueError as e:
            return JSONResponse({"error": str(e)}, status_code=404)

    async def _tests_last_report(self, request: Request) -> JSONResponse:
        report = self.test_engine.last_report()
        if report is None:
            return JSONResponse({"error": "No reports generated yet"}, status_code=404)
        return JSONResponse(self.test_engine.reporter.to_dict(report))

    async def _tests_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.test_engine.stats())

    # ---- Audit ----

    async def _audit_query(self, request: Request) -> JSONResponse:
        events = self.audit.query(
            event_type=request.query_params.get("event_type"),
            agent_id=request.query_params.get("agent_id"),
            decision=request.query_params.get("decision"),
            limit=int(request.query_params.get("limit", "100")),
            offset=int(request.query_params.get("offset", "0")),
        )
        return JSONResponse({"events": events, "count": len(events)})

    async def _audit_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.audit.stats())

    # ---- JSON-RPC Bridge ----

    async def _rpc(self, request: Request) -> JSONResponse:
        body = await request.body()
        try:
            raw = body.decode("utf-8")
        except Exception:
            raw = "{}"
        response_str = self.mcp_gateway.handle_request(raw)
        if response_str is None:
            return JSONResponse({"processed": True})
        return JSONResponse(
            json.loads(response_str),
            media_type="application/json",
        )

    def close(self):
        self.db.close()


def create_app(db_path=":memory:", constitution_dir=None, policies_dir=None, *, auth_required=True, api_keys=None):
    """Factory function to create the AIOS Starlette application.

    Usage:
        app = create_app(db_path=":memory:", constitution_dir="...", policies_dir="...")

    # Or for testing:
        from httpx import AsyncClient, ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
    """
    api = AIOSAPI(
        db_path=db_path,
        constitution_dir=constitution_dir,
        policies_dir=policies_dir,
        auth_required=auth_required,
        api_keys=api_keys,
    )
    return api.create_starlette_app()