"""
AIOS Coder Orchestrator — единый цикл автономной разработки.

Каждые 5 минут:
  1. 🔍 ANALYZE  — LLM анализирует проект, находит проблемы
  2. 📋 PLAN     — LLM составляет план действий (что кодить/чинить)
  3. 💻 CODE     — MetaCognitiveCoder пишет/чинит код
  4. ✅ VALIDATE — AST safety check + syntax check
  5. 📊 REPORT   — отчёт в Telegram человеческим языком

Интеграция:
  - MetaCognitiveCoder (LLM-powered code gen)
  - SafetyValidator (AST analysis)
  - GitOps (commit + push)
  - Telegram (отчёты)
"""
import importlib.util
import re
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Optional web-research & skill toolkit for the coder (best-effort import).
try:
    from aios_core.coder_research import web_research, list_skills, use_skill as _coder_use_skill
    _RESEARCH_OK = True
except Exception:
    web_research = None
    list_skills = lambda: []
    _RESEARCH_OK = False

REPO_PATH = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
TG_TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN", "")
TG_CHAT_ID = os.environ.get("AIOS_AUTO_CODER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
def tg_send(text: str) -> bool:
    if not TG_TOKEN or not TG_CHAT_ID:
        print(f"[WARN] TG not configured")
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": int(TG_CHAT_ID),
        "text": text[:4000],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception as e:
        print(f"[ERROR] TG send: {e}")
        return False


# ---------------------------------------------------------------------------
# LLM Balancer (multi-provider, multi-key)
# ---------------------------------------------------------------------------
_balancer = None

def get_balancer():
    global _balancer
    if _balancer is None:
        # Load balancer module
        spec = importlib.util.spec_from_file_location(
            "llm_balancer", os.path.join(REPO_PATH, "aios_core", "llm_balancer.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["llm_balancer"] = mod
        spec.loader.exec_module(mod)
        _balancer = mod.LLMBalancer()
    return _balancer


class LLMClient:
    """Wrapper around LLMBalancer for backward compatibility."""
    def __init__(self):
        self.balancer = get_balancer()
        self.api_key = "balancer"  # always available
        self.model = os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick")

    def chat(self, messages: list, system: str = "") -> str:
        return self.balancer.chat(messages, model=self.model, system=system)


# ---------------------------------------------------------------------------
# MetaCognitiveCoder loader
# ---------------------------------------------------------------------------
_coder_mod = None
def get_coder():
    global _coder_mod
    if _coder_mod:
        return _coder_mod
    path = os.path.join(REPO_PATH, "aios_core", "meta_cognitive_self_coder.py")
    spec = importlib.util.spec_from_file_location("meta_coder", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["meta_coder"] = mod
    spec.loader.exec_module(mod)
    _coder_mod = mod
    return mod


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def git_cmd(*args) -> str:
    try:
        r = subprocess.run(["git"] + list(args), cwd=REPO_PATH,
                           capture_output=True, text=True, timeout=20)
        return (r.stdout + r.stderr).strip()
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Backlog (persistent task queue)
# ---------------------------------------------------------------------------
BACKLOG_FILE = os.path.join(REPO_PATH, "data", "coder_backlog.json")

def load_backlog() -> dict:
    """Load coder backlog (tasks, history, stats)."""
    if os.path.exists(BACKLOG_FILE):
        try:
            with open(BACKLOG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"tasks": [], "history": [], "completed": 0, "failed": 0, "cycle_count": 0, "lessons": []}


def _extract_lesson(action: str, desc: str, err: str) -> str:
    """Build a short self-learning lesson from a failed coder cycle."""
    err_txt = str(err or "")[:200].replace("\n", " ")
    return f"[{action}] {str(desc or '')[:60]} -> {err_txt or 'unknown error'}"


def _add_lesson(backlog: dict, lesson: str):
    """Append a lesson (deduped, capped) to the backlog for future cycles."""
    if not lesson:
        return
    lessons = backlog.setdefault("lessons", [])
    lesson = lesson[:300]
    if lesson not in lessons:
        lessons.append(lesson)
        backlog["lessons"] = lessons[-30:]  # keep last 30 lessons


def save_backlog(backlog: dict):
    """Save coder backlog."""
    os.makedirs(os.path.dirname(BACKLOG_FILE), exist_ok=True)
    with open(BACKLOG_FILE, "w") as f:
        json.dump(backlog, f, ensure_ascii=False, indent=2)


def get_project_context() -> dict:
    """Deep scan of project state for intelligent analysis."""
    ctx = {
        "git_status": git_cmd("status", "--short") or "clean",
        "git_log": git_cmd("log", "-20", "--oneline", "--no-decorate") or "no commits",
        "branch": git_cmd("branch", "--show-current") or "main",
    }
    # Keep protected auto-coder internals out of the LLM-visible git history.
    _protected_log = ("run_coder_orchestrator", "run_auto_coder", "run_telegram_bot", "llm_balancer", "meta_cognitive_self_coder")
    _log_lines = [ln for ln in ctx["git_log"].splitlines() if not any(p in ln for p in _protected_log)]
    ctx["git_log"] = "\n".join(_log_lines[-10:]) or "no commits"

    # Count modified files
    status_lines = [l for l in ctx["git_status"].split("\n") if l.strip()]
    ctx["modified_files"] = len(status_lines)

    # Scan for TODO/FIXME/HACK in Python files
    todos = []
    try:
        for root, dirs, files in os.walk(REPO_PATH):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "node_modules", "chroma_db", ".venv", "backups"}]
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                            rel = os.path.relpath(fpath, REPO_PATH)
                            # Never surface protected auto-coder internals as TODO targets.
                            if rel in ("run_coder_orchestrator.py", "tools/run_coder_orchestrator.py",
                                       "run_auto_coder.py", "tools/run_auto_coder.py",
                                       "run_telegram_bot.py", "tools/run_telegram_bot.py",
                                       "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"):
                                continue
                            for i, line in enumerate(fp, 1):
                                for tag in ["TODO", "FIXME", "HACK", "XXX", "BUG"]:
                                    up = line.upper()
                                    if tag in up:
                                        # Skip literal mentions (strings/comments describing the scanner itself).
                                        if '"' + tag + '"' in up or "'" + tag + "'" in up:
                                            continue
                                        todos.append(f"{rel}:{i} {tag}: {line.strip()[:80]}")
                                        if len(todos) >= 15:
                                            break
                                if len(todos) >= 15:
                                    break
                    except:
                        pass
                if len(todos) >= 15:
                    break
            if len(todos) >= 15:
                break
    except:
        pass
    ctx["todos"] = todos

    # Find recently modified Python files (top 15)
    recent_files = []
    try:
        result = subprocess.run(
            ["find", REPO_PATH, "-name", "*.py", "-not", "-path", "*/__pycache__/*",
             "-not", "-path", "*/.git/*", "-not", "-path", "*/chroma_db/*",
             "-mtime", "-1", "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        _protected = {"run_coder_orchestrator.py", "tools/run_coder_orchestrator.py",
                      "run_auto_coder.py", "tools/run_auto_coder.py",
                      "run_telegram_bot.py", "tools/run_telegram_bot.py",
                      "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"}
        for line in result.stdout.strip().split("\n")[:15]:
            if line.strip():
                rel = os.path.relpath(line.strip(), REPO_PATH)
                if rel in _protected:
                    continue  # protected auto-coder internals
                recent_files.append(rel)
    except:
        pass
    ctx["recent_files"] = recent_files

    # Count Python files and total lines
    total_files = 0
    total_lines = 0
    try:
        result = subprocess.run(
            ["find", REPO_PATH, "-name", "*.py", "-not", "-path", "*/__pycache__/*",
             "-not", "-path", "*/.git/*", "-type", "f"],
            capture_output=True, text=True, timeout=10
        )
        py_files = [l for l in result.stdout.strip().split("\n") if l.strip()]
        total_files = len(py_files)
        for fp in py_files[:50]:
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    total_lines += sum(1 for _ in f)
            except:
                pass
    except:
        pass
    ctx["total_files"] = total_files
    ctx["total_lines"] = total_lines

    # Check test coverage (count test files)
    test_files = []
    try:
        result = subprocess.run(
            ["find", REPO_PATH, "-name", "test_*.py", "-o", "-name", "*_test.py"],
            capture_output=True, text=True, timeout=10
        )
        test_files = [l for l in result.stdout.strip().split("\n") if l.strip()]
    except:
        pass
    ctx["test_files"] = len(test_files)

    return ctx


# ---------------------------------------------------------------------------
# ORCHESTRATOR CYCLE
# ---------------------------------------------------------------------------

# Track cycle state
_cycle_count = 0
_consecutive_errors = 0
MAX_ERRORS = 5
_previous_issues = []
_last_llm_error_cycle = 0
_LLM_ERROR_COOLDOWN_CYCLES = 60  # ~10 min at 10s interval

def phase_analyze(llm: LLMClient, ctx: dict, backlog: dict) -> dict:
    """Phase 1: Deep intelligent analysis of project state."""
    system = (
        "Ты — AIOS Coder Orchestrator, автономный senior AI-разработчик. "
        "Твоя задача — непрерывно развивать проект. "
        "Анализируй код глубоко: ищи баги, незакрытые TODO, отсутствующие тесты, "
        "плохую архитектуру, проблемы безопасности. "
        "Отвечай на русском. Всегда будь конкретен — указывай файлы и функции."
    )

    # Build detailed context
    todos_text = "\n".join(ctx.get("todos", [])[:10]) or "Нет TODO"
    recent_text = "\n".join(ctx.get("recent_files", [])[:10]) or "Нет изменений"
    history_text = "\n".join(
        f"- {h.get('description', '?')[:60]} ({h.get('status', '?')})" 
        for h in backlog.get("history", [])[-5:]
    ) or "История пуста"
    lessons_text = "\n".join(f"- {l}" for l in backlog.get("lessons", [])[-8:]) or "Уроков пока нет"
    pending_tasks = "\n".join(
        f"- [{t.get('priority', '?')}] {t.get('description', '?')[:60]}" 
        for t in backlog.get("tasks", [])[:5]
    ) or "Нет задач в бэклоге"

    prompt = (
        f"Глубокий анализ проекта AIOS.\n\n"
        f"=== Статистика ===\n"
        f"Python файлов: {ctx.get('total_files', '?')}, строк кода: ~{ctx.get('total_lines', '?')}\n"
        f"Тестов: {ctx.get('test_files', 0)}, изменённых файлов: {ctx.get('modified_files', 0)}\n"
        f"Ветка: {ctx.get('branch', '?')}\n\n"
        f"=== Git log (последние 10) ===\n{ctx.get('git_log', '?')}\n\n"
        f"=== TODO/FIXME в коде ({len(ctx.get('todos', []))}) ===\n{todos_text}\n\n"
        f"=== Недавно изменённые файлы ===\n{recent_text}\n\n"
        f"=== Бэклог задач ===\n{pending_tasks}\n\n"
        f"=== Уроки из прошлых ошибок (НЕ повторяй их) ===\n{lessons_text}\n\n"
        f"=== История последних действий ===\n{history_text}\n\n"
        f"Верни JSON (строго, без markdown):\n"
        f'{{\n'
        f'  "health_score": <1-10>,\n'
        f'  "summary": "<2-3 предложения: что происходит с проектом>",\n'
        f'  "issues": ["<конкретная проблема с указанием файла>"],\n'
        f'  "opportunities": ["<что можно улучшить прямо сейчас>"],\n'
        f'  "priority_task": "<самая важная задача — конкретное действие>",\n'
        f'  "new_tasks": ["<новая задача для бэклога>"]\n'
        f'}}'
    )

    response = llm.chat([{"role": "user", "content": prompt}], system=system)

    try:
        if "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            result = json.loads(response[start:end])
            # Add new tasks to backlog
            new_tasks = result.get("new_tasks", [])
            _prot_kw = ("run_coder_orchestrator", "run_auto_coder", "run_telegram_bot",
                        "llm_balancer", "meta_cognitive")
            for task_desc in new_tasks[:3]:
                _tl = str(task_desc or "").lower()
                if any(k in _tl for k in _prot_kw):
                    continue  # skip tasks that would point back at protected files
                if task_desc and task_desc not in [t.get("description") for t in backlog.get("tasks", [])]:
                    backlog["tasks"].append({
                        "description": task_desc,
                        "priority": "medium",
                        "created": datetime.now(timezone.utc).isoformat(),
                        "status": "pending",
                    })
            return result
    except (json.JSONDecodeError, ValueError):
        pass
    except Exception as e:
        return {
            "health_score": 0,
            "summary": f"LLM Error: {e}",
            "issues": [],
            "opportunities": [],
            "priority_task": "Продолжить развитие",
        }

    return {
        "health_score": 5,
        "summary": response[:200] if response else "Analysis failed",
        "issues": [],
        "opportunities": [],
        "priority_task": "Продолжить развитие",
    }


def _maybe_research(topic: str) -> str:
    """Do a quick web research on a topic and return a compact summary string."""
    if not _RESEARCH_OK or not web_research or not topic:
        return ""
    try:
        res = web_research(topic, max_results=4)
        lines = []
        for r in res.get("results", [])[:4]:
            lines.append(f"- {r.get('title','')[:70]} ({r.get('url','')[:70]})")
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""


def _list_skill_names() -> str:
    try:
        return ", ".join(list_skills()[:12]) if _RESEARCH_OK else ""
    except Exception:
        return ""


def phase_plan(llm: LLMClient, analysis: dict, ctx: dict, backlog: dict) -> dict:
    """Phase 2: Intelligent planning with backlog awareness."""
    system = (
        "Ты — автономный senior AI-разработчик. Ты ОБЯЗАН предложить улучшение кодом. "
        "Выбирай задачи из бэклога или создавай новые. "
        "НИКОГДА не возвращай code_needed: false. "
        "Каждый цикл должен делать проект лучше. "
        "Отвечай JSON без markdown."
    )

    # Get real file list
    real_files = []
    for root, dirs, files in os.walk(REPO_PATH):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "node_modules", "chroma_db", ".venv", "backups"}]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, f), REPO_PATH)
                if rel in ("run_coder_orchestrator.py", "tools/run_coder_orchestrator.py",
                           "run_auto_coder.py", "tools/run_auto_coder.py",
                           "run_telegram_bot.py", "tools/run_telegram_bot.py",
                           "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"):
                    continue  # protected auto-coder internals
                # Focus the coder on the real kernel code only (aios_core/).
                if not rel.startswith("aios_core/"):
                    continue
                real_files.append(rel)
                if len(real_files) >= 40:
                    break
        if len(real_files) >= 40:
            break
    files_list = "\n".join("  - " + f for f in real_files[:35])

    # Check backlog for pending tasks
    pending = [t for t in backlog.get("tasks", []) if t.get("status") == "pending"]

    # Auto-prioritize tasks by keyword: security > bugs/fixes > features > tests/docs.
    _prio_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    def _task_rank(t):
        d = str(t.get("description", "")).lower()
        t_prio = _prio_rank.get(t.get("priority", "medium"), 2)
        if any(k in d for k in ("security", "vulnerab", "xss", "injection", "secret", "auth", "credential")):
            return (0, t_prio)
        if any(k in d for k in ("bug", "fix", "error", "crash", "exception", "broken")):
            return (1, t_prio)
        if any(k in d for k in ("test", "coverage", "doc")):
            return (3, t_prio)
        return (2, t_prio)

    pending_sorted = sorted(pending, key=_task_rank)
    backlog_text = ""
    if pending_sorted:
        backlog_text = "\n".join(
            f"  {i+1}. [{_task_rank(t)[0]}] {t['description']}" for i, t in enumerate(pending_sorted[:6]))

    todos_text = "\n".join(ctx.get("todos", [])[:5]) or "Нет"
    issues_text = json.dumps(analysis.get("issues", []), ensure_ascii=False)
    priority = analysis.get("priority_task", "")

    # Memory: avoid re-picking files already targeted in the last N cycles.
    _recent_targets = []
    for _h in (backlog.get("history", []) or [])[-8:]:
        _f = _h.get("file")
        if _f and _f not in _recent_targets:
            _recent_targets.append(_f)
    _recent_text = ", ".join(_recent_targets) if _recent_targets else "нет"
    _files_list = files_list
    if _recent_targets:
        # Filter recently-handled files out of the candidate list.
        _files_list = "\n".join(
            ln for ln in files_list.split("\n")
            if not any(rt in ln for rt in _recent_targets)
        ) or files_list

    # Optional web research on the priority topic (best-effort, may be empty).
    _research_hint = _maybe_research(str(priority or "")[:80]) if priority else ""
    _skill_hint = _list_skill_names()

    prompt = (
        f"Ты — автономный кодер. Составь план на этот цикл.\n\n"
        f"Проблемы: {issues_text}\n"
        f"Приоритет: {priority}\n"
        f"TODO в коде:\n{todos_text}\n\n"
        f"⚠️ Уже обработаны недавно (НЕ выбирай их): {_recent_text}\n\n"
    )

    if backlog_text:
        prompt += f"Задачи в бэклоге:\n{backlog_text}\n\n"

    if _research_hint:
        prompt += f"📡 Актуальная информация из интернета по теме:\n{_research_hint}\n\n"
    if _skill_hint:
        prompt += f"🧩 Доступные скиллы проекта (можно использовать через coder_research.use_skill): {_skill_hint}\n\n"

    prompt += (
        f"Файлы проекта:\n{_files_list}\n\n"
        f"ПРАВИЛА:\n"
        f"1. code_needed ВСЕГДА true\n"
        f"2. Выбери ОДИН конкретный файл из списка\n"
        f"3. РАБОТАЙ ТОЛЬКО с файлами из aios_core/ (реальные модули ядра). НЕ выбирай tools/, octopus_core/, корневые скрипты.\n"
        f"4. ИЗБЕГАЙ корневых скриптов-раннеров и entry-point файлов — работай с библиотечным кодом\n"
        f"5. Дай ТОЧНУЮ, осмысленную инструкцию: добавь функцию/тест/фикс с конкретным поведением\n"
        f"6. НЕ создавай новый модуль, если можно улучшить существующий — рефакторинг предпочтительнее\n"
        f"7. Если есть задача в бэклоге — бери её\n"
        f"8. Если нет — найди TODO/FIXME в aios_core/ и исправь\n"
        f"6. Если нет TODO — улучши документацию, добавь тест, оптимизируй\n\n"
        f"Верни JSON:\n"
        f'{{\n'
        f'  "action": "fix|refactor|feature|test|docs",\n'
        f'  "description": "<что делаем и зачем>",\n'
        f'  "file": "<путь из списка>",\n'
        f'  "code_needed": true,\n'
        f'  "instruction": "<точная инструкция для кодера>",\n'
        f'  "backlog_task": "<номер задачи из бэклога если берёшь оттуда, иначе null>"\n'
        f'}}'
    )

    response = llm.chat([{"role": "user", "content": prompt}], system=system)

    try:
        if "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            plan = json.loads(response[start:end])

            # Mark backlog task as in-progress if taken
            task_idx = plan.get("backlog_task")
            if task_idx is not None:
                try:
                    idx = int(task_idx) - 1
                    if 0 <= idx < len(backlog.get("tasks", [])):
                        backlog["tasks"][idx]["status"] = "in_progress"
                except:
                    pass

            # Ensure code_needed is always True
            plan["code_needed"] = True
            return plan
    except:
        pass

    # Fallback: pick a random file with TODO and suggest fixing it
    todo_files = list(set(t.split(":")[0] for t in ctx.get("todos", [])))
    protected = {"run_coder_orchestrator.py", "tools/run_coder_orchestrator.py",
                 "run_auto_coder.py", "tools/run_auto_coder.py",
                 "run_telegram_bot.py", "tools/run_telegram_bot.py",
                 "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"}
    todo_files = [t for t in todo_files if t not in protected]
    target = todo_files[0] if todo_files else (real_files[0] if real_files else "aios_core/__init__.py")
    return {
        "action": "refactor",
        "description": "Improve code quality",
        "file": target,
        "code_needed": True,
        "instruction": "Review this file and improve code quality: add type hints, fix any issues, improve docstrings",
    }



def _pick_real_target(hint: str) -> str:
    """Return a real existing aios_core/ module for the coder to refactor.

    Prefers files that actually contain TODO/FIXME/HACK markers (real work),
    then rotates across aios_core/ avoiding files recently targeted (from
    backlog history), so cycles keep doing fresh real work instead of looping.
    """
    try:
        protected = {"aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py",
                     "aios_core/__init__.py"}
        # Files recently handled (from backlog history) to avoid re-looping.
        recent = set()
        try:
            bl = json.load(open(BACKLOG_FILE, encoding="utf-8"))
            for h in bl.get("history", [])[-12:]:
                f = h.get("file")
                if f:
                    recent.add(f)
        except Exception:
            pass

        # Scan aios_core/ for existing .py files, optionally with TODO markers.
        plain, with_todo = [], []
        for root, _dirs, files in os.walk(os.path.join(REPO_PATH, "aios_core")):
            for fn in files:
                if not fn.endswith(".py") or fn.startswith("__"):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), REPO_PATH)
                if rel in protected:
                    continue
                # Prefer files with real TODO/FIXME/HACK markers.
                try:
                    txt = open(os.path.join(root, fn), encoding="utf-8", errors="ignore").read()
                    has_marker = any(t in txt for t in ("TODO", "FIXME", "HACK", "XXX", "BUG"))
                except Exception:
                    has_marker = False
                (with_todo if has_marker else plain).append(rel)

        pool = with_todo or plain
        if not pool:
            return ""
        # Filter out recently-handled files.
        fresh = [f for f in pool if f not in recent]
        pool = fresh or pool
        import time
        pool.sort()
        idx = int(time.time()) % len(pool)
        return pool[idx]
    except Exception:
        return ""

def phase_code(plan: dict) -> dict:
    """Phase 3: Execute coding action if needed."""
    if not plan.get("code_needed") or not plan.get("file"):
        return {"status": "skipped", "reason": "Code not needed"}

    try:
        mod = get_coder()
    except Exception as e:
        print(f"    [CODE] Failed to load coder module: {e}")
        return {"status": "error", "error": f"Module load: {e}"}

    try:
        config = mod.CoderConfig.from_env()
        # Route model by task complexity: heavy tasks -> stronger model.
        _instr = str(plan.get("instruction", "")) + " " + str(plan.get("description", ""))
        _instr_l = _instr.lower()
        _heavy = any(k in _instr_l for k in (
            "security", "vulnerab", "encryption", "crypto", "auth", "permission",
            "concurrency", "async", "thread", "refactor large", "rewrite",
        ))
        _action = plan.get("action", "")
        if _heavy or _action in ("feature", "refactor"):
            # Heavy tasks: same stable model but allow more tokens for depth.
            config.llm_model = os.environ.get("LLM_MODEL_HEAVY", "gpt-4o-mini")
            config.max_tokens = int(os.environ.get("LLM_MAX_TOKENS_HEAVY", "6000"))
        else:
            config.llm_model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
            config.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4000"))
        config.llm_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY", "")
        if config.llm_api_key and config.llm_api_key.startswith("sk-or-"):
            config.llm_base_url = "https://openrouter.ai/api/v1"
        else:
            config.llm_base_url = os.environ.get("LLM_BASE_URL", config.llm_base_url)
        config.repo_path = REPO_PATH
        # max_tokens already set by model routing above; keep as-is.
        coder = mod.MetaCognitiveCoder(config)
    except Exception as e:
        print(f"    [CODE] Failed to init coder: {e}")
        return {"status": "error", "error": f"Init: {e}"}

    file_path = plan["file"]
    instruction = plan.get("instruction", plan.get("description", ""))

    # Clean file path
    file_path = file_path.lstrip("/").lstrip("./")
    # Sanitize: strip "file.py:NN" / "file.py:NN,MM" artifacts the LLM builds
    # from "path:line" TODO markers, and stray digits/punctuation.
    file_path = re.sub(r":\d+[,\s\d]*", "", file_path)  # remove :NN / :NN,MM
    file_path = re.sub(r"[^\w./-]+", "_", file_path)     # replace weird chars
    # Restrict to aios_core/ (real kernel code); fall back to aios_core/
    allowed_prefixes = ["aios_core/", "scripts/", "tools/", "tests/", "skills/", "platforms/", "docs/"]
    if not any(file_path.startswith(p) for p in allowed_prefixes):
        # If LLM hallucinated path, point into aios_core/ (not tools/)
        file_path = "aios_core/" + os.path.basename(file_path)
    # Must be exactly one .py suffix
    while file_path.endswith(".py.py"):
        file_path = file_path[:-3]
    if not file_path.endswith(".py"):
        file_path += ".py"

    # Protected internal files: never rewrite these (would break the pipeline).
    BLACKLIST = {
        "tools/run_coder_orchestrator.py",
        "run_coder_orchestrator.py",
        "run_auto_coder.py",
        "tools/run_auto_coder.py",
        "run_telegram_bot.py",
        "tools/run_telegram_bot.py",
        "aios_core/llm_balancer.py",
        "aios_core/meta_cognitive_self_coder.py",
    }
    if file_path in BLACKLIST:
        print(f"    [CODE] Protected file {file_path} is blacklisted -> skipping (no autogenerated module)")
        return {"status": "skipped", "reason": "protected file is blacklisted", "file": file_path}

    print(f"    [CODE] File: {file_path}")
    print(f"    [CODE] Instruction: {instruction[:80]}")

    try:
        full_path = os.path.join(REPO_PATH, file_path)
        if os.path.exists(full_path):
            print(f"    [CODE] Refactoring existing file...")
            change = coder.refactor_file(file_path, instruction)
        else:
            # The weak local LLM often hallucinates a path. Fall back to a real
            # existing aios_core/ module instead of skipping or inventing files.
            _fb = _pick_real_target(file_path)
            if _fb and os.path.exists(os.path.join(REPO_PATH, _fb)):
                file_path = _fb
                full_path = os.path.join(REPO_PATH, file_path)
                print(f"    [CODE] Hallucinated target -> falling back to real file: {file_path}")
                change = coder.refactor_file(file_path, instruction)
            else:
                print(f"    [CODE] Target {file_path} does not exist and no fallback found -> skipping")
                return {"status": "skipped", "reason": "target does not exist", "file": file_path}

        result = {
            "status": "success" if change.safe else "unsafe",
            "file": file_path,
            "code_length": len(change.new_code) if change.new_code else 0,
            "safe": change.safe,
            "warnings": change.warnings,
        }
        print(f"    [CODE] Result: {result['status']}, {result['code_length']} chars")
        if result.get("warnings"):
            print(f"    [CODE] Warnings: {result['warnings']}")
        return result
    except urllib.error.HTTPError as e:
        if e.code == 402:
            print(f"    [CODE] 402 Payment Required — trying fallback model...")
            try:
                config.llm_model = "mistralai/mistral-small-3.2-24b-instruct"
                coder2 = mod.MetaCognitiveCoder(config)
                full_path = os.path.join(REPO_PATH, file_path)
                if os.path.exists(full_path):
                    change = coder2.refactor_file(file_path, instruction)
                else:
                    print(f"    [CODE] Target {file_path} does not exist -> skipping")
                    return {"status": "skipped", "reason": "target does not exist", "file": file_path}
                return {
                    "status": "success" if change.safe else "unsafe",
                    "file": file_path,
                    "code_length": len(change.new_code) if change.new_code else 0,
                    "safe": change.safe,
                    "warnings": change.warnings,
                    "fallback": True,
                }
            except Exception as e2:
                return {"status": "error", "error": f"Fallback also failed: {e2}"}
        return {"status": "error", "error": str(e)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def phase_validate(code_result: dict) -> dict:
    """Phase 4: Validate changes."""
    if code_result.get("status") == "skipped":
        return {"status": "skipped"}

    if not code_result.get("safe", True):
        return {"status": "failed", "reason": "Safety check failed", "warnings": code_result.get("warnings", [])}

    # Syntax check on changed file
    if code_result.get("file"):
        full_path = os.path.join(REPO_PATH, code_result["file"])
        if os.path.exists(full_path):
            try:
                with open(full_path, "r") as f:
                    compile(f.read(), full_path, "exec")
            except SyntaxError as e:
                return {"status": "failed", "reason": f"Syntax error: {e}"}

            # Lint gate (non-blocking): run ruff on the changed file if available.
            _warnings = list(code_result.get("warnings") or [])
            try:
                import subprocess as _sp
                _ruff = _sp.run(["/opt/aios/.venv/bin/ruff", "check", "--select", "E,F", full_path],
                                capture_output=True, text=True, timeout=30)
                if _ruff.returncode != 0:
                    _warnings.append(f"ruff: {_ruff.stdout.strip()[:200]}")
            except Exception:
                pass
            return {"status": "passed", "warnings": _warnings}

    return {"status": "passed"}


def phase_commit(code_result: dict, plan: dict, validation: dict) -> dict:
    """Phase 5: Commit and push — full autonomous access."""
    code_ok = code_result.get("status") in ("success", "unsafe")

    if not code_ok:
        return {"status": "skipped", "reason": "No code generated"}

    file_path = code_result.get("file", "")
    desc = plan.get("description", "auto-code")[:80]
    action = plan.get("action", "update")

    # Git add all changes
    # Stage only source changes. Runtime data, credentials and unrelated files
    # must never be swept into an autonomous commit.
    allowed_prefixes = ("aios_core/", "aios_cli/", "scripts/", "tools/", "tests/", "skills/", "platforms/", "docs/", ".github/", "run_")
    # Collect changed paths robustly (diff for tracked, untracked via ls-files).
    changed = set()
    _diff = git_cmd("diff", "--name-only", "HEAD").splitlines()
    _untracked = git_cmd("ls-files", "--others", "--exclude-standard").splitlines()
    changed.update(x.strip() for x in _diff if x.strip())
    changed.update(x.strip() for x in _untracked if x.strip())
    safe_paths = [path for path in changed if path.startswith(allowed_prefixes) and not path.startswith(("run_telegram_bot.py", "tools/run_telegram_bot.py"))]
    blocked_paths = sorted(changed - set(safe_paths))
    if blocked_paths:
        print(f"    [COMMIT] excluded non-source paths: {', '.join(blocked_paths[:5])}")
    if safe_paths:
        git_cmd("add", "--", *safe_paths)

    # Check if there is something staged to commit.
    status_out = git_cmd("diff", "--cached", "--name-only")
    if not status_out.strip():
        return {"status": "nothing_to_commit", "full_cycle": True}

    # Commit
    commit_msg = f"auto-coder({action}): {desc}"
    commit_out = git_cmd("commit", "-m", commit_msg)
    print(f"    [COMMIT] {commit_out[:80]}")

    if "nothing to commit" in commit_out.lower():
        return {"status": "nothing_to_commit", "full_cycle": True}

    # Push is opt-in. Production agents must not publish changes merely because
    # they were able to create a local commit.
    if os.environ.get("AIOS_AUTO_PUSH", "false").lower() not in {"1", "true", "yes"}:
        return {"status": "commit_only", "commit": commit_out[:120], "full_cycle": True}

    # Push to current branch
    branch = git_cmd("branch", "--show-current") or "main"
    push_out = git_cmd("push", "origin", branch)
    print(f"    [PUSH] {push_out[:80]}")
    pushed = "error" not in push_out.lower()

    if not pushed:
        import time
        time.sleep(3)
        push_out = git_cmd("push", "origin", branch)
        pushed = "error" not in push_out.lower()

    return {
        "status": "pushed" if pushed else "commit_only",
        "commit": commit_out[:120],
        "full_cycle": True,
    }


def build_report(cycle_num: int, ctx: dict, analysis: dict, plan: dict,
                 code_result: dict, validation: dict, commit_result: dict) -> str:
    """Build human-readable report."""
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    health_raw = analysis.get("health_score", 5)
    try:
        health = int(health_raw)
    except (TypeError, ValueError):
        health = 5
    health_emoji = "🟢" if health >= 8 else "🟡" if health >= 5 else "🔴"

    lines = []
    lines.append(f"🧠 <b>AIOS Coder Orchestrator — цикл #{cycle_num}</b>")
    lines.append(f"<i>{now}</i>")
    lines.append("")

    # Put a plain-language outcome first, before technical diagnostics.
    action = plan.get("action", "monitor")
    description = str(plan.get("description", "")).strip() or "проверил состояние проекта"
    code_status = code_result.get("status", "skipped")
    validation_status = validation.get("status", "skipped")
    if code_status == "success" and validation_status == "passed":
        human_summary = f"В этом цикле кодер выполнил работу: {description}. Изменения проверены успешно."
    elif code_status == "success":
        human_summary = f"Кодер внёс изменения: {description}. Проверка требует внимания: {validation.get('reason', 'нет итогового статуса')}."
    elif code_status == "error":
        human_summary = f"Кодер пытался выполнить задачу «{description}», но столкнулся с ошибкой: {code_result.get('error', 'неизвестная ошибка')}."
    elif action == "monitor":
        human_summary = "Кодер проверил проект; изменений в этом цикле не потребовалось."
    else:
        human_summary = f"Кодер проанализировал задачу: {description}. Изменения в код не вносились."
    lines.append(f"<b>Кратко:</b> {human_summary}")
    lines.append("")

    # Health
    lines.append(f"{health_emoji} <b>Здоровье проекта: {health}/10</b>")
    lines.append(f"  {analysis.get('summary', '')}")
    lines.append("")

    # Issues
    issues = analysis.get("issues", [])
    if issues:
        lines.append(f"🐛 <b>Проблемы ({len(issues)}):</b>")
        for i, issue in enumerate(issues[:3], 1):
            lines.append(f"  {i}. {issue}")
        lines.append("")

    # Plan
    action = plan.get("action", "monitor")
    action_emoji = {"fix": "🔧", "refactor": "♻️", "review": "🔍", "monitor": "👁️"}.get(action, "📋")
    lines.append(f"{action_emoji} <b>План:</b> {plan.get('description', '')}")

    if plan.get("code_needed"):
        lines.append(f"  📁 Файл: <code>{plan.get('file', '?')}</code>")
    lines.append("")

    # Code result
    code_status = code_result.get("status", "skipped")
    if code_status == "success":
        lines.append(f"💻 <b>Код:</b> ✅ Написан ({code_result.get('code_length', 0)} символов)")
    elif code_status == "unsafe":
        lines.append(f"💻 <b>Код:</b> ⚠️ Написан, но не прошёл safety check")
    elif code_status == "error":
        lines.append(f"💻 <b>Код:</b> ❌ Ошибка: {code_result.get('error', '')}")
    else:
        lines.append(f"💻 <b>Код:</b> не потребовался")

    # Validation
    val_status = validation.get("status", "skipped")
    if val_status == "passed":
        lines.append(f"✅ <b>Валидация:</b> OK")
    elif val_status == "failed":
        lines.append(f"❌ <b>Валидация:</b> {validation.get('reason', '')}")

    # Commit
    commit_status = commit_result.get("status", "skipped")
    if commit_status == "pushed":
        full = " (полный цикл ✅)" if commit_result.get("full_cycle") else ""
        lines.append(f"🚀 <b>Git:</b> закоммичено и запушено{full}")
    elif commit_status == "commit_only":
        lines.append(f"📝 <b>Git:</b> закоммичено (push не удался)")
    elif commit_status == "nothing_to_commit":
        lines.append(f"📝 <b>Git:</b> изменений нет")

    lines.append("")
    lines.append(f"<i>⏳ Следующий цикл через 5 мин</i>")

    return "\n".join(lines)


def _is_llm_failed_cycle(analysis: dict) -> bool:
    asum = str(analysis.get("summary", ""))
    return (
        "LLM Error" in asum
        or "Все LLM-провайдеры" in asum
        or "LLM endpoints недоступны" in asum
        or asum.startswith("error")
        or analysis.get("health_score") == 0
    )


def _is_llm_error_str(text: str) -> bool:
    text = text.lower()
    return (
        "Все LLM" in text
        or "LLM endpoints" in text
        or "token expired" in text
        or "payment required" in text
        or "insufficient" in text
        or "auth failed" in text
    )


def run_cycle():
    """Execute full orchestrator cycle."""
    global _cycle_count, _consecutive_errors, _last_llm_error_cycle
    _cycle_count += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"[{now}] Coder Orchestrator — Cycle #{_cycle_count}")
    print(f"{'='*60}")

    llm = LLMClient()
    if not llm.api_key:
        tg_send("❌ <b>Coder Orchestrator</b>\n\nLLM API ключ не настроен")
        return

    ctx = get_project_context()
    backlog = load_backlog()
    backlog["cycle_count"] = backlog.get("cycle_count", 0) + 1

    # Phase 1: Analyze
    print("  [1/5] ANALYZE — анализ проекта...")
    try:
        analysis = phase_analyze(llm, ctx, backlog)
    except Exception as e:
        print(f"  [WARN] Phase 1 failed: {e}")
        analysis = {"health_score": 0, "summary": f"error:{e}", "issues": [], "opportunities": [], "priority_task": "", "new_tasks": []}

    if _is_llm_failed_cycle(analysis):
        _consecutive_errors += 1
        _last_llm_error_cycle = _cycle_count
        print(f"  [WARN] LLM unavailable. Errors: {_consecutive_errors}/{MAX_ERRORS}")
        if _consecutive_errors >= MAX_ERRORS:
            _stop = (
                chr(9940)
                + " <b>AUTO-STOP: "
                + str(MAX_ERRORS)
                + " errors in a row!</b>\n"
                + "LLM not responding.\n"
                + "<code>systemctl start aios-auto-coder</code>"
            )
            tg_send(_stop)
            import subprocess as _sp3
            _sp3.run(["systemctl", "stop", "aios-auto-coder"], timeout=10)
            sys.exit(1)
        _wait = 600
        print(f"  [BACKOFF] Waiting {_wait}s before next cycle")
        if _consecutive_errors == 1 or _consecutive_errors % 10 == 0:
            tg_send(
                chr(9888) + " <b>Coder Orchestrator</b>\n\n"
                "LLM временно недоступен. Цикл пропущен.\n"
                "Проверьте ключи: /llm_status"
            )
        time.sleep(_wait)
        return
    _consecutive_errors = 0

    print(f"    Health: {analysis.get('health_score', '?')}/10")
    print(f"    Issues: {len(analysis.get('issues', []))}")

    # Phase 2: Plan
    print("  [2/5] PLAN — составление плана...")
    try:
        plan = phase_plan(llm, analysis, ctx, backlog)
    except Exception as e:
        print(f"  [WARN] Phase 2 failed: {e}")
        plan = {"action": "monitor", "description": "LLM unavailable", "file": "", "code_needed": False, "instruction": ""}
    print(f"    Action: {plan.get('action', '?')}")
    print(f"    Code needed: {plan.get('code_needed', False)}")

    # Phase 3: Code
    print("  [3/5] CODE — генерация/рефакторинг...")
    try:
        code_result = phase_code(plan)
    except Exception as e:
        print(f"  [WARN] Phase 3 failed: {e}")
        code_result = {"status": "error", "error": str(e), "file": plan.get("file", "")}
    print(f"    Status: {code_result.get('status', '?')}")
    if code_result.get("status") == "error" and _is_llm_error_str(code_result.get("error", "")):
        _consecutive_errors += 1
        _last_llm_error_cycle = _cycle_count
        if _consecutive_errors >= MAX_ERRORS:
            _stop = (
                chr(9940)
                + " <b>AUTO-STOP: "
                + str(MAX_ERRORS)
                + " errors in a row!</b>\n"
                + "LLM not responding.\n"
                + "<code>systemctl start aios-auto-coder</code>"
            )
            tg_send(_stop)
            import subprocess as _sp3
            _sp3.run(["systemctl", "stop", "aios-auto-coder"], timeout=10)
            sys.exit(1)
        _wait = 600
        print(f"  [BACKOFF] LLM error in code phase. Waiting {_wait}s before next cycle")
        if _consecutive_errors == 1 or _consecutive_errors % 10 == 0:
            tg_send(
                chr(9888) + " <b>Coder Orchestrator</b>\n\n"
                "LLM временно недоступен. Цикл пропущен.\n"
                "Проверьте ключи: /llm_status"
            )
        time.sleep(_wait)
        return
    _consecutive_errors = 0

    # Phase 4: Validate
    print("  [4/5] VALIDATE — проверка...")
    try:
        validation = phase_validate(code_result)
    except Exception as e:
        print(f"  [WARN] Phase 4 failed: {e}")
        validation = {"status": "failed", "reason": str(e)}
    print(f"    Status: {validation.get('status', '?')}")

    # Phase 5: Commit
    print("  [5/5] COMMIT — деплой...")
    try:
        commit_result = phase_commit(code_result, plan, validation)
    except Exception as e:
        print(f"  [WARN] Phase 5 failed: {e}")
        commit_result = {"status": "skipped", "reason": str(e)}
    print(f"    Status: {commit_result.get('status', '?')}")

    # Build and send report
    # Save backlog with history
    history_entry = {
        "cycle": backlog["cycle_count"],
        "action": plan.get("action", "?"),
        "file": plan.get("file", "?"),
        "description": plan.get("description", "?")[:80],
        "status": commit_result.get("status", "skipped"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    backlog["history"].append(history_entry)
    backlog["history"] = backlog["history"][-50:]  # keep last 50
    if commit_result.get("status") == "pushed":
        backlog["completed"] = backlog.get("completed", 0) + 1
        # Remove completed task from backlog
        backlog["tasks"] = [t for t in backlog.get("tasks", []) if t.get("status") != "in_progress"]
    elif commit_result.get("status") == "skipped" and code_result.get("status") == "error":
        backlog["failed"] = backlog.get("failed", 0) + 1
        # Self-learning: capture the failure as a lesson for future cycles.
        _add_lesson(
            backlog,
            _extract_lesson(
                plan.get("action", "code"),
                plan.get("description", ""),
                code_result.get("error", "unknown error"),
            ),
        )
    elif validation.get("status") == "failed":
        _add_lesson(
            backlog,
            _extract_lesson("validate", plan.get("description", ""), validation.get("reason", "")),
        )
    save_backlog(backlog)

    report = build_report(_cycle_count, ctx, analysis, plan, code_result, validation, commit_result)
    print(f"\n  Sending report ({len(report)} chars)...")
    if tg_send(report):
        print("  ✅ Report sent to Telegram")
    else:
        print("  ❌ Failed to send report")

    # --- Enhanced alerts ---
    _cs = code_result.get("status", "skipped")
    _vs = validation.get("status", "skipped")
    _ms = commit_result.get("status", "skipped")
    try:
        if _cs == "error":
            tg_send(
                "🚨 <b>AIOS Coder: ОШИБКА</b>\n"
                f"Фаза CODE завершилась ошибкой:\n<code>{code_result.get('error','')[:300]}</code>"
            )
        elif _vs == "failed":
            tg_send(
                "⚠️ <b>AIOS Coder: Валидация не прошла</b>\n"
                f"{validation.get('reason','')[:200]}"
            )
        elif _ms in ("pushed", "commit_only"):
            tg_send(
                "🚀 <b>AIOS Coder: новый коммит</b>\n"
                f"Файл: <code>{code_result.get('file','?')}</code>\n"
                f"Статус: {_ms}"
            )
    except Exception:
        pass

    print(f"[{now}] Cycle #{_cycle_count} complete")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AIOS Coder Orchestrator")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Cycle interval (default: 60s = 1min)")
    args = parser.parse_args()

    print(f"🧠 AIOS Coder Orchestrator v1.0")
    print(f"   Cycle: {args.interval}s")
    print(f"   LLM: {os.environ.get('LLM_MODEL', 'not set')}")
    print(f"   TG: {'OK' if TG_TOKEN and TG_CHAT_ID else 'NOT CONFIGURED'}")

    if args.once:
        run_cycle()
    else:
        while True:
            try:
                run_cycle()
            except KeyboardInterrupt:
                print("\nStopped")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()
            time.sleep(args.interval)
