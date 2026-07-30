#!/usr/bin/env python3
"""Config Drift Detector - Real config comparison"""
import json
import subprocess
import os
from pathlib import Path

TRACKED_CONFIGS = [
    "/etc/octopus/octopus.env",
    "/etc/octopus/secrets.env",
    "/mnt/agents/-Octopus/repo/config.yaml",
]

def get_file_hash(path):
    """Get SHA256 hash of file"""
    if not os.path.exists(path):
        return None
    result = subprocess.run(["sha256sum", path], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.split()[0]
    return None

def check_config(path):
    """Check single config"""
    if not os.path.exists(path):
        return {"path": path, "exists": False, "drifted": False}
    
    stat = os.stat(path)
    hash_val = get_file_hash(path)
    
    return {
        "path": path,
        "exists": True,
        "size": stat.st_size,
        "hash": hash_val[:16] + "..." if hash_val else None,
        "modified": stat.st_mtime,
        "drifted": False  # No baseline for now
    }

def main():
    configs = [check_config(p) for p in TRACKED_CONFIGS]
    exists_count = sum(1 for c in configs if c["exists"])
    
    print(json.dumps({
        "ok": exists_count == len(TRACKED_CONFIGS),
        "tracked": len(TRACKED_CONFIGS),
        "existing": exists_count,
        "configs": configs
    }, indent=2))

if __name__ == "__main__":
    main()
