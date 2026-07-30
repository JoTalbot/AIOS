#!/usr/bin/env python3
"""BATCH 57: IPFS Auto-Pin Coordinator with actual daemon"""
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

IPFS_API = "http://127.0.0.1:5001"
IPFS_GATEWAY = "http://127.0.0.1:8081"

def ipfs_add(file_path):
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": "file_not_found"}
    try:
        with open(path, "rb") as f:
            result = subprocess.run(
                ["ipfs", "add", str(path)],
                capture_output=True, text=True, timeout=30
            )
        if result.returncode == 0:
            cid = result.stdout.strip().split()[1]
            subprocess.run(["ipfs", "pin", "add", cid], check=False, timeout=10)
            return {"ok": True, "cid": cid, "pinned": True, "path": str(path)}
        return {"ok": False, "error": result.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def ipfs_cat(cid):
    try:
        result = subprocess.run(["ipfs", "cat", cid], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return {"ok": True, "cid": cid, "data": result.stdout[:200]}
        return {"ok": False, "error": result.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"Octopus immortal memory - batch 57")
        name = f.name
    print(json.dumps({"add": ipfs_add(name), "ts": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False, indent=2))
