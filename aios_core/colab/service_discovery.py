#!/usr/bin/env python3
"""
AIOS Colab Farm - Service Discovery

Позволяет любому модулю AIOS находить живой Colab-сервис нужного типа
(LLM, Whisper, Quant-ML, Embeddings, RAG, Scraper) с поддержкой
load-balancing/round-robin по нескольким нодам и fallback.

Пример:
    from aios_core.colab.service_discovery import ServiceDiscovery
    svc = ServiceDiscovery().resolve("llm")        # {"base_url": ..., ...}
    url = svc["base_url"] + "/v1/chat/completions"
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .colab_registry import colab_registry


@dataclass
class ResolvedService:
    name: str
    kind: str
    base_url: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    node_id: str = "local"
    local_port: int = 8000
    health_path: str = "/health"
    _rr: int = 0  # round-robin индекс


class ServiceDiscovery:
    """Поиск и балансировка Colab-сервисов."""

    def __init__(self, registry=None):
        self._registry = registry or colab_registry
        # внутренний RR-счётчик по kind для чередования нод
        self._rr: dict[str, int] = {}

    def resolve(
        self,
        kind: str,
        healthy_only: bool = True,
        prefer_node: Optional[str] = None,
    ) -> Optional[ResolvedService]:
        """Вернуть первый/следующий живой сервис заданного типа."""
        services = self._registry.get_by_kind(kind, healthy_only=healthy_only)
        if not services:
            return None

        if prefer_node:
            for s in services:
                if s.get("node_id") == prefer_node:
                    return self._to_resolved(s, kind)

        # round-robin
        idx = self._rr.get(kind, 0) % len(services)
        self._rr[kind] = idx + 1
        return self._to_resolved(services[idx], kind)

    def resolve_all(self, kind: str, healthy_only: bool = True) -> list[ResolvedService]:
        """Вернуть все живые сервисы типа (для отказоустойчивости)."""
        return [
            self._to_resolved(s, kind)
            for s in self._registry.get_by_kind(kind, healthy_only=healthy_only)
        ]

    def _to_resolved(self, rec: dict, kind: str) -> ResolvedService:
        return ResolvedService(
            name=rec.get("name", kind),
            kind=kind,
            base_url=rec["base_url"],
            model=rec.get("model"),
            api_key=rec.get("api_key"),
            node_id=rec.get("node_id", "local"),
            local_port=rec.get("local_port", 8000),
            health_path=rec.get("health_path", "/health"),
        )

    def all_available(self) -> dict[str, list[ResolvedService]]:
        out: dict[str, list[ResolvedService]] = {}
        for kind in sorted({s["kind"] for s in self._registry.all().values()}):
            r = self.resolve_all(kind)
            if r:
                out[kind] = r
        return out


# Singleton
service_discovery = ServiceDiscovery()


if __name__ == "__main__":
    import json
    sd = ServiceDiscovery()
    print(json.dumps({k: [vars(r) for r in v] for k, v in sd.all_available().items()},
                     indent=2, ensure_ascii=False))
