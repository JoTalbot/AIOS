#!/usr/bin/env python3
"""Проверка Батча C (п.4/5/9): скиллы-стандарт, карточки, tier-2 тела, Context7, майнер.

Запуск: /opt/aios/.venv/bin/python scripts/test_batch_c.py
"""
import subprocess
import sys

sys.path.insert(0, "/root/AIOS")
PY = "/opt/aios/.venv/bin/python"
ok = 0

# 1) skill_lint: все SKILL.md по стандарту (после --fix)
r = subprocess.run([PY, "scripts/skill_lint.py"], capture_output=True, text=True, cwd="/root/AIOS")
print("   lint:", r.stdout.strip().splitlines()[0])
assert r.returncode == 0 and "✗" not in r.stdout, r.stdout[:300]
print("[1/5] skill_lint: frontmatter-стандарт соблюдён")
ok += 1

# 2) list_skill_cards: есть описания, coder/ первые
from aios_core.coder_research import list_skill_cards, skill_bodies_for, fetch_context7_docs

cards = list_skill_cards(12)
assert cards and all(n and d for n, d in cards), cards[:3]
assert cards[0][0].startswith("coder/"), cards[0]
print(f"[2/5] list_skill_cards: {len(cards)} карточек, первая coder/: {cards[0][0]}")
ok += 1

# 3) skill_bodies_for: по задаче про pydantic подтягивается pydantic-v2
bodies = skill_bodies_for("исправь pydantic root_validator ошибку в модуле")
assert "pydantic-v2" in bodies and "skip_on_failure" in bodies, bodies[:300]
print(f"[3/5] skill_bodies_for: найден pydantic-v2 ({len(bodies)} символов)")
ok += 1

# 4) Context7: свежие доки по pydantic (сеть)
c7 = fetch_context7_docs("миграция на pydantic v2")
assert "Context7" in c7 and len(c7) > 500, c7[:200]
print(f"[4/5] fetch_context7_docs: {len(c7)} символов документации")
ok += 1

# 5) memory->skills майнер (dry-run + реальный запуск уже сделан при деплое)
r = subprocess.run([PY, "scripts/memory_to_skills.py", "--dry-run"],
                   capture_output=True, text=True, cwd="/root/AIOS")
assert r.returncode == 0, r.stderr[:300]
print("[5/5] memory_to_skills: dry-run OK | " + r.stdout.strip().splitlines()[-1][:90])
ok += 1

# sync_gh_issues dry-run (не считаем отдельным пунктом — сеть/метки могут быть пусты)
r = subprocess.run([PY, "scripts/sync_gh_issues.py", "--dry-run"],
                   capture_output=True, text=True, cwd="/root/AIOS")
print("   gh-issues dry-run:", (r.stdout.strip().splitlines() or ["?"])[-1][:90])

print(f"\n✅ Батч C: {ok}/5 проверок пройдено")
