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
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

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
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except:
        return ""

def get_project_context() -> dict:
    return {
        "git_status": git_cmd("status", "--short") or "clean",
        "git_log": git_cmd("log", "-5", "--oneline", "--no-decorate") or "no commits",
        "branch": git_cmd("branch", "--show-current") or "main",
        "files": len(git_cmd("status", "--short").split("\n")) if git_cmd("status", "--short") else 0,
    }


# ---------------------------------------------------------------------------
# ORCHESTRATOR CYCLE
# ---------------------------------------------------------------------------

# Track cycle state
_cycle_count = 0
_previous_issues = []

def phase_analyze(llm: LLMClient, ctx: dict) -> dict:
    """Phase 1: LLM analyzes project state."""
    system = (
        "Ты — AIOS Coder Orchestrator, автономный AI-разработчик. "
        "Анализируй проект и давай конкретные рекомендации. Отвечай на русском."
    )

    prompt = (
        f"Проанализируй состояние проекта AIOS.\n\n"
        f"Git status:\n{ctx['git_status']}\n\n"
        f"Последние коммиты:\n{ctx['git_log']}\n\n"
        f"Ветка: {ctx['branch']}, изменённых файлов: {ctx['files']}\n\n"
        f"Верни JSON (строго, без markdown):\n"
        f'{{\n'
        f'  "health_score": <1-10>,\n'
        f'  "summary": "<1-2 предложения о состоянии>",\n'
        f'  "issues": ["<проблема 1>", "<проблема 2>"],\n'
        f'  "opportunities": ["<что можно улучшить>"],\n'
        f'  "priority_task": "<самая важная задача сейчас>"\n'
        f'}}'
    )

    response = llm.chat([{"role": "user", "content": prompt}], system=system)

    # Parse JSON from response
    try:
        # Try to extract JSON
        if "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            return json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "health_score": 5,
        "summary": response[:200],
        "issues": [],
        "opportunities": [],
        "priority_task": "Продолжить мониторинг",
    }


def phase_plan(llm: LLMClient, analysis: dict, ctx: dict) -> dict:
    """Phase 2: LLM creates action plan."""
    issues = analysis.get("issues", [])
    priority = analysis.get("priority_task", "")

    if not issues and not priority:
        return {"action": "monitor", "description": "Всё ок, мониторинг", "file": "", "code_needed": False}

    system = (
        "Ты — AI-архитектор автономной системы. Составь план действий. "
        "АГРЕССИВНО предлагай улучшения кодом — добавляй функции, исправляй баги, "
        "улучшай документацию, добавляй тесты, оптимизируй. "
        "Почти всегда code_needed должен быть true. "
        "Указывай конкретный файл и конкретную инструкцию что изменить. "
        "Отвечай JSON без markdown."
    )

    prompt = (
        f"На основе анализа проекта, составь план:\n\n"
        f"Проблемы: {json.dumps(issues, ensure_ascii=False)}\n"
        f"Приоритет: {priority}\n\n"
        f"Верни JSON:\n"
        f'{{\n'
        f'  "action": "fix|refactor|monitor|review",\n'
        f'  "description": "<что делаем и зачем>",\n'
        f'  "file": "<путь к файлу если нужен код>",\n'
        f'  "code_needed": true/false,\n'
        f'  "instruction": "<инструкция для кодера если code_needed>"\n'
        f'}}'
    )

    response = llm.chat([{"role": "user", "content": prompt}], system=system)

    try:
        if "{" in response:
            start = response.index("{")
            end = response.rindex("}") + 1
            return json.loads(response[start:end])
    except:
        pass

    return {"action": "monitor", "description": priority or "Мониторинг", "file": "", "code_needed": False}


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
        # Force model from orchestrator env
        config.llm_model = os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick")
        config.llm_api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY", "")
        config.llm_base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        config.repo_path = REPO_PATH
        config.max_tokens = 1500  # conserve credits
        coder = mod.MetaCognitiveCoder(config)
    except Exception as e:
        print(f"    [CODE] Failed to init coder: {e}")
        return {"status": "error", "error": f"Init: {e}"}

    file_path = plan["file"]
    instruction = plan.get("instruction", plan.get("description", ""))

    # Clean file path
    file_path = file_path.lstrip("/").lstrip("./")
    # Restrict to project directories
    allowed_prefixes = ["aios_core/", "scripts/", "tools/", "tests/", "skills/", "platforms/", "docs/"]
    if not any(file_path.startswith(p) for p in allowed_prefixes):
        # If LLM hallucinated path, put it in tools/
        file_path = "tools/" + os.path.basename(file_path)
    # Must be .py
    if not file_path.endswith(".py"):
        file_path += ".py"

    print(f"    [CODE] File: {file_path}")
    print(f"    [CODE] Instruction: {instruction[:80]}")

    try:
        full_path = os.path.join(REPO_PATH, file_path)
        if os.path.exists(full_path):
            print(f"    [CODE] Refactoring existing file...")
            change = coder.refactor_file(file_path, instruction)
        else:
            print(f"    [CODE] Generating new file...")
            change = coder.generate_code(instruction, target_path=file_path)

        result = {
            "status": "success" if change.safe else "unsafe",
            "file": file_path,
            "code_length": len(change.new_code) if change.new_code else 0,
            "safe": change.safe,
            "warnings": change.warnings,
        }
        print(f"    [CODE] Result: {result['status']}, {result['code_length']} chars")
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
                    change = coder2.generate_code(instruction, target_path=file_path)
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
                return {"status": "passed"}
            except SyntaxError as e:
                return {"status": "failed", "reason": f"Syntax error: {e}"}

    return {"status": "passed"}


def phase_commit(code_result: dict, plan: dict, validation: dict) -> dict:
    """Phase 5: Commit and push — full autonomous access."""
    code_ok = code_result.get("status") in ("success", "unsafe")
    val_ok = validation.get("status") in ("passed", "skipped")

    if not code_ok:
        return {"status": "skipped", "reason": "No code generated"}

    file_path = code_result.get("file", "")
    desc = plan.get("description", "auto-code")[:80]
    action = plan.get("action", "update")

    # Git add + commit
    git_cmd("add", file_path)
    git_cmd("add", "-A")  # catch any side effects
    commit_msg = f"auto-coder({action}): {desc}"
    commit_out = git_cmd("commit", "-m", commit_msg)

    if "nothing to commit" in commit_out.lower():
        return {"status": "nothing_to_commit", "full_cycle": True}

    # Always push
    push_out = git_cmd("push", "origin", "main")
    pushed = push_out != "" and "error" not in push_out.lower()

    if not pushed:
        # Retry once
        import time
        time.sleep(2)
        push_out = git_cmd("push", "origin", "main")
        pushed = push_out != "" and "error" not in push_out.lower()

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


def run_cycle():
    """Execute full orchestrator cycle."""
    global _cycle_count
    _cycle_count += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"[{now}] Coder Orchestrator — Cycle #{_cycle_count}")
    print(f"{'='*60}")

    llm = LLMClient()
    if not llm.api_key:
        tg_send("❌ <b>Coder Orchestrator</b>\n\nLLM API ключ не настроен")
        return

    # Phase 1: Analyze
    print("  [1/5] ANALYZE — анализ проекта...")
    ctx = get_project_context()
    analysis = phase_analyze(llm, ctx)
    print(f"    Health: {analysis.get('health_score', '?')}/10")
    print(f"    Issues: {len(analysis.get('issues', []))}")

    # Phase 2: Plan
    print("  [2/5] PLAN — составление плана...")
    plan = phase_plan(llm, analysis, ctx)
    print(f"    Action: {plan.get('action', '?')}")
    print(f"    Code needed: {plan.get('code_needed', False)}")

    # Phase 3: Code
    print("  [3/5] CODE — генерация/рефакторинг...")
    code_result = phase_code(plan)
    print(f"    Status: {code_result.get('status', '?')}")

    # Phase 4: Validate
    print("  [4/5] VALIDATE — проверка...")
    validation = phase_validate(code_result)
    print(f"    Status: {validation.get('status', '?')}")

    # Phase 5: Commit
    print("  [5/5] COMMIT — деплой...")
    commit_result = phase_commit(code_result, plan, validation)
    print(f"    Status: {commit_result.get('status', '?')}")

    # Build and send report
    report = build_report(_cycle_count, ctx, analysis, plan, code_result, validation, commit_result)
    print(f"\n  Sending report ({len(report)} chars)...")
    if tg_send(report):
        print("  ✅ Report sent to Telegram")
    else:
        print("  ❌ Failed to send report")

    print(f"[{now}] Cycle #{_cycle_count} complete")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AIOS Coder Orchestrator")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=10, help="Cycle interval (default: 10s)")
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
