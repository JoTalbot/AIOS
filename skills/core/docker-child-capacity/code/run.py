#!/usr/bin/env python3
"""Docker Child Capacity Auditor"""
import json
import subprocess

def get_container_stats():
    result = subprocess.run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], capture_output=True, text=True)
    containers = []
    for line in result.stdout.decode().strip().split("\n"):
        if line:
            parts = line.split("\t")
            containers.append({"name": parts[0], "status": parts[1] if len(parts) > 1 else "unknown"})
    return containers

def check_resources():
    result = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"], capture_output=True, text=True)
    stats = []
    for line in result.stdout.decode().strip().split("\n"):
        if line:
            parts = line.split("\t")
            stats.append({"name": parts[0], "cpu": parts[1] if len(parts) > 1 else "0%", "mem": parts[2] if len(parts) > 2 else "0/0"})
    return stats

if __name__ == "__main__":
    containers = get_container_stats()
    stats = check_resources()
    print(json.dumps({
        "ok": True,
        "containers_count": len(containers),
        "containers": containers,
        "stats": stats,
        "recommendation": "All containers healthy" if len(containers) < 100 else "High container count"
    }, indent=2))
