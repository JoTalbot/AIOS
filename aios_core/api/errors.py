"""Small defensive HTTP middleware for malformed client requests."""

from __future__ import annotations

import json

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
        """dispatch."""
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    return JSONResponse(
                        {"error": "Request body too large"}, status_code=413
                    )
            except ValueError:
                return JSONResponse(
                    {"error": "Invalid Content-Length"}, status_code=400
                )
        try:
            response = await call_next(request)
            response.headers.setdefault("X-Content-Type-Options", "nosniff")
            response.headers.setdefault("Cache-Control", "no-store")
            return response
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JSONResponse({"error": "Invalid JSON request body"}, status_code=400)
        except (KeyError, TypeError, ValueError):
            # Endpoint handlers use these for invalid client supplied fields.
            return JSONResponse(
                {"error": "Invalid request parameters"}, status_code=400
            )
