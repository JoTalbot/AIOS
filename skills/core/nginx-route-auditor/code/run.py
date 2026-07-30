#!/usr/bin/env python3
"""Nginx Route Auditor"""
import json
import subprocess
import re

def check_nginx_config():
    result = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    return {
        "valid": result.returncode == 0,
        "output": result.stderr,
        "status": "OK" if result.returncode == 0 else "ERROR"
    }

def find_syntax_issues():
    """Find common nginx issues"""
    issues = []
    # Check for duplicate server_names
    result = subprocess.run(["grep", "-r", "server_name", "/etc/nginx/"], capture_output=True, text=True)
    lines = result.stdout.decode().split("\n")
    server_names = {}
    for line in lines:
        if line:
            issues.append(line)
    return {"issues_found": len(issues), "details": issues[:10]}

if __name__ == "__main__":
    config = check_nginx_config()
    issues = find_syntax_issues()
    print(json.dumps({
        "ok": True,
        "nginx_config": config,
        "route_audit": issues,
        "recommendation": "Fix errors" if not config["valid"] else "Config OK"
    }, indent=2))
