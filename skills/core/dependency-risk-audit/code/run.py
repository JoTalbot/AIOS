#!/usr/bin/env python3
"""Dependency Risk Auditor"""
import json
import subprocess
import re

def check_pip_outdated():
    try:
        result = subprocess.run(["pip", "list", "--outdated", "--format=json"], capture_output=True, text=True, timeout=30)
        packages = json.loads(result.stdout) if result.stdout else []
        return [{"name": p["name"], "version": p["version"], "latest": p["latest_version"]} for p in packages[:10]]
    except:
        return []

def check_npm_outdated():
    try:
        result = subprocess.run(["npm", "outdated", "--json"], capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout) if result.stdout else {}
        return [{"name": k, "current": v.get("current"), "latest": v.get("latest")} for k, v in list(data.items())[:10]]
    except:
        return []

def check_cve_keywords():
    """Simple CVE keyword scan"""
    result = subprocess.run(["grep", "-r", "-i", "cve-\|vulnerability\|exploit", "/mnt/agents/-Octopus/repo/", "--include=*.md"], 
                          capture_output=True, text=True, timeout=10)
    findings = len(result.stdout.split("\n"))
    return {"cve_mentions": findings}

if __name__ == "__main__":
    pip = check_pip_outdated()
    npm = check_npm_outdated()
    cve = check_cve_keywords()
    
    outdated_count = len(pip) + len(npm)
    risk_level = "HIGH" if outdated_count > 20 else "MEDIUM" if outdated_count > 5 else "LOW"
    
    print(json.dumps({
        "ok": True,
        "outdated_pip": len(pip),
        "outdated_npm": len(npm),
        "pip_packages": pip[:5],
        "npm_packages": npm[:5],
        "cve_keywords": cve,
        "risk_level": risk_level,
        "recommendation": f"Update {outdated_count} packages" if outdated_count > 0 else "All dependencies OK"
    }, indent=2))
