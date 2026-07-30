"""
Octopus Cascade Health Watchdog (Instruction #19 & #49)
Inter-node health checks between Parent and Worker nodes.
"""
import urllib.request
import json

NODES = [
    {"name": "Parent Node", "url": "http://127.0.0.1:8000/health"},
    {"name": "Autopilot API", "url": "http://127.0.0.1:8787/health"},
    {"name": "AutoHelp Center", "url": "http://127.0.0.1:8899/api/status"}
]

def check_cascade_health():
    results = {}
    for n in NODES:
        try:
            req = urllib.request.Request(n["url"])
            with urllib.request.urlopen(req, timeout=3) as resp:
                results[n["name"]] = "HEALTHY" if resp.status == 200 else "DEGRADED"
        except Exception:
            results[n["name"]] = "DOWN"
    return results

if __name__ == "__main__":
    print(json.dumps(check_cascade_health(), ensure_ascii=False, indent=2))
