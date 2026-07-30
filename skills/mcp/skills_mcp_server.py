#!/usr/bin/env python3
"""Octopus read-only operations and skills MCP bridge (stdio JSON lines)."""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
PROJECT = BASE.parent.parent
REPO = PROJECT / "repo"
sys.path.insert(0, str(BASE.parent / "loader"))
sys.path.insert(0, str(REPO))
from skills_loader import skills_loader
from swarm.ops.storage_live_read_proof import prove_many

TRACE_RE = re.compile(r"^octo-[0-9]{8}T[0-9]{6}Z-[a-z0-9_-]{1,32}-[0-9a-f]{8}$")
ALLOWED_PROOF_ROOTS = (
    PROJECT.resolve(),
    Path("/mnt/agents/-Octopus").resolve(),
    Path("/root/agents/-Octopus").resolve(),
    Path("/var/lib/octopus"),
    Path("/var/lib/garage"),
    Path("/opt/octopus"),
)
DENIED_PARTS = {"secrets", ".ssh", "credentials", "credential-vault"}
READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}


def trace_id(stream: str, supplied: str | None = None) -> str:
    candidate = supplied or os.environ.get("OCTOPUS_TRACE_ID", "")
    if candidate and TRACE_RE.fullmatch(candidate):
        return candidate
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = re.sub(r"[^a-z0-9_-]", "-", stream.lower())[:32] or "mcp"
    return f"octo-{now}-{safe}-{secrets.token_hex(4)}"


def tool_catalog() -> list[dict[str, Any]]:
    return [
        {"name": "ops/status", "description": "Read-only Octopus health, disk and failed-unit status.", "annotations": READ_ONLY},
        {"name": "storage/proof", "description": "Live-read proof for an allowlisted local storage path.", "annotations": READ_ONLY},
        {"name": "graphrag/search", "description": "Read-only GraphRAG search with exact source citations.", "annotations": READ_ONLY},
        {"name": "skills/list", "description": "List indexed Octopus skills.", "annotations": READ_ONLY},
        {"name": "skills/get", "description": "Read a skill definition.", "annotations": READ_ONLY},
        {"name": "skills/references", "description": "Read skill references.", "annotations": READ_ONLY},
    ]


def valid_proof_target(target: str) -> bool:
    raw = target.split(":", 1)[1] if ":" in target else target
    path = Path(raw)
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    if any(part.lower() in DENIED_PARTS for part in resolved.parts):
        return False
    return any(resolved == root or root in resolved.parents for root in ALLOWED_PROOF_ROOTS)


def ops_status() -> dict[str, Any]:
    disk = subprocess.run(["df", "-P", "/"], capture_output=True, text=True, timeout=5, check=True).stdout.splitlines()[-1].split()
    failed = subprocess.run(
        ["systemctl", "list-units", "--type=service", "--state=failed", "--no-legend", "--no-pager"],
        capture_output=True, text=True, timeout=8, check=False,
    ).stdout.splitlines()
    octopus_failed = [line.strip() for line in failed if "octopus" in line.lower()]
    return {
        "read_only": True,
        "disk": {"blocks_kb": int(disk[1]), "used_kb": int(disk[2]), "available_kb": int(disk[3]), "used_percent": int(disk[4].rstrip("%"))},
        "octopus_failed_count": len(octopus_failed),
        "octopus_failed": octopus_failed,
    }


def storage_proof(params: dict[str, Any]) -> dict[str, Any]:
    target = str(params.get("target", ""))
    if not target or not valid_proof_target(target):
        raise ValueError("target_not_allowlisted")
    max_bytes = min(max(int(params.get("max_hash_bytes", 1024 * 1024)), 1), 16 * 1024 * 1024)
    return prove_many([target], max_hash_bytes=max_bytes)


def graphrag_search(params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query", "")).strip()
    if not query or len(query) > 500:
        raise ValueError("invalid_query")
    limit = min(max(int(params.get("limit", 5)), 1), 20)
    query_params = {"q": query, "limit": limit}
    if params.get("trace_id"):
        query_params["trace_id"] = str(params["trace_id"])
    url = "http://127.0.0.1:9760/search?" + urllib.parse.urlencode(query_params)
    with urllib.request.urlopen(url, timeout=8) as response:
        payload = json.load(response)
    payload["read_only"] = True
    return payload


def dispatch(method: str, params: dict[str, Any]) -> Any:
    if method in {"methods/list", "tools/list"}:
        return {"tools": tool_catalog()}
    if method == "ops/status":
        return ops_status()
    if method == "storage/proof":
        return storage_proof(params)
    if method == "graphrag/search":
        return graphrag_search(params)
    if method == "skills/list":
        return {"skills": skills_loader.list_metadata()}
    if method == "skills/get":
        return {"content": skills_loader.load_full(params.get("name"))}
    if method == "skills/references":
        return {"refs": skills_loader.load_references(params.get("name"))}
    # Legacy activation is intentionally not exposed: it may execute a skill.
    raise ValueError("unknown_method")


def process_request(line: str) -> str:
    request_id: Any = None
    try:
        req = json.loads(line.strip())
        request_id = req.get("id")
        method = str(req.get("method", ""))
        params = req.get("params", {})
        if not isinstance(params, dict):
            raise ValueError("params_must_be_object")
        tid = trace_id(method.replace("/", "-"), params.get("trace_id"))
        params = dict(params)
        params["trace_id"] = tid
        result = dispatch(method, params)
        return json.dumps({"id": request_id, "trace_id": tid, "result": result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"id": request_id, "error": {"code": "request_failed", "message": str(exc)[:300]}}, ensure_ascii=False)


def main() -> int:
    print(json.dumps({"ready": True, "methods": [x["name"] for x in tool_catalog()] + ["methods/list", "tools/list"]}), flush=True)
    for line in sys.stdin:
        if line.strip():
            print(process_request(line), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
