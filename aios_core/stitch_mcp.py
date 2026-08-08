"""
Stitch MCP client for AIOS — полный доступ к Google Stitch через MCP (JSON-RPC over HTTP).

Endpoint: https://stitch.googleapis.com/mcp
Auth:     X-Goog-Api-Key: <STITCH_API_KEY>

Инструменты (15):
  create_project, get_project, delete_project, list_projects,
  list_screens, get_screen,
  generate_screen_from_text, edit_screens, generate_variants,
  upload_design_md, create_design_system, create_design_system_from_design_md,
  update_design_system, list_design_systems, apply_design_system
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIOS.StitchMCP")


def _env(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    for env_path in ("/root/AIOS/.env", ".env"):
        p = Path(env_path)
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        if k.strip() == key:
                            return v.strip().strip('"').strip("'")
            except Exception:
                pass
    return default


class StitchMCPClient:
    """Клиент Stitch MCP (remote, stateless HTTP JSON-RPC)."""

    def __init__(self, api_key: Optional[str] = None, url: str = "https://stitch.googleapis.com/mcp") -> None:
        self.api_key = api_key or _env("STITCH_API_KEY", "")
        self.url = url or _env("STITCH_MCP_URL", "https://stitch.googleapis.com/mcp")
        if not self.api_key:
            raise ValueError("STITCH_API_KEY не задан")
        self._msg_id = 0

    # ── низкий уровень ────────────────────────────────────────────────────
    def _rpc(self, method: str, params: dict) -> Dict[str, Any]:
        self._msg_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._msg_id,
            "method": method,
            "params": params,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "X-Goog-Api-Key": self.api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            logger.error(f"Stitch MCP HTTP {e.code}: {err[:400]}")
            return {"error": {"code": e.code, "message": err[:400]}}
        except Exception as e:
            logger.error(f"Stitch MCP network error: {e}")
            return {"error": {"message": str(e)}}

        # разобрать возможный SSE: data: {...}
        if raw.startswith("data:"):
            raw = raw[5:].strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            return {"error": {"message": f"Не JSON ответ: {raw[:300]}"}}
        if "error" in parsed:
            return {"error": parsed["error"]}
        return parsed.get("result", {})

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Dict[str, Any]:
        """Вызвать MCP-инструмент; вернуть parsed content (text)."""
        res = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if "error" in res:
            return {"status": "error", "error": res["error"]}
        texts = []
        for item in res.get("content", []):
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif item.get("type") == "image":
                texts.append("[image]")
        is_error = bool(res.get("isError"))
        return {"status": "error" if is_error else "ok", "result": "\n".join(texts), "raw": res}

    def initialize(self) -> Dict[str, Any]:
        return self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "aios", "version": "1.0"},
        })

    # ── проекты ───────────────────────────────────────────────────────────
    def create_project(self, title: str) -> Dict[str, Any]:
        return self.call_tool("create_project", {"title": title})

    def list_projects(self) -> Dict[str, Any]:
        return self.call_tool("list_projects", {})

    def get_project(self, project_id: str) -> Dict[str, Any]:
        return self.call_tool("get_project", {"name": f"projects/{project_id}"})

    # ── экраны ────────────────────────────────────────────────────────────
    def list_screens(self, project_id: str) -> Dict[str, Any]:
        return self.call_tool("list_screens", {"name": f"projects/{project_id}"})

    def get_screen(self, screen_ref: str) -> Dict[str, Any]:
        return self.call_tool("get_screen", {"name": screen_ref})

    def generate_screen_from_text(self, project_id: str, prompt: str) -> Dict[str, Any]:
        """Сгенерировать новый экран из текстового промпта."""
        return self.call_tool("generate_screen_from_text", {"name": f"projects/{project_id}", "prompt": prompt})

    def edit_screens(self, project_id: str, prompt: str, screen_refs: Optional[List[str]] = None) -> Dict[str, Any]:
        """Отредактировать экраны текстовым промптом."""
        args: Dict[str, Any] = {"name": f"projects/{project_id}", "prompt": prompt}
        if screen_refs:
            args["screens"] = screen_refs
        return self.call_tool("edit_screens", args)

    def generate_variants(self, project_id: str, prompt: str, screen_ref: str) -> Dict[str, Any]:
        return self.call_tool("generate_variants", {"name": f"projects/{project_id}", "prompt": prompt, "screens": [screen_ref]})

    # ── дизайн-системы ────────────────────────────────────────────────────
    def upload_design_md(self, project_id: str, design_md: str) -> Dict[str, Any]:
        return self.call_tool("upload_design_md", {"name": f"projects/{project_id}", "designMd": design_md})

    def create_design_system(self, project_id: str) -> Dict[str, Any]:
        return self.call_tool("create_design_system", {"name": f"projects/{project_id}"})

    def create_design_system_from_design_md(self, project_id: str, design_md: str) -> Dict[str, Any]:
        return self.call_tool("create_design_system_from_design_md", {"name": f"projects/{project_id}", "designMd": design_md})

    def update_design_system(self, project_id: str, design_md: str) -> Dict[str, Any]:
        return self.call_tool("update_design_system", {"name": f"projects/{project_id}", "designMd": design_md})

    def list_design_systems(self, project_id: str) -> Dict[str, Any]:
        return self.call_tool("list_design_systems", {"name": f"projects/{project_id}"})

    def apply_design_system(self, project_id: str, design_system_id: str, screen_refs: List[str]) -> Dict[str, Any]:
        return self.call_tool("apply_design_system", {
            "name": f"projects/{project_id}",
            "designSystem": design_system_id,
            "screens": screen_refs,
        })
