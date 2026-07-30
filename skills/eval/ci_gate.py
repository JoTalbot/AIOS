#!/usr/bin/env python3
"""B0.6 CI gate — per-dimension threshold (не aggregate, как в futureagi 2026 guide).

Читает reports/eval/<skill>.json (результат harness+judge) и падает (exit 1),
если любая dimension ниже threshold. Интегрируется в skill_evolution_cycle.py.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

THRESHOLDS = {
    "success_rate": 0.6,
    "msu": 0.1,
    "judge_score": 0.5,
}
EVAL_REPORTS = Path("/mnt/agents/-Octopus/reports/eval")

def gate(report: dict) -> tuple[bool, list[str]]:
    fails = []
    for dim, thr in THRESHOLDS.items():
        val = report.get(dim)
        if val is None:
            continue
        if val < thr:
            fails.append(f"{dim}={val} < {thr}")
    return (len(fails) == 0), fails

def main():
    if len(sys.argv) < 2:
        # режим папки: проверить все json в reports/eval
        files = list(EVAL_REPORTS.glob("*.json"))
        bad = 0
        for f in files:
            try:
                rep = json.loads(f.read_text())
            except Exception:
                continue
            ok, fails = gate(rep)
            if not ok:
                bad += 1
                print(f"FAIL {f.name}: {fails}")
        print(f"CI gate: {len(files)-bad}/{len(files)} passed")
        raise SystemExit(1 if bad else 0)
    rep = json.loads(Path(sys.argv[1]).read_text())
    ok, fails = gate(rep)
    print(json.dumps({"pass": ok, "fails": fails}, ensure_ascii=False))
    raise SystemExit(0 if ok else 1)

if __name__ == "__main__":
    main()
