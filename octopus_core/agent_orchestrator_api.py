#!/usr/bin/env python3
"""
Multi-Agent Orchestr API for Octopus.

Allows multiple AI agents (any model) to:
1. Register with capabilities
2. Submit task batches
3. Share experience
4. Deduplicate overlapping tasks
5. Execute optimized merged streams

Architecture:
  Agents (N) → Agent Registry → Task Queue → Deduplicator → Orchestrator → Batch API
                    ↕                                    ↕
             Shared Experience                    Competition Engine
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN = os.getenv("OCTOPUS_TOKEN", "default")
STATE_DIR = Path(
    os.getenv("OCTOPUS_ORCHESTRATOR_STATE_DIR", "/root/agents/-Octopus/data/agent_orchestrator")
)
EXPERIENCE_POOL = Path(os.getenv("OCTOPUS_EXPERIENCE_DIR", "/root/agents/-Octopus/experience"))
MAX_PARALLEL = int(os.getenv("OCTOPUS_BATCH_MAX_PARALLEL", "64"))

router = APIRouter(prefix="/api/v3/orchestrator", tags=["multi-agent"])

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def _check_token(x_octopus_token: str = Header(default="")):
    if x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class AgentRegistration(BaseModel):
    agent_id: str = Field(default="", description="Unique agent ID (auto-generated if empty)")
    model: str = Field(..., description="AI model name (e.g. claude-3.5, gpt-4, gemini-pro)")
    project: str = Field(default="octopus", description="Target project")
    capabilities: List[str] = Field(default_factory=list)
    max_parallel: int = Field(default=64, ge=1, le=256)
    priority: int = Field(default=5, ge=1, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # OpenHands-контур (план F4); все поля optional — обратная совместимость.
    role: str = Field(default="", description="Contour role (architect/coder/tester/...)")
    permissions: List[str] = Field(default_factory=list, description="RBAC permission strings")
    allowed_paths: List[str] = Field(default_factory=list, description="Writable path globs")
    memory_scope: str = Field(default="", description="Memory scope (project/orchestration)")
    parent_agent: str = Field(default="", description="Parent agent ID")
    current_task: str = Field(default="", description="Current task ID")

class AgentStatus(BaseModel):
    agent_id: str
    model: str
    project: str
    registered_at: str
    last_heartbeat: float
    tasks_submitted: int
    tasks_completed: int
    experience_shared: int
    status: str = "active"
    role: str = ""
    parent_agent: str = ""
    current_task: str = ""

class TaskSubmission(BaseModel):
    agent_id: str
    batch_id: str = Field(default="", description="Batch group ID")
    commands: List[Dict[str, Any]] = Field(..., min_length=1, max_length=256)
    priority: int = Field(default=5, ge=1, le=10)
    idempotency_key: str = Field(default="", description="Dedup key")
    tags: List[str] = Field(default_factory=list)
    allow_merge: bool = Field(default=True, description="Allow merging with similar tasks from other agents")
    competition_mode: bool = Field(default=False, description="Run separately for comparison")

class ExperienceShare(BaseModel):
    agent_id: str
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    vector: str = Field(default="learn", description="Which vector this relates to")

class OrchestratorStatus(BaseModel):
    agents: int
    pending_tasks: int
    active_streams: int
    dedup_hits: int
    total_executed: int
    experience_pool_size: int

# ---------------------------------------------------------------------------
# State Management (JSON files for simplicity, can migrate to SQLite)
# ---------------------------------------------------------------------------
def _state_path(name: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{name}.json"

def _load_state(name: str, default=None):
    p = _state_path(name)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return default or {}
    return default or {}

def _save_state(name: str, data):
    p = _state_path(name)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _cmd_fingerprint(cmd: str) -> str:
    """Stable fingerprint for command deduplication."""
    normalized = " ".join(cmd.strip().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def _batch_fingerprint(commands: List[Dict]) -> str:
    """Fingerprint for an entire batch of commands."""
    fps = sorted(_cmd_fingerprint(c.get("command", "")) for c in commands)
    return hashlib.sha256("|".join(fps).encode()).hexdigest()[:16]

# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------
@router.post("/agents/register")
def register_agent(req: AgentRegistration, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    agents = _load_state("agents", {})
    
    agent_id = req.agent_id or f"agent_{uuid.uuid4().hex[:12]}"
    
    agents[agent_id] = {
        "agent_id": agent_id,
        "model": req.model,
        "project": req.project,
        "capabilities": req.capabilities,
        "max_parallel": req.max_parallel,
        "priority": req.priority,
        "metadata": req.metadata,
        "role": req.role,
        "permissions": req.permissions,
        "allowed_paths": req.allowed_paths,
        "memory_scope": req.memory_scope,
        "parent_agent": req.parent_agent,
        "current_task": req.current_task,
        "registered_at": _utc_now(),
        "last_heartbeat": time.time(),
        "tasks_submitted": 0,
        "tasks_completed": 0,
        "experience_shared": 0,
        "status": "active",
    }
    _save_state("agents", agents)
    
    return {
        "ok": True,
        "agent_id": agent_id,
        "message": f"Agent {agent_id} registered (model: {req.model}, project: {req.project})",
        "orchestrator_endpoints": {
            "submit_tasks": f"/api/v3/orchestrator/tasks/submit",
            "share_experience": f"/api/v3/orchestrator/experience/share",
            "get_status": f"/api/v3/orchestrator/status",
            "list_agents": f"/api/v3/orchestrator/agents",
        },
    }

@router.get("/agents")
def list_agents(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    agents = _load_state("agents", {})
    return {"agents": list(agents.values()), "total": len(agents)}

@router.post("/agents/{agent_id}/heartbeat")
def agent_heartbeat(agent_id: str, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    agents = _load_state("agents", {})
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    agents[agent_id]["last_heartbeat"] = time.time()
    agents[agent_id]["status"] = "active"
    _save_state("agents", agents)
    return {"ok": True, "agent_id": agent_id}

# ---------------------------------------------------------------------------
# Task Submission with Deduplication
# ---------------------------------------------------------------------------
@router.post("/tasks/submit")
def submit_tasks(req: TaskSubmission, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    
    agents = _load_state("agents", {})
    if req.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not registered. Call /agents/register first.")
    
    queue = _load_state("task_queue", {"pending": [], "active": [], "completed": [], "dedup_log": {}})
    stats = _load_state("orchestrator_stats", {"dedup_hits": 0, "total_executed": 0, "streams_created": 0})
    
    batch_id = req.batch_id or f"batch_{uuid.uuid4().hex[:8]}"
    batch_fp = _batch_fingerprint(req.commands)
    
    # --- Deduplication ---
    dedup_result = "new"
    existing_batch = None
    
    if req.allow_merge and not req.competition_mode:
        # Check idempotency key
        if req.idempotency_key and req.idempotency_key in queue.get("dedup_log", {}):
            dedup_result = "duplicate_idempotency"
            existing_batch = queue["dedup_log"][req.idempotency_key]
        # Check batch fingerprint
        elif batch_fp in queue.get("dedup_log", {}):
            dedup_result = "duplicate_fingerprint"
            existing_batch = queue["dedup_log"][batch_fp]
        # Check individual command dedup
        else:
            pending_fps = set()
            for task in queue.get("pending", []):
                for cmd in task.get("commands", []):
                    pending_fps.add(_cmd_fingerprint(cmd.get("command", "")))
            
            unique_cmds = []
            deduped_cmds = []
            for cmd in req.commands:
                fp = _cmd_fingerprint(cmd.get("command", ""))
                if fp not in pending_fps:
                    unique_cmds.append(cmd)
                else:
                    deduped_cmds.append(cmd)
            
            if deduped_cmds:
                stats["dedup_hits"] += len(deduped_cmds)
                dedup_result = f"partial_dedup ({len(unique_cmds)} unique, {len(deduped_cmds)} deduped)"
            
            req.commands = unique_cmds if unique_cmds else req.commands
    
    if dedup_result.startswith("duplicate") and existing_batch:
        return {
            "ok": True,
            "status": "deduplicated",
            "batch_id": batch_id,
            "dedup_result": dedup_result,
            "existing_batch": existing_batch,
            "message": "This task batch is identical to an existing one. Merged into existing stream.",
        }
    
    # --- Create task entry ---
    task_entry = {
        "batch_id": batch_id,
        "agent_id": req.agent_id,
        "model": agents[req.agent_id]["model"],
        "project": agents[req.agent_id]["project"],
        "commands": req.commands,
        "priority": req.priority,
        "tags": req.tags,
        "allow_merge": req.allow_merge,
        "competition_mode": req.competition_mode,
        "submitted_at": _utc_now(),
        "fingerprint": batch_fp,
        "command_count": len(req.commands),
    }
    
    queue["pending"].append(task_entry)
    queue.setdefault("dedup_log", {})[batch_fp] = batch_id
    if req.idempotency_key:
        queue["dedup_log"][req.idempotency_key] = batch_id
    
    # Update agent stats
    agents[req.agent_id]["tasks_submitted"] += 1
    
    _save_state("task_queue", queue)
    _save_state("agents", agents)
    _save_state("orchestrator_stats", stats)
    
    return {
        "ok": True,
        "batch_id": batch_id,
        "dedup_result": dedup_result,
        "commands_queued": len(req.commands),
        "total_pending": len(queue["pending"]),
        "message": f"Tasks queued. {len(queue['pending'])} batches pending.",
    }

# ---------------------------------------------------------------------------
# Smart Orchestrator — merge, prioritize, execute
# ---------------------------------------------------------------------------
@router.post("/orchestrate")
def orchestrate(x_octopus_token: str = Header(default=""), max_batches: int = Query(default=10, ge=1, le=100)):
    """Execute pending tasks with smart merging and prioritization."""
    _check_token(x_octopus_token)
    
    queue = _load_state("task_queue", {"pending": [], "active": [], "completed": [], "dedup_log": {}})
    stats = _load_state("orchestrator_stats", {"dedup_hits": 0, "total_executed": 0, "streams_created": 0})
    
    if not queue["pending"]:
        return {"ok": True, "message": "No pending tasks", "executed": 0}
    
    # Sort by priority (higher first) then by submission time
    pending = sorted(queue["pending"], key=lambda t: (-t["priority"], t["submitted_at"]))
    
    # --- Merge compatible batches ---
    streams = []
    used = set()
    
    for i, task in enumerate(pending):
        if i in used:
            continue
        
        if task.get("competition_mode"):
            streams.append([task])
            used.add(i)
            continue
        
        stream = [task]
        used.add(i)
        
        if not task.get("allow_merge"):
            continue
        
        # Try to merge with other compatible tasks
        stream_cmds = {_cmd_fingerprint(c.get("command", "")) for t in stream for c in t["commands"]}
        
        for j in range(i + 1, len(pending)):
            if j in used:
                continue
            other = pending[j]
            if not other.get("allow_merge") or other.get("competition_mode"):
                continue
            if other.get("project") != task.get("project"):
                continue
            
            # Check overlap — if >50% commands overlap, merge
            other_fps = {_cmd_fingerprint(c.get("command", "")) for c in other["commands"]}
            overlap = len(stream_cmds & other_fps)
            total = len(stream_cmds | other_fps)
            
            if total > 0 and overlap / total > 0.3:
                # Merge: add only unique commands
                for cmd in other["commands"]:
                    fp = _cmd_fingerprint(cmd.get("command", ""))
                    if fp not in stream_cmds:
                        stream[0]["commands"].append(cmd)
                        stream_cmds.add(fp)
                
                stream.append(other)
                used.add(j)
                stats["dedup_hits"] += overlap
        
        streams.append(stream)
    
    # Limit streams
    streams = streams[:max_batches]
    
    # --- Execute streams via Batch API ---
    import urllib.request
    API_URL = "http://localhost:8080/api/v2/batch/execute"
    
    results = []
    t0 = time.monotonic()
    
    def execute_stream(stream_tasks):
        """Execute one merged stream."""
        all_cmds = []
        agent_ids = set()
        for t in stream_tasks:
            agent_ids.add(t["agent_id"])
            for c in t["commands"]:
                all_cmds.append(c)
        
        # Deduplicate within stream
        seen = set()
        unique_cmds = []
        for c in all_cmds:
            fp = _cmd_fingerprint(c.get("command", ""))
            if fp not in seen:
                unique_cmds.append(c)
                seen.add(fp)
        
        # Limit to MAX_PARALLEL
        unique_cmds = unique_cmds[:MAX_PARALLEL]
        
        payload = json.dumps({"parallel": True, "commands": unique_cmds}).encode()
        req = urllib.request.Request(
            API_URL, data=payload,
            headers={"Content-Type": "application/json", "X-Octopus-Token": TOKEN},
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.loads(resp.read())
                return {
                    "agents": list(agent_ids),
                    "commands_sent": len(unique_cmds),
                    "commands_merged": len(all_cmds) - len(unique_cmds),
                    "result": data,
                }
        except Exception as e:
            return {"agents": list(agent_ids), "error": str(e)}
    
    # Execute streams in parallel (streams themselves are parallel!)
    with ThreadPoolExecutor(max_workers=min(len(streams), 8)) as pool:
        futures = {pool.submit(execute_stream, s): i for i, s in enumerate(streams)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                result = fut.result()
                results.append({"stream": idx, **result})
            except Exception as e:
                results.append({"stream": idx, "error": str(e)})
    
    elapsed = time.monotonic() - t0
    
    # --- Update state ---
    executed_indices = set()
    for i, task in enumerate(pending):
        for stream in streams:
            if task in stream:
                executed_indices.add(i)
    
    # Move executed tasks to completed
    new_pending = []
    for i, task in enumerate(pending):
        if i not in executed_indices:
            new_pending.append(task)
        else:
            task["completed_at"] = _utc_now()
            queue["completed"].append(task)
    
    queue["pending"] = new_pending
    stats["streams_created"] += len(streams)
    stats["total_executed"] += sum(r.get("commands_sent", 0) for r in results)
    
    _save_state("task_queue", queue)
    _save_state("orchestrator_stats", stats)
    
    return {
        "ok": True,
        "streams_executed": len(streams),
        "batches_merged": sum(len(s) - 1 for s in streams),
        "total_commands": sum(r.get("commands_sent", 0) for r in results),
        "commands_deduped": sum(r.get("commands_merged", 0) for r in results),
        "elapsed_sec": round(elapsed, 2),
        "results": results,
        "remaining_pending": len(queue["pending"]),
    }

# ---------------------------------------------------------------------------
# Shared Experience Pool
# ---------------------------------------------------------------------------
@router.post("/experience/share")
def share_experience(req: ExperienceShare, x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    
    agents = _load_state("agents", {})
    if req.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not registered")
    
    # Save to experience pool
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{ts}_experience_{req.vector}_{req.agent_id}_{uuid.uuid4().hex[:8]}.md"
    filepath = EXPERIENCE_POOL / filename
    
    content = f"""# Experience: {req.title}

**Agent:** {req.agent_id} ({agents[req.agent_id]['model']})
**Vector:** {req.vector}
**Tags:** {', '.join(req.tags)}
**Date:** {_utc_now()}

{req.content}
"""
    filepath.write_text(content, encoding="utf-8")
    
    agents[req.agent_id]["experience_shared"] += 1
    _save_state("agents", agents)
    
    return {
        "ok": True,
        "file": str(filepath),
        "message": f"Experience shared: {filename}",
    }

@router.get("/experience/search")
def search_experience(
    query: str = Query(..., description="Search query"),
    vector: str = Query(default="", description="Filter by vector"),
    limit: int = Query(default=10, ge=1, le=50),
    x_octopus_token: str = Header(default=""),
):
    _check_token(x_octopus_token)
    
    results = []
    for f in sorted(EXPERIENCE_POOL.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        if len(results) >= limit:
            break
        content = f.read_text(encoding="utf-8", errors="replace")
        if query.lower() in content.lower():
            if vector and vector.lower() not in content.lower():
                continue
            results.append({
                "file": f.name,
                "size": f.stat().st_size,
                "preview": content[:500],
            })
    
    return {"results": results, "total": len(results), "query": query}

# ---------------------------------------------------------------------------
# Status & Monitoring
# ---------------------------------------------------------------------------
@router.get("/status")
def get_status(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    
    agents = _load_state("agents", {})
    queue = _load_state("task_queue", {"pending": [], "active": [], "completed": [], "dedup_log": {}})
    stats = _load_state("orchestrator_stats", {"dedup_hits": 0, "total_executed": 0, "streams_created": 0})
    exp_count = len(list(EXPERIENCE_POOL.glob("*.md")))
    
    return {
        "agents_registered": len(agents),
        "agents_active": sum(1 for a in agents.values() if a.get("status") == "active"),
        "pending_batches": len(queue.get("pending", [])),
        "completed_batches": len(queue.get("completed", [])),
        "dedup_hits": stats.get("dedup_hits", 0),
        "total_executed": stats.get("total_executed", 0),
        "streams_created": stats.get("streams_created", 0),
        "experience_pool": exp_count,
        "models": list(set(a["model"] for a in agents.values())),
        "projects": list(set(a["project"] for a in agents.values())),
    }

@router.post("/reset")
def reset_orchestrator(x_octopus_token: str = Header(default="")):
    _check_token(x_octopus_token)
    _save_state("task_queue", {"pending": [], "active": [], "completed": [], "dedup_log": {}})
    _save_state("orchestrator_stats", {"dedup_hits": 0, "total_executed": 0, "streams_created": 0})
    return {"ok": True, "message": "Orchestrator state reset (agents preserved)"}

