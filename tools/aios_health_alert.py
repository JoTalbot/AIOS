#!/usr/bin/env python3
"""Low-noise production health checks with Telegram state-change alerts."""
from __future__ import annotations

import json
import os
import shutil
import ssl
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT = Path("/root/AIOS")
ENV_PATH = PROJECT / ".env"
STATE_PATH = Path("/var/lib/aios-health-alert/state.json")


def env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip("'\"")
    return values


def http_ok(url: str) -> bool:
    result = subprocess.run(["curl", "-fsS", "--max-time", "10", "-o", "/dev/null", url], capture_output=True, timeout=15)
    return result.returncode == 0


def cert_ok(host: str, days: int = 14) -> bool:
    try:
        context = ssl.create_default_context()
        with context.wrap_socket(__import__("socket").create_connection((host, 443), timeout=10), server_hostname=host) as sock:
            import datetime
            expiry = datetime.datetime.strptime(sock.getpeercert()["notAfter"], "%b %d %H:%M:%S %Y %Z")
            return expiry > datetime.datetime.utcnow() + datetime.timedelta(days=days)
    except Exception:
        return False


def check() -> dict[str, bool]:
    docker = subprocess.run(["docker", "compose", "-f", str(PROJECT / "docker-compose.prod.yml"), "ps", "--status", "running", "-q"], capture_output=True, text=True, timeout=20)
    running = {line for line in docker.stdout.splitlines() if line}
    required = {"aios-api", "aios-dashboard", "aios-mcp"}
    names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=20).stdout.splitlines()
    return {
        "api": http_ok("http://127.0.0.1:8000/health"),
        "mcp": http_ok("http://127.0.0.1:8471/health"),
        "dashboard": http_ok("http://127.0.0.1:8080/"),
        "public_https": http_ok("https://api.autosklo.org.ua/"),
        "certificate": cert_ok("api.autosklo.org.ua"),
        "disk": shutil.disk_usage("/").free / shutil.disk_usage("/").total > 0.10,
        "containers": required.issubset(set(names)),
    }


def notify(env: dict[str, str], text: str) -> None:
    token, chat_id = env.get("TELEGRAM_BOT_TOKEN"), env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    data = json.dumps({"chat_id": chat_id, "text": text}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(request, timeout=15).read()
    except Exception:
        pass


def main() -> int:
    env = env_values()
    current = check()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    changed = {name: value for name, value in current.items() if previous.get(name) != value}
    failed = [name for name, value in current.items() if not value]
    if failed and changed:
        notify(env, "🔴 AIOS health alert: " + ", ".join(failed))
    elif previous and not failed and any(previous.get(name) is False for name in current):
        notify(env, "🟢 AIOS health restored: all checks are OK")
    STATE_PATH.write_text(json.dumps(current, sort_keys=True))
    print(json.dumps(current, sort_keys=True))
    # Alert state is persisted and reported via Telegram; the timer itself must
    # remain healthy even while an observed dependency is unavailable.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
