#!/usr/bin/env python3
"""
AIOS Colab Farm - Единый реестр Colab-сервисов (ColabServiceRegistry)

Этап 1. Фундамент фермы.
Управляет CRUD-записями всех сервисов, запущенных в Google Colab, в едином
JSON-файле data/.colab_services.json. Каждый сервис = один Colab-инстанс +
свой cloudflared-туннель + свой внутренний порт.

Формат записи сервиса:
{
  "name": "quant-ml",
  "kind": "quant_ml",            # llm | whisper | quant_ml | embeddings | rag | scraper | ...
  "node_id": "colab-node-3",     # идентификатор ноды кластера
  "role": "static",              # static | worker
  "base_url": "https://abc.trycloudflare.com",
  "local_port": 8001,
  "model": "colab/qwen2.5-coder",
  "status": "healthy",           # healthy | degraded | offline
  "enabled": true,
  "registered_at": 173...,
  "last_heartbeat": 173...
}

Использование в коде AIOS:
    from aios_core.colab.colab_registry import colab_registry
    colab_registry.register(kind="quant_ml", base_url=..., model=...)
    svc = colab_registry.get(kind="llm", healthy_only=True)
"""

from __future__ import annotations

import os
import json
import time
import threading
import urllib.request
from pathlib import Path

# --- Пути (автоопределение корня репозитория) -------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]           # /root/AIOS
_env_reg = os.environ.get("AIOS_COLAB_REGISTRY", "").strip()
REGISTRY_FILE = Path(_env_reg) if _env_reg else (REPO_ROOT / "data" / ".colab_services.json")
LOG_TAG = "[ColabRegistry]"

# Допустимые типы сервисов фермы
SERVICE_KINDS = {
    # base_url хранится БЕЗ /v1 (или с /v1 — как пришло). health_path указывается
    # относительно конца base_url: для OpenAI-совместимых llm base_url обычно
    # заканчивается на /v1, поэтому health = /models.
    "llm":        {"port": 8000, "health": "/models"},
    "whisper":    {"port": 8001, "health": "/health"},
    "quant_ml":   {"port": 8002, "health": "/health"},
    "embeddings": {"port": 8003, "health": "/health"},
    "rag":        {"port": 8004, "health": "/health"},
    "scraper":    {"port": 8005, "health": "/health"},
    "cluster":    {"port": 8006, "health": "/health"},
}


def _now() -> float:
    return time.time()


class ColabServiceRegistry:
    """Потокобезопасный реестр Colab-сервисов с heartbeat."""

    def __init__(self, registry_file: Path | None = None):
        self._file = Path(registry_file or REGISTRY_FILE)
        self._lock = threading.RLock()
        self._services: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------ IO --
    def _load(self) -> None:
        if not self._file.exists():
            self._services = {}
            return
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
            self._services = data.get("services", {}) if isinstance(data, dict) else {}
        except Exception as e:
            print(f"{LOG_TAG} Не удалось прочитать реестр: {e}")
            self._services = {}

    def _save(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": _now(),
            "services": self._services,
        }
        tmp = self._file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._file)

    # --------------------------------------------------------------- CRUD ---
    def register(
        self,
        kind: str,
        base_url: str,
        model: str | None = None,
        name: str | None = None,
        node_id: str = "local",
        role: str = "static",
        api_key: str | None = None,
    ) -> dict:
        """Зарегистрировать (создать/обновить) сервис. Возвращает запись."""
        if kind not in SERVICE_KINDS:
            raise ValueError(
                f"Неизвестный тип сервиса '{kind}'. Доступно: {sorted(SERVICE_KINDS)}"
            )
        base_url = (base_url or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("base_url не может быть пустым")

        name = name or kind
        with self._lock:
            rec = self._services.get(name, {})
            rec.update({
                "name": name,
                "kind": kind,
                "node_id": node_id,
                "role": role,
                "base_url": base_url,
                "local_port": SERVICE_KINDS[kind]["port"],
                "health_path": SERVICE_KINDS[kind]["health"],
                "model": model or rec.get("model"),
                "api_key": api_key or rec.get("api_key"),
                "status": "healthy",
                "enabled": True,
                "registered_at": rec.get("registered_at", _now()),
                "last_heartbeat": _now(),
            })
            self._services[name] = rec
            self._save()
        return rec

    def unregister(self, name: str) -> bool:
        with self._lock:
            removed = self._services.pop(name, None) is not None
            if removed:
                self._save()
            return removed

    def get(self, name: str) -> dict | None:
        with self._lock:
            return dict(self._services.get(name, {}))

    def get_by_kind(
        self, kind: str, healthy_only: bool = True, enabled_only: bool = True
    ) -> list[dict]:
        """Найти все сервисы заданного типа (для load-balancing)."""
        with self._lock:
            out = []
            for rec in self._services.values():
                if rec.get("kind") != kind:
                    continue
                if enabled_only and not rec.get("enabled", True):
                    continue
                if healthy_only and rec.get("status") != "healthy":
                    continue
                out.append(dict(rec))
            return out

    def all(self) -> dict[str, dict]:
        with self._lock:
            return {k: dict(v) for k, v in self._services.items()}

    # ----------------------------------------------------------- heartbeat --
    def touch(self, name: str, status: str = "healthy") -> dict | None:
        with self._lock:
            rec = self._services.get(name)
            if not rec:
                return None
            rec["last_heartbeat"] = _now()
            rec["status"] = status
            self._save()
            return dict(rec)

    def _http_ok(self, url: str, timeout: float = 6.0) -> bool:
        """Проверить HTTP-доступность endpoint (health / models)."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS-ColabRegistry/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return 200 <= resp.status < 500
        except Exception:
            return False

    def _candidate_urls(self, rec: dict) -> list[str]:
        """Сгенерировать список кандидатов health-URL (учитывая /v1 вариации)."""
        base = rec.get("base_url", "").rstrip("/")
        hp = rec.get("health_path", "/health").lstrip("/")
        candidates = [f"{base}/{hp}"]
        # Если base уже заканчивается на /v1, а health без /v1 — уже покрыто.
        # Иначе пробуем и с /v1, и без.
        if not base.endswith("/v1"):
            candidates.append(f"{base}/v1/{hp}")
        candidates.append(f"{base}/health")
        candidates.append(f"{base}/")
        # дедупликация
        seen, out = set(), []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    def health_check(self, name: str, timeout: float = 6.0) -> dict:
        """Проверить живой ли сервис, пробуя несколько health-URL."""
        rec = self.get(name)
        if not rec:
            return {"name": name, "ok": False, "error": "not_registered"}
        ok = False
        checked_url = ""
        for url in self._candidate_urls(rec):
            if self._http_ok(url, timeout=timeout):
                ok = True
                checked_url = url
                break
            checked_url = url
        self.touch(name, status="healthy" if ok else "degraded")
        return {"name": name, "kind": rec["kind"], "ok": ok, "url": checked_url}

    def mark_offline_stale(self, stale_seconds: float = 300.0) -> int:
        """Пометить сервисы без heartbeat за N секунд как offline."""
        cutoff = _now() - stale_seconds
        changed = 0
        with self._lock:
            for rec in self._services.values():
                if rec.get("last_heartbeat", 0) < cutoff and rec.get("status") != "offline":
                    rec["status"] = "offline"
                    changed += 1
            if changed:
                self._save()
        return changed

    def count_by_kind(self) -> dict[str, int]:
        with self._lock:
            counts: dict[str, int] = {}
            for rec in self._services.values():
                k = rec.get("kind", "unknown")
                counts[k] = counts.get(k, 0) + 1
            return counts

    # -------------------------------------------------------------- export --
    def summary(self) -> dict:
        return {
            "total": len(self._services),
            "by_kind": self.count_by_kind(),
            "services": self.all(),
        }


# Единый экземпляр для всего приложения
colab_registry = ColabServiceRegistry()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="AIOS ColabServiceRegistry CLI")
    ap.add_argument("--register", nargs="+", help="kind base_url [model]")
    ap.add_argument("--unregister", metavar="NAME")
    ap.add_argument("--list", action="store_true", help="Показать все сервисы")
    ap.add_argument("--health", metavar="NAME", help="Проверить health сервиса")
    ap.add_argument("--gc", action="store_true", help="Пометить stale-сервисы как offline")
    args = ap.parse_args()

    if args.register:
        kind, base_url = args.register[0], args.register[1]
        model = args.register[2] if len(args.register) > 2 else None
        rec = colab_registry.register(kind, base_url, model=model)
        print(json.dumps(rec, indent=2, ensure_ascii=False))
    elif args.unregister:
        print("removed:", colab_registry.unregister(args.unregister))
    elif args.health:
        print(json.dumps(colab_registry.health_check(args.health), indent=2, ensure_ascii=False))
    elif args.gc:
        print("offline marked:", colab_registry.mark_offline_stale())
    else:
        print(json.dumps(colab_registry.summary(), indent=2, ensure_ascii=False))
