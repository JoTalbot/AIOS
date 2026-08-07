#!/usr/bin/env python3
"""Create and verify a local AIOS database backup through the running API."""
import json
import os
import urllib.request
from pathlib import Path

# Load .env to get AIOS_API_KEYS
env_path = Path(__file__).resolve().parents[1] / ".env"
api_key = ""
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line.startswith("AIOS_API_KEYS"):
            # Extract JSON value
            try:
                # AIOS_API_KEYS={...}
                json_str = line.split("=",1)[1].strip().strip("'").strip('"')
                # It is JSON object mapping key->meta, find admin key
                import json as _j
                keys = _j.loads(json_str)
                for k,v in keys.items():
                    if "admin" in v.get("roles",[]):
                        api_key = k
                        break
                if not api_key and keys:
                    api_key = list(keys.keys())[0]
            except Exception:
                pass
# Fallback to env
if not api_key:
    api_key = os.environ.get("AIOS_API_KEYS","")
    # try parse env as JSON if needed
    try:
        import json as _j2
        if api_key.startswith("{"):
            d=_j2.loads(api_key)
            for k,v in d.items():
                if "admin" in v.get("roles",[]):
                    api_key=k
                    break
    except Exception:
        pass

# Also try AIOS_OPS_ADMIN_API_KEY
if not api_key:
    api_key = os.environ.get("AIOS_OPS_ADMIN_API_KEY","")
if not api_key:
    # try read from data
    try:
        import json as _j3
        ops_path = Path("/root/AIOS/.env")
        for l in ops_path.read_text().splitlines():
            if "AIOS_OPS_ADMIN_API_KEY" in l:
                api_key = l.split("=",1)[1].strip().strip("'").strip('"')
    except Exception:
        pass

payload=json.dumps({"action":"create","label":"scheduled"}).encode()
headers={"Content-Type":"application/json"}
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"
request=urllib.request.Request("http://127.0.0.1:8000/api/backups",data=payload,headers=headers)
with urllib.request.urlopen(request,timeout=120) as response:
    result=json.load(response)
if not result.get("ok") or not result.get("verified"):
    raise SystemExit("backup creation or verification failed")
print(result["backup"]["backup_id"])
