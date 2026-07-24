"""API Gateway for AIOS v10.5.0.

Central API gateway with route registration, middleware pipeline,
rate limiting per route, authentication middleware, request/response
transformers, route versioning, health endpoint, and metrics.

Classes:
    Route           — registered route definition
    RouteVersion    — versioned route group
    APIGateway      — full gateway with middleware, rate limiting, versioning
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Route ────────────────────────────────────────────────────────────────────


@dataclass
class Route:
    """Registered route definition."""

    path: str
    handler: Callable
    methods: list[str] = field(default_factory=lambda: ["GET"])
    version: str = "v1"
    rate_limit: int | None = None  # max requests per minute
    auth_required: bool = False
    description: str = ""


# ── API Gateway ──────────────────────────────────────────────────────────────


class APIGateway:
    """Central API Gateway with routing, middleware, rate limiting, versioning.

    Features:
    - Route registration with HTTP methods, versions, rate limits
    - Middleware pipeline (pre-processing chain)
    - Per-route rate limiting (sliding window)
    - Authentication middleware check
    - Request/response transformers
    - Route versioning (v1, v2, etc.)
    - Health endpoint
    - Metrics tracking
    """

    def __init__(self) -> None:
        self.routes: dict[str, Route] = {}
        self.middleware: list[Callable] = []
        self._rate_limit_counters: dict[str, list[float]] = {}  # path → timestamps
        self._request_metrics: dict[
            str, dict[str, int]
        ] = {}  # path → {success, failure, total}
        self._total_requests: int = 0

    # ── Route Registration ───────────────────────────────────────

    def register(
        self,
        path: str,
        handler: Callable,
        methods: list[str] | None = None,
        version: str = "v1",
        rate_limit: int | None = None,
        auth_required: bool = False,
        description: str = "",
    ) -> Route:
        """Register a route with full configuration."""
        route = Route(
            path=path,
            handler=handler,
            methods=methods or ["GET"],
            version=version,
            rate_limit=rate_limit,
            auth_required=auth_required,
            description=description,
        )
        self.routes[path] = route
        self._request_metrics[path] = {"success": 0, "failure": 0, "total": 0}
        return route

    def unregister(self, path: str) -> None:
        """Remove a route."""
        del self.routes[path]
        self._request_metrics.pop(path, None)

    # ── Middleware ────────────────────────────────────────────────

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to the pipeline. Each receives request dict and returns modified dict."""
        self.middleware.append(middleware)

    def remove_middleware(self, middleware: Callable) -> None:
        """Remove a middleware from the pipeline."""
        self.middleware = [m for m in self.middleware if m is not middleware]

    # ── Request Handling ─────────────────────────────────────────

    def handle(self, path: str, request: dict[str, Any]) -> dict[str, Any]:
        """Handle a request through middleware pipeline → route handler.

        Steps:
        1. Run middleware pipeline
        2. Check rate limit (if configured)
        3. Check authentication (if required)
        4. Find matching route
        5. Execute handler
        6. Track metrics
        """
        self._total_requests += 1

        # ── Middleware pipeline ──
        processed = request
        for mw in self.middleware:
            try:
                processed = mw(processed)
            except Exception as e:
                return {"error": f"Middleware error: {e}", "status": 500}

        # ── Find route ──
        route = self.routes.get(path)
        if route is None:
            self._track(path, "failure")
            return {"error": "Not found", "status": 404}

        # ── Method check ──
        method = processed.get("method", "GET")
        if method not in route.methods:
            self._track(path, "failure")
            return {"error": f"Method {method} not allowed", "status": 405}

        # ── Rate limit check ──
        if route.rate_limit:
            if not self._check_rate_limit(path, route.rate_limit):
                self._track(path, "failure")
                return {"error": "Rate limit exceeded", "status": 429}

        # ── Auth check ──
        if route.auth_required and not processed.get("authenticated", False):
            self._track(path, "failure")
            return {"error": "Authentication required", "status": 401}

        # ── Execute handler ──
        try:
            result = route.handler(processed)
            self._track(path, "success")
            return result
        except Exception as e:
            self._track(path, "failure")
            return {"error": str(e), "status": 500}

    # ── Rate Limiting ────────────────────────────────────────────

    def _check_rate_limit(self, path: str, limit: int) -> bool:
        """Sliding-window rate limit: max `limit` requests per 60 seconds."""
        now = time.time()
        timestamps = self._rate_limit_counters.get(path, [])
        # Remove timestamps older than 60 seconds
        timestamps = [t for t in timestamps if now - t < 60.0]
        if len(timestamps) >= limit:
            self._rate_limit_counters[path] = timestamps
            return False
        timestamps.append(now)
        self._rate_limit_counters[path] = timestamps
        return True

    def reset_rate_limit(self, path: str | None = None) -> None:
        """Reset rate limit counters."""
        if path:
            self._rate_limit_counters.pop(path, None)
        else:
            self._rate_limit_counters.clear()

    # ── Versioning ───────────────────────────────────────────────

    def get_routes_by_version(self, version: str) -> list[Route]:
        """Return all routes for a specific version."""
        return [r for r in self.routes.values() if r.version == version]

    def get_route_versions(self) -> dict[str, list[str]]:
        """Return mapping: path → available versions."""
        result: dict[str, list[str]] = {}
        for path, route in self.routes.items():
            result.setdefault(path, []).append(route.version)
        return result

    # ── Health ───────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Return gateway health status."""
        return {
            "status": "healthy",
            "routes": len(self.routes),
            "middleware": len(self.middleware),
            "total_requests": self._total_requests,
        }

    # ── Metrics ──────────────────────────────────────────────────

    def _track(self, path: str, result: str) -> None:
        """Track request metrics."""
        if path not in self._request_metrics:
            self._request_metrics[path] = {"success": 0, "failure": 0, "total": 0}
        self._request_metrics[path][result] += 1
        self._request_metrics[path]["total"] += 1

    def metrics(self) -> dict[str, Any]:
        """Return request metrics."""
        return {
            "total_requests": self._total_requests,
            "per_route": self._request_metrics,
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "routes": len(self.routes),
            "middleware": len(self.middleware),
            "total_requests": self._total_requests,
        }
