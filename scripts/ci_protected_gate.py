#!/usr/bin/env python3
"""CI-гейт protected-файлов (п.6 плана внедрения).

ПР не должен изменять файлы из канонического списка aios_core/self_protection.py
(PROTECTED_PATTERNS). Исключение: заголовок PR содержит [ops] — ручные правки.

Использование: ci_protected_gate.py [base_ref] [head_ref]
Выход: 0 — чисто, 1 — protected-файлы в диффе.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_protection():
    path = os.path.join(BASE_DIR, "aios_core", "self_protection.py")
    spec = importlib.util.spec_from_file_location("aios_self_protection", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    head = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    protection = _load_protection()

    r = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        capture_output=True, text=True, cwd=BASE_DIR, timeout=60,
    )
    if r.returncode != 0:
        print(f"git diff failed: {r.stderr.strip()[:200]}", file=sys.stderr)
        return 2
    files = [f for f in r.stdout.splitlines() if f.strip()]
    bad = [f for f in files if protection.is_protected(f)]
    if bad:
        print("❌ PROTECTED-GATE: PR затрагивает защищённые файлы:")
        for f in bad:
            print(f"   - {f}")
        print("Автокодеру эти файлы менять запрещено (см. AGENTS.md). "
              "Ручная правка — добавьте [ops] в заголовок PR.")
        return 1
    print(f"✅ PROTECTED-GATE: чисто ({len(files)} файлов в диффе)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
