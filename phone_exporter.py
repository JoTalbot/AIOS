#!/usr/bin/env python3
"""Prometheus-exporter метрик телефона G1: онлайн/батарея/companion.

Читает data/android_gateway/health.json (обновляется watchdog'ом каждые 30 с).
Порт 9102; снаружи закрыт ufw, из docker-сети доступен через 172.18.0.1.
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEALTH = ROOT / "data" / "android_gateway" / "health.json"


def collect() -> str:
    online = 0.0
    battery = 0.0
    companion = 0.0
    checked_at = 0.0
    try:
        d = json.loads(HEALTH.read_text(encoding="utf-8"))
        online = 1.0 if d.get("connected") else 0.0
        companion = 1.0 if (d.get("companion") or {}).get("status") == "ok" else 0.0
        b = d.get("battery")
        if isinstance(b, (int, float)):
            battery = float(b)
        checked_at = d.get("checked_at_epoch", 0.0)
    except Exception:
        pass
    lines = [
        "# HELP aios_phone_online Whether the Android phone (adb) is reachable.",
        "# TYPE aios_phone_online gauge",
        f'aios_phone_online{{device="G1"}} {online}',
        "# HELP aios_phone_companion_ok Whether the Companion HTTP API is healthy.",
        "# TYPE aios_phone_companion_ok gauge",
        f'aios_phone_companion_ok{{device="G1"}} {companion}',
        "# HELP aios_phone_battery_percent Last known battery level.",
        "# TYPE aios_phone_battery_percent gauge",
        f'aios_phone_battery_percent{{device="G1"}} {battery}',
        "# HELP aios_phone_exporter_scrape Unix time of this scrape.",
        "# TYPE aios_phone_exporter_scrape gauge",
        f"aios_phone_exporter_scrape {time.time()}",
    ]
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.startswith("/metrics"):
            body = collect().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # тихо
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 9102), Handler).serve_forever()
