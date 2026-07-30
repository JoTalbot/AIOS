#!/usr/bin/env python3
"""Railway Health Reader - Real Railway API integration"""
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

RAILWAY_URL = "https://octopus-production-71fe.up.railway.app/health"

def check_railway():
    try:
        req = urllib.request.Request(RAILWAY_URL, headers={"User-Agent": "Octopus-Skill/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        
        return {
            "ok": True,
            "status": data.get("status"),
            "role": data.get("role"),
            "uptime_seconds": data.get("uptime"),
            "uptime_hours": round(data.get("uptime", 0) / 3600, 1),
            "agents_synced": data.get("agents_synced"),
            "agents_files": data.get("agents_files"),
            "parent": data.get("parent"),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def main():
    result = check_railway()
    print(json.dumps({"ok": result.get("ok"), "railway": result}, indent=2))

if __name__ == "__main__":
    main()
