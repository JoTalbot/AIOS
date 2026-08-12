#!/usr/bin/env python3
"""Octopus Batch API v2 — mass & parallel endpoints for agent efficiency.

Designed to be imported by main.py or run standalone.  All endpoints are
protected by the same OCTOPUS_TOKEN header auth.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.getenv("OCTOPUS_TOKEN", "default")
SKILLS_BASE = Path(os.path.expanduser("~/agents/-Octopus/skills"))
MAX_PARALLEL = int(os.getenv("OCTOPUS_BATCH_MAX_PARALLEL", "64"))
CMD_TIMEOUT = int(os.getenv("OCTOPUS_BATCH_CMD_TIMEOUT", "120"))
MAX_WALK_DEPTH = int(os.getenv("OCTOPUS_BATCH_MAX_DEPTH", "8"))
MAX_WALK_FILES = int(os.getenv("OCTOPUS_BATCH_MAX_FILES", "5000"))

router = APIRouter(prefix="/api/v2", tags=["batch"])

# ---------------------------------------------------------------------------
# Auth helper (same as main.py)
# ---------------------------------------------------------------------------
def _check_token(x_octopus_token: str = Header(default="")) -> None:
    if x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def _decode(s: str) -> str:
    """Double-URL-decode (Gemini sends double-encoded)."""
    return urllib.parse.unquote(urllib.parse.unquote(s))

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class CmdItem(BaseModel):
    id: str = Field(default="", description="caller-provided ID for correlation")
    command: str
    timeout: int = Field(default=CMD_TIMEOUT, ge=5, le=600)
    cwd: Optional[str] = None

class BatchExecuteRequest(BaseModel):
    commands: List[CmdItem] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True, description="True=ThreadPool, False=sequential")

class SkillRunItem(BaseModel):
    id: str = Field(default="")
    skill_id: str = Field(description="category/name or just name")
    context: str = Field(default="")
    timeout: int = Field(default=60, ge=5, le=600)

class BatchSkillRunRequest(BaseModel):
    skills: List[SkillRunItem] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True)

class MemoryOp(BaseModel):
    id: str = Field(default="")
    op: str = Field(description="insert | get")
    table: str = ""
    key: str = ""
    data: Any = None
    tags: List[str] = Field(default_factory=list)

class BatchMemoryRequest(BaseModel):
    operations: List[MemoryOp] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True)

class FileReadItem(BaseModel):
    path: str
    id: str = Field(default="")
    max_bytes: int = Field(default=50000, ge=100, le=500000)

class BatchFileReadRequest(BaseModel):
    files: List[FileReadItem] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True)

class FileWriteItem(BaseModel):
    path: str
    content: str
    id: str = Field(default="")
    mode: str = Field(default="0o644")

class BatchFileWriteRequest(BaseModel):
    files: List[FileWriteItem] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True)

class ServiceAction(BaseModel):
    name: str
    action: str = Field(description="restart | stop | start | status")

class BatchServiceRequest(BaseModel):
    services: List[ServiceAction] = Field(..., min_length=1, max_length=64)
    parallel: bool = Field(default=True)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_single_cmd(cmd: str, timeout: int = CMD_TIMEOUT, cwd: Optional[str] = None) -> dict:
    """Execute one shell command, return result dict."""
    decoded = _decode(cmd)
    try:
        r = subprocess.run(
            decoded, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
        return {
            "stdout": r.stdout,
            "stderr": r.stderr,
            "returncode": r.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "stdout": (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else str(e.stdout or ""),
            "stderr": f"Timeout after {timeout}s",
            "returncode": 124,
            "timed_out": True,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": 1, "timed_out": False}


def _read_file_safe(path_str: str, max_bytes: int = 50000) -> dict:
    """Read a file safely, return content or error."""
    try:
        p = Path(path_str).expanduser().resolve()
        if not p.exists():
            return {"path": path_str, "error": "not_found", "content": None}
        if not p.is_file():
            return {"path": path_str, "error": "not_a_file", "content": None}
        # Security: restrict to home directory
        home = Path.home()
        try:
            p.relative_to(home)
        except ValueError:
            return {"path": path_str, "error": "path_escape", "content": None}
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > max_bytes:
            content = content[:max_bytes] + f"\n... [truncated at {max_bytes} bytes]"
        return {"path": str(p), "content": content, "size": len(content), "error": None}
    except Exception as e:
        return {"path": path_str, "error": str(e), "content": None}


def _write_file_safe(path_str: str, content: str, mode: str = "0o644") -> dict:
    """Write a file safely, return result."""
    try:
        p = Path(path_str).expanduser().resolve()
        home = Path.home()
        try:
            p.relative_to(home)
        except ValueError:
            return {"path": path_str, "error": "path_escape", "ok": False}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "ok": True, "size": len(content), "error": None}
    except Exception as e:
        return {"path": path_str, "error": str(e), "ok": False}


def _walk_dir(
    root: str,
    pattern: str = "*",
    exclude_dirs: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: int = MAX_WALK_DEPTH,
    max_files: int = MAX_WALK_FILES,
    include_content: bool = False,
    content_max: int = 2000,
) -> dict:
    """Recursively walk a directory with filtering."""
    try:
        base = Path(root).expanduser().resolve()
        home = Path.home()
        try:
            base.relative_to(home)
        except ValueError:
            return {"error": "path_escape", "root": root, "files": [], "total": 0}

        if not base.exists():
            return {"error": "not_found", "root": root, "files": [], "total": 0}
        if not base.is_dir():
            return {"error": "not_a_directory", "root": root, "files": [], "total": 0}

        exclude_dirs = set(exclude_dirs or []) | {"__pycache__", ".git", "node_modules", ".venv", "venv", "__pypackages__"}
        exclude_re = [re.compile(p, re.I) for p in (exclude_patterns or [])]

        files = []
        dirs_visited = 0
        for p in base.rglob(pattern):
            depth = len(p.relative_to(base).parts)
            if depth > max_depth:
                continue
            if p.name in exclude_dirs:
                # Don't descend into excluded dirs
                continue
            # Check if any parent is excluded
            rel_parts = p.relative_to(base).parts
            skip = False
            for part in rel_parts:
                if part in exclude_dirs:
                    skip = True
                    break
            if skip:
                continue

            entry = {
                "path": str(p),
                "relative": str(p.relative_to(base)),
                "name": p.name,
                "is_dir": p.is_dir(),
                "size": p.stat().st_size if p.is_file() else 0,
            }
            if include_content and p.is_file() and p.stat().st_size < 500000:
                try:
                    txt = p.read_text(encoding="utf-8", errors="replace")
                    entry["content"] = txt[:content_max]
                except Exception:
                    pass
            files.append(entry)
            if len(files) >= max_files:
                break
        return {
            "root": str(base),
            "total": len(files),
            "pattern": pattern,
            "max_depth_reached": len(files) >= max_files,
            "files": files,
        }
    except Exception as e:
        return {"error": str(e), "root": root, "files": [], "total": 0}

# ---------------------------------------------------------------------------
# Skills helpers
# ---------------------------------------------------------------------------

def _load_skill_index() -> dict:
    """Load the pre-built skill index."""
    idx_path = SKILLS_BASE / "index.json"
    if idx_path.exists():
        return json.loads(idx_path.read_text(encoding="utf-8"))
    return {"error": "index_not_found", "skills": {}, "audit": {}}


def _read_all_instructions(
    categories: Optional[List[str]] = None,
    real_only: bool = False,
    include_stub: bool = True,
    max_skills: int = 500,
) -> dict:
    """Read all SKILL.md files in one batch call."""
    index = _load_skill_index()
    skills = index.get("skills", {})
    results = []
    count = 0
    for sid, meta in sorted(skills.items()):
        cat = sid.split("/")[0] if "/" in sid else ""
        if categories and cat not in categories:
            continue
        if real_only and meta.get("stub", True):
            continue
        if not include_stub and meta.get("stub", True):
            continue

        skill_path = Path(meta.get("path", ""))
        skill_md = skill_path / "SKILL.md"
        content = ""
        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = f"[error reading {skill_md}]"

        entry = {k: v for k, v in meta.items() if k != "code"}
        entry["content"] = content
        entry["content_length"] = len(content)
        results.append(entry)
        count += 1
        if count >= max_skills:
            break

    return {
        "total": len(results),
        "filtered_categories": categories,
        "real_only": real_only,
        "skills": results,
    }


def _read_skill_content(skill_id: str) -> dict:
    """Read full content of a single skill including code files."""
    index = _load_skill_index()
    skills = index.get("skills", {})

    # Find by exact ID or by name
    meta = skills.get(skill_id)
    if not meta:
        # Try matching by name
        for sid, m in skills.items():
            if m.get("name") == skill_id or m.get("dir_name") == skill_id:
                meta = m
                skill_id = sid
                break

    if not meta:
        return {"error": "skill_not_found", "skill_id": skill_id}

    skill_path = Path(meta.get("path", ""))
    result = {k: v for k, v in meta.items() if k != "code"}
    result["skill_id"] = skill_id

    # Read SKILL.md
    skill_md = skill_path / "SKILL.md"
    if skill_md.exists():
        result["skill_md"] = skill_md.read_text(encoding="utf-8", errors="replace")
    else:
        result["skill_md"] = None

    # Read code files
    code_files = {}
    code_dir = skill_path / "code"
    if code_dir.exists():
        for f in sorted(code_dir.iterdir()):
            if f.is_file() and not f.name.startswith("__"):
                try:
                    code_files[f.name] = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    code_files[f.name] = "[read error]"
    elif (skill_path / "code.py").exists():
        try:
            code_files["code.py"] = (skill_path / "code.py").read_text(encoding="utf-8", errors="replace")
        except Exception:
            code_files["code.py"] = "[read error]"
    result["code_files"] = code_files

    # Read test files (names only + small content)
    test_dir = skill_path / "tests"
    test_files = {}
    if test_dir.exists():
        for f in sorted(test_dir.iterdir()):
            if f.is_file() and f.suffix == ".py":
                try:
                    txt = f.read_text(encoding="utf-8", errors="replace")
                    test_files[f.name] = txt[:5000]  # tests can be long
                except Exception:
                    pass
    result["test_files"] = test_files

    return result

# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------

def _get_all_octopus_services() -> List[dict]:
    """Get status of all octopus-* systemd services."""
    try:
        r = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--all", "--no-legend"],
            capture_output=True, text=True, timeout=10,
        )
        services = []
        for line in (r.stdout or "").strip().split("\n"):
            if "octopus" not in line.lower():
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            name = parts[0]
            load, active, sub = parts[1], parts[2], parts[3]
            services.append({"name": name, "load": load, "active": active, "sub": sub})
        return sorted(services, key=lambda s: s["name"])
    except Exception as e:
        return [{"error": str(e)}]


def _service_action(name: str, action: str) -> dict:
    """Execute a systemd action on a service."""
    if action == "status":
        r = subprocess.run(
            ["systemctl", "is-active", name], capture_output=True, text=True, timeout=10,
        )
        return {"name": name, "action": action, "result": r.stdout.strip(), "ok": r.returncode == 0}
    if action not in ("restart", "stop", "start", "enable", "disable"):
        return {"name": name, "action": action, "error": "invalid_action", "ok": False}
    r = subprocess.run(
        ["sudo", "systemctl", action, name], capture_output=True, text=True, timeout=30,
    )
    return {"name": name, "action": action, "ok": r.returncode == 0, "stderr": r.stderr.strip()}


# ===========================================================================
# ENDPOINTS
# ===========================================================================

# ---- SKILLS: Read ----

@router.get("/skills/index")
def skills_index(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    index = _load_skill_index()
    audit = index.get("audit", {})
    return {
        "total_skills": audit.get("total", 0),
        "real_skills": audit.get("real_skills", 0),
        "stubs": audit.get("stubs", 0),
        "categories": audit.get("categories", {}),
        "skills": {k: {kk: vv for kk, vv in v.items() if kk != "code"} for k, v in index.get("skills", {}).items()},
    }


@router.get("/skills/read_all")
def skills_read_all(
    categories: str = Query(default="", description="Comma-separated category filter"),
    real_only: bool = Query(default=False),
    x_octopus_token: str = Header(default=""),
):
    _check_token(x_octopus_token)
    cats = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
    return _read_all_instructions(categories=cats, real_only=real_only)


@router.get("/skills/{category}")
def skills_by_category(category: str, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    data = _read_all_instructions(categories=[category])
    if not data["skills"] and category not in ("core", "dr", "loader", "marketplace", "mcp", "meta", "research"):
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found or empty")
    return data


@router.get("/skills/{category}/{name}")
def skill_detail(category: str, name: str, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    skill_id = f"{category}/{name}"
    result = _read_skill_content(skill_id)
    if "error" in result and result["error"] == "skill_not_found":
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---- BATCH: Execute ----

@router.post("/batch/execute")
def batch_execute(req: BatchExecuteRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    if req.parallel and len(req.commands) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.commands), MAX_PARALLEL)) as pool:
            futures = {
                pool.submit(_run_single_cmd, item.command, item.timeout, item.cwd): item
                for item in req.commands
            }
            for fut in as_completed(futures):
                item = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"stdout": "", "stderr": str(e), "returncode": 1, "timed_out": False}
                entry = {"id": item.id, "command": item.command, **res}
                results.append(entry)
    else:
        for item in req.commands:
            res = _run_single_cmd(item.command, item.timeout, item.cwd)
            results.append({"id": item.id, "command": item.command, **res})

    # Sort by original order for determinism
    id_order = {item.id: i for i, item in enumerate(req.commands)}
    results.sort(key=lambda r: id_order.get(r["id"], 999))

    elapsed = time.monotonic() - t0
    return {
        "total": len(results),
        "parallel": req.parallel,
        "elapsed_sec": round(elapsed, 3),
        "results": results,
    }


@router.post("/batch/skills/run")
def batch_skills_run(req: BatchSkillRunRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    def _run_one(item: SkillRunItem) -> dict:
        try:
            content = _read_skill_content(item.skill_id)
            # Execute the skill's code/run.py if it exists
            code_path = Path(content.get("path", "")) / "code" / "run.py"
            if code_path.exists():
                r = subprocess.run(
                    [sys.executable, str(code_path)],
                    capture_output=True, text=True, timeout=item.timeout,
                    cwd=str(Path(content["path"]) / "code"),
                    env={**os.environ, "SKILL_CONTEXT": item.context},
                )
                content["execution"] = {
                    "stdout": r.stdout[:10000],
                    "stderr": r.stderr[:5000],
                    "returncode": r.returncode,
                }
            else:
                content["execution"] = {"skipped": True, "reason": "no code/run.py found"}
            return {"id": item.id, "skill_id": item.skill_id, **content}
        except Exception as e:
            return {"id": item.id, "skill_id": item.skill_id, "error": str(e)}

    if req.parallel and len(req.skills) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.skills), MAX_PARALLEL)) as pool:
            futures = {pool.submit(_run_one, item): item for item in req.skills}
            for fut in as_completed(futures):
                results.append(fut.result())
    else:
        for item in req.skills:
            results.append(_run_one(item))

    elapsed = time.monotonic() - t0
    return {
        "total": len(results),
        "parallel": req.parallel,
        "elapsed_sec": round(elapsed, 3),
        "results": results,
    }


# ---- BATCH: Memory ----

@router.post("/batch/memory")
def batch_memory(req: BatchMemoryRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    def _mem_op(op: MemoryOp) -> dict:
        try:
            if op.op == "insert":
                # Try swarm memory if available
                try:
                    from swarm.memory.repository import MemoryRepository
                    loop = asyncio.new_event_loop()
                    # This needs a container which we may not have in this context
                    # So we use the file-based fallback
                    loop.close()
                except ImportError:
                    pass
                # Fallback: file-based storage
                store_path = SKILLS_BASE / ".batch_memory" / op.table
                store_path.mkdir(parents=True, exist_ok=True)
                key = op.key or str(int(time.time() * 1000))
                fpath = store_path / f"{key}.json"
                fpath.write_text(json.dumps({"data": op.data, "tags": op.tags, "ts": time.time()}))
                return {"id": op.id, "op": "insert", "table": op.table, "key": key, "ok": True, "path": str(fpath)}
            elif op.op == "get":
                store_path = SKILLS_BASE / ".batch_memory" / op.table
                fpath = store_path / f"{op.key}.json"
                if fpath.exists():
                    data = json.loads(fpath.read_text())
                    return {"id": op.id, "op": "get", "table": op.table, "key": op.key, "data": data, "ok": True}
                return {"id": op.id, "op": "get", "table": op.table, "key": op.key, "ok": False, "error": "not_found"}
            else:
                return {"id": op.id, "op": op.op, "error": "unknown_op", "ok": False}
        except Exception as e:
            return {"id": op.id, "op": op.op, "error": str(e), "ok": False}

    if req.parallel and len(req.operations) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.operations), MAX_PARALLEL)) as pool:
            for fut in as_completed({pool.submit(_mem_op, op): op for op in req.operations}):
                results.append(fut.result())
    else:
        for op in req.operations:
            results.append(_mem_op(op))

    elapsed = time.monotonic() - t0
    return {"total": len(results), "elapsed_sec": round(elapsed, 3), "results": results}


# ---- FILESYSTEM ----

@router.get("/fs/walk")
def fs_walk(
    root: str = Query(default="~", description="Directory root to walk"),
    pattern: str = Query(default="*", description="Glob pattern"),
    exclude_dirs: str = Query(default="", description="Comma-separated dirs to skip"),
    max_depth: int = Query(default=MAX_WALK_DEPTH, ge=1, le=20),
    max_files: int = Query(default=MAX_WALK_FILES, ge=1, le=50000),
    include_content: bool = Query(default=False),
    x_octopus_token: str = Header(default=""),
):
    _check_token(x_octopus_token)
    excl = [d.strip() for d in exclude_dirs.split(",") if d.strip()] if exclude_dirs else None
    return _walk_dir(root, pattern=pattern, exclude_dirs=excl, max_depth=max_depth,
                     max_files=max_files, include_content=include_content)


@router.post("/fs/read_batch")
def fs_read_batch(req: BatchFileReadRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    if req.parallel and len(req.files) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.files), MAX_PARALLEL)) as pool:
            for fut in as_completed({pool.submit(_read_file_safe, f.path, f.max_bytes): f for f in req.files}):
                item = list({f.id: f for f in req.files if f.path == fut.result().get("path", "")}.values())
                res = fut.result()
                res["id"] = item[0].id if item else ""
                results.append(res)
    else:
        for f in req.files:
            res = _read_file_safe(f.path, f.max_bytes)
            res["id"] = f.id
            results.append(res)

    elapsed = time.monotonic() - t0
    return {"total": len(results), "elapsed_sec": round(elapsed, 3), "results": results}


@router.post("/fs/write_batch")
def fs_write_batch(req: BatchFileWriteRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    if req.parallel and len(req.files) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.files), MAX_PARALLEL)) as pool:
            for fut in as_completed({pool.submit(_write_file_safe, f.path, f.content, f.mode): f for f in req.files}):
                res = fut.result()
                results.append(res)
    else:
        for f in req.files:
            res = _write_file_safe(f.path, f.content, f.mode)
            res["id"] = f.id
            results.append(res)

    elapsed = time.monotonic() - t0
    return {"total": len(results), "elapsed_sec": round(elapsed, 3), "results": results}


# ---- SYSTEM ----

@router.get("/system/services")
def system_services(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    svcs = _get_all_octopus_services()
    return {"total": len(svcs), "services": svcs}


@router.post("/system/services/batch")
def system_services_batch(req: BatchServiceRequest, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    t0 = time.monotonic()
    results = []

    if req.parallel and len(req.services) > 1:
        with ThreadPoolExecutor(max_workers=min(len(req.services), 8)) as pool:
            for fut in as_completed({pool.submit(_service_action, s.name, s.action): s for s in req.services}):
                results.append(fut.result())
    else:
        for s in req.services:
            results.append(_service_action(s.name, s.action))

    elapsed = time.monotonic() - t0
    return {"total": len(results), "elapsed_sec": round(elapsed, 3), "results": results}


@router.get("/system/ports")
def system_ports(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    try:
        r = subprocess.run(
            ["ss", "-tlnp"], capture_output=True, text=True, timeout=10,
        )
        return {"raw": r.stdout, "error": None}
    except Exception as e:
        return {"raw": "", "error": str(e)}


# ---- GEMINI COMPAT (GET-based, returns JSON in HTML meta) ----

@router.get("/gemini/read_all_instructions")
def gemini_read_all(
    token: str,
    categories: str = "",
    x_octopus_token: str = Header(default=""),
):
    """Gemini-hack style: read all instructions via GET with token in URL."""
    if token != TOKEN and x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cats = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
    return _read_all_instructions(categories=cats)


@router.get("/gemini/run_batch")
def gemini_run_batch(
    token: str,
    cmds: str,  # semicolon-separated commands
    parallel: bool = True,
    x_octopus_token: str = Header(default=""),
):
    """Gemini-hack style: run batch commands via GET."""
    if token != TOKEN and x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    commands = [{"id": str(i), "command": cmd.strip()} for i, cmd in enumerate(cmds.split(";")) if cmd.strip()]
    t0 = time.monotonic()
    results = []
    if parallel and len(commands) > 1:
        with ThreadPoolExecutor(max_workers=min(len(commands), MAX_PARALLEL)) as pool:
            futures = {pool.submit(_run_single_cmd, c["command"]): c for c in commands}
            for fut in as_completed(futures):
                item = futures[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"stdout": "", "stderr": str(e), "returncode": 1, "timed_out": False}
                results.append({"id": item["id"], "command": item["command"], **res})
    else:
        for item in commands:
            res = _run_single_cmd(item["command"])
            results.append({"id": item["id"], "command": item["command"], **res})

    return {"total": len(results), "parallel": parallel, "elapsed_sec": round(time.monotonic() - t0, 3), "results": results}


@router.get("/gemini/walk")
def gemini_walk_hack(
    token: str,
    path: str = Query(default="."),
    pattern: str = Query(default="*"),
    max_depth: int = Query(default=5, ge=1, le=MAX_WALK_DEPTH),
    x_octopus_token: str = Header(default=""),
):
    """Gemini-hack style: walk directory via GET."""
    if token != TOKEN and x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    root = Path(path)
    if not root.is_absolute():
        root = SKILLS_BASE / path
    return _walk_dir(root, pattern=pattern, max_depth=max_depth)
