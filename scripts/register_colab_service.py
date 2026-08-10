#!/usr/bin/env python3
"""
AIOS Colab Farm - Универсальный регистратор Colab-сервисов (Этап 1)

Заменяет старые register_colab_llm.py / register_colab_whisper.py единым
интерфейсом. Регистрирует любой Colab-сервис (llm, whisper, quant_ml,
embeddings, rag, scraper, cluster) в реестре data/.colab_services.json и,
при необходимости, в .env (для LLM сохраняется обратная совместимость с
LLMBalancer через COLAB_LLM_URL / COLAB_LLM_MODEL).

Использование:
    python scripts/register_colab_service.py llm https://abc.trycloudflare.com colab/qwen2.5-coder
    python scripts/register_colab_service.py quant_ml https://def.trycloudflare.com --name quant-ml --node colab-node-3
    python scripts/register_colab_service.py list
    python scripts/register_colab_service.py health <NAME>
    python scripts/register_colab_service.py remove <NAME>
"""

from __future__ import annotations

import sys
import os
import json
import argparse
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # /root/AIOS
sys.path.insert(0, str(REPO_ROOT))

from aios_core.colab.colab_registry import colab_registry, SERVICE_KINDS  # noqa: E402

ENV_FILE = REPO_ROOT / ".env"


def _env_get(name: str) -> str:
    """Прочитать переменную из .env файла."""
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _env_set(name: str, value: str) -> None:
    """Записать/заменить переменную в .env."""
    try:
        content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
        lines = content.splitlines()
        if any(l.startswith(name + "=") for l in lines):
            lines = [
                f"{name}={value}" if l.startswith(name + "=") else l for l in lines
            ]
        else:
            lines.append(f"{name}={value}")
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Не удалось обновить .env: {e}")


def cmd_register(kind: str, url: str, model: str | None, name: str | None,
                 node_id: str, role: str) -> dict:
    """Зарегистрировать сервис и применить legacy-интеграции."""
    rec = colab_registry.register(
        kind=kind,
        base_url=url,
        model=model,
        name=name,
        node_id=node_id,
        role=role,
    )
    print(f"✅ [{kind}] зарегистрирован: {rec['name']} -> {rec['base_url']}")

    # Обратная совместимость: для LLM пишем COLAB_LLM_* в .env (LLMBalancer)
    if kind == "llm":
        _env_set("COLAB_LLM_URL", rec["base_url"])
        _env_set("COLAB_LLM_MODEL", rec.get("model") or "colab/qwen2.5-coder")
        print("ℹ️  Обновлены COLAB_LLM_URL / COLAB_LLM_MODEL в .env (для LLMBalancer).")

    # Для остальных типов также пишем обобщённую переменную <KIND>_URL
    key = f"COLAB_{kind.upper()}_URL"
    if kind != "llm":
        _env_set(key, rec["base_url"])
        print(f"ℹ️  Обновлена {key} в .env.")

    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="AIOS Colab Service Register")
    sub = ap.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register", help="Зарегистрировать сервис")
    p_reg.add_argument("kind", choices=sorted(SERVICE_KINDS))
    p_reg.add_argument("url")
    p_reg.add_argument("model", nargs="?", default=None)
    p_reg.add_argument("--name", default=None)
    p_reg.add_argument("--node", default="local", help="node_id кластера")
    p_reg.add_argument("--role", default="static", choices=["static", "worker"])

    sub.add_parser("list", help="Список всех сервисов")
    sub.add_parser("summary", help="Сводка по типам")

    p_health = sub.add_parser("health", help="Проверить health сервиса")
    p_health.add_argument("name")

    p_remove = sub.add_parser("remove", help="Удалить сервис")
    p_remove.add_argument("name")

    p_gc = sub.add_parser("gc", help="Пометить stale-сервисы offline")

    args = ap.parse_args()

    if args.command == "register":
        cmd_register(args.kind, args.url, args.model, args.name, args.node, args.role)
    elif args.command == "list":
        print(json.dumps(colab_registry.summary(), indent=2, ensure_ascii=False))
    elif args.command == "summary":
        print(json.dumps(colab_registry.count_by_kind(), indent=2, ensure_ascii=False))
    elif args.command == "health":
        print(json.dumps(colab_registry.health_check(args.name), indent=2, ensure_ascii=False))
    elif args.command == "remove":
        print("removed:", colab_registry.unregister(args.name))
    elif args.command == "gc":
        print("offline marked:", colab_registry.mark_offline_stale())
    return 0


if __name__ == "__main__":
    sys.exit(main())
