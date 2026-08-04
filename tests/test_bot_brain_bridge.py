"""Тест моста бота → Phone Brain.

run_telegram_bot.py (438 КБ) целиком не импортируется: AST извлекает только
функцию _phone_brain_gateway_run + глобальные константы моста и исполняет их
в изолированном namespace против фейкового HTTP API.
"""
from __future__ import annotations

import ast
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

BOT_PATH = Path(__file__).resolve().parents[1] / "run_telegram_bot.py"


def _load_bridge(api_url: str):
    source = BOT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    snippets: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id in ("_PHONE_BRAIN_API", "_phone_brain_state")
                for t in node.targets):
            snippets.append(ast.get_source_segment(source, node) or "")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id in ("_PHONE_BRAIN_API", "_phone_brain_state"):
            snippets.append(ast.get_source_segment(source, node) or "")
        if isinstance(node, ast.FunctionDef) and node.name == "_phone_brain_gateway_run":
            snippets.append(ast.get_source_segment(source, node) or "")
    code = "\n\n".join(snippets)
    assert "_phone_brain_gateway_run" in code, "мост не найден в run_telegram_bot.py"
    import os as _os
    namespace: dict = {"json": json, "os": _os, "__name__": "bridge_test"}
    exec(compile(code, str(BOT_PATH), "exec"), namespace)
    namespace["_PHONE_BRAIN_API"] = api_url
    return namespace["_phone_brain_gateway_run"]


class _FakeBrain:
    """Мини-имитация API Phone Brain: принимает job, отдаёт готовый результат."""

    def __init__(self, result: dict):
        self.result = result
        self.requests: list[dict] = []
        self.server: ThreadingHTTPServer | None = None

    def start(self) -> str:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a) -> None:  # тишина
                pass

            def _send(self, code: int, payload: dict) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                outer.requests.append(body)
                self._send(201, {"status": "ok", "job": {"id": 77, "status": "queued"}})

            def do_GET(self) -> None:
                self._send(200, {"status": "ok", "job": {"id": 77, "status": "done",
                                                         "result": outer.result}})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()


@pytest.fixture()
def fake_brain():
    servers: list[_FakeBrain] = []

    def make(result: dict) -> tuple[_FakeBrain, str]:
        fake = _FakeBrain(result)
        url = fake.start()
        servers.append(fake)
        return fake, url

    yield make
    for fake in servers:
        fake.stop()


def test_read_only_maps_to_gateway_cli(fake_brain) -> None:
    fake, url = fake_brain({"output": {"status": "ok", "connected": True}})
    run = _load_bridge(url)
    result = run(["status"], 30)
    assert result == {"status": "ok", "connected": True}
    assert fake.requests[0] == {"kind": "gateway.cli", "payload": {"command": "status"}}


def test_open_with_confirm_maps_to_app_open(fake_brain) -> None:
    fake, url = fake_brain({"package": "com.whatsapp", "message": "opened"})
    run = _load_bridge(url)
    result = run(["open", "com.whatsapp", "--confirm"], 30)
    assert result["status"] == "ok" and result["package"] == "com.whatsapp"
    assert fake.requests[0]["kind"] == "app.open"
    assert fake.requests[0]["payload"]["confirm"] is True


def test_pull_maps_to_device_pull(fake_brain) -> None:
    fake, url = fake_brain({"file": "/root/AIOS/data/android_gateway/files/x.pdf", "bytes": 10})
    run = _load_bridge(url)
    result = run(["pull", "/sdcard/Download/x.pdf", "--confirm"], 150)
    assert result["status"] == "ok" and result["file"].endswith("x.pdf")
    assert fake.requests[0]["kind"] == "device.pull"


def test_location_confirm_maps(fake_brain) -> None:
    fake, url = fake_brain({"latitude": 48.4, "longitude": 35.0, "accuracy_m": 12.0})
    run = _load_bridge(url)
    result = run(["location", "--confirm"], 45)
    assert result["status"] == "ok" and result["accuracy_m"] == 12.0


def test_unknown_command_returns_none(fake_brain) -> None:
    _fake, url = fake_brain({})
    run = _load_bridge(url)
    assert run(["whatsapp-draft", "привет", "--confirm"], 30) is None
    assert run(["home", "--confirm"], 30) is None


def test_daemon_down_returns_none_for_fallback() -> None:
    run = _load_bridge("http://127.0.0.1:59999")  # ничего не слушает
    assert run(["status"], 30) is None  # вызывающий код уйдёт в legacy subprocess


def test_failed_job_returns_error(fake_brain) -> None:
    class FailedHandler(BaseHTTPRequestHandler):
        def log_message(self, *a) -> None:
            pass

        def _send(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self._send(201, {"status": "ok", "job": {"id": 5}})

        def do_GET(self) -> None:
            self._send(200, {"status": "ok", "job": {"id": 5, "status": "failed",
                                                     "error": "таймаут обработчика"}})

    server = ThreadingHTTPServer(("127.0.0.1", 0), FailedHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        host, port = server.server_address
        run = _load_bridge(f"http://{host}:{port}")
        result = run(["apps"], 30)
        assert result["status"] == "error" and "таймаут" in result["error"]
    finally:
        server.shutdown()
