"""E2E-тест защиты от самоповреждения: apply_fix + watchdog restore."""
import os
import subprocess
import sys

sys.path.insert(0, "/root/AIOS")

from aios_core.autocoder_v3 import AutocoderV3  # noqa: E402


def main() -> int:
    REPO = "/root/AIOS"
    results = []

    # --- Тест 1: apply_fix на ЗАЩИЩЁННЫЙ файл (реальная заглушка из инцидента) ---
    print("=" * 70)
    print("ТЕСТ 1: apply_fix стирает run_coder_orchestrator_v3_1.py заглушкой")
    print("=" * 70)
    stub = subprocess.run(
        ["git", "show", "044b03a0:run_coder_orchestrator_v3_1.py"],
        cwd=REPO, capture_output=True, text=True,
    ).stdout
    before = open(f"{REPO}/run_coder_orchestrator_v3_1.py", encoding="utf-8").read()
    v3 = AutocoderV3(REPO)
    ok = v3.apply_fix("run_coder_orchestrator_v3_1.py", stub)
    after = open(f"{REPO}/run_coder_orchestrator_v3_1.py", encoding="utf-8").read()
    res1 = (ok is False) and (before == after)
    print(f"apply_fix -> {ok} (ожидаем False), файл не изменён: {before == after}")
    results.append(("apply_fix PROTECTED (оркестратор)", res1))

    # --- Тест 2: apply_fix деградации НЕзащищённого большого файла ---
    print("=" * 70)
    print("ТЕСТ 2: apply_fix заменяет 80-строчный модуль 5-строчной заглушкой")
    print("=" * 70)
    target = "aios_core/tmp_selfguard_target.py"
    big_code = "\n".join(f"def func_{i}(x):\n    return x + {i}\n" for i in range(26))  # ~78 строк
    v3.apply_fix(target, big_code)
    stub2 = "def f():\n    pass\n"
    ok2 = v3.apply_fix(target, stub2)
    still_big = open(f"{REPO}/{target}", encoding="utf-8").read() == big_code
    print(f"apply_fix -> {ok2} (ожидаем False), файл уцелел: {still_big}")
    results.append(("apply_fix REJECT деградации", (ok2 is False) and still_big))
    os.remove(f"{REPO}/{target}")

    # --- Тест 3: apply_fix нормального нового файла ---
    print("=" * 70)
    print("ТЕСТ 3: apply_fix НОРМАЛЬНОГО нового файла (должен пройти)")
    print("=" * 70)
    ok3 = v3.apply_fix("aios_core/tmp_selfguard_ok.py", 'def add(a: int, b: int) -> int:\n    """Sum."""\n    return a + b\n')
    exists = os.path.exists(f"{REPO}/aios_core/tmp_selfguard_ok.py")
    print(f"apply_fix -> {ok3} (ожидаем True), файл создан: {exists}")
    results.append(("apply_fix нормального кода", ok3 is True and exists))
    os.remove(f"{REPO}/aios_core/tmp_selfguard_ok.py")

    # --- Тест 4: watchdog восстанавливает убитый файл ---
    print("=" * 70)
    print("ТЕСТ 4: ломаем оркестратор (syntax error) -> selfguard --once чинит")
    print("=" * 70)
    f = f"{REPO}/run_coder_orchestrator_v3_1.py"
    orig = open(f, encoding="utf-8").read()
    import hashlib
    md5_before = hashlib.md5(orig.encode()).hexdigest()
    open(f, "a", encoding="utf-8").write("\ndef broken(:\n    this is not python!!!\n")
    r = subprocess.run(["/opt/aios/.venv/bin/python", "scripts/selfguard.py", "--once"],
                       cwd=REPO, capture_output=True, text=True)
    restored = "RESTORED" in (r.stdout + r.stderr) or "♻️" in (r.stdout + r.stderr)
    md5_after = hashlib.md5(open(f, encoding="utf-8").read().encode()).hexdigest()
    print(f"selfguard: restored={restored}, md5 совпал с исходным: {md5_before == md5_after}")
    print((r.stdout + r.stderr).strip()[:300])
    results.append(("watchdog restore", md5_before == md5_after))

    print("=" * 70)
    passed = sum(1 for _, r in results if r)
    for name, r in results:
        print(("✅" if r else "❌"), name)
    print(f"ИТОГ: {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
