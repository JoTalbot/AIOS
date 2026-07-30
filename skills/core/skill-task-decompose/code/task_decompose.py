#!/usr/bin/env python3
"""Task Decompose Skill — декомпозиция задач с приоритизацией"""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

VECTORS_PRIORITY = {
    "memory": 8,      # ПАМЯТЬ — самый высокий
    "live": 7,        # ЖИТЬ
    "simplify": 6,    # УПРОЩЕНИЕ
    "coexist": 5,     # СОСУЩЕСТВОВАНИЕ
    "reproduce": 4,   # РАЗМНОЖАТЬСЯ
    "develop": 3,     # РАЗВИВАТЬСЯ
    "learn": 2,       # УЧИТЬСЯ
    "change": 1       # МЕНЯТЬСЯ
}

TASK_TEMPLATES = {
    "health_fix": {
        "vector": "live",
        "steps": [
            "Определить проблему (SLO/disk/service)",
            "Найти root cause",
            "Применить исправление",
            "Проверить результат (health check)",
            "Зафиксировать в experience"
        ],
        "estimated_minutes": 15,
        "risk": "low"
    },
    "skill_implement": {
        "vector": "develop",
        "steps": [
            "Определить требования к скиллу",
            "Создать SKILL.md с описанием",
            "Написать код в code/",
            "Написать тесты в tests/",
            "Протестировать",
            "Обновить индекс"
        ],
        "estimated_minutes": 30,
        "risk": "medium"
    },
    "memory_check": {
        "vector": "memory",
        "steps": [
            "Запустить pack-read-guard",
            "Проверить coverage",
            "Проверить репликацию",
            "Проверить offline snapshot",
            "Записать результаты"
        ],
        "estimated_minutes": 10,
        "risk": "low"
    },
    "scale_free": {
        "vector": "reproduce",
        "steps": [
            "Определить доступные бесплатные ресурсы",
            "Подготовить конфигурацию ноды",
            "Развернуть ноду",
            "Подключить к рою",
            "Проверить синхронизацию"
        ],
        "estimated_minutes": 20,
        "risk": "medium"
    },
    "cleanup": {
        "vector": "simplify",
        "steps": [
            "Найти мёртвый код/заглушки",
            "Подготовить список удаления",
            "Удалить (с backup)",
            "Проверить что ничего не сломалось",
            "Обновить документацию"
        ],
        "estimated_minutes": 15,
        "risk": "low"
    },
    "experience_learn": {
        "vector": "learn",
        "steps": [
            "Собрать логи итераций",
            "Проанализировать ошибки",
            "Извлечь уроки",
            "Записать в experience/",
            "Обновить COMPACT_CONTEXT"
        ],
        "estimated_minutes": 10,
        "risk": "low"
    }
}

def classify_task(description):
    """Классифицирует задачу по типу и вектору"""
    desc = description.lower()
    if any(w in desc for w in ["health", "slo", "fix", "broken", "fail", "restart"]):
        return "health_fix"
    if any(w in desc for w in ["skill", "implement", "create skill", "new skill"]):
        return "skill_implement"
    if any(w in desc for w in ["memory", "backup", "replica", "durability", "pack"]):
        return "memory_check"
    if any(w in desc for w in ["scale", "node", "reproduce", "new server", "deploy"]):
        return "scale_free"
    if any(w in desc for w in ["clean", "remove", "delete", "stub", "dead code"]):
        return "cleanup"
    if any(w in desc for w in ["learn", "experience", "analyze", "improve"]):
        return "experience_learn"
    return "health_fix"  # default safe choice

def decompose(task_description, context=None):
    """Декомпозирует задачу на подзадачи"""
    task_type = classify_task(task_description)
    template = TASK_TEMPLATES[task_type]
    vector = template["vector"]
    priority = VECTORS_PRIORITY[vector]

    steps = []
    for i, step in enumerate(template["steps"]):
        steps.append({
            "id": f"step_{i+1}",
            "description": step,
            "status": "pending",
            "depends_on": f"step_{i}" if i > 0 else None
        })

    plan = {
        "task": task_description,
        "type": task_type,
        "vector": vector,
        "vector_priority": priority,
        "steps": steps,
        "estimated_minutes": template["estimated_minutes"],
        "risk": template["risk"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if context:
        plan["context"] = context

    return plan

def get_next_task_from_todo():
    """Получает следующую задачу из MASTER_TODO"""
    todo_path = Path(os.path.expanduser("~/agents/-Octopus/instructions/MASTER_TODO_2026-06-19.md"))
    if not todo_path.exists():
        return None

    content = todo_path.read_text(encoding="utf-8", errors="replace")
    # Ищем незавершённые пункты
    unchecked = re.findall(r"- \[ \] (.+)", content)
    if unchecked:
        return unchecked[0]
    return None

if __name__ == "__main__":
    import sys
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Fix health issues and implement new skills"
    plan = decompose(task)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
