#!/usr/bin/env python3
"""Eval harness v2 — расширенный с N-run и golden corpus loader."""

from __future__ import annotations
import json, os, sys, shutil, subprocess, tempfile, time, argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

BASE = Path("/mnt/agents/-Octopus")
EVAL = BASE / "skills" / "eval"

# Импортируем loader
sys.path.insert(0, str(EVAL))
from golden_tasks_loader import GoldenTasksLoader

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_sandbox(task: dict) -> Path:
    """Создать временный sandbox."""
    td = Path(tempfile.mkdtemp(prefix="octo_eval_"))
    fx = task.get("fixtures")
    if fx:
        src = EVAL / "golden" / "fixtures" / fx
        if src.exists():
            shutil.copytree(src, td / fx, dirs_exist_ok=True)
    return td

def run_once(skill_dir: Path, task: dict, sandbox: Path, timeout: int = 30) -> dict:
    """Запустить скилл один раз в sandbox."""
    runpy = skill_dir / "code" / "run.py"
    if not runpy.exists():
        return {"ok": False, "error": "no_runpy", "rc": 127, "stdout": "", "stderr": "", "latency": 0.0}

    env = dict(os.environ)
    env["OCTOPUS_EVAL_SANDBOX"] = str(sandbox)
    t0 = time.perf_counter()

    try:
        r = subprocess.run([sys.executable, str(runpy)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(skill_dir), env=env)
        latency = time.perf_counter() - t0

        try:
            out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {"raw": r.stdout[:500]}
        except Exception:
            out = {"raw": r.stdout[:500]}

        issue = (r.returncode != 0) and bool(r.stdout.strip().startswith("{"))
        return {"ok": r.returncode == 0, "rc": r.returncode, "stdout": r.stdout[:2000],
                "stderr": r.stderr[:500], "latency": round(latency, 3), "parsed": out,
                "issue_detected": issue}

    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "rc": 124, "stdout": "", "stderr": "timeout", "latency": timeout}

    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "rc": 1, "stdout": "", "stderr": str(e)[:300], "latency": 0.0}

def eval_skill(skill_dir: Path, task: dict, n: int = 3, timeout: int = 30) -> dict:
    """Запустить скилл N раз и собрать метрики."""
    sandbox = build_sandbox(task)
    runs = [run_once(skill_dir, task, sandbox, timeout) for _ in range(n)]
    shutil.rmtree(sandbox, ignore_errors=True)

    ok = sum(1 for r in runs if r["ok"])
    latencies = [r["latency"] for r in runs]
    errors = Counter(r.get("error", "none") if not r["ok"] else "none" for r in runs)

    return {
        "skill": skill_dir.name,
        "task_id": task.get("id"),
        "task_name": task.get("name"),
        "task_description": task.get("description"),
        "n_runs": n,
        "ok_runs": ok,
        "success_rate": round(ok / n, 3),
        "latency_mean": round(sum(latencies) / len(latencies), 3),
        "latency_max": round(max(latencies), 3),
        "latency_std": round((sum((l - sum(latencies)/len(latencies))**2 for l in latencies) / len(latencies))**0.5, 3),
        "variance_flag": (max(latencies) - min(latencies)) > 2.0,
        "error_types": dict(errors),
        "sample_output": runs[0].get("parsed") if runs else None,
        "vector": task.get("vector"),
        "test_type": task.get("test_type"),
    }

def main():
    ap = argparse.ArgumentParser(description="Eval harness v2 с расширенным golden corpus")
    ap.add_argument("skill", help="путь к скиллу (core/quality-api-smoke)")
    ap.add_argument("--task", help="ID задачи (или все для выборки)")
    ap.add_argument("--n", type=int, default=3, help="количество запусков")
    ap.add_argument("--vector", help="фильтр по вектору (quality/memory/swarm/money/meta)")
    ap.add_argument("--list", action="store_true", help="список всех golden tasks")
    ap.add_argument("--loader", choices=["legacy", "expanded", "all"], default="all", help="источник golden tasks")
    args = ap.parse_args()

    skill_dir = (BASE / "skills" / args.skill) if not Path(args.skill).is_absolute() else Path(args.skill)

    if not skill_dir.exists():
        print(json.dumps({"error": f"skill not found: {args.skill}"}, ensure_ascii=False))
        return 2

    # Загрузка golden tasks
    loader = GoldenTasksLoader()
    all_tasks = loader.load(args.loader)

    if args.list:
        print(f"\n📋 Golden Tasks ({args.loader}):")
        for task in all_tasks:
            vec = task.get("vector", "unknown")
            ttype = task.get("test_type", "unknown")
            print(f"  {task.get('id', 'unknown')}: {task.get('name', 'unknown')} [{vec}/{ttype}]")
        return 0

    # Фильтрация
    tasks_to_eval = all_tasks
    if args.vector:
        tasks_to_eval = [t for t in tasks_to_eval if t.get("vector") == args.vector]
    if args.task:
        tasks_to_eval = [t for t in tasks_to_eval if t.get("id") == args.task]

    if not tasks_to_eval:
        print(json.dumps({"error": "no tasks match criteria"}, ensure_ascii=False))
        return 1

    # Выполнение
    results = []
    for task in tasks_to_eval:
        result = eval_skill(skill_dir, task, args.n)
        result["timestamp"] = now_iso()
        results.append(result)

    # Сводка
    summary = {
        "total_tasks": len(tasks_to_eval),
        "overall_success_rate": round(sum(r["success_rate"] for r in results) / len(results), 3),
        "total_latency_ms": round(sum(r["latency_mean"] for r in results), 2),
        "avg_latency_ms": round(sum(r["latency_mean"] for r in results) / len(results), 3),
        "skills": results,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
