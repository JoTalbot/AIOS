"""Локальный HTTP API Phone Brain (stdlib, 127.0.0.1:8790).

Единая точка входа для внешних потребителей (постепенная миграция Telegram-бота
с subprocess-вызовов run_android_gateway.py). Bind только localhost — как и
остальные внутренние сервисы AIOS. Payload ограничен 64 КБ.
"""
from __future__ import annotations

import json
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MAX_BODY = 64 * 1024


class BrainAPI:
    """HTTP-обёртка над демоном; сама бизнес-логики не содержит."""

    def __init__(self, daemon: Any, host: str = "127.0.0.1", port: int = 8790):
        self.daemon = daemon
        self.host = host
        self.port = int(port)
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        handler = self._make_handler()
        self._server = ThreadingHTTPServer((self.host, self.port), handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="phone-brain-api", daemon=True)
        self._thread.start()
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        if self._server is not None:
            try:
                self._server.shutdown()
                self._server.server_close()
            except Exception:
                pass

    # ------------------------------------------------------------- handler

    def _make_handler(self):
        daemon = self.daemon

        class APIHandler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, fmt: str, *args: Any) -> None:
                daemon.logger.debug("api: " + fmt, *args)

            # ------------------------------------------------------ helpers
            def _send(self, code: int, payload: dict | list) -> None:
                body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _query(self) -> dict[str, str]:
                parsed = urllib.parse.urlsplit(self.path)
                return dict(urllib.parse.parse_qsl(parsed.query))

            def _segments(self) -> list[str]:
                return [seg for seg in urllib.parse.urlsplit(self.path).path.split("/") if seg]

            def _body(self) -> dict:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    return {}
                if length > MAX_BODY:
                    return {"__error__": "payload too large"}
                try:
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                except Exception:
                    return {"__error__": "invalid json"}
                return data if isinstance(data, dict) else {"__error__": "json object expected"}

            # -------------------------------------------------------- GET
            def do_GET(self) -> None:  # noqa: N802 (stdlib naming)
                try:
                    segments = self._segments()
                    if segments == ["health"]:
                        return self._send(200, daemon.health())
                    if segments == ["metrics"]:
                        return self._send(200, daemon.metrics())
                    if segments == ["kinds"]:
                        return self._send(200, {"status": "ok",
                                                "kinds": daemon.executor.handlers_meta()})
                    if segments == ["events"]:
                        limit = int(self._query().get("limit") or 50)
                        return self._send(200, {"status": "ok", "events": daemon.events.recent(limit)})
                    if segments == ["reactions"]:
                        return self._send(200, daemon.reactions_info())
                    if segments == ["jobs"]:
                        query = self._query()
                        jobs = daemon.store.list(status=query.get("status") or None,
                                                 limit=int(query.get("limit") or 50))
                        return self._send(200, {"status": "ok", "jobs": jobs})
                    if len(segments) == 2 and segments[0] == "jobs":
                        job = daemon.store.get(int(segments[1]))
                        if job is None:
                            return self._send(404, {"status": "error", "error": "job not found"})
                        return self._send(200, {"status": "ok", "job": job})
                    return self._send(404, {"status": "error", "error": "not found"})
                except ValueError:
                    return self._send(400, {"status": "error", "error": "invalid id/limit"})
                except Exception as exc:  # noqa: BLE001
                    return self._send(500, {"status": "error", "error": str(exc)[:200]})

            # ------------------------------------------------------- POST
            def do_POST(self) -> None:  # noqa: N802
                try:
                    segments = self._segments()
                    body = self._body()
                    if "__error__" in body:
                        return self._send(400, {"status": "error", "error": body["__error__"]})
                    if segments == ["jobs"]:
                        kind = str(body.get("kind") or "").strip()
                        if kind not in daemon.executor.kinds():
                            return self._send(400, {"status": "error",
                                                    "error": f"Неизвестный kind '{kind}'; см. GET /kinds"})
                        job = daemon.store.enqueue(
                            kind, body.get("payload") if isinstance(body.get("payload"), dict) else {},
                            priority=int(body.get("priority") or 50),
                            max_attempts=body.get("max_attempts"),
                            dedup_key=body.get("dedup_key"))
                        return self._send(201, {"status": "ok", "job": job})
                    if len(segments) == 3 and segments[0] == "jobs" and segments[2] == "cancel":
                        _draft_feedback(daemon.store, int(segments[1]), "cancelled")
                        return self._send(200, daemon.store.cancel(int(segments[1])))
                    if len(segments) == 3 and segments[0] == "jobs" and segments[2] == "confirm":
                        _draft_feedback(daemon.store, int(segments[1]), "confirmed")
                        return self._send(200, daemon.store.confirm_job(int(segments[1])))
                    if segments == ["device", "connect"]:
                        job = daemon.store.enqueue("device.connect", {}, priority=90,
                                                   dedup_key="manual-device-connect")
                        return self._send(201, {"status": "ok", "job": job})
                    return self._send(404, {"status": "error", "error": "not found"})
                except ValueError:
                    return self._send(400, {"status": "error", "error": "invalid id"})
                except Exception as exc:  # noqa: BLE001
                    return self._send(500, {"status": "error", "error": str(exc)[:200]})

        return APIHandler



def _draft_feedback(store, job_id: int, decision: str) -> None:
    """Решение владельца по черновику → сигнал для обучения стиля ответов."""
    try:
        job = store.get(job_id) or {}
        skill = str((job.get("payload") or {}).get("skill") or "")
        if not (skill.endswith("_send_draft") or skill == "olx_reply_draft"):
            return
        import json as _json
        from datetime import datetime as _dt
        fp = Path(__file__).resolve().parents[2] / "data" / "draft_feedback.json"
        data = []
        try:
            data = _json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            pass
        data.append({"skill": skill, "decision": decision,
                     "draft": str((job.get("payload") or {}).get("params", {}).get("text") or "")[:300],
                     "at": _dt.now().isoformat(timespec="seconds")})
        fp.write_text(_json.dumps(data[-200:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
