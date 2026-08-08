"""Coder-команды Telegram-бота (выделено из run_telegram_bot.py).

Статус MetaCognitiveCoder, генерация/ревью/фикс кода.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from tg_bot.common import _safe

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_coder_mod = None


def _get_coder_module():
    """Load MetaCognitiveCoder module."""
    global _coder_mod
    if _coder_mod is not None:
        return _coder_mod
    mod_name = "aios_core.meta_cognitive_self_coder"
    spec = importlib.util.spec_from_file_location(
        mod_name, str(PROJECT_ROOT / "aios_core" / "meta_cognitive_self_coder.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__name__ = mod_name
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    _coder_mod = mod
    return mod


@_safe
def cmd_coder_status() -> str:
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    s = coder.status()
    lines = []
    lines.append("🧠 <b>MetaCognitiveCoder v" + str(s.get("version", "?")) + "</b>")
    lines.append("")
    lines.append("  🤖 Модель: <code>" + str(s.get("llm_model", "?")) + "</code>")
    api_status = "✅ настроен" if s.get("llm_configured") else "❌ нет ключа"
    lines.append("  🔑 API: " + api_status)
    lines.append("  📁 Репозиторий: <code>" + str(s.get("repo_path", "?")) + "</code>")
    lines.append("  📝 Изменений: " + str(s.get("changes_made", 0)))
    lines.append("  🔄 Auto-commit: " + ("✅" if s.get("auto_commit") else "❌"))
    lines.append("  🚀 Auto-push: " + ("✅" if s.get("auto_push") else "❌"))
    return "\n".join(lines)


@_safe
def cmd_code_generate(args: str) -> str:
    if not args.strip():
        return "ℹ️ Использование: <code>/code Generate a function that...</code>"
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    change = coder.generate_code(args.strip())
    safe_status = "✅ Безопасно" if change.safe else "⚠️ Опасно"
    warn_list = change.warnings if change.warnings else ["Нет"]
    code_preview = change.new_code[:300].replace("<", "&lt;").replace(">", "&gt;")
    lines = []
    lines.append("🧠 <b>Код сгенерирован</b>")
    lines.append("")
    lines.append("  Безопасность: " + safe_status)
    lines.append("  Предупреждения:")
    for w in warn_list:
        lines.append("    • " + str(w))
    lines.append("")
    lines.append("<b>Код</b> (" + str(len(change.new_code)) + " символов):")
    lines.append("<pre>" + code_preview + "...</pre>")
    return "\n".join(lines)


@_safe
def cmd_code_review(args: str) -> str:
    file_path = args.strip()
    if not file_path:
        return "ℹ️ Использование: <code>/review run_telegram_bot.py</code>"
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    review = coder.review_code(file_path)
    lines = []
    lines.append("📋 <b>Code Review: " + file_path + "</b>")
    lines.append("")
    lines.append(review[:3500])
    return "\n".join(lines)


@_safe
def cmd_code_fix(args: str) -> str:
    parts = args.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "ℹ️ Использование: <code>/fix file.py описание бага или traceback</code>"
    file_path, bug_desc = parts
    mod = _get_coder_module()
    coder = mod.MetaCognitiveCoder(mod.CoderConfig.from_env())
    change = coder.fix_bug(file_path, bug_desc)
    safe_status = "✅ Исправлено" if change.safe else "⚠️ Ошибка безопасности"
    lines = []
    lines.append("🔧 <b>Bug Fix: " + file_path + "</b>")
    lines.append("")
    lines.append("  Статус: " + safe_status)
    lines.append("  Предупреждения: " + str(change.warnings or "Нет"))
    lines.append("  Размер кода: " + str(len(change.new_code)) + " символов")
    return "\n".join(lines)
