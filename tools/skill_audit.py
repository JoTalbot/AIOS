#!/usr/bin/env python3
"""Глубокий аудит скиллов Octopus. Read-only: ничего не меняет, только классифицирует.

Критерии классификации:
- algorithm: 'unique' (связан с назначением) / 'template' (7-строчный универсальный шаблон) / 'missing'
- code_size: строки code/run.py (или альтернативы)
- test_size: строки тестов
- references: кол-во файлов в references/
- substance_score: взвешенная оценка реальной наполненности
- tier: REAL / HYBRID / SCAFFOLD (каркас)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SKILLS_BASE = Path("/mnt/agents/-Octopus/skills")
CATEGORIES = ["core", "dr", "mcp", "memory", "meta", "research", "swarm"]

# Сигнатуры шаблонного алгоритма (универсальный каркасный текст)
TEMPLATE_MARKERS = [
    "Классифицировать навык по тегам (health/api/memory",
    "generic_skill_runtime",
    "выполнить только безопасные read-only проверки",
]


def detect_algorithm_kind(body: str) -> str:
    """Определить, уникальный ли алгоритм или шаблонный."""
    if not re.search(r"##\s*Алгоритм", body, re.I):
        return "missing"
    # Извлечём блок алгоритма
    m = re.search(r"##\s*Алгоритм\s*\n(.*?)(?=\n##\s|\Z)", body, re.S | re.I)
    if not m:
        return "missing"
    block = m.group(1)
    for marker in TEMPLATE_MARKERS:
        if marker.lower() in block.lower():
            return "template"
    return "unique"


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        return sum(1 for _ in path.read_text(encoding="utf-8", errors="replace").splitlines())
    except Exception:
        return 0


def find_code_file(skill_dir: Path) -> tuple[str, int]:
    """Найти основной исполняемый файл скилла и его размер (только run.py)."""
    candidates = [
        skill_dir / "code" / "run.py",
        skill_dir / "code.py",
        skill_dir / "code" / "main.py",
        skill_dir / "code" / "skill.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c.relative_to(skill_dir)), count_lines(c)
    code_dir = skill_dir / "code"
    if code_dir.exists():
        pys = sorted([p for p in code_dir.iterdir() if p.suffix == ".py" and p.name != "__init__.py"])
        if pys:
            return str(pys[0].relative_to(skill_dir)), count_lines(pys[0])
    return "", 0


def total_real_code_lines(skill_dir: Path) -> tuple[int, int, int]:
    """Суммарный объём .py в code/ МИНУС .bak/__pycache__. -> (total_lines, real_files, bak_files)."""
    code_dir = skill_dir / "code"
    if not code_dir.exists():
        return 0, 0, 0
    total = 0
    real_files = 0
    bak_files = 0
    for p in code_dir.rglob("*"):
        if p.is_dir():
            continue
        if "__pycache__" in str(p):
            continue
        if p.suffix != ".py":
            continue
        if ".bak" in p.name:
            bak_files += 1
            continue
        real_files += 1
        total += count_lines(p)
    return total, real_files, bak_files


def find_test_info(skill_dir: Path) -> tuple[int, int]:
    """Вернуть (кол-во строк тестов, кол-во функций test_)."""
    test_dir = skill_dir / "tests"
    total_lines = 0
    test_fns = 0
    if not test_dir.exists():
        return 0, 0
    for p in test_dir.rglob("*.py"):
        total_lines += count_lines(p)
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
            test_fns += len(re.findall(r"^\s*def test_", txt, re.M))
        except Exception:
            pass
    return total_lines, test_fns


def count_references(skill_dir: Path) -> int:
    ref_dir = skill_dir / "references"
    if not ref_dir.exists():
        return 0
    return len([p for p in ref_dir.iterdir() if p.is_file()])


def substance_tier(alg_kind, code_lines, test_lines, test_fns, refs, real_code_total, bak_files):
    """Эвристическая классификация наполненности.

    REAL: уникальный алгоритм + нетривиальный код + тесты.
    HYBRID: что-то реальное есть, но неполно.
    SCAFFOLD: шаблонный каркас (только тонкий run.py-обёртка).
    Код оцениваем по РЕАЛЬНОМУ объёму (все .py минус .bak), а не по обёртке run.py.
    """
    score = 0
    if alg_kind == "unique":
        score += 40
    # код: учитываем реальный суммарный объём
    effective_code = max(code_lines, real_code_total)
    if real_code_total >= 100:
        score += 30
    elif real_code_total >= 40:
        score += 20
    elif real_code_total >= 20:
        score += 12
    if test_fns >= 3 and test_lines >= 30:
        score += 20
    elif test_fns >= 1:
        score += 8
    if refs >= 2:
        score += 10

    if alg_kind == "template" and real_code_total <= 12:
        return "SCAFFOLD", score
    if score >= 70:
        return "REAL", score
    if score >= 35:
        return "HYBRID", score
    return "SCAFFOLD", score


def main():
    skills = []
    for cat in CATEGORIES:
        cat_path = SKILLS_BASE / cat
        if not cat_path.exists():
            continue
        for d in sorted(cat_path.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            skill_md = d / "SKILL.md"
            if not skill_md.exists():
                continue
            content = skill_md.read_text(encoding="utf-8", errors="replace")
            # отделить frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.S)
            body = fm_match.group(2) if fm_match else content

            alg_kind = detect_algorithm_kind(body)
            code_rel, code_lines = find_code_file(d)
            real_code_total, real_files, bak_files = total_real_code_lines(d)
            test_lines, test_fns = find_test_info(d)
            refs = count_references(d)
            tier, score = substance_tier(alg_kind, code_lines, test_lines, test_fns, refs, real_code_total, bak_files)

            skills.append({
                "id": f"{cat}/{d.name}",
                "category": cat,
                "name": d.name,
                "algorithm": alg_kind,
                "code_file": code_rel,
                "code_lines": code_lines,
                "real_code_total": real_code_total,
                "real_code_files": real_files,
                "bak_files": bak_files,
                "test_lines": test_lines,
                "test_functions": test_fns,
                "references": refs,
                "score": score,
                "tier": tier,
            })

    # Сортировка для вывода
    skills.sort(key=lambda s: (-s["score"], s["id"]))

    # Сводка
    from collections import Counter
    tier_counts = Counter(s["tier"] for s in skills)
    alg_counts = Counter(s["algorithm"] for s in skills)
    cat_tier = {}
    for s in skills:
        cat_tier.setdefault(s["category"], Counter())[s["tier"]] += 1

    report = {
        "total": len(skills),
        "by_tier": dict(tier_counts),
        "by_algorithm": dict(alg_counts),
        "by_category_tier": {k: dict(v) for k, v in sorted(cat_tier.items())},
        "skills": skills,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
