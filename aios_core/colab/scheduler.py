#!/usr/bin/env python3
"""
AIOS Colab Farm - Планировщик задач по нодам (Этап 6)

Распределяет задачи по доступным нодам кластера. Каждая задача требует роль
(тип сервиса). Планировщик находит живую ноду нужной роли через
service_discovery и назначает задачу. Если ноды нет - задача остаётся в очереди.

Поддержка статичных ролей (по умолчанию) с заделом на динамическую очередь.

Пример задачи:
    {"task_id": "...", "role": "quant_ml", "payload": {...}, "status": "pending"}

Использование:
    from aios_core.colab.scheduler import ColabScheduler
    s = ColabScheduler()
    s.submit({"role": "scraper", "payload": {"url": "..."}})
    s.run_pending()
"""

from __future__ import annotations

import time
from typing import Optional

from .colab_registry import colab_registry
from .service_discovery import service_discovery


class ColabScheduler:
    """Планировщик задач по нодам Colab-кластера."""

    def __init__(self):
        self._queue: list[dict] = []

    # ------------------------------------------------------------- queue ----
    def submit(self, task: dict) -> str:
        """Добавить задачу в очередь. Возвращает task_id."""
        task_id = task.get("task_id") or f"task-{int(time.time())}-{len(self._queue)}"
        task.setdefault("task_id", task_id)
        task.setdefault("status", "pending")
        task.setdefault("assigned_node", None)
        self._queue.append(task)
        return task_id

    def pending(self, role: Optional[str] = None) -> list[dict]:
        return [t for t in self._queue if t.get("status") == "pending"
                and (role is None or t.get("role") == role)]

    # ------------------------------------------------------ scheduling ------
    def _find_node(self, role: str) -> Optional[dict]:
        """Найти живую ноду для роли через service_discovery."""
        kind = {
            "llm": "llm", "whisper": "whisper", "quant_ml": "quant_ml",
            "embeddings": "embeddings", "rag": "rag", "scraper": "scraper",
        }.get(role)
        if not kind:
            return None
        svc = service_discovery.resolve(kind, healthy_only=True)
        if not svc:
            return None
        return {"node_id": svc.node_id, "base_url": svc.base_url, "kind": svc.kind}

    def run_pending(self) -> dict:
        """Назначить все pending-задачи на доступные ноды."""
        stats = {"assigned": 0, "waiting": 0, "no_node": []}
        for task in self._queue:
            if task.get("status") != "pending":
                continue
            node = self._find_node(task.get("role", ""))
            if node:
                task["status"] = "running"
                task["assigned_node"] = node
                stats["assigned"] += 1
            else:
                task["status"] = "pending"
                stats["waiting"] += 1
                stats["no_node"].append(task.get("task_id"))
        return stats

    def list_tasks(self, status: Optional[str] = None) -> list[dict]:
        return [t for t in self._queue if status is None or t.get("status") == status]


colab_scheduler = ColabScheduler()


if __name__ == "__main__":
    import json
    s = ColabScheduler()
    s.submit({"role": "quant_ml", "payload": {"job": "train"}})
    s.submit({"role": "scraper", "payload": {"job": "cryptopanic"}})
    print("Задачи в очереди:", json.dumps(s.list_tasks(), ensure_ascii=False))
    print("Распределение:", json.dumps(s.run_pending(), ensure_ascii=False))
