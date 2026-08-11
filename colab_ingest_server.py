#!/usr/bin/env python3
"""
AIOS Colab - приёмник файлов из Colab через HTTP (POST /upload)

Colab отправляет модели/файлы POST-запросами на trycloudflare-URL этого
сервера. Файлы сохраняются в указанную папку (data/quant/models по умолчанию).

После приёма каждого файла запускается авто-загрузка всей папки на Google Диск
(через upload_gdrive.py - прямой Drive REST API, обходит rate-limit rclone).

Запуск на VPS:
    python colab_ingest_server.py --port 8123 --dir /root/AIOS/data/quant/models \
                                  --gdrive-folder AIOS_colab_models
"""
from __future__ import annotations
import os, sys, argparse, cgi, subprocess, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

MODELS_DIR = "/root/AIOS/data/quant/models"
GDRIVE_FOLDER = os.environ.get("AIOS_GDRIVE_FOLDER", "AIOS_colab_models")
UPLOAD_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "upload_gdrive.py")
if not os.path.exists(UPLOAD_SCRIPT):
    UPLOAD_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_gdrive.py")
UPLOAD_SCRIPT = os.path.abspath(UPLOAD_SCRIPT)

_last_upload = {"t": 0}
_upload_lock = threading.Lock()
_debounce = 8  # секунд после последнего файла перед выгрузкой


def schedule_gdrive_upload():
    """Отложенная (debounced) авто-загрузка папки на Google Диск."""
    def worker():
        # ждём, пока перестанут приходить файлы (debounce)
        while True:
            with _upload_lock:
                dt = time.time() - _last_upload["t"]
            if dt >= _debounce:
                break
            time.sleep(2)
        print("🚀 Авто-загрузка моделей на Google Диск...", flush=True)
        try:
            subprocess.run(
                [sys.executable, UPLOAD_SCRIPT,
                 "--dir", MODELS_DIR, "--folder", GDRIVE_FOLDER],
                timeout=600,
            )
            print("✅ Авто-загрузка на Google Диск завершена", flush=True)
        except Exception as e:
            print(f"⚠️ Авто-загрузка на Google Диск: {e}", flush=True)
    with _upload_lock:
        _last_upload["t"] = time.time()
    threading.Thread(target=worker, daemon=True).start()


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
            fname = os.path.basename(fname)
            os.makedirs(MODELS_DIR, exist_ok=True)
            dest = os.path.join(MODELS_DIR, fname)
            with open(dest, "wb") as f:
                f.write(data)
            self._send(200, f"OK saved {fname} ({len(data)} bytes)")
            print(f"📥 Получен файл: {dest} ({len(data)} байт)", flush=True)
            schedule_gdrive_upload()
        else:
            self._send(400, "bad request: need /upload?name=FILE")

    def log_message(self, fmt, *args):
        pass


def main():
    global MODELS_DIR, GDRIVE_FOLDER
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--dir", default=MODELS_DIR)
    ap.add_argument("--gdrive-folder", default=GDRIVE_FOLDER)
    args = ap.parse_args()
    MODELS_DIR = args.dir
    GDRIVE_FOLDER = args.gdrive_folder
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"Слушаю на 127.0.0.1:{args.port} -> {MODELS_DIR}", flush=True)
    print(f"Авто-загрузка на Google Диск: папка '{GDRIVE_FOLDER}'", flush=True)
    print(f"Скрипт: {UPLOAD_SCRIPT}", flush=True)
    srv = HTTPServer(("127.0.0.1", args.port), Handler)
    srv.serve_forever()


if __name__ == "__main__":
    main()
