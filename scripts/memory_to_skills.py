#!/usr/bin/env python3
"""Memory→Skills майнер (п.9 плана): повторяющиеся ошибки автокодера -> SKILL.md.

Читает data/autocoder_v3_memory.json (failed_attempts), кластеризует по
нормализованной причине ошибки; кластеры с >= MIN_OCC повторов превращаются
в skills/coder/auto-lesson-<slug>/SKILL.md со статистикой и рекомендациями.
Скиллы сразу видны планировщику (list_skills) и генератору (skill_bodies_for).

Использование: memory_to_skills.py [--dry-run]
Перидичность: aios-memory-skills.timer (еженедельно).
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

REPO = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
MEMORY = os.path.join(REPO, "data", "autocoder_v3_memory.json")
OUT_DIR = os.path.join(REPO, "skills", "coder")
MIN_OCC = int(os.environ.get("AIOS_LESSON_MIN_OCC", "3"))
MAX_LESSONS = 10

_GUIDANCE = {
    "search": "Перед SEARCH-блоком перечитай присланный фрагмент файла и копируй "
              "его посимвольно; уменьши блок до 1-10 строк (см. skills/coder/diff-edit-contract).",
    "syntax": "Сгенерированный код синтаксически невалиден. Проведи мысленный "
              "py_compile: сбалансированы скобки/кавычки, нет обрезанных строк. "
              "Для pydantic — см. skills/coder/pydantic-v2.",
    "import": "Правка ломает импорт. Не удаляй публичные имена модуля; "
              "проверяй `python -c 'import <модуль>'`.",
    "empty": "Пустой/тривиальный ответ. Дай полноценную реализацию вместо pass.",
    "protected": "Задача целится в protected-файл — пропускай такие задачи "
                 "(см. skills/coder/aios-self-protection).",
}


def normalize(err: str) -> str:
    e = (err or "unknown").lower()
    e = re.sub(r"aios_core/[\w./]+", "<file>", e)
    e = re.sub(r"\d+", "<n>", e)
    e = re.sub(r"\s+", " ", e).strip()
    return e[:90]


def bucket(key: str) -> str:
    if "search" in key:
        return "search"
    if "syntax" in key or "indent" in key:
        return "syntax"
    if "import" in key:
        return "import"
    if "empty" in key or "nothing" in key:
        return "empty"
    if "protected" in key or "self-protection" in key:
        return "protected"
    return "misc"


def slugify(key: str) -> str:
    s = re.sub(r"[^a-zа-яё0-9]+", "-", key.lower())[:48].strip("-")
    return s or "misc"


def main() -> int:
    dry = "--dry-run" in sys.argv
    try:
        data = json.load(open(MEMORY, encoding="utf-8"))
    except Exception as e:
        print(f"memory unreadable: {e}")
        return 1
    fails = data.get("failed_attempts", [])
    clusters: dict[str, list[dict]] = defaultdict(list)
    for f in fails:
        clusters[normalize(f.get("error", ""))].append(f)

    candidates = sorted(((k, v) for k, v in clusters.items() if len(v) >= MIN_OCC),
                        key=lambda kv: -len(kv[1]))[:MAX_LESSONS]
    if not candidates:
        print(f"кластеров с >= {MIN_OCC} повторами нет (всего ошибок: {len(fails)})")
        return 0

    written = 0
    for key, items in candidates:
        b = bucket(key)
        slug = slugify(key)
        name = f"auto-lesson-{slug}"
        files = Counter(x.get("file", "?") for x in items)
        top_files = ", ".join(f"{f} ({c})" for f, c in files.most_common(3))
        guidance = _GUIDANCE.get(b, "Разбери примеры ниже; избегай повторения причины.")
        md = f"""---
name: {name}
description: "Урок из {len(items)} повторяющихся ошибок автокодера: {key[:150]}"
---

# Auto-lesson: {key[:80]}

Этот навык сгенерирован автоматически (scripts/memory_to_skills.py, {datetime.now(timezone.utc).date()}),
кластер: **{len(items)}** повторяющихся отказов с одной причины.

## Причина (нормализованная)

`{key}`

## Где повторялось

{top_files}

## Рекомендация

{guidance}

## Последние примеры

"""
        for x in items[-3:]:
            md += f"- `{x.get('file', '?')}`: {str(x.get('error', ''))[:160]}\n"
        dest = os.path.join(OUT_DIR, name, "SKILL.md")
        if dry:
            print(f"[dry] {name}: {len(items)} occ ({b})")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(md)
        written += 1
        print(f"✍ {name}: {len(items)} повторов ({b})")
    if not dry:
        print(f"Готово: {written} навыков в skills/coder/ (видны планировщику со следующего цикла)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
