#!/usr/bin/env python3
"""Create and verify a local AIOS database backup through the running API."""
import json
import urllib.request
payload=json.dumps({"action":"create","label":"scheduled"}).encode()
request=urllib.request.Request("http://127.0.0.1:8000/api/backups",data=payload,headers={"Content-Type":"application/json"})
with urllib.request.urlopen(request,timeout=120) as response:
    result=json.load(response)
if not result.get("ok") or not result.get("verified"):
    raise SystemExit("backup creation or verification failed")
print(result["backup"]["backup_id"])
