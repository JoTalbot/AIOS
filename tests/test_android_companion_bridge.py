"""Тесты защищённого server-side моста к AIOS Companion."""
from __future__ import annotations

import io
import json


def test_companion_request_requires_config(tmp_path):
    from aios_core.android_gateway import AndroidGateway

    result = AndroidGateway(tmp_path)._companion_request("health")
    assert result["status"] == "unconfigured"


def test_companion_request_uses_token(monkeypatch, tmp_path):
    from aios_core.android_gateway import AndroidGateway

    gateway = AndroidGateway(tmp_path)
    gateway.data_dir.mkdir(parents=True)
    (gateway.data_dir / "companion.json").write_text(json.dumps({
        "endpoint": "http://10.203.0.2:8765", "token": "x" * 32,
    }), encoding="utf-8")
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"status":"ok","battery":80}'

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["token"] = request.get_header("X-aios-token")
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    result = gateway._companion_request("health")
    assert result["status"] == "ok"
    assert captured["url"].endswith("/health")
    assert captured["token"] == "x" * 32
