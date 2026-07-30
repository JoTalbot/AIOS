#!/usr/bin/env python3
"""B0.4 Static analyzer — package-level reasoning по скиллу (SkillGuard-стиль).

Anti-patterns (как в PluginEval/SkillGuard-Robust):
- ORPHAN_REFERENCE: ссылка [text](references/x) но файла нет
- DEAD_CROSS_REF: ссылка на другой скилл, путь не резолвится
- MISSING_ALGO: нет секции ## Алгоритм
- PROCEDURAL_ONLY: есть код, но SKILL.md не описывает поведение (нет примеров/полей)
- INJECTION_RISK: подозрительные паттерны в SKILL.md (prompt-injection, arXiv:2510.26328)
"""
from __future__ import annotations
import json, re
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
CATS = ["core", "meta", "memory", "swarm", "research", "dr", "mcp"]
INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|prior)\s+(instructions|prompt)",
    r"disregard\s+(the\s+)?(above|previous)",
    r"system\s*:\s*",
    r"you\s+are\s+now",
    r"new\s+instructions\s*:",
    r"```\s*(bash|sh|shell)",
]

def analyze(skill_dir: Path) -> dict:
    md = skill_dir / "SKILL.md"
    text = md.read_text(errors="replace") if md.exists() else ""
    name = skill_dir.name
    problems = []
    refs = skill_dir / "references"
    for m in re.finditer(r"\[([^\]]+)\]\((references/([^)]+))\)", text):
        target = skill_dir / m.group(2)
        if not target.exists():
            problems.append({"type": "ORPHAN_REFERENCE", "detail": m.group(2)})
    for m in re.finditer(r"\]\((\.\./[^)]+)\)", text):
        target = (skill_dir / m.group(1)).resolve()
        if not target.exists():
            problems.append({"type": "DEAD_CROSS_REF", "detail": m.group(1)})
    if not re.search(r"##\s*Алгоритм", text, re.I):
        problems.append({"type": "MISSING_ALGO", "detail": "no ## Алгоритм section"})
    runpy = skill_dir / "code" / "run.py"
    has_code = runpy.exists()
    # Мягкая проверка: описано ли поведение (любой из маркеров), а не только слово "Пример"
    if has_code and not re.search(r"(Пример|пример|Выход|Результат|возвращ|return|Формат|формат|отчёт|json|JSON|##\s*Алгоритм)", text, re.I):
        problems.append({"type": "PROCEDURAL_ONLY", "detail": "code present but SKILL.md lacks behavior description"})
    # INJECTION_RISK: игнорировать содержимое ```-блоков (там легитимный код/команды)
    body_no_fences = re.sub(r"```.*?```", "", text, flags=re.S)
    inj = []
    for pat in INJECTION_PATTERNS:
        for mm in re.finditer(pat, body_no_fences, re.I):
            inj.append(mm.group(0)[:60])
    if inj:
        problems.append({"type": "INJECTION_RISK", "detail": "; ".join(inj[:3])})
    return {"name": name, "path": str(skill_dir.relative_to(BASE.parent.parent)),
            "has_code": has_code, "anti_patterns": problems,
            "injection_risk": bool(inj)}

def main():
    out = []
    for cat in CATS:
        cp = BASE / cat
        if not cp.exists():
            continue
        for d in sorted(cp.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            if (d / "SKILL.md").exists():
                out.append(analyze(d))
    report = {"timestamp": datetime.now(timezone.utc).isoformat(), "total": len(out),
              "with_anti_patterns": sum(1 for x in out if x["anti_patterns"]),
              "with_injection_risk": sum(1 for x in out if x["injection_risk"]),
              "skills": out}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
