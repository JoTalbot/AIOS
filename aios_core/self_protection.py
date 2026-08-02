"""
Self-Protection v1.0 — защита AIOS от самоповреждения автокодером.

Инцидент 2026-08-02: автокоммит 044b03a0 «auto(v3): Improve code quality» переписал
run_coder_orchestrator_v3_1.py в нерабочую заглушку (166 -> 67 строк, тела функций
заменены на `pass`, пропали все импорты LLM). Сервис aios-auto-coder-v3 падал каждые
10 секунд, пока файл не восстановили вручную.

Механизмы:
1. PROTECTED_PATTERNS — файлы, которые автокодер НЕ имеет права изменять через
   apply_fix (собственный оркестратор, LLM-балансер, чат-бот, env/ключи, compose).
   Ручные правки человеком не затрагиваются — проверка только в пайплайне автокодера.
2. check_code_health() — AST-детектор «вырождения» кода в заглушку:
   синтаксис, доля pass-тел, исчезновение функций/классов, схлопывание размера,
   опасные вызовы (eval/exec/os.system).
3. WATCH_FILES — файлы, за которыми следит scripts/selfguard.py: делает снапшоты
   здорового состояния и автоматически восстанавливает при повреждении.

ВАЖНО: после намеренного крупного рефакторинга критичных файлов (вручную)
пересоздайте снапшоты: /opt/aios/.venv/bin/python scripts/selfguard.py --force-snapshot
"""
from __future__ import annotations

import ast
import fnmatch

# Файлы, запрещённые для автономного изменения (fnmatch-паттерны относительно корня репо)
PROTECTED_PATTERNS = (
    # Сам оркестратор и его зависимости — инцидент 2026-08-02
    "run_coder_orchestrator*.py",
    # Чат-бот (также исключён из auto-commit в phase_commit)
    "run_telegram_bot.py",
    # Мозг автокодера и LLM-инфраструктура — ломать нельзя, правит человек
    "aios_core/autocoder_v3*.py",
    "aios_core/llm_balancer.py",
    "aios_core/self_protection.py",
    "aios_core/code_rag.py",
    "aios_core/autocoder_memory.py",
    # Импортная цепочка пакета: инцидент 2026-08-02 #2 — auto-коммит c87c3bd4
    # сжал orchestrator.py до 14 строк и оборвал import aios_core целиком
    "aios_core/orchestrator.py",
    "aios_core/__init__.py",
    # Инцидент 2026-08-02 #3: поэтапное поедание за утро (756->80 и др.)
    "octopus_core/api_v2_batch.py",
    "aios_core/advanced_security.py",
    "aios_core/inter_swarm.py",
    # Сторож
    "scripts/selfguard.py",
    # Секреты и инфраструктура
    ".env",
    ".env.*",
    "data/.llm_keys.json",
    "docker-compose*.yml",
    "docker-compose*.yaml",
)

# Файлы под наблюдением сторожа (снапшоты + автовосстановление)
WATCH_FILES = (
    "run_coder_orchestrator_v3_1.py",
    "run_coder_orchestrator.py",
    "run_telegram_bot.py",
    "aios_core/autocoder_v3.py",
    "aios_core/llm_balancer.py",
    "aios_core/orchestrator.py",
    "aios_core/__init__.py",
    "octopus_core/api_v2_batch.py",
    "aios_core/advanced_security.py",
    "aios_core/inter_swarm.py",
)


def is_protected(rel_path: str) -> bool:
    """True, если путь запрещён для автономного изменения автокодером."""
    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    rel = rel.lstrip("/")
    # v3.6: basename-матч — дубликат protected-файла внутри пакета
    # (aios_core/run_coder_orchestrator_v3_1.py, инцидент 02.08) тоже под защитой.
    # Побочный эффект: __init__.py защищён везде (это плюс: два инцидента ломали import).
    base = rel.rsplit("/", 1)[-1]
    return any(
        fnmatch.fnmatch(rel, pat)
        or fnmatch.fnmatch("/" + rel, pat)
        or fnmatch.fnmatch(base, pat)
        or fnmatch.fnmatch(base, pat.rsplit("/", 1)[-1])
        for pat in PROTECTED_PATTERNS
    )


def _trivial_body(node: ast.AST) -> bool:
    """Тело функции тривиально: только pass / ... / docstring / raise NotImplementedError."""
    body = list(getattr(node, "body", []))
    if body and isinstance(body[0], ast.Expr) and isinstance(
        getattr(body[0], "value", None), ast.Constant
    ) and isinstance(body[0].value.value, str):
        body = body[1:]  # отрезаем docstring
    if not body:
        return True
    for st in body:
        if isinstance(st, ast.Pass):
            continue
        if isinstance(st, ast.Expr) and isinstance(getattr(st, "value", None), ast.Constant) \
                and st.value.value is Ellipsis:
            continue
        if isinstance(st, ast.Raise):
            exc = st.exc
            name = ""
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                name = exc.func.id
            elif isinstance(exc, ast.Name):
                name = exc.id
            if name == "NotImplementedError":
                continue
        return False
    return True


def _functions(tree: ast.AST) -> dict[str, ast.AST]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _classes(tree: ast.AST) -> set[str]:
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def _dangerous_calls(tree: ast.AST) -> list[str]:
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = ""
            if isinstance(f, ast.Name):
                name = f.id
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                name = f"{f.value.id}.{f.attr}"
            if name in ("eval", "exec", "os.system", "os.popen"):
                bad.append(name)
    return bad


def check_code_health(path: str, new_code: str, old_code: str = "", min_keep_ratio: float = 0.5) -> tuple[bool, list[str]]:
    """Проверяет, что new_code — не деградация файла.

    Сравнивает со старой версией (old_code — с диска/из git HEAD/снапшота).
    Возвращает (ok, reasons): ok=True — код здоров.
    """
    reasons: list[str] = []
    try:
        new_tree = ast.parse(new_code, filename=str(path))
    except SyntaxError as e:
        return False, [f"syntax error: {e}"]

    new_lines = len([l for l in new_code.splitlines() if l.strip()])

    bad = _dangerous_calls(new_tree)
    if bad:
        reasons.append(f"опасные вызовы: {sorted(set(bad))}")

    if old_code:
        try:
            old_tree: ast.AST | None = ast.parse(old_code)
        except SyntaxError:
            old_tree = None
        old_lines = len([l for l in old_code.splitlines() if l.strip()])
        if old_tree is not None and old_lines > 30:
            # 0. Замена содержательного файла почти пустым (инцидент: 159 -> 51)
            if new_lines < 5:
                reasons.append(f"файл почти пуст ({new_lines} строк вместо {old_lines})")
            old_funcs, new_funcs = _functions(old_tree), _functions(new_tree)
            old_cls, new_cls = _classes(old_tree), _classes(new_tree)
            # 1. Схлопывание размера (инцидент: 166 -> 67 строк)
            if new_lines < min_keep_ratio * old_lines:
                reasons.append(f"размер сжался {old_lines} -> {new_lines} строк")
            # 2. Массовое исчезновение функций
            if old_funcs:
                missing = set(old_funcs) - set(new_funcs)
                if len(missing) / len(old_funcs) >= 0.6:
                    reasons.append(f"исчезли функции: {sorted(missing)[:5]}")
            # 3. Массовое исчезновение классов
            if old_cls:
                missing_c = old_cls - new_cls
                if len(missing_c) / len(old_cls) >= 0.6:
                    reasons.append(f"исчезли классы: {sorted(missing_c)[:5]}")
            # 4. Замена реальных тел на pass-заглушки
            if new_funcs:
                common = set(old_funcs) & set(new_funcs)
                became_trivial = [
                    n for n in common
                    if not _trivial_body(old_funcs[n]) and _trivial_body(new_funcs[n])
                ]
                if new_lines >= 5 and len(new_funcs) >= 3:
                    trivial_cnt = sum(1 for n in new_funcs.values() if _trivial_body(n))
                    if trivial_cnt / len(new_funcs) >= 0.6:
                        reasons.append(f"{trivial_cnt}/{len(new_funcs)} функций — пустые pass-заглушки")
                if common and len(became_trivial) / len(common) >= 0.5:
                    reasons.append(f"тела функций заменены на pass/None: {sorted(became_trivial)[:5]}")
    return (len(reasons) == 0), reasons
