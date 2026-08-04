"""Private, owner-managed templates for CRM phone follow-up drafts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

MAX_TEMPLATES = 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read(path: Path) -> list[dict]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    except Exception:
        return []


def _write(path: Path, value: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value[-MAX_TEMPLATES:], ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


class FollowupTemplateStore:
    """Templates are private local draft material; they are never auto-sent."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.path = self.root / "data" / "android_gateway" / "followup_templates.json"

    def _items(self) -> list[dict]:
        return _read(self.path)

    def list(self) -> list[dict]:
        return [
            {"name": str(item.get("name") or ""), "created_at": str(item.get("created_at") or ""), "updated_at": str(item.get("updated_at") or "")}
            for item in self._items()
        ]

    def get(self, name: str) -> dict | None:
        key = " ".join(str(name or "").casefold().split())
        for item in self._items():
            if " ".join(str(item.get("name") or "").casefold().split()) == key:
                return dict(item)
        return None

    def upsert(self, name: str, text: str) -> dict:
        clean_name = " ".join(str(name or "").split())[:80]
        clean_text = str(text or "").strip()
        if not clean_name:
            return {"status": "error", "error": "Укажите название шаблона"}
        if not clean_text or len(clean_text) > 3500:
            return {"status": "error", "error": "Текст шаблона должен быть от 1 до 3500 символов"}
        items = self._items()
        key = clean_name.casefold()
        now = _now()
        for item in items:
            if str(item.get("name") or "").casefold() == key:
                item.update({"name": clean_name, "text": clean_text, "updated_at": now})
                _write(self.path, items)
                return {"status": "updated", "name": clean_name}
        items.append({"name": clean_name, "text": clean_text, "created_at": now, "updated_at": now})
        _write(self.path, items)
        return {"status": "created", "name": clean_name}
