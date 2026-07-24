"""Small defensive HTTP middleware for malformed client requests."""

from __future__ import annotations

import json
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestSafetyMiddleware(BaseHTTPMiddleware):
    """Reject oversized bodies and convert common parse errors to safe 400s."""

    def __init__(self, app, *, max_body_bytes: int = 1_048_576):
        """Initialize RequestSafetyMiddleware."""
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply request validation and attach a safe correlation identifier."""
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = supplied_request_id if len(supplied_request_id) <= 128 and supplied_request_id.isprintable() else str(uuid.uuid4())
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    return JSONResponse(
                        {"error": "Request body too large"}, status_code=413, headers={"X-Request-ID": request_id}
                    )
            except ValueError:
                return JSONResponse(
                    {"error": "Invalid Content-Length"}, status_code=400, headers={"X-Request-ID": request_id}
                )
        try:
            response = await call_next(request)
            # Security defaults that are safe for API and dashboard responses alike.
            # Deployments terminating TLS should add HSTS at the reverse proxy.
            response.headers.setdefault("X-Request-ID", request_id)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Referrer-Policy", "no-referrer")
            response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
            response.headers.setdefault("Cache-Control", "no-store")
            return response
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "Invalid JSON request body"}, status_code=400, headers={"X-Request-ID": request_id})
        except (KeyError, TypeError, ValueError):
            # Endpoint handlers use these for invalid client supplied fields.
            return JSONResponse(
                {"error": "Invalid request parameters"}, status_code=400, headers={"X-Request-ID": request_id}
            )
