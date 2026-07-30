#!/usr/bin/env python3
"""Schedule Runner Skill — выполнение запланированных задач"""
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SCHEDULE_PATH = Path(os.path.expanduser("~/agents/-Octopus/configs/schedule.json"))
HISTORY_PATH = Path(os.path.expanduser("~/agents/-Octopus/logs/schedule_history.jsonl"))

DEFAULT_SCHEDULE = {
    "tasks": [
        {"name": "health_check", "interval_minutes": 5, "command": "python3 ~/agents/-Octopus/skills/core/skill-health-monitor/code/health_monitor.py", "vector": "live"},
        {"name": "disk_monitor", "interval_minutes": 10, "command": "df -h /", "vector": "live"},
        {"name": "docker_check", "interval_minutes": 15, "command": "docker ps --format '{{.Names}}: {{.Status}}'", "vector": "live"},
        {"name": "service_check", "interval_minutes": 15, "command": "systemctl list-units --type=service | grep octopus | grep -v active", "vector": "live"},
        {"name": "autonomous_cycle", "interval_minutes": 30, "command": "python3 ~/agents/-Octopus/skills/core/skill-autonomous-agent/code/autonomous_agent.py cycle", "vector": "develop"},
        {"name": "memory_check", "interval_minutes": 60, "command": "echo 'memory_check_placeholder'", "vector": "memory"},
        {"name": "experience_update", "interval_minutes": 120, "command": "echo 'experience_update_placeholder'", "vector": "learn"}
    ]
}

def ensure_schedule():
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SCHEDULE_PATH.exists():
        SCHEDULE_PATH.write_text(json.dumps(DEFAULT_SCHEDULE, indent=2, ensure_ascii=False))
    return json.loads(SCHEDULE_PATH.read_text())

def get_last_run(task_name):
    if not HISTORY_PATH.exists():
        return None
    last = None
    with open(HISTORY_PATH) as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("task") == task_name:
                    last = entry
            except:
                continue
    return last

def should_run(task):
    last = get_last_run(task["name"])
    if not last:
        return True
    try:
        last_time = datetime.fromisoformat(last["timestamp"])
        now = datetime.now(timezone.utc)
        diff = (now - last_time).total_seconds() / 60
        return diff >= task.get("interval_minutes", 30)
    except:
        return True

def run_task(task):
    try:
        result = subprocess.run(
            task["command"], shell=True, capture_output=True, text=True, timeout=120
        )
        entry = {
            "task": task["name"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exit_code": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:200],
            "vector": task.get("vector", "unknown")
        }
    except subprocess.TimeoutExpired:
        entry = {
            "task": task["name"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exit_code": -1,
            "error": "timeout"
        }
    except Exception as e:
        entry = {
            "task": task["name"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "exit_code": -1,
            "error": str(e)
        }

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry

def run_due_tasks():
    schedule = ensure_schedule()
    results = []
    for task in schedule.get("tasks", []):
        if should_run(task):
            result = run_task(task)
            results.append(result)
    return results

if __name__ == "__main__":
    results = run_due_tasks()
    if results:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("No tasks due")
