"""Serve AIOS auto-coder + autonomy metrics from the shared data volume."""
import http.server
import os

METRICS_DIR = "/data/metrics_exporter"
FILES = ["aios_service.prom", "autonomy.prom"]

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/metrics"):
            try:
                body = b""
                for name in FILES:
                    p = os.path.join(METRICS_DIR, name)
                    if os.path.exists(p):
                        body += open(p, "rb").read() + b"\n"
                if not body:
                    body = b"# no metrics yet\n"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body = str(e).encode()
                self.send_response(500); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a): pass

if __name__ == "__main__":
    http.server.HTTPServer(("0.0.0.0", 9101), H).serve_forever()
