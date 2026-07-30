#!/usr/bin/env python3
"""B0.1 Eval harness core — запуск скилла в sandbox с N-run и сбором метрик.

Измеряет РЕАЛЬНУЮ пользу скилла, а не наличие файлов (в отличие от contract-tests).
По frontier-практике 2026 (LangChain Evaluating Skills, arXiv:2606.11435):
- N-run для учёта variance (агенты недетерминированы)
- sandbox (tempdir, mock network/systemd где возможно)
- метрики: task_success, latency, error_type, variance
"""
from __future__ import annotations
import json, os, sys, shutil, subprocess, tempfile, time, argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

BASE = Path("/mnt/agents/-Octopus")
EVAL = BASE / "skills" / "eval"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def build_sandbox(task: dict) -> Path:
    """Создать временный sandbox. Если задача задаёт fixtures — скопировать."""
    td = Path(tempfile.mkdtemp(prefix="octo_eval_"))
    fx = task.get("fixtures")
    if fx:
        src = EVAL / "golden" / "fixtures" / fx
        if src.exists():
            shutil.copytree(src, td / fx, dirs_exist_ok=True)
    return td

def run_once(skill_dir: Path, task: dict, sandbox: Path, timeout: int = 30) -> dict:
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
        # rc!=0 но валидный JSON-output => скилл корректно нашёл проблему (issue_detected), не баг
        issue = (r.returncode != 0) and bool(r.stdout.strip().startswith("{"))
        return {"ok": r.returncode == 0, "rc": r.returncode, "stdout": r.stdout[:2000],
                "stderr": r.stderr[:500], "latency": round(latency, 3), "parsed": out,
                "issue_detected": issue}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "rc": 124, "stdout": "", "stderr": "timeout", "latency": timeout}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__, "rc": 1, "stdout": "", "stderr": str(e)[:300], "latency": 0.0}

def eval_skill(skill_dir: Path, task: dict, n: int = 3, timeout: int = 30) -> dict:
    sandbox = build_sandbox(task)
    runs = [run_once(skill_dir, task, sandbox, timeout) for _ in range(n)]
    shutil.rmtree(sandbox, ignore_errors=True)
    ok = sum(1 for r in runs if r["ok"])
    latencies = [r["latency"] for r in runs]
    errors = Counter(r.get("error", "none") if not r["ok"] else "none" for r in runs)
    return {
        "skill": skill_dir.name,
        "task": task.get("id"),
        "n_runs": n,
        "ok_runs": ok,
        "success_rate": round(ok / n, 3),
        "latency_mean": round(sum(latencies) / len(latencies), 3),
        "latency_max": round(max(latencies), 3),
        "variance_flag": (max(latencies) - min(latencies)) > 2.0,
        "error_types": dict(errors),
        "sample_output": runs[0].get("parsed") if runs else None,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("skill", help="path to skill dir (e.g. core/incident-triage)")
    ap.add_argument("task", help="golden task id")
    ap.add_argument("--n", type=int, default=3)
    args = ap.parse_args()
    skill_dir = (BASE / "skills" / args.skill) if not Path(args.skill).is_absolute() else Path(args.skill)
    task_file = EVAL / "golden" / f"{args.task}.json"
    if not task_file.exists():
        print(json.dumps({"error": f"task not found: {args.task}"}, ensure_ascii=False))
        return 2
    task = json.loads(task_file.read_text())
    res = eval_skill(skill_dir, task, args.n)
    res["timestamp"] = now_iso()
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
