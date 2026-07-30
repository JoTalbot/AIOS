#!/usr/bin/env python3
"""GitHub Actions Health Reader - Real GH API"""
import json
import subprocess
import os

def check_github_runner():
    """Check GitHub Actions runner status"""
    result = subprocess.run(
        ["systemctl", "is-active", "github-runner-octopus.service"],
        capture_output=True, text=True
    )
    status = result.stdout.strip()
    
    # Get runner info
    result2 = subprocess.run(
        ["systemctl", "show", "github-runner-octopus.service", "--property=ActiveEnterTimestamp,SubState"],
        capture_output=True, text=True
    )
    info = result2.stdout.strip()
    
    return {
        "service_active": status == "active",
        "status": status,
        "info": info.replace("=", ": "),
        "ok": status == "active"
    }

def check_workflows():
    """Check recent workflow runs"""
    gh_dir = "/root/.github-runner"
    result = subprocess.run(
        ["ls", "-la", gh_dir], capture_output=True, text=True
    )
    return {"gh_dir_exists": os.path.exists(gh_dir), "gh_dir_content": len(result.stdout) > 0}

def main():
    runner = check_github_runner()
    workflows = check_workflows()
    
    print(json.dumps({
        "ok": runner["ok"],
        "runner": runner,
        "workflows": workflows
    }, indent=2))

if __name__ == "__main__":
    main()
