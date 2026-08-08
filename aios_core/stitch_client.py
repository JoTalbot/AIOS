"""
Stitch REST client for AIOS — доступ к Google Stitch (UI design) через REST API.

Использует переменные окружения:
  STITCH_API_KEY      — API-ключ (X-Goog-Api-Key)
  STITCH_PROJECT_ID   — проект по умолчанию
  STITCH_API_URL      — базовый URL (по умолчанию https://stitch.googleapis.com)

Реализованные операции (проверены на 2026-08-08):
  - list_projects / get_project
  - list_screens / get_screen (с htmlCode.downloadUrl)
  - upload_screen (POST /v1/projects/{id}/screens:batchCreate) — HTML/Markdown/Image
  - export_screen_html — скачать HTML экрана по downloadUrl

Примечание: генерация из текста (generate_screen_from_text) доступна только через
Stitch MCP Server, в REST её нет — используйте скил upload-to-stitch для загрузки
готового HTML и доработки через MCP.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AIOS.StitchClient")


def _env(key: str, default: str = "") -> str:
    """Значение из окружения или из .env проекта (как fallback)."""
    val = os.getenv(key)
    if val:
        return val
    # попробовать прочитать .env рядом с проектом
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


class StitchClient:
    """Тонкий клиент REST API Google Stitch."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        api_url: str = "https://stitch.googleapis.com",
    ) -> None:
        self.api_key = api_key or _env("STITCH_API_KEY", "")
        self.project_id = project_id or _env("STITCH_PROJECT_ID", "")
        self.api_url = (api_url or _env("STITCH_API_URL", "https://stitch.googleapis.com")).rstrip("/")
        if not self.api_key:
            raise ValueError("STITCH_API_KEY не задан (в .env или аргументом)")

    # ── helpers ────────────────────────────────────────────────────────────
    def _headers(self, json_body: bool = False) -> Dict[str, str]:
        h = {"X-Goog-Api-Key": self.api_key}
        if json_body:
            h["Content-Type"] = "application/json"
        return h

    def _request(self, method: str, path: str, body: Optional[dict] = None, timeout: int = 120) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(json_body=body is not None), method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            logger.error(f"Stitch HTTP {e.code} {e.reason}: {err[:400]}")
            return {"error": {"code": e.code, "reason": e.reason, "body": err[:400]}}

    # ── projects ───────────────────────────────────────────────────────────
    def list_projects(self) -> List[dict]:
        """Список проектов Stitch."""
        res = self._request("GET", "/v1/projects", timeout=30)
        return res.get("projects", [])

    def get_project(self, project_id: Optional[str] = None) -> dict:
        pid = project_id or self.project_id
        if not pid:
            raise ValueError("STITCH_PROJECT_ID не задан")
        return self._request("GET", f"/v1/projects/{pid}", timeout=30)

    # ── screens ────────────────────────────────────────────────────────────
    def list_screens(self, project_id: Optional[str] = None) -> List[dict]:
        """Список экранов проекта (каждый содержит screenshot/htmlCode с downloadUrl)."""
        pid = project_id or self.project_id
        if not pid:
            raise ValueError("STITCH_PROJECT_ID не задан")
        res = self._request("GET", f"/v1/projects/{pid}/screens", timeout=30)
        return res.get("screens", [])

    def get_screen(self, screen_id: str, project_id: Optional[str] = None) -> dict:
        pid = project_id or self.project_id
        if not pid:
            raise ValueError("STITCH_PROJECT_ID не задан")
        return self._request("GET", f"/v1/projects/{pid}/screens/{screen_id}", timeout=30)

    def upload_screen(
        self,
        file_path: str | Path,
        title: Optional[str] = None,
        generated_by: Optional[str] = None,
        project_id: Optional[str] = None,
        create_instances: bool = False,
    ) -> dict:
        """Загрузить HTML/Markdown/изображение как экран (batchCreate).

        Позволяет «занести» готовый интерфейс (напр. каталог склада) в Stitch,
        после чего его можно дорабатывать в Stitch UI / через MCP.
        """
        pid = project_id or self.project_id
        if not pid:
            raise ValueError("STITCH_PROJECT_ID не задан")
        path = Path(file_path)
        if not path.exists():
            return {"error": {"message": f"Файл не найден: {path}"}}
        mime = mimetypes.guess_type(path.name)[0] or "text/html"
        b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
        if mime in ("text/html", "text/markdown"):
            screen: Dict[str, Any] = {
                "htmlCode": {"fileContentBase64": b64, "mimeType": mime},
                "screenType": "DOCUMENT",
                "isCreatedByClient": True,
            }
            screen["generatedBy"] = generated_by or ("UserUploadedDesignMd" if mime == "text/markdown" else "UserUploadedHtml")
        else:
            screen = {
                "screenshot": {"fileContentBase64": b64, "mimeType": mime},
                "screenType": "IMAGE",
                "isCreatedByClient": True,
            }
        if title:
            screen["title"] = title
        payload = {"parent": f"projects/{pid}", "requests": [{"screen": screen}], "createScreenInstances": create_instances}
        return self._request("POST", f"/v1/projects/{pid}/screens:batchCreate", payload, timeout=180)

    def export_screen_html(self, screen: dict, timeout: int = 60) -> str:
        """Скачать HTML экрана по downloadUrl из htmlCode (если есть)."""
        url = (screen.get("htmlCode") or {}).get("downloadUrl")
        if not url:
            return ""
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Не удалось скачать HTML экрана: {e}")
            return ""

    def export_screenshot(self, screen: dict, out_path: str | Path, timeout: int = 60) -> bool:
        """Скачать скриншот экрана в файл."""
        url = (screen.get("screenshot") or {}).get("downloadUrl")
        if not url:
            return False
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                Path(out_path).write_bytes(resp.read())
            return True
        except Exception as e:
            logger.error(f"Не удалось скачать скриншот: {e}")
            return False
