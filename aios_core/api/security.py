"""HTTP security primitives for AIOS.

The API is fail-closed: when authentication is enabled but no API keys are
configured, every endpoint except ``/health`` returns 503. API keys are
intended for service-to-service use; deploy behind TLS and a real identity
provider for multi-user installations.
"""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class Principal:
    """Principal."""

    subject: str
    roles: frozenset[str]


def load_api_keys(raw: str | None = None) -> dict[str, Principal]:
    """Load ``AIOS_API_KEYS`` JSON mapping key -> {subject, roles}.

    Example::
      export AIOS_API_KEYS='{"long-random-secret":{"subject":"ops","roles":["admin"]}}'
    """
    raw = os.environ.get("AIOS_API_KEYS") if raw is None else raw
    if not raw:
        return {}
    try:
        configured: dict[str, Any] = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("AIOS_API_KEYS must be a JSON object") from exc
    result: dict[str, Principal] = {}
    for key, value in configured.items():
        if not isinstance(key, str) or not key or not isinstance(value, dict):
            raise ValueError("Each API key must map to an object")
        subject = value.get("subject")
        roles = value.get("roles", [])
        if not isinstance(subject, str) or not subject or not isinstance(roles, list):
            raise ValueError("API key entries require subject and roles")
        result[key] = Principal(subject=subject, roles=frozenset(map(str, roles)))
    return result


def required_roles(path: str, method: str) -> set[str]:
    """Return any role that may access an API route."""
    if "/audit" in path:
        return {"admin"}
    if "/approvals/" in path and method == "POST":
        return {"approver", "admin"}
    if "/evolution/" in path and method == "POST":
        return {"operator", "admin"}
    if "/tests/run" in path and method == "POST":
        return {"operator", "admin"}
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return {"writer", "operator", "admin"}
    return {"viewer", "writer", "operator", "approver", "admin"}


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Authenticate bearer API keys and enforce a small role policy."""

    def __init__(
        self, app, *, enabled: bool = True, api_keys: dict[str, Principal] | None = None
    ):
        """Initialize APIKeyAuthMiddleware."""
        super().__init__(app)
        self.enabled = enabled
        if api_keys is None:
            self.api_keys = load_api_keys()
        else:
            self.api_keys = {
                key: (
                    value
                    if isinstance(value, Principal)
                    else Principal(
                        subject=value["subject"],
                        roles=frozenset(value.get("roles", [])),
                    )
                )
                for key, value in api_keys.items()
            }

    async def dispatch(self, request: Request, call_next) -> Response:
        """dispatch."""
        if request.url.path == "/health" or not self.enabled:
            request.state.principal = Principal("development", frozenset({"admin"}))
            return await call_next(request)
        if not self.api_keys:
            return JSONResponse(
                {"error": "API authentication is not configured"}, status_code=503
            )
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Bearer authentication required"}, status_code=401
            )
        supplied = header[7:]
        principal = next(
            (
                p
                for key, p in self.api_keys.items()
                if hmac.compare_digest(key, supplied)
            ),
            None,
        )
        if principal is None:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)
        if not principal.roles.intersection(
            required_roles(request.url.path, request.method)
        ):
            return JSONResponse({"error": "Insufficient role"}, status_code=403)
        request.state.principal = principal
        return await call_next(request)
