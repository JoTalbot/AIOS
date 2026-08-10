#!/usr/bin/env python3
"""
AIOS Colab Farm - Управление многонодовым кластером (Этап 6)

Каждая бесплатная Colab-сессия = отдельная "нода" (свой Chrome CDP + свой
cloudflared-туннель + роль). Координатор на VPS управляет нодами через реестр.

Роли нод (статичные): llm, whisper, quant_ml, embeddings, rag, scraper.

Кластер регистрирует ноды в едином реестре (data/.colab_services.json) и
предоставляет view по нодам. Полный планировщик задач - в scheduler.py.

Использование:
    from aios_core.colab.cluster import ColabCluster
    cl = ColabCluster()
    cl.register_node("colab-node-1", role="llm", base_url="...")
    cl.list_nodes()
"""

from __future__ import annotations

import time
from typing import Optional

from .colab_registry import colab_registry


class ColabCluster:
    """Координатор нод Colab-кластера (тонкая обёртка над реестром)."""

    # роли -> типы сервисов
    ROLE_KIND = {
        "llm": "llm",
        "whisper": "whisper",
        "quant_ml": "quant_ml",
        "embeddings": "embeddings",
        "rag": "rag",
        "scraper": "scraper",
        "cluster": "cluster",
    }

    def register_node(
        self,
        node_id: str,
        role: str,
        base_url: str,
        model: Optional[str] = None,
    ) -> dict:
        """Зарегистрировать ноду с ролью. node_id уникален."""
        if role not in self.ROLE_KIND:
            raise ValueError(f"Неизвестная роль '{role}'. Доступно: {sorted(self.ROLE_KIND)}")
        kind = self.ROLE_KIND[role]
        # имя ноды: role-node_id (уникально)
        name = f"node-{node_id}-{role}"
        return colab_registry.register(
            kind=kind, base_url=base_url, model=model,
            name=name, node_id=node_id, role="static",
        )

    def unregister_node(self, node_id: str, role: str) -> bool:
        name = f"node-{node_id}-{role}"
        return colab_registry.unregister(name)

    def list_nodes(self) -> list[dict]:
        """Все зарегистрированные ноды, сгруппированные по node_id."""
        nodes: dict[str, dict] = {}
        for rec in colab_registry.all().values():
            nid = rec.get("node_id", "local")
            if nid not in nodes:
                nodes[nid] = {"node_id": nid, "services": []}
            nodes[nid]["services"].append({
                "kind": rec.get("kind"),
                "name": rec.get("name"),
                "role": rec.get("role"),
                "base_url": rec.get("base_url"),
                "status": rec.get("status"),
                "last_heartbeat": rec.get("last_heartbeat"),
            })
        return list(nodes.values())

    def healthy_node_count(self) -> int:
        """Количество нод, у которых есть хотя бы один healthy сервис."""
        nodes = {}
        for rec in colab_registry.all().values():
            if rec.get("status") == "healthy":
                nodes[rec.get("node_id")] = True
        return len(nodes)

    def summary(self) -> dict:
        return {
            "nodes": len(self.list_nodes()),
            "healthy_nodes": self.healthy_node_count(),
            "by_kind": colab_registry.count_by_kind(),
            "registry_file": str(colab_registry._file),
        }


colab_cluster = ColabCluster()


if __name__ == "__main__":
    import json
    print(json.dumps(colab_cluster.summary(), indent=2, ensure_ascii=False))
