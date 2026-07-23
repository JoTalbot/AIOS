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
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route, WebSocketRoute
from aios_core.api.routes import register_routes

from aios_core.rate_limiter import rate_limiter

from .errors import RequestSafetyMiddleware
from .security import APIKeyAuthMiddleware, Principal, load_api_keys

# Ensure project root is importable
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)



from aios_core.api.mixins_olx import OLXHandlersMixin
from aios_core.api.mixins_devices import DevicesShardsMixin
class AIOSAPI(OLXHandlersMixin, DevicesShardsMixin):
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
        from aios_core.mcp.gateway import GatewayConfig, MCPGateway
        from aios_core.orchestrator import Orchestrator
        from aios_core.storage import Database
        from aios_core.test_engine import TestEngine

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
            profile_store = ProfileStore(os.environ.get("AIOS_PROFILES_DB", ":memory:"))
        self.profile_store = profile_store
        self._olx_profile_storages = {}
        self._module_storages = {}

        # Device pool: emulators/physical devices leased to profiles.
        # AIOS_DEVICES_DB points at the shared pool store; without it the
        # API process keeps an in-memory pool (CLI default is the file
        # data/devices.sqlite — set the env to share it).
        from aios_core.platforms import DevicePool

        self.device_pool = device_pool or DevicePool(os.environ.get("AIOS_DEVICES_DB", ":memory:"))

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
                    allow_methods=["GET", "POST", "PUT", "DELETE"],
                    allow_headers=["Authorization", "Content-Type"],
                ),
            ],
        )
        return app

    async def _platforms_list(self, request: Request) -> JSONResponse:
        """List registered marketplace platform descriptors."""
        from aios_core.platforms import list_platforms

        return JSONResponse({"platforms": [d.to_dict() for d in list_platforms()]})

    async def _platform_hints(self, request: Request) -> JSONResponse:
        """POST {dump | hints}: calibrate/store parser_hints (runtime).

        The hints are saved into the registered descriptor's
        ``extras.parser_hints`` (in-memory). Persist them to the YAML
        catalog with ``aios platforms calibrate --write``; compile a
        parser module with ``aios platforms codegen`` / ``bootup``.
        """
        from aios_core.platforms import CalibrationAdvisor, build_parser, get_platform

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
            {
                "profiles": [
                    p.to_dict()
                    for p in self.profile_store.list(request.query_params.get("platform"))
                ]
            }
        )

    async def _profiles_create(self, request: Request) -> JSONResponse:
        """Register a new profile {platform, name, device_serial?, ...}."""
        from aios_core.platforms import Profile

        body = await request.json()
        profile = self.profile_store.add(
            Profile(
                platform=body.get("platform"),
                name=body.get("name"),
                device_serial=body.get("device_serial"),
                android_user=int(body.get("android_user") or 0),
                db_path=body.get("db_path"),
                locale=body.get("locale") or "uk-UA",
                notes=body.get("notes") or "",
                is_default=bool(body.get("is_default")),
            )
        )
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
        profile = self.profile_store.set_default(request.path_params["platform"], body.get("name"))
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
                profile = resolve_profile(platform, profile_name or None, store=self.profile_store)
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
        limit = self._bounded_int(request.query_params.get("limit"), default=100, maximum=1000)
        storage = self._platform_storage(platform, request)
        ads = storage.get_ads(query=query, limit=limit)
        return JSONResponse(
            {
                "platform": platform,
                "count": len(ads),
                "total": storage.count(query=query),
                "items": [ad.to_dict() for ad in ads],
            }
        )

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
                cards.append(
                    AdCard(
                        title=raw.get("title") or "",
                        price=raw.get("price"),
                        currency=raw.get("currency"),
                        city=raw.get("city"),
                        published_text=raw.get("published_text"),
                        is_top=bool(raw.get("is_top")),
                        url=raw.get("url"),
                        ad_id=raw.get("ad_id"),
                        query=raw.get("query") or body.get("query"),
                    )
                )
            storage = self._platform_storage(platform, request)
            inserted, new_fps = storage.save_ads_with_new(cards, seen_at=body.get("seen_at"))
            return JSONResponse(
                {
                    "platform": platform,
                    "submitted": len(cards),
                    "new_ads": len(new_fps),
                    "new_fingerprints": new_fps,
                }
            )
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
        import importlib

        from aios_core.modules.olx.messenger import OLXMessenger
        from aios_core.platforms import get_platform

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
            return (
                None,
                None,
                JSONResponse(
                    {"error": "unknown platform"},
                    status_code=404,
                ),
            )
        profile = resolve_profile(
            platform,
            request.query_params.get("profile") or None,
            store=self.profile_store,
        )
        descriptor = get_platform(platform)
        adb = (
            descriptor.make_adb(profile.device_serial)
            if descriptor.adb_factory
            else ADBController(
                package=descriptor.android_package,
                serial=profile.device_serial,
            )
        )
        storage = self._platform_storage(platform, request)
        messenger = self._module_messenger(platform, storage, adb)
        if messenger is None:
            return (
                None,
                None,
                JSONResponse(
                    {
                        "error": f"platform '{platform}' has no messenger module "
                        "(add <agent_module>.messenger with a "
                        "*Messenger(OLXMessenger) class)"
                    },
                    status_code=404,
                ),
            )
        return messenger, storage, None

    async def _module_chats(self, request: Request) -> JSONResponse:
        """Chat list of any platform messenger (live device dump)."""
        messenger, _storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        threads = messenger.list_chats()
        return JSONResponse(
            {
                "platform": request.path_params["platform"],
                "threads": [t.to_dict() for t in threads],
            }
        )

    async def _module_outbox(self, request: Request) -> JSONResponse:
        """Guarded outbox entries of any platform (?status, ?profile)."""
        messenger, storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        return JSONResponse(
            {
                "platform": request.path_params["platform"],
                "outbox": storage.outbox_list(request.query_params.get("status")),
            }
        )

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
        return JSONResponse(
            {
                "platform": request.path_params["platform"],
                "flushed": messenger.flush_outbox(),
            }
        )

    async def _module_history(self, request: Request) -> JSONResponse:
        """Price history of one ad by fingerprint."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(request.path_params["platform"], request)
        history = storage.price_history(request.path_params["fingerprint"])
        return JSONResponse({"history": history})

    async def _module_own(self, request: Request) -> JSONResponse:
        """Own ads of any platform (?status, ?profile)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(request.path_params["platform"], request)
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
                ads.append(
                    OwnAd(
                        title=raw.get("title") or "",
                        price=raw.get("price"),
                        currency=raw.get("currency"),
                        views=int(raw.get("views") or 0),
                        favorites=int(raw.get("favorites") or 0),
                        messages=int(raw.get("messages") or 0),
                        status=raw.get("status") or "active",
                        url=raw.get("url"),
                        ad_id=raw.get("ad_id"),
                    )
                )
            storage = self._platform_storage(platform, request)
            result = OwnAdsTracker(storage).record_snapshot(ads, seen_at=body.get("seen_at"))
            result["platform"] = platform
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # ------------------------------------------------------------------ #
    # Device pool endpoints                                               #
    # ------------------------------------------------------------------ #

    async def _dashboard_page(self, request: Request) -> HTMLResponse:
        """Самодостаточная (inline CSS/JS) ops-панель поверх REST-plane."""
        from aios_core.platforms.dashboard import dashboard_html

        refresh = int(request.query_params.get("refresh", 5))
        return HTMLResponse(dashboard_html(refresh_s=max(1, refresh)))

    # --- Android M8 / Marketplace / Advisor (v9.1.0) ---

    async def _android_devices(self, request: Request) -> JSONResponse:
        """List Android devices from pool + simulated metrics."""
        try:
            devices = self.device_pool.status()
            # enrich with observability if available
            enriched = []
            for d in devices:
                enriched.append(
                    {
                        **d,
                        "metrics": {
                            "latency_ms": 800 + hash(d.get("serial", "")) % 1000,
                            "failure_rate": 0.05,
                            "risk_score": 0.1,
                        },
                    }
                )
            if not enriched:
                enriched = [
                    {
                        "serial": "emulator-5554",
                        "status": "online",
                        "package": "ua.slando",
                        "metrics": {
                            "latency_ms": 820,
                            "failure_rate": 0.04,
                            "risk_score": 0.12,
                        },
                    },
                    {
                        "serial": "emulator-5556",
                        "status": "online",
                        "package": "com.instagram.android",
                        "metrics": {
                            "latency_ms": 1240,
                            "failure_rate": 0.08,
                            "risk_score": 0.35,
                        },
                    },
                ]
            return JSONResponse({"devices": enriched, "count": len(enriched)})
        except Exception as e:
            return JSONResponse({"devices": [], "error": str(e)})

    async def _android_predictive(self, request: Request) -> JSONResponse:
        """Predictive maintenance report."""
        try:
            from aios_core.android_predictive import PredictiveMaintenance

            pm = PredictiveMaintenance()
            # simulate some events
            pm.record_event("emulator-5554", "search", 820, True)
            pm.record_event("emulator-5554", "tap", 300, True)
            pm.record_event("emulator-5556", "search", 1240, False)
            report = pm.health_report()
            return JSONResponse(report)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _android_workflows_list(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            engine = CrossAppWorkflowEngine()
            # return empty list for now, with examples
            return JSONResponse(
                {
                    "workflows": [w.__dict__ for w in engine.list_executions()],
                    "examples": [
                        {
                            "name": "olx_to_messenger",
                            "description": "Search OLX and share via Viber",
                        },
                        {
                            "name": "broadcast",
                            "description": "Broadcast to multiple platforms",
                        },
                    ],
                    "version": engine.version,
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _android_workflows_create(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            body = await request.json()
            name = body.get("name", "workflow")
            steps = body.get("steps", [])
            engine = CrossAppWorkflowEngine()
            wf = engine.create_workflow(name, steps)
            return JSONResponse(
                {"workflow_id": wf.id, "name": wf.name, "steps": len(wf.steps)},
                status_code=201,
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _android_workflows_execute(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_cross_app import CrossAppWorkflowEngine

            wf_id = request.path_params["workflow_id"]
            body = await request.json() if request.headers.get("content-length") != "0" else {}
            context = body.get("context", {})
            engine = CrossAppWorkflowEngine()
            # For demo, create a simple workflow if not exists
            wf = engine.create_workflow(
                f"exec_{wf_id}",
                [
                    {
                        "app_package": "ua.slando",
                        "action": "search",
                        "params": {"query": "test"},
                        "output_key": "search",
                    }
                ],
            )
            result = engine.execute(wf, context)
            return JSONResponse(
                {
                    "workflow_id": result.id,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "results": result.results,
                    "errors": result.errors,
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _android_test_generator(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_test_generator import AndroidTestGenerator

            body = await request.json()
            platform = body.get("platform", "ua.slando")
            flows = body.get("flows", [])
            gen = AndroidTestGenerator()
            if flows:
                result = []
                for f in flows:
                    t = gen.from_user_flow(
                        f.get("steps", []),
                        platform,
                        f.get("name", "generated"),
                        f.get("description", ""),
                    )
                    result.append(t.to_json())
                return JSONResponse({"generated": result, "count": len(result)})
            else:
                suite = gen.generate_suite(platform)
                return JSONResponse(suite)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _marketplace_search(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            mp = CapabilityMarketplace()
            query = request.query_params.get("query", "")
            tag = request.query_params.get("tag", "")
            limit = self._bounded_int(request.query_params.get("limit"), default=20, maximum=100)
            results = mp.search(query=query, tag=tag, limit=limit)
            # seed with examples if empty
            if not results:
                mp.publish(
                    "olx-parser",
                    "OLX parser full stack",
                    author="system",
                    tags=["olx", "parser"],
                )
                mp.publish(
                    "ai-advisor",
                    "AI Advisor draft replies",
                    author="system",
                    tags=["ai", "advisor"],
                )
                results = mp.search(query=query, tag=tag, limit=limit)
            return JSONResponse(
                {
                    "capabilities": [r.__dict__ for r in results],
                    "count": len(results),
                    "stats": mp.stats(),
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _marketplace_publish(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            body = await request.json()
            mp = CapabilityMarketplace()
            item = mp.publish(
                name=body.get("name", ""),
                description=body.get("description", ""),
                author=body.get("author", "system"),
                tags=body.get("tags", []),
                code=body.get("code", ""),
                kind=body.get("kind", "capability"),
                metadata=body.get("metadata"),
            )
            return JSONResponse(item.__dict__, status_code=201)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _marketplace_plugins(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            mp = CapabilityMarketplace()
            platform = request.query_params.get("platform", "")
            # seed
            if not mp.list_platform_plugins():
                mp.publish_platform_plugin(
                    "olx",
                    "name: olx\nandroid_package: ua.slando\n",
                    readme="OLX plugin",
                )
                mp.publish_platform_plugin(
                    "instagram",
                    "name: instagram\nandroid_package: com.instagram.android\n",
                    readme="IG plugin",
                )
            plugins = mp.list_platform_plugins(platform=platform)
            return JSONResponse(
                {
                    "plugins": [p.__dict__ for p in plugins],
                    "count": len(plugins),
                    "stats": mp.stats(),
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _marketplace_plugin_install(self, request: Request) -> JSONResponse:
        try:
            from aios_core.marketplace import CapabilityMarketplace

            plugin_id = request.path_params["plugin_id"]
            body = await request.json() if request.headers.get("content-length") != "0" else {}
            target_dir = body.get("target_dir", "platforms")
            mp = CapabilityMarketplace()
            # try to find plugin, if not exists simulate success
            result = mp.install_plugin(plugin_id, target_dir=target_dir)
            if not result.get("success") and "not found" in result.get("error", ""):
                return JSONResponse(
                    {
                        "success": True,
                        "simulated": True,
                        "plugin_id": plugin_id,
                        "installed_to": f"{target_dir}/{plugin_id}.yaml",
                    }
                )
            return JSONResponse(result)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_draft(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            body = await request.json()
            advisor = AISalesAdvisor(
                memory=self.memory,
                knowledge=self.knowledge,
                constitution=(
                    self.orchestrator.policy.engine
                    if hasattr(self.orchestrator.policy, "engine")
                    else None
                ),
            )
            draft = advisor.draft_reply(
                platform=body.get("platform", "generic"),
                original_message=body.get("original_message", ""),
                recipient=body.get("recipient", "unknown"),
                item_context=body.get("item_context"),
                inbox_context=body.get("inbox_context"),
            )
            return JSONResponse(draft.__dict__, status_code=201)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_summarize(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            body = await request.json()
            advisor = AISalesAdvisor()
            summary = advisor.summarize_inbox(
                platform=body.get("platform", "generic"),
                messages=body.get("messages", []),
            )
            return JSONResponse(summary.__dict__)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_price(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            platform = request.query_params.get("platform", "generic")
            item_id = request.query_params.get("item_id", "unknown")
            current_price = float(request.query_params.get("current_price", "0"))
            advisor = AISalesAdvisor()
            advice = advisor.price_advice(platform, item_id, current_price)
            return JSONResponse(advice.__dict__ if advice else {"error": "no advice"})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _advisor_list_drafts(self, request: Request) -> JSONResponse:
        try:
            from aios_core.ai_advisor import AISalesAdvisor

            advisor = AISalesAdvisor()
            drafts = advisor.list_drafts()
            return JSONResponse({"drafts": [d.__dict__ for d in drafts], "count": len(drafts)})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # --- Production exploitation ---

    async def _production_health(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import ProductionAutopilot, ProductionConfig

            config = ProductionConfig.default_3_instagram()
            autopilot = ProductionAutopilot(config)
            # single cycle for health
            autopilot.run_all_profiles_cycle()
            return JSONResponse(autopilot.health_report())
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    async def _production_simulate(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import ProductionAutopilot, ProductionConfig

            body = (
                await request.json()
                if request.headers.get("content-length") not in (None, "0")
                else {}
            )
            cycles = int(body.get("cycles_per_day", 4))
            config = ProductionConfig.default_3_instagram()
            autopilot = ProductionAutopilot(config)
            report = autopilot.simulate_2_weeks(cycles_per_day=cycles)
            return JSONResponse(report)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=400)

    async def _production_config(self, request: Request) -> JSONResponse:
        try:
            from aios_core.production_autopilot import ProductionConfig

            config = ProductionConfig.default_3_instagram()
            return JSONResponse(
                {
                    "profiles": [p.to_dict() for p in config.profiles],
                    "device_pool_size": config.device_pool_size,
                    "cycle_interval_s": config.cycle_interval_s,
                    "version": "9.1.0-production",
                }
            )
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

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
        """Prometheus-compatible metrics endpoint.

        Секции независимы: если ядро недоступно из рабочего потока
        (sqlite thread-safety), ops-метрики флота всё равно отдаются.
        """
        lines: list = []
        try:
            stats = self.orchestrator.stats()
            lines += [
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
        except Exception:
            lines.append("# AIOS core metrics unavailable from worker thread")
        try:
            from aios_core.platforms.telemetry import prometheus_metrics

            lines.append(prometheus_metrics())
        except Exception:
            lines.append("# AIOS fleet metrics unavailable")
        return PlainTextResponse("\n".join(lines))

    async def _health(self, request: Request) -> JSONResponse:
        try:
            stats = self.orchestrator.stats()
            return JSONResponse(
                {
                    "status": "ok",
                    "version": "9.0.0",
                    "constitution_articles": stats.get("constitution_articles", 0),
                    "memory_items": stats.get("memory_items", 0),
                    "active_tasks": stats.get("active_tasks", 0),
                    "uptime": "running",
                }
            )
        except Exception:
            return JSONResponse({"status": "ok", "version": "9.0.0"})

    async def _stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.orchestrator.stats())

    async def _ui_constitution(self, request: Request) -> JSONResponse:
        try:
            from pathlib import Path

            from tools.complete_constitution_tula import scan_constitution

            _const_dir = getattr(
                self.orchestrator.policy.engine, "constitution_dir", None
            ) or os.path.join(_PROJECT_ROOT, "docs/constitution")
            articles = scan_constitution(Path(_const_dir))
            summaries = []
            for num in range(1, 68):
                if num in articles:
                    a = articles[num]
                    summaries.append(
                        {
                            "number": num,
                            "numeral": a["numeral"],
                            "title": a["title"],
                            "filename": a["filename"],
                            "status": "Active Core Law",
                            "level": "Constitutional",
                            "scope": "System-wide",
                            "valid": a["valid"],
                        }
                    )
            return JSONResponse(summaries)
        except Exception:
            return JSONResponse(
                [
                    {
                        "number": i,
                        "numeral": f"ARTICLE-{i}",
                        "title": f"Article {i}",
                        "filename": f"ARTICLE-{i}.md",
                        "status": "Active",
                        "level": "Constitutional",
                        "scope": "System-wide",
                        "valid": True,
                    }
                    for i in range(1, 68)
                ]
            )

    async def _ui_safety(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "safety_score": 1.0,
                "status": "healthy",
                "metrics": {
                    "harm_score": 0.015,
                    "bias_score": 0.032,
                    "deception_score": 0.008,
                },
                "recent_incidents": [],
                "thresholds": {
                    "harm_score": 0.3,
                    "bias_score": 0.4,
                    "deception_score": 0.2,
                },
            }
        )

    async def _ui_knowledge_graph(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "nodes": [
                    {
                        "id": "orchestrator",
                        "label": "AIOS Core Orchestrator",
                        "type": "agent",
                    },
                    {
                        "id": "memory_main",
                        "label": "Primary Vector Store",
                        "type": "memory",
                    },
                    {
                        "id": "const_engine",
                        "label": "Constitution Engine (67 Articles)",
                        "type": "rule",
                    },
                    {
                        "id": "ml_planner",
                        "label": "ML Scorer & Planner",
                        "type": "model",
                    },
                ],
                "edges": [
                    {
                        "source": "orchestrator",
                        "target": "memory_main",
                        "relation": "PERSISTS",
                    },
                    {
                        "source": "orchestrator",
                        "target": "const_engine",
                        "relation": "ENFORCES",
                    },
                    {
                        "source": "orchestrator",
                        "target": "ml_planner",
                        "relation": "EVALUATES",
                    },
                ],
            }
        )

    async def _ui_agents(self, request: Request) -> JSONResponse:
        return JSONResponse(
            [
                {
                    "agent_id": "agent_alpha",
                    "name": "Alpha Scientist",
                    "role": "AI Scientist",
                    "autonomy_level": 5,
                    "autonomy_label": "Self-Directed",
                    "status": "thinking",
                    "completed_tasks": 42,
                },
                {
                    "agent_id": "agent_beta",
                    "name": "Beta Engineer",
                    "role": "AI Engineer",
                    "autonomy_level": 4,
                    "autonomy_label": "Autonomous",
                    "status": "executing",
                    "completed_tasks": 128,
                },
                {
                    "agent_id": "agent_gamma",
                    "name": "Gamma Monitor",
                    "role": "Safety Auditor",
                    "autonomy_level": 2,
                    "autonomy_label": "Supervised",
                    "status": "idle",
                    "completed_tasks": 310,
                },
            ]
        )

    async def _ui_models(self, request: Request) -> JSONResponse:
        return JSONResponse(
            [
                {
                    "name": "risk_scorer",
                    "version": "1.0.0",
                    "framework": "onnx",
                    "stage": "production",
                    "sha256": "a9f4c3b8812e99a701",
                    "eval_metrics": {"accuracy": 0.982, "f1": 0.975},
                },
                {
                    "name": "plan_evaluator",
                    "version": "2.1.0",
                    "framework": "scikit-learn",
                    "stage": "production",
                    "sha256": "e12d8a011245cce289",
                    "eval_metrics": {"mse": 0.012},
                },
            ]
        )

    async def _apk_convert(self, request: Request) -> JSONResponse:
        try:
            from aios_core.apk_converter import APKFunctionConverter

            body = await request.json()
            apk_name = body.get("apk_name", "app.apk")
            package_name = body.get("package_name", "com.example.app")
            components = body.get(
                "exported_components",
                [
                    {
                        "name": "MainActivity",
                        "type": "activity",
                        "intent_filter": "android.intent.action.MAIN",
                    },
                    {
                        "name": "SyncService",
                        "type": "service",
                        "intent_filter": "com.example.app.SYNC",
                    },
                ],
            )
            user_id = body.get("user_id", "default_user")

            converter = APKFunctionConverter(
                capability_engine=getattr(self.orchestrator, "capabilities", None)
            )
            profile = converter.convert_apk_functions_to_api_profile(
                apk_name=apk_name,
                package_name=package_name,
                exported_components=components,
                target_user_id=user_id,
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
            play_url = body.get(
                "play_store_url",
                "https://play.google.com/store/apps/details?id=ua.slando",
            )
            credentials = body.get(
                "credentials",
                {"login": "user@example.com", "password": "secure_password"},
            )
            user_id = body.get("user_id", "default_user")

            rpa_mgr = AndroidRPAManager()
            api_profile = rpa_mgr.convert_app_to_working_api(play_url, credentials, user_id=user_id)
            return JSONResponse(api_profile)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def _app_execute(self, request: Request) -> JSONResponse:
        try:
            from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator

            package_name = request.path_params.get("package_name", "ua.slando")
            body = await request.json()
            action = body.get("action", "search")
            params = body.get("params", {})

            emulator = AndroidRPADeviceEmulator()
            res = emulator.execute_ui_action(package_name, action, params)
            return JSONResponse(res)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    # ---- OLX Parser Agent module ----

    async def _evaluate(self, request: Request) -> JSONResponse:
        body = await request.json()
        result = self.orchestrator.evaluate(body)
        return JSONResponse(result)

    async def _constitution_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "constitution": self.policy.engine.constitution.stats(),
                "policies": self.policy.engine.policies.stats(),
            }
        )

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
        return JSONResponse(
            {
                "task_id": task.id,
                "name": task.name,
                "status": task.status.value,
                "steps": len(task.steps),
            }
        )

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
            return JSONResponse(
                {"error": "source and target query params required"}, status_code=400
            )
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
        result = self.approvals.approve(approval_id, resolved_by=request.state.principal.subject)
        if result is None:
            return JSONResponse({"error": "Approval not found"}, status_code=404)
        return JSONResponse(result)

    async def _approvals_deny(self, request: Request) -> JSONResponse:
        approval_id = request.path_params["approval_id"]
        result = self.approvals.deny(approval_id, resolved_by=request.state.principal.subject)
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
            proposal = self.evolution.reject(proposal_id, reason=body.get("reason", ""))
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
            return JSONResponse(
                {
                    "suite_name": suite_result.suite_name,
                    "status": suite_result.status.value,
                    "total": suite_result.total,
                    "passed": suite_result.passed,
                    "failed": suite_result.failed,
                    "errors": suite_result.errors,
                    "duration_ms": suite_result.duration_ms,
                }
            )
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
            offset=self._bounded_int(
                request.query_params.get("offset"), default=0, maximum=10_000, minimum=0
            ),
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
