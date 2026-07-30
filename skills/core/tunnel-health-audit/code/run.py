#!/usr/bin/env python3
"""Tunnel Health Auditor"""
import json
import subprocess

def check_ssh_tunnels():
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    tunnels = []
    for line in result.stdout.decode().split("\n"):
        if "ssh" in line and ("-N" in line or "-L" in line):
            tunnels.append(line.strip()[:100])
    return tunnels

def check_cf_tunnel():
    result = subprocess.run(["systemctl", "is-active", "cloudflared"], capture_output=True, text=True)
    cf_status = result.stdout.decode().strip()
    return {"service": "cloudflared", "active": cf_status == "active"}

def check_cloudflare_status():
    """Check CF tunnel status"""
    result = subprocess.run(["curl", "-s", "--max-time", "3", "http://127.0.0.1:8080/"], capture_output=True, text=True)
    return {"responding": result.returncode == 0}

if __name__ == "__main__":
    ssh_tunnels = check_ssh_tunnels()
    cf = check_cf_tunnel()
    cf_responding = check_cloudflare_status()
    print(json.dumps({
        "ok": True,
        "ssh_tunnels": ssh_tunnels,
        "cloudflare": cf,
        "cloudflare_responding": cf_responding,
        "recommendation": "Tunnels OK" if ssh_tunnels or cf["active"] else "No tunnels running"
    }, indent=2))
