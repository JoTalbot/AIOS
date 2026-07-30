#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

STORAGE_DIR = Path(os.environ.get("OCTOPUS_MEMORY_POOL", "/data/memory_pool"))
NONCE_DIR = Path(os.environ.get("OCTOPUS_REPLICATION_NONCE_DIR", "/data/nonces"))
MAX_CLOCK_SKEW_SECONDS = int(os.environ.get("OCTOPUS_REPLICATION_MAX_SKEW_SECONDS", "300"))
INDEX_FILE = Path(os.environ.get("OCTOPUS_MEMORY_INDEX", "/data/index.jsonl"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("OCTOPUS_PORT", "8080")))


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ensure_dirs():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    NONCE_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_secret() -> str:
    secret = os.environ.get("OCTOPUS_REPLICATION_HMAC_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("OCTOPUS_REPLICATION_HMAC_SECRET missing or too short")
    return secret


def timing_safe_equal_hex(a: str, b: str) -> bool:
    try:
        ab = bytes.fromhex(a)
        bb = bytes.fromhex(b)
    except ValueError:
        return False
    return len(ab) == len(bb) and hmac.compare_digest(ab, bb)


def cleanup_nonces():
    cutoff = time.time() - (MAX_CLOCK_SKEW_SECONDS * 2)
    for p in list(NONCE_DIR.iterdir())[:2000]:
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink(missing_ok=True)
        except Exception:
            pass


def verify_nonce(nonce: str):
    if not re.match(r"^[a-zA-Z0-9._:-]{8,128}$", nonce or ""):
        raise ValueError("Invalid nonce format")
    cleanup_nonces()
    nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
    marker = NONCE_DIR / nonce_hash
    if marker.exists():
        raise ValueError("Replay detected: nonce already used")
    marker.write_text(now_iso(), encoding="utf-8")


def get_headers(handler: BaseHTTPRequestHandler):
    ts = handler.headers.get("x-octopus-timestamp", "")
    nonce = handler.headers.get("x-octopus-nonce", "")
    signature = handler.headers.get("x-octopus-signature", "").removeprefix("sha256=")
    if not ts or not nonce or not signature:
        raise ValueError("Missing replication auth headers")
    if not ts.isdigit():
        raise ValueError("Invalid timestamp")
    if not re.match(r"^[a-fA-F0-9]{64}$", signature):
        raise ValueError("Invalid signature format")
    now_ts = int(time.time())
    if abs(now_ts - int(ts)) > MAX_CLOCK_SKEW_SECONDS:
        raise ValueError("Timestamp outside allowed clock skew")
    verify_nonce(nonce)
    return ts, nonce, signature


def verify_post(handler: BaseHTTPRequestHandler, raw_body: bytes):
    ts, nonce, signature = get_headers(handler)
    canonical = ts.encode() + b"." + nonce.encode() + b"." + raw_body
    expected = hmac.new(load_secret().encode(), canonical, hashlib.sha256).hexdigest()
    if not timing_safe_equal_hex(signature, expected):
        raise ValueError("Invalid HMAC signature")


def verify_get(handler: BaseHTTPRequestHandler, pathq: str):
    ts, nonce, signature = get_headers(handler)
    canonical = f"{ts}.{nonce}.{pathq}".encode()
    expected = hmac.new(load_secret().encode(), canonical, hashlib.sha256).hexdigest()
    if not timing_safe_equal_hex(signature, expected):
        raise ValueError("Invalid HMAC signature")


def write_index(entry: dict):
    with INDEX_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "OctopusMemoryReceiver/1.0"

    def _json(self, status: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt, *args):
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))
        sys.stdout.flush()

    def do_GET(self):
        ensure_dirs()
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            files = sum(1 for p in STORAGE_DIR.glob("*") if p.is_file()) if STORAGE_DIR.exists() else 0
            return self._json(200, {"ok": True, "time": now_iso(), "files": files})
        if parsed.path == "/api/v1/memory/blob":
            try:
                verify_get(self, self.path)
                ref = parse_qs(parsed.query).get("ref", [""])[0]
                if not ref.startswith("sha256:") or not re.match(r"^[a-fA-F0-9]{64}$", ref[7:]):
                    return self._json(400, {"ok": False, "error": "invalid ref"})
                fp = STORAGE_DIR / ref[7:].lower()
                if not fp.exists():
                    return self._json(404, {"ok": False, "error": "not found"})
                data = fp.read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("x-octopus-content-sha256", sha)
                self.send_header("x-octopus-ref", ref)
                self.end_headers()
                self.wfile.write(data)
                return
            except ValueError as e:
                return self._json(401, {"ok": False, "error": str(e)})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        ensure_dirs()
        parsed = urlparse(self.path)
        if parsed.path != "/api/v1/memory/replicate":
            return self._json(404, {"ok": False, "error": "not found"})
        try:
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            verify_post(self, raw)
            payload = json.loads(raw.decode("utf-8"))
            ref = payload.get("ref", "")
            content_sha = (payload.get("contentSha256") or "").lower()
            file_b64 = payload.get("fileBase64", "")
            if not ref.startswith("sha256:") or not re.match(r"^[a-fA-F0-9]{64}$", ref[7:]):
                return self._json(400, {"ok": False, "error": "ref must start with sha256:"})
            if not re.match(r"^[a-fA-F0-9]{64}$", content_sha):
                return self._json(400, {"ok": False, "error": "invalid contentSha256"})
            if not file_b64:
                return self._json(400, {"ok": False, "error": "fileBase64 is required"})
            data = base64.b64decode(file_b64)
            actual_sha = hashlib.sha256(data).hexdigest()
            if actual_sha != content_sha:
                return self._json(422, {"ok": False, "error": "contentSha256 mismatch"})
            fp = STORAGE_DIR / ref[7:].lower()
            stored = False
            if not fp.exists():
                fp.write_bytes(data)
                os.chmod(fp, 0o640)
                stored = True
            entry = {
                "received_at": now_iso(),
                "ref": ref,
                "source_node_id": payload.get("sourceNodeId") or payload.get("nodeId") or "unknown",
                "content_sha256": actual_sha,
                "size_bytes": len(data),
                "mime_type": payload.get("mimeType") or "application/octet-stream",
                "tags": payload.get("tags") or [],
                "attrs": payload.get("attrs") or {},
            }
            write_index(entry)
            return self._json(200, {
                "ok": True,
                "stored": stored,
                "ref": ref,
                "contentSha256": actual_sha,
                "blobUrl": "/api/v1/memory/blob?ref=" + quote(ref, safe=':'),
            })
        except ValueError as e:
            return self._json(401, {"ok": False, "error": str(e)})
        except Exception as e:
            return self._json(500, {"ok": False, "error": str(e)})


def main():
    ensure_dirs()
    load_secret()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Octopus Memory Receiver listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
