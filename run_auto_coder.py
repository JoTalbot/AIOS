"""
AIOS Auto-Coder — автономный цикл кодера (каждые 5 минут).

Анализирует проект, ищет проблемы, генерирует отчёт и отправляет в Telegram.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
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
        print(f"[WARN] No TG_TOKEN or CHAT_ID. Message: {text[:200]}")
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
        print(f"[ERROR] Telegram send failed: {e}")
        return False


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------
class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY", "")
        self.base_url = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.environ.get("LLM_MODEL", "deepseek/deepseek-chat-v3-0324")

    def chat(self, messages: list, system: str = "") -> str:
        if not self.api_key:
            return "LLM_API_KEY not configured"
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        payload = json.dumps({
            "model": self.model,
            "messages": all_messages,
            "max_tokens": 2000,
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
                "X-Title": "AIOS AutoCoder",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"LLM Error: {e}"


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------
def git_log(n: int = 5) -> str:
    try:
        r = subprocess.run(
            ["git", "log", f"-{n}", "--oneline", "--no-decorate"],
            cwd=REPO_PATH, capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


def git_diff_stat() -> str:
    try:
        r = subprocess.run(
            ["git", "diff", "--stat", "HEAD"],
            cwd=REPO_PATH, capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


def git_status_short() -> str:
    try:
        r = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_PATH, capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Code analysis
# ---------------------------------------------------------------------------
def get_recent_changes() -> dict:
    """Get info about recent changes for LLM analysis."""
    status = git_status_short()
    diff_stat = git_diff_stat()
    log = git_log(3)

    # Get list of recently modified Python files
    modified_files = []
    for line in status.split("\n"):
        line = line.strip()
        if line and line.endswith(".py"):
            # Extract filename (skip status chars)
            fname = line[2:].strip() if len(line) > 2 else ""
            if fname:
                modified_files.append(fname)

    # Read first 50 lines of most recently modified files (max 3)
    file_previews = {}
    for f in modified_files[:3]:
        fpath = os.path.join(REPO_PATH, f)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as fp:
                    lines = fp.readlines()[:50]
                    file_previews[f] = "".join(lines)
            except Exception:
                pass

    return {
        "git_status": status,
        "git_diff_stat": diff_stat,
        "git_log": log,
        "modified_files": modified_files,
        "file_previews": file_previews,
    }


def analyze_project(llm: LLMClient, changes: dict) -> str:
    """Ask LLM to analyze project state and suggest improvements."""

    status_text = changes["git_status"] or "No uncommitted changes"
    log_text = changes["git_log"] or "No recent commits"

    # Build file previews text
    previews_text = ""
    for fname, preview in changes["file_previews"].items():
        previews_text += f"\n\n--- {fname} (first 50 lines) ---\n{preview}"

    system_prompt = (
        "Ты — AIOS AutoCoder, автономный агент-кодер. "
        "Отвечай на русском языке, кратко и по делу. "
        "Твоя задача — анализировать состояние проекта и давать конкретные рекомендации."
    )

    user_prompt = (
        f"Проанализируй текущее состояние проекта AIOS.\n\n"
        f"=== Git Status ===\n{status_text}\n\n"
        f"=== Последние коммиты ===\n{log_text}\n\n"
        f"=== Превью файлов ==={previews_text}\n\n"
        f"Дай краткий отчёт:\n"
        f"1. 📊 Общее состояние проекта (1-2 предложения)\n"
        f"2. 🐛 Найденные проблемы или баги (если есть)\n"
        f"3. ⚡ Что можно улучшить прямо сейчас (конкретные действия)\n"
        f"4. 🎯 Приоритетная задача на следующий цикл\n"
        f"5. 📈 Оценка здоровья проекта (1-10)\n\n"
        f"Будь конкретен, упоминай имена файлов и функций."
    )

    return llm.chat([{"role": "user", "content": user_prompt}], system=system_prompt)


def check_for_bugs(llm: LLMClient, changes: dict) -> str:
    """Check modified files for potential bugs."""
    if not changes["file_previews"]:
        return ""

    files_text = ""
    for fname, preview in changes["file_previews"].items():
        files_text += f"\n\n--- {fname} ---\n{preview}"

    system_prompt = (
        "Ты — senior Python разработчик. Ищи баги, проблемы безопасности "
        "и ошибки типов в коде. Отвечай на русском, кратко."
    )

    user_prompt = (
        f"Проверь эти файлы на баги и проблемы:\n{files_text}\n\n"
        f"Если всё ОК — напиши '✅ Проблем не найдено'.\n"
        f"Если есть баги — опиши конкретную проблему и как исправить (макс 3 проблемы)."
    )

    return llm.chat([{"role": "user", "content": user_prompt}], system=system_prompt)


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------
def run_cycle():
    """Run one auto-coder cycle."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n{'='*60}")
    print(f"[{now}] Auto-Coder cycle started")
    print(f"{'='*60}")

    llm = LLMClient()
    if not llm.api_key:
        msg = "❌ <b>Auto-Coder</b>\n\nLLM API ключ не настроен (OPENROUTER_API_KEY)"
        tg_send(msg)
        return

    # Gather project state
    changes = get_recent_changes()
    print(f"  Modified files: {len(changes['modified_files'])}")
    print(f"  File previews: {list(changes['file_previews'].keys())}")

    # Analysis
    print("  Running LLM analysis...")
    analysis = analyze_project(llm, changes)

    # Bug check
    print("  Running bug check...")
    bug_check = check_for_bugs(llm, changes)

    # Build report
    report_lines = []
    report_lines.append(f"🧠 <b>Auto-Coder — {now}</b>")
    report_lines.append("")
    report_lines.append("<b>Кратко:</b> Кодер проверил изменения и состояние проекта; подробности и найденные риски — ниже.")
    report_lines.append("")
    report_lines.append(f"<b>📋 Анализ проекта:</b>")
    report_lines.append(analysis)

    if bug_check and "Проблем не найдено" not in bug_check:
        report_lines.append("")
        report_lines.append(f"<b>🐛 Проверка багов:</b>")
        report_lines.append(bug_check)
    elif bug_check:
        report_lines.append("")
        report_lines.append(f"🐛 {bug_check}")

    report_lines.append("")
    report_lines.append(f"<i>Следующий цикл через 5 минут</i>")

    report = "\n".join(report_lines)

    # Send to Telegram
    print(f"  Sending report ({len(report)} chars)...")
    if tg_send(report):
        print("  ✅ Report sent to Telegram")
    else:
        print("  ❌ Failed to send report")

    print(f"[{now}] Cycle complete\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AIOS Auto-Coder")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=300, help="Cycle interval in seconds (default: 300)")
    args = parser.parse_args()

    print(f"🧠 AIOS Auto-Coder started (interval={args.interval}s)")
    print(f"   Repo: {REPO_PATH}")
    print(f"   LLM: {os.environ.get('LLM_MODEL', 'not set')}")
    print(f"   TG Chat: {TG_CHAT_ID or 'not set'}")

    if args.once:
        run_cycle()
    else:
        while True:
            try:
                run_cycle()
            except KeyboardInterrupt:
                print("\n👋 Auto-Coder stopped")
                break
            except Exception as e:
                print(f"[ERROR] Cycle failed: {e}")
                import traceback
                traceback.print_exc()
            time.sleep(args.interval)
