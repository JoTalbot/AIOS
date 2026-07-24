"""AIOS API — Devices & Shards Handler Mixin.

Extracted from ``aios_core.api.app.AIOSAPI``.
"""

from starlette.requests import Request
from starlette.responses import JSONResponse


class DevicesShardsMixin:
    """Device pool and shard routing handlers — mixed into ``AIOSAPI``."""

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
            profile_key,
            method,
            path,
            params=body.get("params"),
            json_body=body.get("body"),
        )
        if result.get("local"):
            return JSONResponse(result)
        status = result.get("status", 502)
        return JSONResponse(result.get("payload", result), status_code=int(status))

    async def _shards_unroute(self, request: Request) -> JSONResponse:
        """Forget a profile's route {profile} (re-assigned on next route)."""
        body = await request.json()
        removed = self.shard_router.unroute(body.get("profile"))
        return JSONResponse({"unrouted": removed})

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
            return JSONResponse({"error": "no healthy shard hosts"}, status_code=409)
        return JSONResponse(route)

    async def _shard_jobs_stats(self, request: Request) -> JSONResponse:
        """Глубина очереди, счётчики, зависшие claim'ы, heartbeats."""
        ttl = float(request.query_params.get("ttl", 600))
        with self._shard_jobs() as jobs:
            return JSONResponse(jobs.stats(stale_after_s=ttl))

    async def _shard_jobs_enqueue(self, request: Request) -> JSONResponse:
        """Повесить джобу на профиль {profile, kind, payload?}.

        Нода-исполнитель заберёт её pull-моделью (sticky HRW-маршрут);
        guarded-семантика сохраняется на уровне видов джоб.
        """
        body = await request.json()
        profile_key = body.get("profile")
        kind = body.get("kind")
        if not profile_key or not kind:
            return JSONResponse(
                {"error": "'profile' and 'kind' are required"},
                status_code=400,
            )
        with self._shard_jobs() as jobs:
            job_id = jobs.enqueue(profile_key, kind, payload=body.get("payload"))
        return JSONResponse(
            {"enqueued": job_id, "profile_key": profile_key, "kind": kind},
            status_code=201,
        )

    async def _shard_jobs_list(self, request: Request) -> JSONResponse:
        """Очередь джобов (?status=pending|claimed|done|failed)."""
        with self._shard_jobs() as jobs:
            return JSONResponse(
                {"jobs": jobs.list(status=request.query_params.get("status"))}
            )

    def _shard_jobs(self):
        from aios_core.platforms.shardexec import ShardJobs

        return ShardJobs()

    async def _shards_remove(self, request: Request) -> JSONResponse:
        """Remove a shard host and its routes."""
        removed = self.shard_router.remove_host(request.path_params["host"])
        if not removed:
            return JSONResponse({"error": "host not found"}, status_code=404)
        return JSONResponse({"removed": True})

    # ------------------------------------------------------------------ #
    # Shard pull-jobs (очередь джобов для dashboard/worker-нод)          #
    # ------------------------------------------------------------------ #

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

    async def _shards_list(self, request: Request) -> JSONResponse:
        """All shard hosts with health flags."""
        return JSONResponse({"shards": self.shard_router.hosts()})

    async def _devices_waitlist_cancel(self, request: Request) -> JSONResponse:
        """Remove a profile from the waitlist {profile}."""
        body = await request.json()
        cancelled = self.device_pool.cancel_wait(body.get("profile"))
        return JSONResponse({"cancelled": cancelled})

    # ------------------------------------------------------------------ #
    # Shard routing endpoints                                             #
    # ------------------------------------------------------------------ #

    async def _devices_waitlist(self, request: Request) -> JSONResponse:
        """Device lease waitlist (?status=waiting|served|cancelled|all)."""
        status = request.query_params.get("status", "waiting")
        status = None if status == "all" else status
        return JSONResponse({"waitlist": self.device_pool.waitlist(status)})

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

    async def _devices_limits_get(self, request: Request) -> JSONResponse:
        """Current pool quotas {max_devices, max_busy:<platform>, max_avds}."""
        return JSONResponse({"limits": self.device_pool.limits()})

    async def _devices_reap(self, request: Request) -> JSONResponse:
        """Mark silent devices offline {max_silence_s?} and free leases."""
        body = (
            await request.json()
            if (request.headers.get("content-length") or "0") != "0"
            else {}
        )
        reaped = self.device_pool.reap_stale(
            self._bounded_int(body.get("max_silence_s"), default=900, maximum=86400)
        )
        return JSONResponse({"reaped": reaped})

    async def _devices_heartbeat(self, request: Request) -> JSONResponse:
        """Heartbeat from a device {serial}."""
        body = await request.json()
        ok = self.device_pool.heartbeat(body.get("serial"))
        return JSONResponse({"ok": ok})

    async def _devices_release(self, request: Request) -> JSONResponse:
        """Release the device leased to a profile {profile}."""
        body = await request.json()
        freed = self.device_pool.release(body.get("profile"))
        return JSONResponse({"released": freed})

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
            return JSONResponse({"error": "no idle device available"}, status_code=409)
        return JSONResponse(record)

    async def _devices_register(self, request: Request) -> JSONResponse:
        """Register a device {serial, avd_name?}."""
        body = await request.json()
        if not body.get("serial"):
            return JSONResponse({"error": "'serial' is required"}, status_code=400)
        record = self.device_pool.register(
            body["serial"], avd_name=body.get("avd_name")
        )
        return JSONResponse(record, status_code=201)

    async def _devices_list(self, request: Request) -> JSONResponse:
        """Pool status: all registered devices with lease info."""
        return JSONResponse({"devices": self.device_pool.status()})
