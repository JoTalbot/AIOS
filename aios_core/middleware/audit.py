from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from aios_core.audit.recorder import recorder


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            user_id = "anonymous"
            try:
                if hasattr(request.state, "user"):
                    user_id = request.state.user.get("username", "anonymous")
            except Exception:
                pass
            await recorder.record(
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
        return response
