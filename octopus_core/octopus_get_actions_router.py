import os
import time
import threading
import subprocess
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List
from fastapi import APIRouter, HTTPException, Query, Request
from urllib.parse import parse_qs, urlparse

router = APIRouter()

HOME = Path(os.getenv("HOME", "/root"))
TOKEN_FILE = HOME / "agents" / ".octopus_autopilot_token"
LOG_DIR = HOME / "agents" / "-Octopus" / "logs"
TOKEN = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else os.getenv("OCTOPUS_MASTER_TOKEN", "")

MAX_OUTPUT_CHARS = int(os.getenv("OCTOPUS_MAX_OUTPUT_CHARS", "80000"))
PROTECTED_PREFIXES = ("/mnt/memory", "/mnt/swarm")
_RUN_LOCK = threading.Lock()

@dataclass(frozen=True)
class ActionSpec:
    title: str
    cmd: str
    category: str
    description: str
    timeout: int = 60
    destructive: bool = False
    confirm_value: str = "YES"

def _multiline_cmd(cmd: str) -> str:
    return "set -o pipefail\n" + cmd.strip() + "\n"

ACTIONS: Dict[str, ActionSpec] = {
    "health": ActionSpec(
        title="Health",
        category="core",
        description="Fast local health check.",
        timeout=15,
        cmd=_multiline_cmd("echo 'ok' && hostname && date -Is")
    ),
    "status": ActionSpec(
        title="Status",
        category="core",
        description="Detailed Octopus Swarm status.",
        cmd=_multiline_cmd("octopus status")
    ),
    "info": ActionSpec(
        title="System Info",
        category="core",
        description="System resources and node count.",
        cmd=_multiline_cmd("octopus info")
    ),
    "version": ActionSpec(
        title="Version",
        category="core",
        description="Octopus Protocol Version.",
        cmd=_multiline_cmd("echo 'Octopus Protocol v2.4'")
    ),
    "audit-full": ActionSpec(
        title="Full Audit",
        category="audit",
        description="Complete system audit (disk, nodes, modules).",
        timeout=120,
        cmd=_multiline_cmd("/root/agents/tools/full_audit.sh")
    ),
    "audit-disk": ActionSpec(
        title="Disk Audit",
        category="audit",
        description="Analysis of largest directories.",
        cmd=_multiline_cmd("du -xhd1 /root /opt /var 2>/dev/null | sort -h")
    ),
    "audit-node-modules": ActionSpec(
        title="Node Modules Audit",
        category="audit",
        description="Find largest node_modules folders.",
        cmd=_multiline_cmd("find /root /opt -type d -name node_modules -prune -exec du -sh {} + 2>/dev/null | sort -hr | head -20")
    ),
    "audit-python-venvs": ActionSpec(
        title="Python Venv Audit",
        category="audit",
        description="Find largest Python virtual environments.",
        cmd=_multiline_cmd("find /root /opt -type d -name '*venv*' -prune -exec du -sh {} + 2>/dev/null | sort -hr")
    ),
    "audit-docker": ActionSpec(
        title="Docker Audit",
        category="audit",
        description="Analyze docker images and containers size.",
        cmd=_multiline_cmd("docker system df -v")
    ),
    "audit-ipfs": ActionSpec(
        title="IPFS Audit",
        category="audit",
        description="Check IPFS repo state.",
        cmd=_multiline_cmd("docker exec ipfs-node ipfs repo stat")
    ),
    "audit-fleet": ActionSpec(
        title="Fleet Audit",
        category="audit",
        description="Detailed list of swarm services and nodes.",
        cmd=_multiline_cmd("docker service ls && echo -e '\\n--- Local Nodes ---' && docker ps --format 'table {{.Names}}\t{{.Status}}'")
    ),
    "audit-repos": ActionSpec(
        title="Repo Audit",
        category="audit",
        description="Check git status of all repositories.",
        cmd=_multiline_cmd("find /root/agents -name .git -type d -prune -execdir sh -c 'echo \"--- {} ---\"; git log -1 --oneline; git status -s' \;")
    ),
    "audit-media": ActionSpec(
        title="Media Audit",
        category="audit",
        description="Find large media files outside protected zones.",
        cmd=_multiline_cmd("find /root /opt /var /tmp -xdev -type f -size +1M \( -iname '*.mp3' -o -iname '*.wav' -o -iname '*.m4a' -o -iname '*.ogg' -o -iname '*.mp4' \) -printf '%s %p\\n' 2>/dev/null | sort -nr | head -50")
    ),
    "audit-logs": ActionSpec(
        title="Logs Audit",
        category="audit",
        description="Largest log files in /var/log.",
        cmd=_multiline_cmd("du -ah /var/log 2>/dev/null | sort -hr | head -20")
    ),
    "ports": ActionSpec(
        title="Ports Audit",
        category="audit",
        description="List all listening ports.",
        cmd=_multiline_cmd("netstat -tulpn | grep LISTEN")
    ),
    "processes": ActionSpec(
        title="Process Audit",
        category="audit",
        description="Top processes by RAM usage.",
        cmd=_multiline_cmd("ps aux --sort=-rss | head -15")
    ),
    "aggressive-clean": ActionSpec(
        title="Aggressive Clean",
        category="clean",
        description="Clean docker, npm, cache, and journals. IRREVERSIBLE.",
        timeout=180,
        destructive=True,
        cmd=_multiline_cmd("journalctl --vacuum-time=1h && docker system prune -af --volumes && rm -rf ~/.npm ~/.cache/* && octopus clean")
    ),
    "docker-prune": ActionSpec(
        title="Docker Prune",
        category="clean",
        description="Remove unused docker data.",
        destructive=True,
        cmd=_multiline_cmd("docker system prune -f")
    ),
    "cache-clean": ActionSpec(
        title="Cache Clean",
        category="clean",
        description="Clear npm and user cache.",
        destructive=True,
        cmd=_multiline_cmd("rm -rf ~/.npm ~/.cache/*")
    ),
    "journal-clean": ActionSpec(
        title="Journal Clean",
        category="clean",
        description="Clear systemd journals older than 1h.",
        destructive=True,
        cmd=_multiline_cmd("journalctl --vacuum-time=1h")
    ),
    "tmp-clean": ActionSpec(
        title="TMP Clean",
        category="clean",
        description="Wipe /tmp directory.",
        destructive=True,
        cmd=_multiline_cmd("rm -rf /tmp/* /var/tmp/*")
    ),
    "ipfs-gc": ActionSpec(
        title="IPFS GC",
        category="clean",
        description="Run IPFS garbage collection.",
        cmd=_multiline_cmd("docker exec ipfs-node ipfs repo gc")
    ),
    "offload-media": ActionSpec(
        title="Offload Media",
        category="clean",
        description="Move large local media to IPFS.",
        timeout=300,
        cmd=_multiline_cmd("python3 /opt/octopus-media-offloader.py")
    ),
    "node-modules-prune-prod": ActionSpec(
        title="Node Modules Prune",
        category="clean",
        description="Remove devDependencies from production modules.",
        destructive=True,
        cmd=_multiline_cmd("find /root /opt -name package.json -execdir npm prune --production \;")
    ),
    "backup": ActionSpec(
        title="Backup",
        category="maintenance",
        description="Run standard backup manager.",
        timeout=300,
        cmd=_multiline_cmd("octopus backup")
    ),
    "sync": ActionSpec(
        title="Sync",
        category="maintenance",
        description="Sync with ubu-worker.",
        timeout=300,
        cmd=_multiline_cmd("octopus sync")
    ),
    "backup-sync": ActionSpec(
        title="Backup & Sync",
        category="maintenance",
        description="Run backup then sync.",
        timeout=600,
        cmd=_multiline_cmd("octopus backup && octopus sync")
    ),
    "octopus-help": ActionSpec(
        title="Octopus Help",
        category="maintenance",
        description="Show octopus CLI help.",
        cmd=_multiline_cmd("octopus --help || octopus")
    ),
}

@router.get("/actions")
async def list_actions(token: str = Query(...)):
    if not secrets.compare_digest(token, TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "protocol": "Octopus GET-only v2.4",
        "server": "Octopus Autopilot",
        "actions": {k: {
            "title": v.title,
            "category": v.category,
            "description": v.description,
            "destructive": v.destructive,
            "url": f"/run/{k}?token={token}"
        } for k, v in ACTIONS.items()}
    }

@router.get("/run/{action}")
async def run_action(
    action: str,
    token: str = Query(...),
    confirm: Optional[str] = Query(None),
    dry_run: Optional[bool] = Query(False)
):
    if not secrets.compare_digest(token, TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    spec = ACTIONS.get(action)
    if not spec:
        raise HTTPException(status_code=404, detail="Action not found")
    
    if spec.destructive and confirm != spec.confirm_value:
        return {
            "status": "error",
            "error": "Destructive action requires confirmation",
            "hint": f"Add &confirm={spec.confirm_value} to the URL"
        }
    
    if dry_run:
        return {
            "status": "dry_run",
            "action": action,
            "command": spec.cmd
        }

    if not _RUN_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Another action is already running")
    
    try:
        start_time = time.time()
        process = subprocess.run(
            spec.cmd,
            shell=True,
            capture_output=True,
            text=True,
            executable="/bin/bash",
            timeout=spec.timeout
        )
        duration = time.time() - start_time
        
        stdout = (process.stdout or "").replace(TOKEN, "[REDACTED_TOKEN]")
        stderr = (process.stderr or "").replace(TOKEN, "[REDACTED_TOKEN]")
        
        # Log the action
        log_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"{log_date}_action.md"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, "a") as f:
            f.write(f"## {datetime.now(timezone.utc).isoformat()} | Action: {action}\n")
            f.write(f"- Title: {spec.title}\n")
            f.write(f"- Duration: {duration:.2f}s\n")
            f.write(f"- Exit Code: {process.returncode}\n")
            f.write("### Output\n```\n")
            f.write(stdout[-2000:] if len(stdout) > 2000 else stdout)
            f.write("\n```\n\n")

        return {
            "action": action,
            "title": spec.title,
            "exit_code": process.returncode,
            "duration_s": round(duration, 2),
            "stdout": stdout[-MAX_OUTPUT_CHARS:] if len(stdout) > MAX_OUTPUT_CHARS else stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Timeout after {spec.timeout}s"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        _RUN_LOCK.release()
