import hashlib
import hmac

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette

from aios_core.webhooks.router import router


@pytest.fixture
def app(): return Starlette(routes=router.routes)

@pytest.mark.asyncio
async def test_olx_sig(app, monkeypatch):
    monkeypatch.setenv("OLX_WEBHOOK_SECRET", "sec")
    payload = b'{"t":"1"}'
    sig = hmac.new(b"sec", payload, hashlib.sha256).hexdigest()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/webhooks/olx", content=payload, headers={"X-OLX-Signature": sig})
        assert r.status_code == 200