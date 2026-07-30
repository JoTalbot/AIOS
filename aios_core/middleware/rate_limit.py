import hashlib
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=100, window_seconds=60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else "unknown"
        key = hashlib.md5(ip.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        self.requests[key] = [t for t in self.requests[key] if t > now - timedelta(seconds=self.window_seconds)]
        if len(self.requests[key]) >= self.max_requests:
            return JSONResponse(status_code=429, content={"error": "Too many requests"})
        self.requests[key].append(now)
        return await call_next(request)


class WebhookSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)
