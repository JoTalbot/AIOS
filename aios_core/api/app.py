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

import json
import os
import sys

from starlette.applications import Starlette
from starlette.routing import Route, WebSocketRoute
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .security import APIKeyAuthMiddleware, Principal, load_api_keys
from .errors import RequestSafetyMiddleware
from aios_core.rate_limiter import rate_limiter

# Ensure project root is importable
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class AIOSAPI:
    """Central API state holder.

    Holds references to all AIOS subsystems and provides
    the Starlette application.
    """

    def __init__(self, db_path=":memory:", constitution_dir=None, policies_dir=None, *, auth_required=True, api_keys=None, olx_storage=None, olx_collector=None, olx_messenger=None, profile_store=None, device_pool=None, shard_router=None, shard_gateway=None):
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
            profile_store = ProfileStore(
                os.environ.get("AIOS_PROFILES_DB", ":memory:")
            )
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
        routes = [
            # Health & Metrics
            Route("/health", self._health),
            Route("/metrics", self._metrics),

            # Stats & Web UI endpoints
            Route("/api/v1/stats", self._stats),
            Route("/api/v1/constitution", self._ui_constitution),
            Route("/api/v1/safety", self._ui_safety),
            Route("/api/v1/knowledge-graph", self._ui_knowledge_graph),
            Route("/api/v1/agents", self._ui_agents),
            Route("/api/v1/models", self._ui_models),
            Route("/api/v1/apk/convert", self._apk_convert, methods=["POST"]),
            Route("/api/v1/apk/profiles", self._apk_profiles, methods=["GET"]),
            Route("/api/v1/apps/transform", self._app_transform, methods=["POST"]),
            Route("/api/v1/apps/{package_name}/execute", self._app_execute, methods=["POST"]),

            # OLX Parser Agent module
            Route("/api/v1/modules/olx/ads", self._olx_ads, methods=["GET"]),
            Route("/api/v1/modules/olx/stats", self._olx_stats, methods=["GET"]),
            Route("/api/v1/modules/olx/history", self._olx_history, methods=["GET"]),
            Route("/api/v1/modules/olx/drops", self._olx_drops, methods=["GET"]),
            Route("/api/v1/modules/olx/recommendations", self._olx_recommend, methods=["POST"]),
            Route("/api/v1/modules/olx/collect", self._olx_collect, methods=["POST"]),
            Route("/api/v1/modules/olx/schedule", self._olx_schedule, methods=["POST"]),
            Route("/api/v1/modules/olx/schedule", self._olx_unschedule, methods=["DELETE"]),
            Route("/api/v1/modules/olx/detail", self._olx_detail_parse, methods=["POST"]),
            Route("/api/v1/modules/olx/chats", self._olx_chats, methods=["GET"]),
            Route("/api/v1/modules/olx/chats/reply", self._olx_chat_reply, methods=["POST"]),
            Route("/api/v1/modules/olx/outbox", self._olx_outbox, methods=["GET"]),
            Route("/api/v1/modules/olx/outbox/send", self._olx_outbox_send, methods=["POST"]),
            Route("/api/v1/modules/olx/outbox/cancel", self._olx_outbox_cancel, methods=["POST"]),
            Route("/api/v1/modules/olx/own", self._olx_own_list, methods=["GET"]),
            Route("/api/v1/modules/olx/own/snapshot", self._olx_own_snapshot, methods=["POST"]),
            Route("/api/v1/modules/olx/own/stagnant", self._olx_own_stagnant, methods=["GET"]),
            Route("/api/v1/modules/olx/own/improve", self._olx_own_improve, methods=["POST"]),
            Route("/api/v1/modules/olx/own/repost", self._olx_own_repost, methods=["POST"]),
            Route("/api/v1/modules/olx/own/edit", self._olx_own_edit, methods=["POST"]),
            Route("/api/v1/modules/olx/notify", self._olx_notify, methods=["POST"]),
            Route("/api/v1/modules/olx/subscriptions", self._olx_subscriptions, methods=["GET"]),
            Route("/api/v1/modules/olx/subscriptions", self._olx_subscription_add, methods=["POST"]),
            Route("/api/v1/modules/olx/subscriptions/check", self._olx_subscription_check, methods=["POST"]),
            Route("/api/v1/modules/olx/subscriptions/{subscription_id:int}", self._olx_subscription_remove, methods=["DELETE"]),
            Route("/api/v1/modules/olx/favorites", self._olx_favorites, methods=["GET"]),
            Route("/api/v1/modules/olx/favorites", self._olx_favorite_add, methods=["POST"]),
            Route("/api/v1/modules/olx/favorites/alerts", self._olx_favorite_alerts, methods=["GET"]),
            Route("/api/v1/modules/olx/favorites/{fingerprint}", self._olx_favorite_remove, methods=["DELETE"]),
            Route("/api/v1/modules/olx/autowatch", self._olx_autowatch, methods=["POST"]),
            Route("/api/v1/modules/olx/doctor", self._olx_doctor, methods=["GET"]),
            Route("/api/v1/modules/olx/profile", self._olx_profile, methods=["GET"]),
            Route("/api/v1/modules/olx/profile/parse", self._olx_profile_parse, methods=["POST"]),
            Route("/api/v1/modules/olx/profile/edit", self._olx_profile_edit, methods=["POST"]),
            Route("/api/v1/modules/olx/competitive", self._olx_competitive, methods=["GET"]),
            Route("/api/v1/modules/olx/competitive/refresh", self._olx_competitive_refresh, methods=["POST"]),
            Route("/api/v1/modules/olx/competitive/seller-scan", self._olx_competitive_seller_scan, methods=["POST"]),
            Route("/api/v1/platforms", self._platforms_list, methods=["GET"]),
            Route("/api/v1/platforms/{platform}/hints", self._platform_hints, methods=["POST"]),
            Route("/api/v1/profiles", self._profiles_list, methods=["GET"]),
            Route("/api/v1/profiles", self._profiles_create, methods=["POST"]),
            Route("/api/v1/profiles/{platform}/{name}", self._profiles_show, methods=["GET"]),
            Route("/api/v1/profiles/{platform}/{name}", self._profiles_remove, methods=["DELETE"]),
            Route("/api/v1/profiles/{platform}/default", self._profiles_set_default, methods=["POST"]),
            Route("/api/v1/devices", self._devices_list, methods=["GET"]),
            Route("/api/v1/devices/register", self._devices_register, methods=["POST"]),
            Route("/api/v1/devices/lease", self._devices_lease, methods=["POST"]),
            Route("/api/v1/devices/release", self._devices_release, methods=["POST"]),
            Route("/api/v1/devices/heartbeat", self._devices_heartbeat, methods=["POST"]),
            Route("/api/v1/devices/reap", self._devices_reap, methods=["POST"]),
            Route("/api/v1/devices/limits", self._devices_limits_get, methods=["GET"]),
            Route("/api/v1/devices/limits", self._devices_limits_set, methods=["POST"]),
            Route("/api/v1/devices/waitlist", self._devices_waitlist, methods=["GET"]),
            Route("/api/v1/devices/waitlist/cancel", self._devices_waitlist_cancel, methods=["POST"]),
            Route("/api/v1/shards", self._shards_list, methods=["GET"]),
            Route("/api/v1/shards", self._shards_add, methods=["POST"]),
            Route("/api/v1/shards/route", self._shards_route, methods=["POST"]),
            Route("/api/v1/shards/route", self._shards_unroute, methods=["DELETE"]),
            Route("/api/v1/shards/gateway", self._shards_gateway, methods=["POST"]),
            Route("/api/v1/shards/{host}", self._shards_remove, methods=["DELETE"]),

            # Generic platform module surfaces (descriptor-driven). Статичные
            # роуты olx зарегистрированы выше и матчатся первыми.
            Route("/api/v1/modules/{platform}/ads", self._module_ads, methods=["GET"]),
            Route("/api/v1/modules/{platform}/ads/ingest", self._module_ads_ingest, methods=["POST"]),
            Route("/api/v1/modules/{platform}/stats", self._module_stats, methods=["GET"]),
            Route("/api/v1/modules/{platform}/ads/{fingerprint}/history", self._module_history, methods=["GET"]),
            Route("/api/v1/modules/{platform}/own", self._module_own, methods=["GET"]),
            Route("/api/v1/modules/{platform}/own/snapshot", self._module_own_snapshot, methods=["POST"]),
            Route("/api/v1/modules/{platform}/chats", self._module_chats, methods=["GET"]),
            Route("/api/v1/modules/{platform}/outbox", self._module_outbox, methods=["GET"]),
            Route("/api/v1/modules/{platform}/outbox/send", self._module_outbox_send, methods=["POST"]),
            Route("/api/v1/modules/{platform}/outbox/flush", self._module_outbox_flush, methods=["POST"]),
            Route("/api/v1/modules/olx/advisor", self._olx_advisor, methods=["GET"]),

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

            # WebSocket (real-time)
            WebSocketRoute("/ws", self._websocket_endpoint),
        ]

        async def _value_error_response(request: Request, exc: ValueError):
            # Например: неизвестный профиль платформы (?profile=...).
            return JSONResponse({"error": str(exc)}, status_code=400)

        app = Starlette(
            routes=routes,
            exception_handlers={ValueError: _value_error_response},
            middleware=[
                Middleware(RequestSafetyMiddleware),
                Middleware(APIKeyAuthMiddleware, enabled=self.auth_required, api_keys=self.api_keys),
                # Same-origin by default. Configure a deliberate allow-list at the reverse proxy.
                Middleware(CORSMiddleware, allow_origins=[], allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Authorization", "Content-Type"]),
            ],
        )
        return app

    def _olx_db(self, request: Request):
        """Profile-scoped OLX storage.

        ``?profile=<name>`` switches the request to that account's isolated
        storage (cached per name); without the parameter the API-wide
        default storage is used. Unknown names raise ``ValueError`` which
        the app-level exception handler maps to HTTP 400.
        """
        name = request.query_params.get("profile")
        if not name:
            return self.olx_storage
        storage = self._olx_profile_storages.get(name)
        if storage is None:
            from aios_core.platforms import resolve_profile
            from aios_core.modules.olx import OLXStorage
            profile = resolve_profile("olx", name, store=self.profile_store)
            storage = OLXStorage(profile.db_path)
            self._olx_profile_storages[name] = storage
        return storage

    # ------------------------------------------------------------------ #
    # Platforms & profiles registry endpoints                             #
    # ------------------------------------------------------------------ #

    async def _platforms_list(self, request: Request) -> JSONResponse:
        """List registered marketplace platform descriptors."""
        from aios_core.platforms import list_platforms
        return JSONResponse(
            {"platforms": [d.to_dict() for d in list_platforms()]}
        )

    async def _platform_hints(self, request: Request) -> JSONResponse:
        """POST {dump | hints}: calibrate/store parser_hints (runtime).

        The hints are saved into the registered descriptor's
        ``extras.parser_hints`` (in-memory). Persist them to the YAML
        catalog with ``aios platforms calibrate --write``; compile a
        parser module with ``aios platforms codegen`` / ``bootup``.
        """
        from aios_core.platforms import (
            CalibrationAdvisor,
            build_parser,
            get_platform,
        )
        try:
            descriptor = get_platform(request.path_params["platform"])
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        body = await request.json()
        dump_xml = body.get("dump")
        hints = body.get("hints")
        if hints is None and dump_xml:
            hints = CalibrationAdvisor().analyze(dump_xml)
        if not isinstance(hints, dict) or not hints:
            return JSONResponse(
                {"error": "provide 'dump' (ui xml) or 'hints' (object)"},
                status_code=400,
            )
        descriptor.extras["parser_hints"] = hints
        response = {
            "platform": descriptor.name,
            "hints": hints,
            "saved": "descriptor.extras.parser_hints (runtime)",
        }
        if dump_xml:
            cards = build_parser(hints).parse(dump_xml)
            response["parser_preview"] = {
                "cards": len(cards),
                "sample_titles": [c.title for c in cards[:3]],
            }
        return JSONResponse(response)

    async def _profiles_list(self, request: Request) -> JSONResponse:
        """List profiles, optionally filtered by ?platform=."""
        return JSONResponse(
            {"profiles": [
                p.to_dict()
                for p in self.profile_store.list(
                    request.query_params.get("platform")
                )
            ]}
        )

    async def _profiles_create(self, request: Request) -> JSONResponse:
        """Register a new profile {platform, name, device_serial?, ...}."""
        from aios_core.platforms import Profile
        body = await request.json()
        profile = self.profile_store.add(Profile(
            platform=body.get("platform"), name=body.get("name"),
            device_serial=body.get("device_serial"),
            android_user=int(body.get("android_user") or 0),
            db_path=body.get("db_path"),
            locale=body.get("locale") or "uk-UA",
            notes=body.get("notes") or "",
            is_default=bool(body.get("is_default")),
        ))
        return JSONResponse(profile.to_dict(), status_code=201)

    async def _profiles_show(self, request: Request) -> JSONResponse:
        """One profile by path {platform}/{name}."""
        profile = self.profile_store.get(
            request.path_params["platform"], request.path_params["name"]
        )
        if profile is None:
            return JSONResponse({"error": "profile not found"}, status_code=404)
        return JSONResponse(profile.to_dict())

    async def _profiles_remove(self, request: Request) -> JSONResponse:
        """Delete a profile (its storage file is kept untouched)."""
        removed = self.profile_store.remove(
            request.path_params["platform"], request.path_params["name"]
        )
        self._olx_profile_storages.pop(request.path_params["name"], None)
        return JSONResponse({"removed": removed})

    async def _profiles_set_default(self, request: Request) -> JSONResponse:
        """Mark {name} as the default profile of {platform}."""
        body = await request.json()
        profile = self.profile_store.set_default(
            request.path_params["platform"], body.get("name")
        )
        if profile is None:
            return JSONResponse({"error": "profile not found"}, status_code=404)
        return JSONResponse(profile.to_dict())

    # ------------------------------------------------------------------ #
    # Generic platform module surfaces (descriptor-driven)                #
    # ------------------------------------------------------------------ #

    def _platform_storage(self, platform: str, request: Request):
        """Profile-scoped storage for ANY registered platform.

        Works off the platform descriptor (``storage_factory``), so a
        scaffold-генерированная платформа получает рабочий data-plane без
        единой строки серверного кода. ``?profile=`` переключает аккаунт
        точно так же, как у OLX; результат кэшируется на ключ
        ``platform:profile``.
        """
        profile_name = request.query_params.get("profile") or ""
        cache_key = f"{platform}:{profile_name}"
        storage = self._module_storages.get(cache_key)
        if storage is None:
            if platform == "olx" and not profile_name:
                storage = self.olx_storage
            else:
                from aios_core.platforms import get_platform, resolve_profile
                descriptor = get_platform(platform)
                profile = resolve_profile(
                    platform, profile_name or None, store=self.profile_store
                )
                storage = descriptor.make_storage(profile.db_path)
            self._module_storages[cache_key] = storage
        return storage

    def _module_or_404(self, request: Request):
        """Дескриптор платформы пути или None (→ 404)."""
        from aios_core.platforms import get_platform
        try:
            return get_platform(request.path_params["platform"])
        except ValueError:
            return None

    async def _module_ads(self, request: Request) -> JSONResponse:
        """List ads of any platform (?query, ?limit, ?profile)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        platform = request.path_params["platform"]
        query = request.query_params.get("query")
        limit = self._bounded_int(
            request.query_params.get("limit"), default=100, maximum=1000
        )
        storage = self._platform_storage(platform, request)
        ads = storage.get_ads(query=query, limit=limit)
        return JSONResponse({
            "platform": platform,
            "count": len(ads),
            "total": storage.count(query=query),
            "items": [ad.to_dict() for ad in ads],
        })

    async def _module_ads_ingest(self, request: Request) -> JSONResponse:
        """Ingest platform-agnostic AdCard dicts (collector push)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        try:
            from aios_core.modules.olx import AdCard
            platform = request.path_params["platform"]
            body = await request.json()
            cards = []
            for raw in body.get("ads") or []:
                cards.append(AdCard(
                    title=raw.get("title") or "",
                    price=raw.get("price"),
                    currency=raw.get("currency"),
                    city=raw.get("city"),
                    published_text=raw.get("published_text"),
                    is_top=bool(raw.get("is_top")),
                    url=raw.get("url"),
                    ad_id=raw.get("ad_id"),
                    query=raw.get("query") or body.get("query"),
                ))
            storage = self._platform_storage(platform, request)
            inserted, new_fps = storage.save_ads_with_new(
                cards, seen_at=body.get("seen_at")
            )
            return JSONResponse({
                "platform": platform,
                "submitted": len(cards),
                "new_ads": len(new_fps),
                "new_fingerprints": new_fps,
            })
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _module_stats(self, request: Request) -> JSONResponse:
        """Market statistics of any platform (?query, ?profile)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        from aios_core.modules.olx import CompetitorAnalyzer
        platform = request.path_params["platform"]
        query = request.query_params.get("query")
        storage = self._platform_storage(platform, request)
        ads = storage.get_ads(query=query, active_only=True)
        payload = CompetitorAnalyzer().analyze(ads, query=query).to_dict()
        payload["platform"] = platform
        return JSONResponse(payload)

    # ------------------------------------------------------------------ #
    # Generic guarded messenger plane (per-platform messenger module)     #
    # ------------------------------------------------------------------ #

    def _module_messenger(self, platform: str, storage, adb):
        """OLXMessenger-совместимый мессенджер платформы или None.

        Резолв: ``<agent_module>.messenger`` → класс *Messenger
        (наследник OLXMessenger). Instagram получает hints-driven
        Direct, OLX — родной; платформа без messenger-модуля → 404.
        """
        from aios_core.modules.olx.messenger import OLXMessenger
        from aios_core.platforms import get_platform
        import importlib

        descriptor = get_platform(platform)
        try:
            module = importlib.import_module(f"{descriptor.agent_module}.messenger")
        except ImportError:
            if platform == "olx":
                module = importlib.import_module("aios_core.modules.olx.messenger")
            else:
                return None
        for attr in dir(module):
            candidate = getattr(module, attr)
            if (
                isinstance(candidate, type)
                and attr.endswith("Messenger")
                and issubclass(candidate, OLXMessenger)
                and candidate is not OLXMessenger
            ):
                return candidate(adb=adb, storage=storage)
        if platform == "olx":
            return OLXMessenger(adb=adb, storage=storage)
        return None

    def _module_messenger_or_404(self, request: Request):
        """(messenger, storage, error_response) для guarded-плоскости."""
        from aios_core.modules.olx.adb import ADBController
        from aios_core.platforms import get_platform, resolve_profile

        platform = request.path_params["platform"]
        if self._module_or_404(request) is None:
            return None, None, JSONResponse(
                {"error": "unknown platform"}, status_code=404,
            )
        profile = resolve_profile(
            platform,
            request.query_params.get("profile") or None,
            store=self.profile_store,
        )
        descriptor = get_platform(platform)
        adb = descriptor.make_adb(profile.device_serial) \
            if descriptor.adb_factory else ADBController(
                package=descriptor.android_package,
                serial=profile.device_serial,
            )
        storage = self._platform_storage(platform, request)
        messenger = self._module_messenger(platform, storage, adb)
        if messenger is None:
            return None, None, JSONResponse(
                {"error": f"platform '{platform}' has no messenger module "
                          "(add <agent_module>.messenger with a "
                          "*Messenger(OLXMessenger) class)"},
                status_code=404,
            )
        return messenger, storage, None

    async def _module_chats(self, request: Request) -> JSONResponse:
        """Chat list of any platform messenger (live device dump)."""
        messenger, _storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        threads = messenger.list_chats()
        return JSONResponse({
            "platform": request.path_params["platform"],
            "threads": [t.to_dict() for t in threads],
        })

    async def _module_outbox(self, request: Request) -> JSONResponse:
        """Guarded outbox entries of any platform (?status, ?profile)."""
        messenger, storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        return JSONResponse({
            "platform": request.path_params["platform"],
            "outbox": storage.outbox_list(request.query_params.get("status")),
        })

    async def _module_outbox_send(self, request: Request) -> JSONResponse:
        """Queue (default) or immediately send a messenger reply.

        Guarded: without ``auto_send: true`` the text only lands in the
        approval outbox — ничего не уходит на устройство молча.
        """
        messenger, _storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        body = await request.json()
        result = messenger.send_reply(
            body.get("chat_key") or "",
            body.get("text") or "",
            interlocutor=body.get("interlocutor"),
            auto_send=bool(body.get("auto_send")),
        )
        result["platform"] = request.path_params["platform"]
        return JSONResponse(result)

    async def _module_outbox_flush(self, request: Request) -> JSONResponse:
        """Send every approved pending outbox entry of the platform."""
        messenger, _storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        return JSONResponse({
            "platform": request.path_params["platform"],
            "flushed": messenger.flush_outbox(),
        })

    async def _module_history(self, request: Request) -> JSONResponse:
        """Price history of one ad by fingerprint."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(
            request.path_params["platform"], request
        )
        history = storage.price_history(request.path_params["fingerprint"])
        return JSONResponse({"history": history})

    async def _module_own(self, request: Request) -> JSONResponse:
        """Own ads of any platform (?status, ?profile)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(
            request.path_params["platform"], request
        )
        items = storage.own_ads(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _module_own_snapshot(self, request: Request) -> JSONResponse:
        """Record own-ads counters snapshot for any platform."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        try:
            from aios_core.modules.olx import OwnAd, OwnAdsTracker
            platform = request.path_params["platform"]
            body = await request.json()
            ads = []
            for raw in body.get("ads") or []:
                ads.append(OwnAd(
                    title=raw.get("title") or "",
                    price=raw.get("price"),
                    currency=raw.get("currency"),
                    views=int(raw.get("views") or 0),
                    favorites=int(raw.get("favorites") or 0),
                    messages=int(raw.get("messages") or 0),
                    status=raw.get("status") or "active",
                    url=raw.get("url"),
                    ad_id=raw.get("ad_id"),
                ))
            storage = self._platform_storage(platform, request)
            result = OwnAdsTracker(storage).record_snapshot(
                ads, seen_at=body.get("seen_at")
            )
            result["platform"] = platform
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------ #
    # Device pool endpoints                                               #
    # ------------------------------------------------------------------ #

    async def _devices_list(self, request: Request) -> JSONResponse:
        """Pool status: all registered devices with lease info."""
        return JSONResponse({"devices": self.device_pool.status()})

    async def _devices_register(self, request: Request) -> JSONResponse:
        """Register a device {serial, avd_name?}."""
        body = await request.json()
        if not body.get("serial"):
            return JSONResponse({"error": "'serial' is required"}, status_code=400)
        record = self.device_pool.register(
            body["serial"], avd_name=body.get("avd_name")
        )
        return JSONResponse(record, status_code=201)

    async def _devices_lease(self, request: Request) -> JSONResponse:
        """Lease a device to a profile {profile: "olx:work", serial?,
        enqueue?, priority?}.

        Updates the profile's ``device_serial`` in the profiles registry
        when the profile exists there. With ``enqueue`` a failed lease
        puts the profile on the waitlist (HTTP 202) instead of 409 —
        исполнение очереди происходит автоматически при release/reap.
        """
        body = await request.json()
        profile_key = body.get("profile")
        if not profile_key:
            return JSONResponse({"error": "'profile' is required"}, status_code=400)
        try:
            record = self.device_pool.lease(
                profile_key,
                serial=body.get("serial"),
                profile_store=self.profile_store,
            )
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if record is None:
            if body.get("enqueue"):
                wait_id = self.device_pool.enqueue(
                    profile_key, priority=int(body.get("priority") or 0)
                )
                return JSONResponse(
                    {"queued": wait_id, "profile": profile_key},
                    status_code=202,
                )
            return JSONResponse(
                {"error": "no idle device available"}, status_code=409
            )
        return JSONResponse(record)

    async def _devices_release(self, request: Request) -> JSONResponse:
        """Release the device leased to a profile {profile}."""
        body = await request.json()
        freed = self.device_pool.release(body.get("profile"))
        return JSONResponse({"released": freed})

    async def _devices_heartbeat(self, request: Request) -> JSONResponse:
        """Heartbeat from a device {serial}."""
        body = await request.json()
        ok = self.device_pool.heartbeat(body.get("serial"))
        return JSONResponse({"ok": ok})

    async def _devices_reap(self, request: Request) -> JSONResponse:
        """Mark silent devices offline {max_silence_s?} and free leases."""
        body = await request.json() if (request.headers.get("content-length") or "0") != "0" else {}
        reaped = self.device_pool.reap_stale(
            self._bounded_int(body.get("max_silence_s"), default=900, maximum=86400)
        )
        return JSONResponse({"reaped": reaped})

    async def _devices_limits_get(self, request: Request) -> JSONResponse:
        """Current pool quotas {max_devices, max_busy:<platform>, max_avds}."""
        return JSONResponse({"limits": self.device_pool.limits()})

    async def _devices_limits_set(self, request: Request) -> JSONResponse:
        """Set one quota {key, value} (int)."""
        body = await request.json()
        key, value = body.get("key"), body.get("value")
        if not key or value is None:
            return JSONResponse(
                {"error": "'key' and 'value' are required"}, status_code=400
            )
        try:
            self.device_pool.set_limit(key, int(value))
        except (TypeError, ValueError):
            return JSONResponse(
                {"error": "'value' must be an integer"}, status_code=400
            )
        return JSONResponse({"limits": self.device_pool.limits()})

    async def _devices_waitlist(self, request: Request) -> JSONResponse:
        """Device lease waitlist (?status=waiting|served|cancelled|all)."""
        status = request.query_params.get("status", "waiting")
        status = None if status == "all" else status
        return JSONResponse({"waitlist": self.device_pool.waitlist(status)})

    async def _devices_waitlist_cancel(self, request: Request) -> JSONResponse:
        """Remove a profile from the waitlist {profile}."""
        body = await request.json()
        cancelled = self.device_pool.cancel_wait(body.get("profile"))
        return JSONResponse({"cancelled": cancelled})

    # ------------------------------------------------------------------ #
    # Shard routing endpoints                                             #
    # ------------------------------------------------------------------ #

    async def _shards_list(self, request: Request) -> JSONResponse:
        """All shard hosts with health flags."""
        return JSONResponse({"shards": self.shard_router.hosts()})

    async def _shards_add(self, request: Request) -> JSONResponse:
        """Register a shard host {host, base_url}."""
        body = await request.json()
        if not body.get("host") or not body.get("base_url"):
            return JSONResponse(
                {"error": "'host' and 'base_url' are required"},
                status_code=400,
            )
        record = self.shard_router.add_host(body["host"], body["base_url"])
        return JSONResponse(record, status_code=201)

    async def _shards_remove(self, request: Request) -> JSONResponse:
        """Remove a shard host and its routes."""
        removed = self.shard_router.remove_host(request.path_params["host"])
        if not removed:
            return JSONResponse({"error": "host not found"}, status_code=404)
        return JSONResponse({"removed": True})

    async def _shards_route(self, request: Request) -> JSONResponse:
        """Sticky route for a profile {profile: "olx:work"}.

        Роутинг липкий и персистентен: повторный вызов возвращает тот же
        хост, пока он здоров.
        """
        body = await request.json()
        profile_key = body.get("profile")
        if not profile_key:
            return JSONResponse({"error": "'profile' is required"}, status_code=400)
        route = self.shard_router.route_for(profile_key)
        if route is None:
            return JSONResponse(
                {"error": "no healthy shard hosts"}, status_code=409
            )
        return JSONResponse(route)

    async def _shards_unroute(self, request: Request) -> JSONResponse:
        """Forget a profile's route {profile} (re-assigned on next route)."""
        body = await request.json()
        removed = self.shard_router.unroute(body.get("profile"))
        return JSONResponse({"unrouted": removed})

    async def _shards_gateway(self, request: Request) -> JSONResponse:
        """Proxy a module call to the profile's shard host.

        Body: ``{profile, method, path, params?, body?}``. Когда маршрут
        ведёт на этот узел (``AIOS_HOST_ID``) — возвращается маркер
        ``local`` без HTTP-петли (клиент вызывает локальный роут напрямую).
        """
        body = await request.json()
        profile_key = body.get("profile")
        method = body.get("method") or "GET"
        path = body.get("path") or ""
        if not profile_key or not path:
            return JSONResponse(
                {"error": "'profile' and 'path' are required"}, status_code=400
            )
        result = self.shard_gateway.proxy(
            profile_key, method, path,
            params=body.get("params"), json_body=body.get("body"),
        )
        if result.get("local"):
            return JSONResponse(result)
        status = result.get("status", 502)
        return JSONResponse(
            result.get("payload", result), status_code=int(status)
        )

    def _memory_actor(self, request: Request) -> tuple[str, bool]:
        """Return authenticated subject and administrative scope for memory ACLs."""
        principal: Principal = request.state.principal
        return principal.subject, "admin" in principal.roles

    def _can_access_task(self, request: Request, task) -> bool:
        principal: Principal = request.state.principal
        return "admin" in principal.roles or task.agent_id == principal.subject

    @staticmethod
    def _bounded_int(value, *, default: int, maximum: int, minimum: int = 1) -> int:
        try:
            parsed = int(value) if value is not None else default
        except (TypeError, ValueError):
            return default
        return min(max(parsed, minimum), maximum)

    # ---- Health & Stats ----

    async def _metrics(self, request: Request) -> JSONResponse:
        """Prometheus-compatible metrics endpoint"""
        try:
            stats = self.orchestrator.stats()
            lines = [
                "# HELP aios_constitution_articles Total constitution articles",
                "# TYPE aios_constitution_articles gauge",
                f'aios_constitution_articles {stats.get("constitution_articles", 0)}',
                "",
                "# HELP aios_memory_items Total memory items",
                "# TYPE aios_memory_items gauge",
                f'aios_memory_items {stats.get("memory_items", 0)}',
                "",
                "# HELP aios_active_tasks Active tasks count",
                "# TYPE aios_active_tasks gauge",
                f'aios_active_tasks {stats.get("active_tasks", 0)}',
                "",
                "# HELP aios_evolution_proposals Evolution proposals",
                "# TYPE aios_evolution_proposals gauge",
                f'aios_evolution_proposals {stats.get("evolution_proposals", 0)}',
            ]
            return JSONResponse("\n".join(lines), media_type="text/plain")
        except Exception:
            return JSONResponse("# AIOS metrics unavailable", media_type="text/plain")

    async def _health(self, request: Request) -> JSONResponse:
        try:
            stats = self.orchestrator.stats()
            return JSONResponse({
                "status": "ok",
                "version": "9.0.0-alpha.14",
                "constitution_articles": stats.get("constitution_articles", 0),
                "memory_items": stats.get("memory_items", 0),
                "active_tasks": stats.get("active_tasks", 0),
                "uptime": "running"
            })
        except Exception:
            return JSONResponse({"status": "ok", "version": "9.0.0-alpha.14"})

    async def _stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.orchestrator.stats())

    async def _ui_constitution(self, request: Request) -> JSONResponse:
        try:
            from tools.complete_constitution_tula import scan_constitution
            _const_dir = getattr(self.orchestrator.policy.engine, "constitution_dir", None) or os.path.join(_PROJECT_ROOT, "docs/constitution")
            articles = scan_constitution(Path(_const_dir))
            summaries = []
            for num in range(1, 68):
                if num in articles:
                    a = articles[num]
                    summaries.append({
                        "number": num,
                        "numeral": a["numeral"],
                        "title": a["title"],
                        "filename": a["filename"],
                        "status": "Active Core Law",
                        "level": "Constitutional",
                        "scope": "System-wide",
                        "valid": a["valid"]
                    })
            return JSONResponse(summaries)
        except Exception:
            return JSONResponse([{"number": i, "numeral": f"ARTICLE-{i}", "title": f"Article {i}", "filename": f"ARTICLE-{i}.md", "status": "Active", "level": "Constitutional", "scope": "System-wide", "valid": True} for i in range(1, 68)])

    async def _ui_safety(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "safety_score": 1.0,
            "status": "healthy",
            "metrics": {"harm_score": 0.015, "bias_score": 0.032, "deception_score": 0.008},
            "recent_incidents": [],
            "thresholds": {"harm_score": 0.3, "bias_score": 0.4, "deception_score": 0.2}
        })

    async def _ui_knowledge_graph(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "nodes": [
                {"id": "orchestrator", "label": "AIOS Core Orchestrator", "type": "agent"},
                {"id": "memory_main", "label": "Primary Vector Store", "type": "memory"},
                {"id": "const_engine", "label": "Constitution Engine (67 Articles)", "type": "rule"},
                {"id": "ml_planner", "label": "ML Scorer & Planner", "type": "model"}
            ],
            "edges": [
                {"source": "orchestrator", "target": "memory_main", "relation": "PERSISTS"},
                {"source": "orchestrator", "target": "const_engine", "relation": "ENFORCES"},
                {"source": "orchestrator", "target": "ml_planner", "relation": "EVALUATES"}
            ]
        })

    async def _ui_agents(self, request: Request) -> JSONResponse:
        return JSONResponse([
            {"agent_id": "agent_alpha", "name": "Alpha Scientist", "role": "AI Scientist", "autonomy_level": 5, "autonomy_label": "Self-Directed", "status": "thinking", "completed_tasks": 42},
            {"agent_id": "agent_beta", "name": "Beta Engineer", "role": "AI Engineer", "autonomy_level": 4, "autonomy_label": "Autonomous", "status": "executing", "completed_tasks": 128},
            {"agent_id": "agent_gamma", "name": "Gamma Monitor", "role": "Safety Auditor", "autonomy_level": 2, "autonomy_label": "Supervised", "status": "idle", "completed_tasks": 310}
        ])

    async def _ui_models(self, request: Request) -> JSONResponse:
        return JSONResponse([
            {"name": "risk_scorer", "version": "1.0.0", "framework": "onnx", "stage": "production", "sha256": "a9f4c3b8812e99a701", "eval_metrics": {"accuracy": 0.982, "f1": 0.975}},
            {"name": "plan_evaluator", "version": "2.1.0", "framework": "scikit-learn", "stage": "production", "sha256": "e12d8a011245cce289", "eval_metrics": {"mse": 0.012}}
        ])

    async def _apk_convert(self, request: Request) -> JSONResponse:
        try:
            from aios_core.apk_converter import APKFunctionConverter
            body = await request.json()
            apk_name = body.get("apk_name", "app.apk")
            package_name = body.get("package_name", "com.example.app")
            components = body.get("exported_components", [
                {"name": "MainActivity", "type": "activity", "intent_filter": "android.intent.action.MAIN"},
                {"name": "SyncService", "type": "service", "intent_filter": "com.example.app.SYNC"}
            ])
            user_id = body.get("user_id", "default_user")

            converter = APKFunctionConverter(capability_engine=getattr(self.orchestrator, "capabilities", None))
            profile = converter.convert_apk_functions_to_api_profile(
                apk_name=apk_name,
                package_name=package_name,
                exported_components=components,
                target_user_id=user_id
            )
            return JSONResponse(profile)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _apk_profiles(self, request: Request) -> JSONResponse:
        user_id = request.query_params.get("user_id", "default_user")
        from aios_core.apk_converter import APKFunctionConverter
        converter = APKFunctionConverter()
        profiles = converter.get_user_profiles(user_id)
        return JSONResponse(profiles)

    async def _app_transform(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_rpa_bridge import AndroidRPAManager
            body = await request.json()
            play_url = body.get("play_store_url", "https://play.google.com/store/apps/details?id=ua.olx.android")
            credentials = body.get("credentials", {"login": "user@example.com", "password": "secure_password"})
            user_id = body.get("user_id", "default_user")

            rpa_mgr = AndroidRPAManager()
            api_profile = rpa_mgr.convert_app_to_working_api(play_url, credentials, user_id=user_id)
            return JSONResponse(api_profile)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _app_execute(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator
            package_name = request.path_params.get("package_name", "ua.olx.android")
            body = await request.json()
            action = body.get("action", "search")
            params = body.get("params", {})

            emulator = AndroidRPADeviceEmulator()
            res = emulator.execute_ui_action(package_name, action, params)
            return JSONResponse(res)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # ---- OLX Parser Agent module ----

    async def _olx_history(self, request: Request) -> JSONResponse:
        """Price history for one tracked ad (`fingerprint` is required)."""
        fingerprint = request.query_params.get("fingerprint")
        if not fingerprint:
            return JSONResponse(
                {"error": "query parameter 'fingerprint' is required"},
                status_code=400,
            )
        history = self._olx_db(request).price_history(fingerprint)
        return JSONResponse({"fingerprint": fingerprint, "count": len(history), "history": history})

    async def _olx_drops(self, request: Request) -> JSONResponse:
        """Price drops and ads that left the feed (`gone` = sold/removed)."""
        from aios_core.modules.olx import PriceTracker
        query = request.query_params.get("query")
        tracker = PriceTracker(self._olx_db(request))
        drops = tracker.price_drops(query=query)
        gone = tracker.gone_from_feed(query=query)
        return JSONResponse({
            "drops_count": len(drops),
            "drops": [change.to_dict() for change in drops],
            "gone_count": len(gone),
            "gone": [ad.to_dict() for ad in gone],
        })

    async def _olx_detail_parse(self, request: Request) -> JSONResponse:
        """Parse a UIAutomator dump of an open ad into structured detail data."""
        try:
            from aios_core.modules.olx import AdDetailParser
            body = await request.json()
            xml_text = body.get("xml")
            if not xml_text:
                return JSONResponse({"error": "field 'xml' is required"}, status_code=400)
            detail = AdDetailParser().parse(xml_text, url=body.get("url"))
            return JSONResponse(detail.to_dict())
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_chats(self, request: Request) -> JSONResponse:
        """List personal chat threads from the device (requires ADB)."""
        try:
            threads = self.olx_messenger.list_chats()
            return JSONResponse({
                "count": len(threads),
                "unread_total": sum(t.unread_count for t in threads),
                "items": [t.to_dict() for t in threads],
            })
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_chat_reply(self, request: Request) -> JSONResponse:
        """Queue a chat reply (default) or send it (`send_now: true`)."""
        try:
            body = await request.json()
            text = body.get("text") or ""
            if not text.strip():
                return JSONResponse({"error": "field 'text' is required"}, status_code=400)
            result = self.olx_messenger.send_reply(
                chat_key=body.get("chat_key") or "unknown",
                text=text,
                interlocutor=body.get("interlocutor"),
                auto_send=bool(body.get("send_now", False)),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_outbox(self, request: Request) -> JSONResponse:
        """List reply drafts (filterable by `status`)."""
        items = self._olx_db(request).outbox_list(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_outbox_send(self, request: Request) -> JSONResponse:
        """Flush every pending draft to the device."""
        try:
            results = self.olx_messenger.flush_outbox()
            return JSONResponse({"processed": len(results), "results": results})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_outbox_cancel(self, request: Request) -> JSONResponse:
        """Cancel a pending draft by id."""
        try:
            body = await request.json()
            outbox_id = int(body.get("id"))
            cancelled = self._olx_db(request).outbox_mark(outbox_id, "cancelled")
            return JSONResponse({"id": outbox_id, "cancelled": cancelled})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_list(self, request: Request) -> JSONResponse:
        """List my own tracked listings (filterable by `status`)."""
        items = self._olx_db(request).own_ads(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_own_snapshot(self, request: Request) -> JSONResponse:
        """Record a counters snapshot of own ads (parsed client-side or by the agent)."""
        try:
            from aios_core.modules.olx import OwnAd, OwnAdsTracker
            body = await request.json()
            ads = []
            for raw in body.get("ads") or []:
                ads.append(OwnAd(
                    title=raw.get("title") or "",
                    price=raw.get("price"),
                    currency=raw.get("currency"),
                    views=int(raw.get("views") or 0),
                    favorites=int(raw.get("favorites") or 0),
                    messages=int(raw.get("messages") or 0),
                    status=raw.get("status") or "active",
                    url=raw.get("url"),
                    ad_id=raw.get("ad_id"),
                ))
            result = OwnAdsTracker(self._olx_db(request)).record_snapshot(
                ads, seen_at=body.get("seen_at")
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_stagnant(self, request: Request) -> JSONResponse:
        """Own listings with too few views per day (repost candidates)."""
        from aios_core.modules.olx import OwnAdsTracker
        min_age = float(request.query_params.get("min_age_days", 3.0))
        min_rate = float(request.query_params.get("min_views_per_day", 1.0))
        items = OwnAdsTracker(self._olx_db(request)).stagnant(
            min_age_days=min_age, min_views_per_day=min_rate
        )
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_own_improve(self, request: Request) -> JSONResponse:
        """Improvement suggestion for one of my listings vs competitors."""
        try:
            from aios_core.modules.olx import AdImprover, OwnAd
            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"], ad_id=row["ad_id"],
                status=row["status"],
            )
            competitors = self._olx_db(request).get_ads(query=body.get("query"))
            suggestion = AdImprover().improve(own_ad, competitors)
            payload = suggestion.to_dict()
            payload["text"] = suggestion.to_text()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_repost(self, request: Request) -> JSONResponse:
        """Repost plan (dry-run default) or guarded execution (`confirm: true`)."""
        try:
            from aios_core.modules.olx import OwnAd, Reposter
            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                url=row["url"], ad_id=row["ad_id"], status=row["status"],
            )
            reposter = Reposter(adb=self.olx_messenger.adb)
            result = reposter.repost(own_ad, confirm=bool(body.get("confirm", False)))
            if result.get("status") == "executed":
                self._olx_db(request).own_ad_set_status(fingerprint, "inactive")
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_notify(self, request: Request) -> JSONResponse:
        """Send price-drop and stagnant-listing alerts to a webhook."""
        try:
            from aios_core.modules.olx import (
                OwnAdsTracker, PriceTracker, WebhookNotifier,
                notify_price_drops, notify_stagnant,
            )
            body = await request.json()
            notifier = WebhookNotifier(
                url=body.get("webhook_url"), chat_id=body.get("chat_id")
            )
            if not notifier.url:
                return JSONResponse(
                    {"error": "field 'webhook_url' is required"}, status_code=400
                )
            tracker = PriceTracker(self._olx_db(request))
            query = body.get("query")
            drops_summary = notify_price_drops(tracker, notifier, query=query)
            stagnant_items = OwnAdsTracker(self._olx_db(request)).stagnant()
            stagnant_summary = notify_stagnant(stagnant_items, notifier)
            return JSONResponse({"drops": drops_summary, "stagnant": stagnant_summary})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_own_edit(self, request: Request) -> JSONResponse:
        """Apply an improvement as an edit (dry-run default, `confirm` to run)."""
        try:
            from aios_core.modules.olx import AdImprover, OwnAd, OwnAdEditor
            body = await request.json()
            fingerprint = body.get("fingerprint")
            rows = [row for row in self._olx_db(request).own_ads() if row["fingerprint"] == fingerprint]
            if not rows:
                return JSONResponse({"error": "own ad not found"}, status_code=404)
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"], ad_id=row["ad_id"],
                status=row["status"],
            )
            competitors = self._olx_db(request).get_ads(query=body.get("query"))
            suggestion = AdImprover().improve(own_ad, competitors)
            editor = OwnAdEditor(adb=self.olx_messenger.adb)
            result = editor.apply(own_ad, suggestion, confirm=bool(body.get("confirm", False)))
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_subscriptions(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import SubscriptionManager
        items = SubscriptionManager(self._olx_db(request)).list()
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_subscription_add(self, request: Request) -> JSONResponse:
        try:
            from aios_core.modules.olx import SubscriptionManager
            body = await request.json()
            query = body.get("query")
            if not query:
                return JSONResponse({"error": "field 'query' is required"}, status_code=400)
            sub_id = SubscriptionManager(self._olx_db(request)).add(
                name=body.get("name") or query,
                query=query,
                min_price=body.get("min_price"),
                max_price=body.get("max_price"),
                city=body.get("city"),
            )
            return JSONResponse({"id": sub_id})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_subscription_remove(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import SubscriptionManager
        sub_id = int(request.path_params["subscription_id"])
        removed = SubscriptionManager(self._olx_db(request)).remove(sub_id)
        return JSONResponse({"id": sub_id, "removed": removed})

    async def _olx_subscription_check(self, request: Request) -> JSONResponse:
        """Match stored ads (optionally only recent) against all subscriptions."""
        try:
            from aios_core.modules.olx import SubscriptionManager
            body = await request.json() if request.method == "POST" else {}
            manager = SubscriptionManager(self._olx_db(request))
            query_filter = body.get("query")
            cards = self._olx_db(request).get_ads(query=query_filter)
            alerts = manager.check_new(cards)
            return JSONResponse({"alerts_count": len(alerts), "alerts": alerts})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_favorites(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch
        items = FavoritesWatch(self._olx_db(request)).list()
        return JSONResponse({"count": len(items), "items": items})

    async def _olx_favorite_add(self, request: Request) -> JSONResponse:
        try:
            from aios_core.modules.olx import FavoritesWatch
            body = await request.json()
            fingerprint = body.get("fingerprint")
            if not fingerprint:
                return JSONResponse(
                    {"error": "field 'fingerprint' is required"}, status_code=400
                )
            added = FavoritesWatch(self._olx_db(request)).add(fingerprint)
            return JSONResponse({"fingerprint": fingerprint, "added": added})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_favorite_remove(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch
        fingerprint = request.path_params["fingerprint"]
        removed = FavoritesWatch(self._olx_db(request)).remove(fingerprint)
        return JSONResponse({"fingerprint": fingerprint, "removed": removed})

    async def _olx_favorite_alerts(self, request: Request) -> JSONResponse:
        from aios_core.modules.olx import FavoritesWatch
        alerts = FavoritesWatch(self._olx_db(request)).price_alerts()
        return JSONResponse({"count": len(alerts), "alerts": alerts})

    async def _olx_autowatch(self, request: Request) -> JSONResponse:
        """Run one full AutoWatch cycle (collect → own → plan → notify)."""
        try:
            from aios_core.modules.olx import AutoWatch, WebhookNotifier
            body = await request.json()
            queries = body.get("queries")
            watch = AutoWatch(
                storage=self._olx_db(request),
                collector=self.olx_collector,
                notifier=WebhookNotifier(
                    url=body.get("webhook_url"), chat_id=body.get("chat_id")
                ),
                max_cards=self._bounded_int(body.get("max_cards"), default=50, maximum=500),
            )
            report = watch.run_cycle(
                queries=queries if isinstance(queries, list) else None,
                collect=bool(body.get("collect", True)),
                min_age_days=float(body.get("min_age_days", 3.0)),
                min_views_per_day=float(body.get("min_views_per_day", 1.0)),
            )
            return JSONResponse(report)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_doctor(self, request: Request) -> JSONResponse:
        """Environment readiness checklist for OLX automation."""
        from aios_core.modules.olx import OLXBootstrap
        report = OLXBootstrap().doctor_report()
        return JSONResponse(report)

    async def _olx_profile(self, request: Request) -> JSONResponse:
        """Stored profile fields and pending edits."""
        return JSONResponse({"fields": self._olx_db(request).profile_all()})

    async def _olx_profile_parse(self, request: Request) -> JSONResponse:
        """Parse a profile/settings screen dump and store the fields."""
        try:
            from aios_core.modules.olx import ProfileParser
            body = await request.json()
            xml_text = body.get("xml")
            if not xml_text:
                return JSONResponse({"error": "field 'xml' is required"}, status_code=400)
            parser = ProfileParser()
            profile = parser.parse_profile(xml_text)
            for key, value in profile.fields.items():
                self._olx_db(request).profile_set(key, value)
            payload = profile.to_dict()
            if body.get("include_settings"):
                texts = parser._texts(xml_text)
                payload["settings"] = parser.settings_from_texts(texts).to_dict()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_profile_edit(self, request: Request) -> JSONResponse:
        """Stage/execute a profile field edit (dry-run default)."""
        try:
            from aios_core.modules.olx import ProfileEditor
            body = await request.json()
            field_key = body.get("field")
            new_value = body.get("value")
            if not field_key or new_value is None:
                return JSONResponse(
                    {"error": "fields 'field' and 'value' are required"}, status_code=400
                )
            editor = ProfileEditor(adb=self.olx_messenger.adb)
            result = editor.apply(
                self._olx_db(request), field_key, str(new_value),
                confirm=bool(body.get("confirm", False)),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_competitive_refresh(self, request: Request) -> JSONResponse:
        """Re-link active own listings against the current market."""
        try:
            from aios_core.modules.olx import CompetitiveWatch, OwnAd
            body = await request.json() if (request.headers.get("content-length") or "0") != "0" else {}
            watch = CompetitiveWatch(self._olx_db(request))
            own_list = [
                OwnAd(
                    title=row["title"], price=row["price"], currency=row["currency"],
                    views=row["last_views"] or 0, url=row["url"],
                    ad_id=row["ad_id"], status=row["status"],
                )
                for row in self._olx_db(request).own_ads(status="active")
            ]
            result = watch.refresh(own_list)
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_competitive_seller_scan(self, request: Request) -> JSONResponse:
        """Crawl a competitor's portfolio from a detail-page UI dump.

        Body: ``{"fingerprint": <own ad fp>, "xml": "<hierarchy ...>"}``.
        """
        try:
            from aios_core.modules.olx import CompetitiveWatch, OwnAd
            body = await request.json()
            fingerprint = body.get("fingerprint")
            xml = body.get("xml")
            if not fingerprint or not xml:
                return JSONResponse(
                    {"error": "body must contain 'fingerprint' and 'xml'"},
                    status_code=400,
                )
            rows = [
                row for row in self._olx_db(request).own_ads()
                if row["fingerprint"] == fingerprint
            ]
            if not rows:
                return JSONResponse(
                    {"error": f"own ad '{fingerprint}' not found"}, status_code=404
                )
            row = rows[0]
            own = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"],
                ad_id=row["ad_id"], status=row["status"],
            )
            result = CompetitiveWatch(self._olx_db(request)).observe_seller_ads(
                xml, own,
                viewed_url=body.get("viewed_url"),
                viewed_ad_id=body.get("viewed_ad_id"),
            )
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_competitive(self, request: Request) -> JSONResponse:
        """Competitive report for one own listing (`fingerprint` required)."""
        from aios_core.modules.olx import CompetitiveWatch
        fingerprint = request.query_params.get("fingerprint")
        if not fingerprint:
            return JSONResponse(
                {"error": "query parameter 'fingerprint' is required"}, status_code=400
            )
        report = CompetitiveWatch(self._olx_db(request)).report(fingerprint)
        return JSONResponse(report)

    async def _olx_advisor(self, request: Request) -> JSONResponse:
        """Portfolio advice: actions for own ads + new-listing suggestions."""
        from aios_core.modules.olx import StrategyAdvisor
        advisor = StrategyAdvisor(self._olx_db(request))
        actions = [item.to_dict() for item in advisor.advise_actions()]
        payload: Dict[str, object] = {"actions": actions}
        if request.query_params.get("new") == "1":
            payload["new_listings"] = [
                item.to_dict() for item in advisor.advise_new_listings()
            ]
        return JSONResponse(payload)

    def _olx_get_scheduler(self, interval_s: float = 3600.0):
        # Фоновый планировщик — API-wide синглтон: работает на дефолтном
        # хранилище. Per-profile фоновые сборы запускаются через CLI/cron
        # с --profile (см. docs/PLATFORMS_SCALING.md).
        if self._olx_scheduler is None:
            from aios_core.modules.olx import CollectionScheduler
            self._olx_scheduler = CollectionScheduler(
                collector=self.olx_collector,
                storage=self.olx_storage,
                interval_s=interval_s,
            )
        self._olx_scheduler.interval_s = float(interval_s)
        return self._olx_scheduler

    async def _olx_ads(self, request: Request) -> JSONResponse:
        """List collected OLX ads (`query` filter, bounded `limit`)."""
        query = request.query_params.get("query")
        limit = self._bounded_int(request.query_params.get("limit"), default=100, maximum=1000)
        ads = self._olx_db(request).get_ads(query=query, limit=limit)
        return JSONResponse({
            "count": len(ads),
            "total": self._olx_db(request).count(query=query),
            "items": [ad.to_dict() for ad in ads],
        })

    async def _olx_stats(self, request: Request) -> JSONResponse:
        """Competitor market statistics for a search query (or the whole store)."""
        from aios_core.modules.olx import CompetitorAnalyzer
        query = request.query_params.get("query")
        ads = self._olx_db(request).get_ads(query=query)
        report = CompetitorAnalyzer().analyze(ads, query=query)
        return JSONResponse(report.to_dict())

    async def _olx_recommend(self, request: Request) -> JSONResponse:
        """Generate listing advice from collected competitors."""
        try:
            from dataclasses import asdict
            from aios_core.modules.olx import AdCard, RecommendationEngine
            body = await request.json()
            query = body.get("query")
            ads = self._olx_db(request).get_ads(query=query)
            my_ad = None
            if body.get("title") is not None or body.get("price") is not None:
                my_ad = AdCard(
                    title=body.get("title") or "",
                    price=body.get("price"),
                    currency=body.get("currency", "UAH"),
                    query=query,
                )
            advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
            payload = asdict(advice)
            payload["text"] = advice.to_text()
            return JSONResponse(payload)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_collect(self, request: Request) -> JSONResponse:
        """Run a one-off ADB collection for one or more search queries."""
        try:
            body = await request.json()
            queries = body.get("queries")
            if not isinstance(queries, list) or not queries:
                queries = [body.get("query") or "olx"]
            max_cards = self._bounded_int(body.get("max_cards"), default=50, maximum=500)
            scheduler = self._olx_get_scheduler()
            summaries = scheduler.run_once(queries, max_cards=max_cards)
            return JSONResponse({"summaries": summaries})
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_schedule(self, request: Request) -> JSONResponse:
        """Start periodic background collection."""
        try:
            body = await request.json()
            queries = body.get("queries")
            if not isinstance(queries, list) or not queries:
                queries = [body.get("query") or "olx"]
            interval_s = float(body.get("interval_s", 3600.0))
            if interval_s < 10.0:
                return JSONResponse(
                    {"error": "interval_s must be at least 10 seconds"},
                    status_code=400,
                )
            max_cards = self._bounded_int(body.get("max_cards"), default=50, maximum=500)
            scheduler = self._olx_get_scheduler(interval_s)
            started = scheduler.start(queries, max_cards=max_cards)
            return JSONResponse({
                "scheduled": scheduler.running,
                "started_now": started,
                "queries": queries,
                "interval_s": scheduler.interval_s,
                "max_cards": max_cards,
            })
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _olx_unschedule(self, request: Request) -> JSONResponse:
        """Stop the periodic background collection."""
        scheduler = self._olx_get_scheduler()
        was_running = scheduler.running
        scheduler.stop()
        return JSONResponse({
            "scheduled": False,
            "was_running": was_running,
            "history": scheduler.history[-20:],
        })

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
        principal: Principal = request.state.principal
        if "admin" not in principal.roles:
            tasks = [task for task in tasks if task.get("agent_id") == principal.subject]
        return JSONResponse({"tasks": tasks, "count": len(tasks)})

    async def _tasks_create(self, request: Request) -> JSONResponse:
        # Rate limiting
        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

        body = await request.json()
        task = self.orchestrator.create_task(
            name=body.get("name", "unnamed"),
            description=body.get("description", ""),
            agent_id=request.state.principal.subject,
            authority="user",
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
        if task is None or not self._can_access_task(request, task):
            return JSONResponse({"error": "Task not found"}, status_code=404)
        return JSONResponse(self.orchestrator._task_summary(task))

    async def _tasks_execute(self, request: Request) -> JSONResponse:
        task_id = request.path_params["task_id"]
        task = self.orchestrator.get_task(task_id)
        if task is None or not self._can_access_task(request, task):
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
            limit=self._bounded_int(request.query_params.get("limit"), default=100, maximum=100),
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
            depth=self._bounded_int(request.query_params.get("depth"), default=1, maximum=5),
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
        result = self.approvals.approve(
            approval_id, resolved_by=request.state.principal.subject
        )
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    async def _approvals_deny(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.deny(
            approval_id, resolved_by=request.state.principal.subject
        )
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
            limit=self._bounded_int(request.query_params.get("limit"), default=100, maximum=100),
            offset=self._bounded_int(request.query_params.get("offset"), default=0, maximum=10_000, minimum=0),
        )
        return JSONResponse({"events": events, "count": len(events)})

    async def _audit_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.audit.stats())

    # ---- WebSocket ----

    async def _websocket_endpoint(self, request: Request):
        from starlette.websockets import WebSocket
        from aios_core.websocket import ws_manager

        websocket = WebSocket(scope=request.scope, receive=request.receive, send=request.send)
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            ws_manager.disconnect(websocket)

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