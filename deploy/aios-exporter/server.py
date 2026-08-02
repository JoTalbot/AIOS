"""Serve AIOS auto-coder metrics from the shared data volume."""
import http.server
import os

METRICS = "/data/metrics_exporter/aios_service.prom"

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/metrics"):
            try:
                if os.path.exists(METRICS):
                    body = open(METRICS, "rb").read()
                else:
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
