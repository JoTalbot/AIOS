#!/usr/bin/env python3
"""B0.5 Compare: run-with/without skill -> Marginal Skill Utility (MSU).

Имитация без живого агента (LangChain-style):
- 'without' = вывод скилла-заглушки (generic обёртка, пустой отчёт)
- 'with'    = вывод целевого скилла
Оба подаются в judge.py; MSU = score(with) - score(without).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

BASE = Path("/mnt/agents/-Octopus/skills")
EVAL = BASE / "eval"

def main():
    if len(sys.argv) < 3:
        print("usage: compare.py <skill-path> <task-id> [--no-llm]")
        raise SystemExit(2)
    skill_rel = sys.argv[1]
    task_id = sys.argv[2]
    use_llm = "--no-llm" not in sys.argv
    skill_dir = BASE / skill_rel
    task = json.loads((EVAL / "golden" / f"{task_id}.json").read_text())
    # 'with'
    out_with = None
    issue_detected = False
    runpy = skill_dir / "code" / "run.py"
    if runpy.exists():
        import subprocess
        r = subprocess.run([sys.executable, str(runpy)], capture_output=True, text=True, timeout=30, cwd=str(skill_dir))
        if r.stdout.strip().startswith("{"):
            out_with = json.loads(r.stdout)
            issue_detected = (r.returncode != 0)  # rc!=0 + valid JSON = нашёл проблему
    # 'without' = пустой отчёт (заглушка)
    out_without = {"ok": True, "skill": "stub", "note": "no skill applied"}
    from judge import judge
    j_with = judge(task, out_with, use_llm, issue_detected=issue_detected)
    j_without = judge(task, out_without, use_llm)
    msu = round(j_with["score"] - j_without["score"], 3)
    result = {"skill": skill_dir.name, "task": task_id, "score_with": j_with["score"],
              "score_without": j_without["score"], "msu": msu,
              "issue_detected": issue_detected,
              "rationale_with": j_with["rationale"], "method": j_with["method"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    raise SystemExit(main())
