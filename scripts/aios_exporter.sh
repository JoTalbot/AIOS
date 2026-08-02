#!/bin/bash
PORT=9101
OUT_DIR=/var/lib/docker/volumes/aios_aios-data/_data/metrics_exporter
mkdir -p "$OUT_DIR"

check_port() {
  local name="$1" host="$2" port="$3"
  if timeout 3 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
    echo "aios_service_up{service=\"$name\",port=\"$port\"} 1"
  else
    echo "aios_service_up{service=\"$name\",port=\"$port\"} 0"
  fi
}

render_metrics() {
  {
    echo "# HELP aios_service_up Whether a service TCP port is reachable"
    echo "# TYPE aios_service_up gauge"
    check_port "api" "127.0.0.1" 8000
    check_port "mcp" "127.0.0.1" 8471
    check_port "grafana" "127.0.0.1" 3000
    check_port "prometheus" "127.0.0.1" 9090
    check_port "dashboard" "127.0.0.1" 8080
    check_port "ssh" "127.0.0.1" 22
    if systemctl is-active --quiet aios-auto-coder; then
      echo "aios_coder_service_up 1"
    else
      echo "aios_coder_service_up 0"
    fi
    local ap_log="/root/AIOS/logs/auto_promote.log"
    local promotes=$(grep -c "auto-promote complete" "$ap_log" 2>/dev/null || echo 0)
    local blocked=$(grep -c "BLOCKED" "$ap_log" 2>/dev/null || echo 0)
    echo "aios_auto_promotes_total $promotes"
    echo "aios_auto_promote_blocked_total $blocked"
    # Extended metrics
    /opt/aios/.venv/bin/python3.11 /root/AIOS/scripts/metrics_extended.py 2>/dev/null || true
  } > "$OUT_DIR/aios_service.prom"
}

render_metrics

if [ "${1:-}" = "--serve" ]; then
  exec /usr/bin/python3 -c "
import http.server, socketserver
d='/root/AIOS/data/metrics_exporter'
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/metrics'):
            try:
                body=open(d+'/aios_service.prom','rb').read()
                self.send_response(200)
                self.send_header('Content-Type','text/plain; version=0.0.4')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                body=str(e).encode()
                self.send_response(500); self.end_headers(); self.wfile.write(body)
        else:
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
with socketserver.TCPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv)>1 else 9101), H) as s:
    s.serve_forever()
" "$PORT"
fi
