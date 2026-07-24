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

  # OLX Parser Agent module
  GET    /api/v1/modules/olx/ads                — List collected OLX ads
  GET    /api/v1/modules/olx/stats              — OLX market statistics
  GET    /api/v1/modules/olx/history            — Price history for one ad
  GET    /api/v1/modules/olx/drops              — Price drops & gone-from-feed ads
  POST   /api/v1/modules/olx/recommendations    — Listing recommendations
  POST   /api/v1/modules/olx/collect            — One-off ADB collection run
  POST   /api/v1/modules/olx/schedule           — Start periodic collection
  DELETE /api/v1/modules/olx/schedule           — Stop periodic collection

  # JSON-RPC bridge
  POST /rpc                             — Forward to MCP Gateway
"""

import os
import sys

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from aios_core.api.routes import register_routes

from .errors import RequestSafetyMiddleware
from .security import APIKeyAuthMiddleware, load_api_keys

# Ensure project root is importable
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


from aios_core.api.mixins_core import CoreHandlersMixin
from aios_core.api.mixins_devices import DevicesShardsMixin
from aios_core.api.mixins_olx import OLXHandlersMixin
from aios_core.api.mixins_platforms import PlatformsModulesMixin


class AIOSAPI(
    OLXHandlersMixin, DevicesShardsMixin, PlatformsModulesMixin, CoreHandlersMixin
):
    """Central API state holder.

    Holds references to all AIOS subsystems and provides
    the Starlette application.
    """

    def __init__(
        self,
        db_path=":memory:",
        constitution_dir=None,
        policies_dir=None,
        *,
        auth_required=True,
        api_keys=None,
        olx_storage=None,
        olx_collector=None,
        olx_messenger=None,
        profile_store=None,
        device_pool=None,
        shard_router=None,
        shard_gateway=None,
    ):
        """Initialize AIOSAPI."""
        from aios_core.mcp.gateway import GatewayConfig, MCPGateway
        from aios_core.orchestrator import Orchestrator
        from aios_core.storage import Database
        from aios_core.test_engine import TestEngine

        self.db = Database(db_path=db_path)
        self.auth_required = auth_required
        self.api_keys = (
            load_api_keys(api_keys) if isinstance(api_keys, str) else api_keys
        )

        _const_dir = constitution_dir or os.path.join(
            _PROJECT_ROOT, "docs/constitution"
        )
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

        # OLX Parser Agent module (aios_core.modules.olx)
        if olx_storage is None:
            from aios_core.modules.olx import OLXStorage

            olx_storage = OLXStorage(os.environ.get("AIOS_OLX_DB", ":memory:"))
        self.olx_storage = olx_storage
        if olx_collector is None:
            from aios_core.modules.olx import OLXCollector

            olx_collector = OLXCollector()
        self.olx_collector = olx_collector
        if olx_messenger is None:
            from aios_core.modules.olx import OLXMessenger

            olx_messenger = OLXMessenger(storage=self.olx_storage)
        self.olx_messenger = olx_messenger
        self._olx_scheduler = None

        # Marketplace platforms: multi-account profile registry.
        # AIOS_PROFILES_DB points at the shared SQLite registry; without it
        # every API instance gets an empty in-memory registry.
        from aios_core.platforms import ProfileStore

        if profile_store is None:
            profile_store = ProfileStore(os.environ.get("AIOS_PROFILES_DB", ":memory:"))
        self.profile_store = profile_store
        self._olx_profile_storages = {}
        self._module_storages = {}

        # Device pool: emulators/physical devices leased to profiles.
        # AIOS_DEVICES_DB points at the shared pool store; without it the
        # API process keeps an in-memory pool (CLI default is the file
        # data/devices.sqlite — set the env to share it).
        from aios_core.platforms import DevicePool

        self.device_pool = device_pool or DevicePool(
            os.environ.get("AIOS_DEVICES_DB", ":memory:")
        )

        # Shard router: profile → host sticky routing across servers.
        # AIOS_SHARDS_DB points at the shared routes store; without it the
        # API process keeps an in-memory router.
        from aios_core.platforms import ShardRouter

        self.shard_router = shard_router or ShardRouter(
            os.environ.get("AIOS_SHARDS_DB", ":memory:")
        )

        # Shard gateway: proxies module calls to the profile's host.
        from aios_core.platforms import ShardGateway

        self.shard_gateway = shard_gateway or ShardGateway(self.shard_router)

    def create_starlette_app(self) -> Starlette:
        """Build the Starlette application with all routes."""
        routes = register_routes(self)
        # Admin handlers are defined separately because they own their
        # persistence helpers; initialise and register them with the main app.
        from aios_core.api.admin_routes import get_admin_routes, init_admin_routes

        init_admin_routes(db_path=self.db.db_path)
        routes.extend(get_admin_routes())

        async def _value_error_response(request: Request, exc: ValueError):
            # Например: неизвестный профиль платформы (?profile=...).
            return JSONResponse({"error": str(exc)}, status_code=400)

        app = Starlette(
            routes=routes,
            exception_handlers={ValueError: _value_error_response},
            middleware=[
                Middleware(RequestSafetyMiddleware),
                Middleware(
                    APIKeyAuthMiddleware,
                    enabled=self.auth_required,
                    api_keys=self.api_keys,
                ),
                # Same-origin by default. Configure a deliberate allow-list at the reverse proxy.
                Middleware(
                    CORSMiddleware,
                    allow_origins=[],
                    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                    allow_headers=["Authorization", "Content-Type"],
                ),
            ],
        )
        return app

    def close(self) -> None:
        """Clean up resources."""
        self.db.close()


def create_app(
    db_path=":memory:",
    constitution_dir=None,
    policies_dir=None,
    *,
    auth_required=True,
    api_keys=None,
):
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
