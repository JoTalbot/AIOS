import json, urllib.request, sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TG_TOKEN = "8374235817:AAFYRj2DJGcBLfJU7MeHX6CFwbP1AkwsDok"
TG_CHAT = "588113957"

def tg_send(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": int(TG_CHAT), "text": text[:4000], "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=10)

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            ln = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(ln) or b"{}")
            alerts = body.get("alerts", [])
            for a in alerts:
                status = a.get("status", "?")
                name = a.get("labels", {}).get("alertname", "?")
                sev = a.get("labels", {}).get("severity", "info")
                msg = a.get("annotations", {}).get("summary", a.get("annotations", {}).get("description", ""))
                emoji = "🟢" if status == "resolved" else ("🔴" if sev == "critical" else "🟠")
                tg_send(f"{emoji} <b>AIOS Alert: {name}</b>\n{status}\n{msg[:500]}")
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        except Exception as e:
            self.send_response(200); self.end_headers(); self.wfile.write(str(e).encode())

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9099), H).serve_forever()
