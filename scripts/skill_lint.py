#!/usr/bin/env python3
"""Линт/починка SKILL.md под открытый стандарт agentskills.io (п.4 плана).

Стандарт: YAML-frontmatter с обязательными name + description, затем markdown-тело.
Наши исторические файлы начинаются с "# SKILL: <name>" — frontmatter добавляем.

Использование:
  skill_lint.py           — только отчёт
  skill_lint.py --fix     — дописать недостающий frontmatter (in-place)
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
SKILLS = os.path.join(REPO, "skills")
MAX_DESC = 220


def parse(md: str) -> dict:
    has_fm = md.lstrip().startswith("---")
    name = ""
    desc = ""
    if has_fm:
        m = re.match(r"\s*---\n(.*?)\n---", md, re.S)
        if m:
            fm = m.group(1)
            nm = re.search(r"^name:\s*(.+)$", fm, re.M)
            dm = re.search(r"^description:\s*(.+)$", fm, re.M)
            name = nm.group(1).strip() if nm else ""
            desc = dm.group(1).strip() if dm else ""
    return {"has_frontmatter": bool(name and desc), "name": name, "description": desc}


def extract_description(md: str, fallback: str) -> str:
    """Описание из секции '## Описание' или первого нетривиального абзаца."""
    m = re.search(r"##\s*Описание\s*\n+(.+)", md)
    if not m:
        m = re.search(r"##\s*Description\s*\n+(.+)", md)
    if m:
        line = m.group(1).strip().splitlines()[0].strip()
    else:
        lines = [l.strip() for l in md.splitlines() if l.strip()
                 and not l.startswith(("#", "---", "name:", "description:", "**"))]
        line = lines[0] if lines else fallback
    line = re.sub(r"\s+", " ", line)[:MAX_DESC]
    return line or fallback


def main() -> int:
    fix = "--fix" in sys.argv
    total, ok, fixed = 0, 0, 0
    bad: list[str] = []
    for root, _dirs, files in os.walk(SKILLS):
        if "SKILL.md" not in files:
            continue
        total += 1
        path = os.path.join(root, "SKILL.md")
        rel = os.path.relpath(path, REPO)
        slug = os.path.basename(root)
        try:
            md = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            bad.append(rel)
            continue
        info = parse(md)
        if info["has_frontmatter"]:
            ok += 1
            continue
        if fix:
            desc = extract_description(md, f"Навык {slug} проекта AIOS")
            fm = f"---\nname: {slug}\ndescription: {desc}\n---\n\n"
            # Убираем существующий frontmatter без обязательных полей, если был
            body = re.sub(r"^\s*---\n.*?\n---\n*", "", md, flags=re.S)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fm + body.lstrip("\n"))
            fixed += 1
        else:
            bad.append(rel)
    print(f"SKILL.md: {total}, по стандарту: {ok}, "
          + (f"исправлено: {fixed}" if fix else f"без frontmatter: {len(bad)}"))
    if bad and not fix:
        for b in bad[:15]:
            print(f"  ✗ {b}")
        if len(bad) > 15:
            print(f"  … ещё {len(bad) - 15}")
        print("\nЗапусти с --fix для автопочинки")
    return 0 if fix or not bad or ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
