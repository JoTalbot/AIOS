#!/usr/bin/env python3
"""
AIOS Colab - приёмник файлов из Colab через HTTP (POST /upload)

Colab отправляет модели/файлы POST-запросами на trycloudflare-URL этого
сервера. Файлы сохраняются в указанную папку (data/quant/models по умолчанию).

Запуск на VPS:
    python colab_ingest_server.py --port 8123 --dir /root/AIOS/data/quant/models
"""
from __future__ import annotations
import os, sys, argparse, cgi
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

MODELS_DIR = "/root/AIOS/data/quant/models"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, msg):
        body = msg.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, "OK: AIOS colab ingest server")

    def do_POST(self):
        parsed = urlparse(self.path)
        q = parse_qs(parsed.query)
        fname = (q.get("name") or [None])[0]
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        if parsed.path.rstrip("/") == "/upload" and fname:
            # безопасное имя
            fname = os.path.basename(fname)
            os.makedirs(MODELS_DIR, exist_ok=True)
            dest = os.path.join(MODELS_DIR, fname)
            with open(dest, "wb") as f:
                f.write(data)
            self._send(200, f"OK saved {fname} ({len(data)} bytes)")
            print(f"📥 Получен файл: {dest} ({len(data)} байт)", flush=True)
        else:
            self._send(400, "bad request: need /upload?name=FILE")

    def log_message(self, fmt, *args):
        pass


def main():
    global MODELS_DIR
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--dir", default=MODELS_DIR)
    args = ap.parse_args()
    MODELS_DIR = args.dir
    os.makedirs(MODELS_DIR, exist_ok=True)
    srv = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Слушаю на 127.0.0.1:{args.port} -> {MODELS_DIR}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
