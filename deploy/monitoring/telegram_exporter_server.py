#!/usr/bin/env python3
"""Serve one pre-rendered, redacted Prometheus snapshot.

The container intentionally has no access to the AIOS checkout, queue databases,
credential directories, or message payloads. A hardened host service renders the
snapshot atomically.
"""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SNAPSHOT = Path(os.environ.get("AIOS_TELEGRAM_METRICS_SNAPSHOT", "/metrics/metrics.prom"))
MAX_BYTES = 2 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.partition("?")[0].rstrip("/") or "/"
        if path in ("/-/healthy", "/-/ready"):
            self.send_response(200 if SNAPSHOT.is_file() else 503)
            self.end_headers()
            return
        if path != "/metrics":
            self.send_error(404)
            return
        try:
            payload = SNAPSHOT.read_bytes()
            if len(payload) > MAX_BYTES:
                raise ValueError("snapshot exceeds size limit")
        except (OSError, ValueError):
            self.send_error(503)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    host = os.environ.get("TELEGRAM_PROMETHEUS_HOST", "0.0.0.0")
    port = int(os.environ.get("TELEGRAM_PROMETHEUS_PORT", "9103"))
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
