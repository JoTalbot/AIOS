#!/usr/bin/env python3
"""Targeted pytest-gate для автокодера (п.2 плана внедрения).

Для изменённого файла ищет релевантные тесты в tests/ и прогоняет их дважды:
  1) на рабочем дереве (с применённой правкой)
  2) на чистом HEAD во временном git-worktree (базовая линия)

Правка отклоняется ТОЛЬКО при НОВЫХ падениях (что-то, что на HEAD работало).

Коды выхода:
  0 — тесты пройдены / нет релевантных тестов
  2 — новые падения (блокировать коммит, откатить файл)
  3 — базовая линия недоступна (non-blocking, warn)
  4 — тесты красные, но так же красные на HEAD (pre-existing, non-blocking)
  1 — внутренняя ошибка гейта (non-blocking)

Использование: pytest_gate.py <относительный/путь/файла.py>
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
PY = os.environ.get("AIOS_PYTEST_PY", "/opt/aios/.venv/bin/python")
GATE_TIMEOUT = int(os.environ.get("AIOS_PYTEST_GATE_TIMEOUT", "240"))
MAX_TEST_FILES = 4


def find_tests(changed: str) -> list[str]:
    """Кандидатные тест-файлы по имени модуля."""
    changed = os.path.normpath(changed)
    base = os.path.basename(changed)
    stem = os.path.splitext(base)[0]
    if changed.startswith("tests/") and base.startswith("test_"):
        return [changed]
    out: list[str] = []
    tests_root = os.path.join(REPO, "tests")
    if not os.path.isdir(tests_root):
        return out
    for root, dirs, files in os.walk(tests_root):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "e2e", "chaos"}]
        for f in files:
            if not f.endswith(".py"):
                continue
            if f == f"test_{stem}.py" or f.startswith(f"test_{stem}_") or f == f"{stem}_test.py":
                out.append(os.path.relpath(os.path.join(root, f), REPO))
    return sorted(out)[:MAX_TEST_FILES]


def run_pytest(paths: list[str], cwd: str) -> set[str]:
    """Возвращает множество упавших nodeid ('TIMEOUT' при зависании)."""
    try:
        r = subprocess.run(
            [PY, "-m", "pytest", *paths, "-q", "--tb=no", "--no-header",
             "-p", "no:cacheprovider"],
            capture_output=True, text=True, timeout=GATE_TIMEOUT, cwd=cwd,
        )
        out = r.stdout + "\n" + r.stderr
        failed = set()
        for line in out.splitlines():
            m = re.match(r"^(FAILED|ERROR)\s+(\S+)", line.strip())
            if m:
                nodeid = m.group(2).split(" - ")[0]
                failed.add(nodeid)
        if r.returncode != 0 and not failed:
            failed.add(f"<rc{r.returncode}>")
        return failed
    except subprocess.TimeoutExpired:
        return {"<TIMEOUT>"}
    except Exception as e:  # noqa
        return {f"<gate-error:{e}>"}


def is_dirty(path: str) -> bool:
    r = subprocess.run(["git", "status", "--porcelain", "--", path],
                       capture_output=True, text=True, cwd=REPO, timeout=20)
    return bool(r.stdout.strip())


def head_failures(paths: list[str]) -> set[str] | None:
    """Прогон тех же тестов на чистом HEAD. None — если worktree не удался."""
    wt = tempfile.mkdtemp(prefix="aios_gate_", dir="/tmp")
    try:
        r = subprocess.run(["git", "worktree", "add", "--detach", wt, "HEAD"],
                           capture_output=True, text=True, cwd=REPO, timeout=120)
        if r.returncode != 0:
            return None
        return run_pytest(paths, wt)
    except Exception:
        return None
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", wt],
                       capture_output=True, cwd=REPO, timeout=30)
        shutil.rmtree(wt, ignore_errors=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: pytest_gate.py <file>", file=sys.stderr)
        return 1
    changed = sys.argv[1]
    tests = find_tests(changed)
    if not tests:
        print(f"NO-TESTS: нет тестов для {changed}")
        return 0
    print(f"Гейт: {changed} -> {len(tests)} тест-файл(а): {', '.join(tests)}")

    cur = run_pytest(tests, REPO)
    if not cur:
        print(f"PASS: все таргетные тесты зелёные ({len(tests)})")
        return 0

    if not is_dirty(changed):
        print(f"WARN: падения {sorted(cur)[:3]}, но файл закоммичен — базовая линия недоступна")
        return 3

    base = head_failures(tests)
    if base is None:
        print(f"WARN: падения {sorted(cur)[:3]}, worktree-база недоступна (non-blocking)")
        return 3

    new_fail = cur - base
    if new_fail:
        print(f"NEW-FAILS: новые падения vs HEAD: {sorted(new_fail)[:5]} "
              f"(на HEAD падало: {len(base)}, сейчас: {len(cur)})")
        return 2
    print(f"PRE-EXISTING: падения те же, что на HEAD ({len(cur)}) — не вина правки")
    return 4


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # гейт не должен ронять конвейер
        print(f"gate internal error: {e}", file=sys.stderr)
        sys.exit(1)
