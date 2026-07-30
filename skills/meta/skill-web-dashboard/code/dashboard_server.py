#!/usr/bin/env python3
"""Octopus Web Dashboard — статус проекта в браузере"""
import http.server
import json
import os
import subprocess
from pathlib import Path

PORT = 8080
BASE = Path(os.path.expanduser("~/agents/-Octopus"))

def get_health():
    try:
        skill_path = BASE / "skills/core/skill-health-monitor/code/health_monitor.py"
        r = subprocess.run(["python3", str(skill_path)], capture_output=True, text=True, timeout=15)
        return json.loads(r.stdout)
    except:
        return {"score": 0, "grade": "?", "status": "unavailable"}

def get_autonomy_state():
    path = Path("/run/octopus/autonomy_state.json")
    if path.exists():
        try:
            return json.loads(path.read_text())
        except:
            pass
    return {"status": "never_run"}

def get_skills_audit():
    try:
        loader_path = BASE / "skills/loader/skills_loader_v3.py"
        r = subprocess.run(["python3", str(loader_path)], capture_output=True, text=True, timeout=15)
        # Парсим audit из вывода
        lines = r.stdout.split("\n")
        audit = {}
        for line in lines:
            if "Total:" in line:
                audit["total"] = int(line.split(":")[1].strip())
            elif "Real:" in line:
                audit["real"] = int(line.split(":")[1].strip())
            elif "Stubs:" in line:
                audit["stubs"] = int(line.split(":")[1].strip())
        return audit
    except:
        return {"total": "?", "real": "?", "stubs": "?"}

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/status", "/dashboard"):
            self.serve_dashboard()
        elif self.path == "/api/health":
            self.serve_json(get_health())
        elif self.path == "/api/autonomy":
            self.serve_json(get_autonomy_state())
        elif self.path == "/api/skills":
            self.serve_json(get_skills_audit())
        else:
            self.send_error(404)

    def serve_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def serve_dashboard(self):
        health = get_health()
        autonomy = get_autonomy_state()
        skills = get_skills_audit()

        score = health.get("score", 0)
        grade = health.get("grade", "?")
        status_color = "#4CAF50" if score >= 700 else "#FF9800" if score >= 400 else "#F44336"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Octopus Dashboard</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;margin:0;padding:20px;background:#1a1a2e;color:#e0e0e0}}
.container{{max-width:900px;margin:0 auto}}
h1{{color:#00d4ff;border-bottom:2px solid #00d4ff;padding-bottom:10px}}
h2{{color:#7b68ee;margin-top:30px}}
.card{{background:#16213e;border-radius:12px;padding:20px;margin:15px 0;box-shadow:0 4px 6px rgba(0,0,0,0.3)}}
.score{{font-size:64px;font-weight:bold;color:{status_color};text-align:center}}
.grade{{font-size:32px;text-align:center;color:{status_color}}}
.metric{{display:inline-block;margin:10px 20px;text-align:center}}
.metric-value{{font-size:28px;font-weight:bold;color:#00d4ff}}
.metric-label{{font-size:12px;color:#888}}
a{{color:#00d4ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
.dashboards{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.dash-item{{background:#0f3460;padding:15px;border-radius:8px;text-align:center}}
.btn{{display:inline-block;background:#00d4ff;color:#1a1a2e;padding:10px 20px;border-radius:6px;font-weight:bold;margin:5px}}
.btn-danger{{background:#F44336;color:white}}
code{{background:#0f3460;padding:2px 6px;border-radius:3px;font-size:13px}}
.warning{{background:#3d2800;border-left:4px solid #FF9800;padding:10px;margin:10px 0}}
.success{{background:#1b3d1b;border-left:4px solid #4CAF50;padding:10px;margin:10px 0}}
</style></head><body>
<div class="container">
<h1>🐙 Octopus Dashboard</h1>

<div class="card">
<div class="score">{score}</div>
<div class="grade">Grade {grade}</div>
<div style="text-align:center;margin-top:10px;color:#888">Health Score | {health.get('status','?').upper()}</div>
</div>

<div class="card">
<h2>📊 Метрики</h2>
<div class="metric"><div class="metric-value">{health.get('disk',{{}}).get('percent','?')}%</div><div class="metric-label">Disk Usage</div></div>
<div class="metric"><div class="metric-value">{health.get('docker',{{}}).get('running','?')}</div><div class="metric-label">Docker Running</div></div>
<div class="metric"><div class="metric-value">{health.get('docker',{{}}).get('total','?')}</div><div class="metric-label">Docker Total</div></div>
<div class="metric"><div class="metric-value">{health.get('services',{{}}).get('failed_count','?')}</div><div class="metric-label">Failed Services</div></div>
<div class="metric"><div class="metric-value">{skills.get('total','?')}</div><div class="metric-label">Total Skills</div></div>
<div class="metric"><div class="metric-value">{skills.get('real','?')}</div><div class="metric-label">Real Skills</div></div>
</div>

<div class="card">
<h2>🤖 Автономный агент</h2>
<p>Статус: <strong>{autonomy.get('status','unknown')}</strong></p>
<p>Последний цикл: {autonomy.get('last_cycle','never')}</p>
<p>Завершён: {autonomy.get('last_completed','N/A')}</p>
<p>Health Score: {autonomy.get('health_score','N/A')}</p>
<p>Следующий цикл: <strong>через 30 минут</strong></p>
</div>

<div class="card">
<h2>🔗 Дашборды и доступы</h2>
<div class="dashboards">
<div class="dash-item"><a href="https://railway.app/project/84619dda-ba59-4b99-9073-da89ffbcb472" target="_blank">Railway</a></div>
<div class="dash-item"><a href="https://github.com/JoTalbot/octopus" target="_blank">GitHub Repo</a></div>
<div class="dash-item"><a href="https://github.com/JoTalbot/octopus/actions" target="_blank">GitHub Actions</a></div>
<div class="dash-item"><a href="https://octopus-production-71fe.up.railway.app/health" target="_blank">Railway Health</a></div>
</div>
</div>

<div class="card">
<h2>🔑 Восстановление доступа</h2>
<div class="success"><strong>SSH ubu-worker:</strong> <code>ssh -p 2222 -i KEY root@traff.tplinkdns.com</code></div>
<div class="success"><strong>SSH parent:</strong> <code>ssh -p 9922 root@localhost</code> (с ubu)</div>
<div class="success"><strong>Disaster Recovery:</strong> <code>curl -sSL https://huggingface.co/datasets/JoTalbot/octopus-eternal/raw/main/octopus-bootstrap.sh | bash</code></div>
</div>

<div class="card">
<h2>🛑 Терминация</h2>
<div class="warning">
<p><strong>Остановка автономного агента:</strong> <code>systemctl stop octopus-autonomous-agent.timer</code></p>
<p><strong>Заморозка автономии:</strong> <code>octopus freeze</code></p>
<p><strong>Аварийная остановка:</strong> <code>octopus panic</code></p>
</div>
</div>

<div class="card">
<h2>📋 API Endpoints</h2>
<p><a href="/api/health">/api/health</a> — JSON здоровья системы</p>
<p><a href="/api/autonomy">/api/autonomy</a> — JSON состояния автономии</p>
<p><a href="/api/skills">/api/skills</a> — JSON аудита скиллов</p>
</div>

<p style="text-align:center;color:#666;margin-top:30px">Octopus v3.0 | Обновлено: {health.get('timestamp','N/A')}</p>
</div></body></html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass  # Quiet logging

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = http.server.HTTPServer(("0.0.0.0", port), DashboardHandler)
    print(f"🐙 Octopus Dashboard running on http://0.0.0.0:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
