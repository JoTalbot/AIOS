"""AIOS API — Platforms, Profiles & Generic Module Handler Mixin.

Extracted from ``aios_core.api.app.AIOSAPI``.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse


class PlatformsModulesMixin:
    """Platform registry, profiles, and generic module handlers — mixed into ``AIOSAPI``."""

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

    async def _module_own(self, request: Request) -> JSONResponse:
        """Own ads of any platform (?status, ?profile)."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(request.path_params["platform"], request)
        items = storage.own_ads(status=request.query_params.get("status"))
        return JSONResponse({"count": len(items), "items": items})

    async def _module_history(self, request: Request) -> JSONResponse:
        """Price history of one ad by fingerprint."""
        if self._module_or_404(request) is None:
            return JSONResponse({"error": "unknown platform"}, status_code=404)
        storage = self._platform_storage(request.path_params["platform"], request)
        history = storage.price_history(request.path_params["fingerprint"])
        return JSONResponse({"history": history})

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

    async def _module_outbox(self, request: Request) -> JSONResponse:
        """Guarded outbox entries of any platform (?status, ?profile)."""
        _messenger, storage, error = self._module_messenger_or_404(request)
        if error is not None:
            return error
        return JSONResponse(
            {
                "platform": request.path_params["platform"],
                "outbox": storage.outbox_list(request.query_params.get("status")),
            }
        )

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
            _inserted, new_fps = storage.save_ads_with_new(
                cards, seen_at=body.get("seen_at")
            )
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
        return JSONResponse(
            {
                "platform": platform,
                "count": len(ads),
                "total": storage.count(query=query),
                "items": [ad.to_dict() for ad in ads],
            }
        )

    def _module_or_404(self, request: Request):
        """Дескриптор платформы пути или None (→ 404)."""
        from aios_core.platforms import get_platform

        try:
            return get_platform(request.path_params["platform"])
        except ValueError:
            return None

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

    async def _profiles_remove(self, request: Request) -> JSONResponse:
        """Delete a profile (its storage file is kept untouched)."""
        removed = self.profile_store.remove(
            request.path_params["platform"], request.path_params["name"]
        )
        self._olx_profile_storages.pop(request.path_params["name"], None)
        return JSONResponse({"removed": removed})

    async def _profiles_show(self, request: Request) -> JSONResponse:
        """One profile by path {platform}/{name}."""
        profile = self.profile_store.get(
            request.path_params["platform"], request.path_params["name"]
        )
        if profile is None:
            return JSONResponse({"error": "profile not found"}, status_code=404)
        return JSONResponse(profile.to_dict())

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

    async def _profiles_list(self, request: Request) -> JSONResponse:
        """List profiles, optionally filtered by ?platform=."""
        return JSONResponse(
            {
                "profiles": [
                    p.to_dict()
                    for p in self.profile_store.list(
                        request.query_params.get("platform")
                    )
                ]
            }
        )

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

    async def _platforms_list(self, request: Request) -> JSONResponse:
        """List registered marketplace platform descriptors."""
        from aios_core.platforms import list_platforms

        return JSONResponse({"platforms": [d.to_dict() for d in list_platforms()]})
