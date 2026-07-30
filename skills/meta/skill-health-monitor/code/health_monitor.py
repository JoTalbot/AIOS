#!/usr/bin/env python3
"""Health Monitor Skill — проверка здоровья системы Octopus"""
import subprocess
import json
import re
import os
from datetime import datetime, timezone

def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1

def check_disk():
    out, _ = run_cmd("df -h /")
    lines = out.split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 5:
            pct = int(parts[4].replace("%", ""))
            return {"percent": pct, "used": parts[2], "total": parts[1], "available": parts[3]}
    return {"percent": -1, "error": "cannot parse df"}

def check_services():
    out, _ = run_cmd("systemctl list-units --type=service --all --no-pager")
    failed = []
    restarting = []
    for line in out.split("\n"):
        if "failed" in line.lower() and "octopus" in line.lower():
            failed.append(line.strip())
        if "auto-restart" in line.lower() and "octopus" in line.lower():
            restarting.append(line.strip())
    return {"failed": failed, "restarting": restarting, "failed_count": len(failed), "restarting_count": len(restarting)}

def check_docker():
    out, _ = run_cmd("docker ps --format '{{.Names}}|{{.Status}}'")
    containers = []
    for line in out.split("\n"):
        if "|" in line:
            name, status = line.split("|", 1)
            containers.append({"name": name, "status": status})
    total = len(containers)
    running = sum(1 for c in containers if "Up" in c["status"])
    return {"total": total, "running": running, "stopped": total - running, "containers": containers}

def check_orphan_processes():
    out, _ = run_cmd("ps aux | grep python3 | grep -v grep | grep -v systemd")
    suspicious = []
    for line in out.split("\n"):
        if line.strip() and "octopus" in line.lower():
            parts = line.split()
            if len(parts) >= 2:
                suspicious.append({"pid": parts[1], "cmd": " ".join(parts[10:]) if len(parts) > 10 else ""})
    return {"suspicious_count": len(suspicious), "processes": suspicious[:10]}

def check_octopus_api():
    out, rc = run_cmd("curl -s --max-time 5 http://localhost:8000/health 2>/dev/null")
    if rc == 0 and out:
        try:
            return json.loads(out)
        except:
            return {"status": "parse_error", "raw": out[:200]}
    return {"status": "unreachable"}

def compute_health_score(disk, services, docker, orphans):
    score = 1000
    # Disk penalty
    if disk["percent"] > 90:
        score -= 200
    elif disk["percent"] > 80:
        score -= 100
    elif disk["percent"] > 70:
        score -= 30
    # Service penalties
    score -= services["failed_count"] * 100
    score -= services["restarting_count"] * 50
    # Docker penalties
    if docker["total"] > 0:
        stopped_pct = docker["stopped"] / docker["total"]
        score -= int(stopped_pct * 200)
    # Orphan penalty
    score -= orphans["suspicious_count"] * 10
    return max(0, min(1000, score))

def grade_from_score(score):
    if score >= 1000: return "S"
    if score >= 900: return "A"
    if score >= 700: return "B"
    if score >= 500: return "C"
    if score >= 300: return "D"
    return "F"

def run_health_check():
    disk = check_disk()
    services = check_services()
    docker = check_docker()
    orphans = check_orphan_processes()
    api = check_octopus_api()
    score = compute_health_score(disk, services, docker, orphans)
    grade = grade_from_score(score)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "grade": grade,
        "status": "healthy" if score >= 700 else "degraded" if score >= 400 else "critical",
        "disk": disk,
        "services": services,
        "docker": {"total": docker["total"], "running": docker["running"], "stopped": docker["stopped"]},
        "orphans": orphans,
        "api": api
    }
    return report

if __name__ == "__main__":
    report = run_health_check()
    print(json.dumps(report, indent=2, ensure_ascii=False))
