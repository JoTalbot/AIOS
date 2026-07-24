"""API Versioning for AIOS v10.6.0.

Version negotiation (header, path, query), version routing,
deprecation notices, version-specific middleware, and backward
compatibility. No Starlette dependency.

Classes:
    VersionNegotiation — strategy for determining API version
    VersionRoute        — versioned route definition
    APIVersioning       — full versioning engine with routing and deprecation
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ── Version Negotiation ─────────────────────────────────────────────────────


class VersionNegotiation:
    """Strategy for determining API version from request."""

    @staticmethod
    def from_header(request: dict[str, Any], header: str = "X-API-Version") -> str:
        """Extract version from request header."""
        headers = request.get("headers", {})
        return headers.get(header, "v1")

    @staticmethod
    def from_path(request: dict[str, Any]) -> str:
        """Extract version from URL path prefix (/v1/..., /v2/...)."""
        path = request.get("path", "")
        if path.startswith("/v"):
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[1]  # e.g., "v2"
        return "v1"

    @staticmethod
    def from_query(request: dict[str, Any], param: str = "version") -> str:
        """Extract version from query parameter."""
        query = request.get("query", {})
        return query.get(param, "v1")

    @staticmethod
    def negotiate(request: dict[str, Any], priority: list[str] | None = None) -> str:
        """Negotiate version using multiple strategies with priority.

        Default priority: header → path → query.
        """
        priority = priority or ["header", "path", "query"]
        for strategy in priority:
            if strategy == "header":
                v = VersionNegotiation.from_header(request)
                if v != "v1":  # explicitly set
                    return v
            elif strategy == "path":
                v = VersionNegotiation.from_path(request)
                if v != "v1":
                    return v
            elif strategy == "query":
                v = VersionNegotiation.from_query(request)
                if v != "v1":
                    return v
        return "v1"


# ── Version Route ───────────────────────────────────────────────────────────


@dataclass
class VersionRoute:
    """Versioned route definition."""

    version: str
    path: str
    handler: Callable
    deprecated: bool = False
    deprecation_message: str = ""
    sunset_date: str | None = None  # YYYY-MM-DD
    description: str = ""


# ── API Versioning ──────────────────────────────────────────────────────────


class APIVersioning:
    """Full versioning engine with routing, deprecation, and negotiation.

    Features:
    - Version negotiation from header, path, or query
    - Version-specific route handlers
    - Deprecation notices with sunset dates
    - Default version fallback
    - Version listing
    """

    def __init__(self, default_version: str = "v1") -> None:
        self.versions: dict[
            str, dict[str, VersionRoute]
        ] = {}  # version → {path: route}
        self.default_version = default_version
        self._negotiation_priority: list[str] = ["header", "path", "query"]

    # ── Registration ────────────────────────────────────────────

    def register(
        self,
        version: str,
        path: str,
        handler: Callable,
        deprecated: bool = False,
        deprecation_message: str = "",
        sunset_date: str | None = None,
        description: str = "",
    ) -> VersionRoute:
        """Register a versioned route."""
        if version not in self.versions:
            self.versions[version] = {}
        route = VersionRoute(
            version=version,
            path=path,
            handler=handler,
            deprecated=deprecated,
            deprecation_message=deprecation_message,
            sunset_date=sunset_date,
            description=description,
        )
        self.versions[version][path] = route
        return route

    def register_version(self, version: str, routes: dict[str, Callable]) -> None:
        """Register multiple routes for a version (backward-compatible)."""
        for path, handler in routes.items():
            self.register(version, path, handler)

    # ── Routing ────────────────────────────────────────────────

    def route(self, version: str, path: str) -> Callable:
        """Decorator to register a handler for a versioned route."""

        def decorator(func: Callable) -> Callable:
            self.register(version, path, func)
            return func

        return decorator

    def resolve(self, request: dict[str, Any]) -> dict[str, Any]:
        """Resolve a request to the appropriate version handler.

        Returns handler result or error dict.
        """
        version = VersionNegotiation.negotiate(request, self._negotiation_priority)

        # Try exact version
        version_routes = self.versions.get(version, {})
        path = request.get("path", "")

        # Try matching the path after removing version prefix
        clean_path = path
        if path.startswith(f"/{version}"):
            clean_path = path[len(version) + 1 :] or "/"

        route = version_routes.get(clean_path) or version_routes.get(path)
        if route:
            result = route.handler(request)

            # Add deprecation notice if applicable
            response = result if isinstance(result, dict) else {"data": result}
            if route.deprecated:
                warnings = response.get("warnings", [])
                warnings.append(
                    {
                        "type": "deprecation",
                        "message": route.deprecation_message
                        or f"Version {version} is deprecated",
                        "sunset": route.sunset_date,
                    }
                )
                response["warnings"] = warnings

            return response

        # Fallback to default version
        if version != self.default_version:
            default_routes = self.versions.get(self.default_version, {})
            route = default_routes.get(clean_path) or default_routes.get(path)
            if route:
                return route.handler(request)

        return {"error": "Not found", "status": 404}

    def get_version(self, request: dict[str, Any]) -> str:
        """Determine API version from request (backward-compatible)."""
        headers = request.get("headers", {}) if isinstance(request, dict) else {}
        return headers.get("X-API-Version", self.default_version)

    # ── Deprecation ─────────────────────────────────────────────

    def deprecate_version(
        self, version: str, message: str = "", sunset_date: str | None = None
    ) -> None:
        """Mark all routes in a version as deprecated."""
        for route in self.versions.get(version, {}).values():
            route.deprecated = True
            route.deprecation_message = message
            route.sunset_date = sunset_date

    def get_deprecated_versions(self) -> list[str]:
        """Return list of deprecated versions."""
        deprecated = []
        for version, routes in self.versions.items():
            if any(r.deprecated for r in routes.values()):
                deprecated.append(version)
        return deprecated

    # ── Listing ─────────────────────────────────────────────────

    def list_versions(self) -> list[str]:
        """Return all registered versions."""
        return sorted(self.versions.keys())

    def list_routes(self, version: str | None = None) -> list[VersionRoute]:
        """Return all routes, optionally filtered by version."""
        if version:
            return list(self.versions.get(version, {}).values())
        all_routes = []
        for routes in self.versions.values():
            all_routes.extend(routes.values())
        return all_routes

    def set_negotiation_priority(self, priority: list[str]) -> None:
        """Set version negotiation strategy priority."""
        self._negotiation_priority = priority

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        total_routes = sum(len(routes) for routes in self.versions.values())
        deprecated_routes = sum(
            1
            for routes in self.versions.values()
            for r in routes.values()
            if r.deprecated
        )
        return {
            "versions": len(self.versions),
            "total_routes": total_routes,
            "deprecated_routes": deprecated_routes,
            "default_version": self.default_version,
        }


api_versioning = APIVersioning()
