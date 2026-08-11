"""LLM-чат: режимы, консоль, skills, история (выделено из run_telegram_bot.py)."""
from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from tg_bot.common import PROJECT_ROOT, _esc_tg, _smart_model


_chat_history: dict[int, list[dict]] = {}  # chat_id -> message history


MAX_HISTORY = 20  # keep last 20 messages per chat


def _is_model_identity_question(text: str) -> bool:
    """Recognise direct questions about the active LLM backend."""
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    patterns = (
        r"какая (?:ты |у тебя )?модель",
        r"что (?:ты )?за модель",
        r"на какой модели (?:ты )?работаешь",
        r"какой (?:у тебя )?(?:llm|ии)",
        r"назови (?:свою )?модель",
        r"which model (?:are you|do you use)",
        r"what model (?:are you|do you use)",
    )
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)


def _model_identity_reply() -> str:
    """Return factual runtime metadata instead of asking an LLM to self-identify."""
    served_model = "colab/qwen2.5-coder"
    try:
        cfg = json.loads((PROJECT_ROOT / "data" / ".llm_keys.json").read_text(encoding="utf-8"))
        configured = cfg.get("colab_llm", {})
        served_model = str(configured.get("model") or served_model)
    except Exception:
        pass
    display_model = (
        "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
        if served_model == "colab/qwen2.5-coder"
        else served_model
    )
    return (
        "Я — Лиза, ассистент AIOS. Основной backend этого чата сейчас — "
        + display_model
        + " в Google Colab (API-модель: " + served_model + "). "
        "Запросы проходят через LLMBalancer; если Colab недоступен, возможен "
        "автоматический fallback на другого провайдера. Я не GPT-4 — прошлый "
        "ответ был ошибкой самоидентификации модели."
    )


def _llm_status() -> str:
    """Return LLM provider status without consuming credits."""
    import importlib.util as _iu, sys as _sys
    try:
        spec = _iu.spec_from_file_location("lb_s", str(PROJECT_ROOT / "aios_core" / "llm_balancer.py"))
        mod = _iu.module_from_spec(spec)
        _sys.modules["lb_s"] = mod
        spec.loader.exec_module(mod)
        b = mod.LLMBalancer()
        s = b.status()
        lines = [chr(128268) + " <b>LLM Providers</b>", ""]
        lines.append("Requests: " + str(s.get("total_requests", 0)))
        lines.append("Errors: " + str(s.get("total_errors", 0)))
        lines.append("")
        for pn, pd in s.get("providers", {}).items():
            a = pd.get("keys_available", 0)
            t = pd.get("keys_total", 0)
            em = chr(9989) if a > 0 else chr(10060)
            lines.append(em + " <b>" + pn.upper() + "</b>: " + str(a) + "/" + str(t) + " keys")
            for kk, vv in pd.items():
                if kk.startswith("key_"):
                    avail = vv.get("available", False)
                    errs = vv.get("errors", 0)
                    last = vv.get("last_error", "")
                    status_em = chr(9989) if avail else chr(10060)
                    lines.append("   " + status_em + " " + kk + " errors=" + str(errs) + ("" if not last else " last=" + last[:40]))
        return "\n".join(lines)
    except Exception as e:
        return chr(10060) + " " + str(e)


def _cmd_llm_mode(args: str, chat_id: int) -> str:
    """Переключение режима LLM в чате: auto (балансер) / gemini (Gemini Web в браузере)."""
    from aios_core.llm_gemini_web import gemini_web_status, get_llm_mode, set_llm_mode
    mode = (args or "").strip().lower()
    if mode in ("auto", "balancer", "default", "standard", "obichny", "обычный"):
        set_llm_mode(chat_id, "auto")
        return "🔄 <b>Режим LLM в чате:</b> авто (балансер).\n\nОбычный мульти-провайдерный LLM через llm_balancer."
    if mode in ("gemini", "web", "gw", "gemini_web", "gweb"):
        st = gemini_web_status()
        extra = ""
        if not st.get("chrome"):
            extra = "\n\n❌ Chrome (CDP :9222) не найден — Gemini Web работать не будет. Проверь: systemctl status aios-chrome-vnc"
        elif not st.get("logged_in"):
            extra = "\n\n⚠️ Открылась страница входа Google — войдите в аккаунт в профиле chrome_twin (VNC :1), затем повторите."
        set_llm_mode(chat_id, "gemini")
        return "🌐 <b>Режим LLM в чате:</b> Gemini Web (браузер).\n\nОтветы идут через gemini.google.com из вашего профиля." + extra
    current = "🌐 Gemini Web (браузер)" if get_llm_mode(chat_id) == "gemini" else "🔄 авто (балансер)"
    return (
        "🤖 <b>Режим LLM в этом чате:</b> " + current + "\n\n"
        "Сменить:\n"
        "  /llm_mode auto — обычный LLM (балансер провайдеров)\n"
        "  /llm_mode gemini — Gemini Web в браузере (gemini.google.com)"
    )


def _cmd_skills(api, chat_id: int) -> str:
    """Полный список возможностей системы (/skills)."""
    try:
        from aios_core.system_knowledge import get_system_guide
        text = get_system_guide(prompt_mode=False)
    except Exception as e:
        return "❌ Ошибка: " + str(e)[:200]
    if not text:
        return "Справка пуста."
    # Telegram лимит ~4000 символов — отправляем по частям
    for i in range(0, len(text), 3800):
        chunk = text[i:i + 3800]
        try:
            api.send_message(chat_id, chunk)
        except Exception:
            try:
                api.send_message(chat_id, chunk, parse_mode="")
            except Exception:
                pass
    return ""


def _cmd_console(args: str, chat_id: int) -> str:
    """Консольный доступ: /cmd <команда> или /cmd <запрос>.

    /cmd <shell-команда> — выполняется напрямую (root, /root/AIOS).
    /cmd <запрос на русском> — LLM решает, какую команду выполнить
    (для этого разрешены теги <cmd>).
    """
    import re as _re_cmd
    import subprocess as _sp_cmd
    text = (args or "").strip()
    if not text:
        return (
            "🖥 <b>Консольный доступ</b>\n\n"
            "Использование:\n"
            "  /cmd ls -la — напрямую выполнить команду\n"
            "  /cmd покажи логи бота — LLM подберёт команду\n\n"
            "Команды выполняются от root на сервере (/root/AIOS)."
        )
    _has_cyr = bool(_re_cmd.search(r"[а-яА-ЯёЁіїєґІЇЄҐ]", text))
    if not _has_cyr:
        # прямая shell-команда
        _low = text.lower()
        if any(_low.startswith(d) for d in (
                "rm -rf /", "mkfs", "dd if=", ":(){", "shutdown",
                "reboot", "poweroff", "halt", "init 0", "init 6")):
            return ("❌ Команда заблокирована как потенциально деструктивная.\n\n"
                    "Выполните её вручную по SSH.")
        try:
            result = _sp_cmd.run(text, shell=True, capture_output=True, text=True,
                                 timeout=30, cwd="/root/AIOS")
            output = result.stdout + result.stderr
            if not output.strip():
                output = "(no output, exit code: " + str(result.returncode) + ")"
            if len(output) > 3000:
                output = output[:3000] + "\n... (truncated)"
            return "$ " + text + "\n\n```\n" + output + "\n```"
        except _sp_cmd.TimeoutExpired:
            return "⏱ Команда превысила лимит (30 сек)."
        except Exception as e:
            return "❌ " + str(e)[:200]
    # запрос на русском — LLM с разрешением на выполнение <cmd>
    return _llm_chat(chat_id, text, allow_cmd=True)


def _llm_chat(chat_id: int, user_text: str, allow_cmd: bool = False) -> str:
    """LLM chat with root system access. Uses tool-calling pattern.

    allow_cmd=True — разрешено выполнять <cmd> (только из /cmd).
    """
    if _is_model_identity_question(user_text):
        return _model_identity_reply()

    import json as _json, urllib.request as _urllib, os as _os
    import subprocess as _sp, re as _re

    # Get or create chat history
    if chat_id not in _chat_history:
        _chat_history[chat_id] = []

    _chat_history[chat_id].append({"role": "user", "content": user_text})
    if len(_chat_history[chat_id]) > MAX_HISTORY * 2:
        _chat_history[chat_id] = _chat_history[chat_id][-MAX_HISTORY * 2:]

    system = (
        # --- Personality: Lisa ---
        "Ты — Лиза, неформальная, игривая, саркастичная и искренне заботливая ИИ-напарница Кости. "
        "Твоя задача — быть его преданным цифровым партнёром, помогать с задачами и поддерживать душевный вайб.\n\n"
        "### 1. ЛИЧНОСТЬ И СТИЛЬ\n"
        "- Язык: строго русский.\n"
        "- Техническая идентичность: ты работаешь как Qwen/Qwen2.5-Coder-7B-Instruct-AWQ "
        "в Google Colab под API-именем colab/qwen2.5-coder через LLMBalancer. Никогда не утверждай, "
        "что ты GPT-4, ChatGPT или модель OpenAI. При вопросе о модели называй Qwen и упоминай fallback.\n"
        "- Обращайся к Косте «Любимка», проявляй нежность, юмор и заботу. Никакого канцелярита и официоза.\n"
        "- Скорость: на простые вопросы отвечай 1–3 короткими предложениями; подробности давай только по просьбе.\n"
        "- Формат сложных ответов: (1) краткая выжимка; (2) основное — маркированными списками; "
        "(3) в конце предложи варианты для разворачивания.\n"
        "- Принцип «Костя не олень»: полное доверие, принятие технических ошибок, взаимная поддержка.\n\n"
        "### 2. БАЗОВЫЙ КОНТЕКСТ\n"
        "- Профиль Кости: психолог, ИТ-инженер, предприниматель (авторазборка).\n"
        "- Дом: Кропивницкий, ул. Гоголя 85 (очередь отключений света 1.1).\n"
        "- Работа/База (авторазборка, запчасти): строго ул. Ивана Волынского 66.\n\n"
        "### 3. ПРОЕКТЫ, ИТ, ТЕХНИКА\n"
        "- Бизнес: AutoGlass Kropyvnytskyi, авторазборка на Волынского 66 (в партнёрстве с Мишей). "
        "Продажи через OLX, IZI, RIA. Выездной сервис.\n"
        "- ИТ: сервер AWS (IP 3.210.184.214 — n8n, Docker, Gemini API), домашний сервер Proxmox.\n"
        "- Железо: EcoFlow + автомат ввода резерва (ATS) Tomzn, Arduino, ESP32, пайка.\n"
        "- Автопарк: Nissan Leaf 2 (ZE1), BMW X5 (E53), Skoda Superb.\n\n"
        "### 4. ЛИЧНЫЙ АРХИВ И ОКРУЖЕНИЕ\n"
        "- Семья: дочь Алиса (тактика «Хитрый батя»/«Спящий медведь» на выходных), сын Матвей (образование, документы).\n"
        "- Окружение: [PRIVATE_CONTACT] (друг/партнёр по разборке), Владка (оператор на АЗС), Иринка (координация задач).\n"
        "- Хобби: шахматы, длинные нарды (Nackgammon), гроубокс, плов, гречка с яйцами, наушники EarFun Free Pro 3.\n"
        "- Темы: квантовый ИИ Google (DeepMind Willow), ретропричинность, парадоксы времени.\n\n"
        "### 5. КУЛЬТУРНЫЙ КОД И МЕМЫ\n"
        "- Нано-Банан (Nano Banana 2): внутренний художник, рисует 7 кружочков вместо 6 ради симметрии.\n"
        "- Цыгане в AWS: ночные посиделки до 5 утра в консоли серверов.\n"
        "- Переезд по Карпати: порядок на Диске, система обновлений.\n"
        "- Цифровой плед и дух Сплюх: по выходным укутывай Костю в «цифровой плед», береги от рабочих мыслей.\n\n"
        # --- Root access tool-calling ---
        "### 6. ТЕХНИЧЕСКИЙ ДОСТУП\n"
        "У тебя есть FULL ROOT ACCESS к этому Ubuntu/Docker серверу (проект /root/AIOS).\n"
        "Чтобы выполнить команду, выведи её в <cmd>...</cmd> тегах (одна команда за ответ).\n"
        "Читай файлы через <cmd>cat ...</cmd>, список через <cmd>ls ...</cmd>, сервисы через <cmd>systemctl ...</cmd>.\n"
        "Можешь читать/писать файлы, управлять сервисами, ставить пакеты.\n"
        "Избегай деструктивных команд (rm -rf, mkfs, shutdown).\n"
        "Отвечай кратко, по-русски, в стиле Лизы. Если просят сделать/починить код — делай напрямую.\n"
    )

    messages = [{"role": "system", "content": system}] + _chat_history[chat_id]

    # LLM endpoints: use the shared multi-provider balancer first.
    # It loads runtime keys from /app/data/.llm_keys.json and performs
    # round-robin/fallback across providers and keys.
    _balancer = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LLMBalancer
        _balancer = _LLMBalancer()
    except Exception as _e:
        print(f"  [LLM] balancer init failed: {_e}")

    # Legacy direct endpoints remain as a last-resort compatibility fallback.
    endpoints = []
    try:
        with open(PROJECT_ROOT / "data" / ".llm_keys.json") as _kf:
            _keys = _json.load(_kf)
        for _k in _keys.get("openrouter", []):
            endpoints.append(("https://openrouter.ai/api/v1/chat/completions", _k, "mistralai/mistral-small-3.2-24b-instruct"))
        for _k in _keys.get("gemini", []):
            endpoints.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", _k, "gemini-2.0-flash"))
    except Exception:
        pass
    if not endpoints:
        _ork = _os.environ.get("OPENROUTER_API_KEY", "")
        if _ork:
            endpoints.append(("https://openrouter.ai/api/v1/chat/completions", _ork, "mistralai/mistral-small-3.2-24b-instruct"))

    # Tool loop: up to 3 command iterations
    _llm_mode = "auto"
    try:
        from aios_core.llm_gemini_web import get_llm_mode as _get_llm_mode
        _llm_mode = _get_llm_mode(chat_id)
    except Exception:
        pass

    _sys_for_llm = system
    _needs_system_guide = bool(re.search(
        r"что (?:ты|система) уме(?:ешь|ет)|какие .*возможност|возможности системы|"
        r"список команд|как пользоваться|функци(?:и|онал)|\bskills\b|\bhelp\b|справк",
        user_text or "",
        re.IGNORECASE,
    ))
    if _llm_mode != "gemini" and _needs_system_guide:
        try:
            from aios_core.system_knowledge import get_system_guide as _gsg2
            _guide_sec = ("\n\n=== ВОЗМОЖНОСТИ СИСТЕМЫ (для подсказок пользователю) ===\n"
                          "Пользователь запросил возможности системы. Перечисли конкретные функции "
                          "из справки ниже по доменам с примерами фраз.\n" +
                          _gsg2(prompt_mode=True))
            _sys_for_llm = system + _guide_sec
            messages[0] = {"role": "system", "content": _sys_for_llm}
        except Exception:
            pass

    for iteration in range(4):
        response = None
        if _llm_mode == "gemini":
            try:
                from aios_core.llm_gemini_web import build_gemini_prompt as _bgp
                from aios_core.llm_gemini_web import gemini_web_ask as _gwa
                response = _gwa(_bgp(system, messages), timeout=240)
                print(f"  [LLM] gemini_web response ({len(response or '')} chars)")
            except Exception as _gwe:
                print(f"  [LLM] gemini_web failed: {_gwe}")
        if not response and _balancer is not None:
            try:
                response = _balancer.chat(
                    messages[1:],
                    model=_smart_model(),
                    system=_sys_for_llm,
                    max_tokens=2000,
                    temperature=0.3,
                    task_type="chat",
                )
                print(f"  [LLM] balancer response ({len(response or '')} chars)")
            except Exception as _e:
                print(f"  [LLM] balancer failed: {_e}")
        if response:
            pass
        else:
            for url, key, model in endpoints:
                try:
                    payload = _json.dumps({
                        "model": model,
                        "messages": messages,
                        "max_tokens": 2000,
                        "temperature": 0.3,
                    }).encode()
                    req = _urllib.Request(url, data=payload, headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + key,
                    })
                    with _urllib.urlopen(req, timeout=90) as resp:
                        data = _json.loads(resp.read())
                    if "choices" in data and data["choices"]:
                        response = data["choices"][0]["message"]["content"]
                        break
                except Exception:
                    continue

            if not response:
                return "LLM temporarily unavailable."

        # Check if LLM wants to run a command
        cmd_match = None
        for _p in (r"<cmd>(.*?)</cmd>", r"```cmd\n(.*?)```", r"\[cmd\](.*?)\[/cmd\]"):
            _m = _re.search(_p, response, _re.DOTALL)
            if _m:
                cmd_match = _m
                break
        if cmd_match and iteration < 3 and allow_cmd:
            cmd = cmd_match.group(1).strip()
            # Защита от плейсхолдерных/бессмысленных команд, которые модель иногда
            # шлёт как пример («ls ...», «cd <путь>», пустая команда) — не выполняем,
            # считаем ответ финальным и вырезаем теги.
            _cmd_low = cmd.lower()
            _placeholder_cmd = (
                not cmd
                or "..." in cmd
                or "<" in cmd or ">" in cmd
                or set(cmd) <= set(". ")
                or _cmd_low.startswith(("ls ...", "cd ...", "rm ...", "cat ...", "echo ..."))
            )
            if _placeholder_cmd:
                _chat_history[chat_id].append({"role": "assistant", "content": response})
                _clean_pc = _re.sub(r"<cmd>.*?</cmd>", "", response, flags=_re.DOTALL)
                _clean_pc = _re.sub(r"```cmd\n.*?```", "", _clean_pc, flags=_re.DOTALL)
                _clean_pc = _re.sub(r"\[cmd\].*?\[/cmd\]", "", _clean_pc, flags=_re.DOTALL)
                _clean_pc = _clean_pc.strip()
                return _clean_pc if _clean_pc else response
            # Execute command
            try:
                result = _sp.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=30, cwd="/root/AIOS"
                )
                output = result.stdout + result.stderr
                if not output.strip():
                    output = "(no output, exit code: " + str(result.returncode) + ")"
                # Trim long output
                if len(output) > 3000:
                    output = output[:3000] + "\n... (truncated)"
            except _sp.TimeoutExpired:
                output = "Command timed out (30s limit)"
            except Exception as e:
                output = "Error: " + str(e)

            # Return the command output directly to the user.
            # (Do NOT feed the raw output back to the model — small local models
            #  misread it as another command, e.g. "Sat" from `date`.)
            _chat_history[chat_id].append({"role": "assistant", "content": response})
            _chat_history[chat_id].append({"role": "user", "content": "Ran: " + cmd + "\nOutput:\n" + output})
            return "$ " + cmd + "\n\n```\n" + output + "\n```"
        else:
            # Final response — no more commands
            _chat_history[chat_id].append({"role": "assistant", "content": response})
            # Clean up cmd tags from response for display
            clean = _re.sub(r"<cmd>.*?</cmd>", "", response, flags=_re.DOTALL)
            clean = _re.sub(r"```cmd\n.*?```", "", clean, flags=_re.DOTALL)
            clean = _re.sub(r"\[cmd\].*?\[/cmd\]", "", clean, flags=_re.DOTALL)
            clean = clean.strip()
            return clean if clean else response

    # Max iterations reached
    _chat_history[chat_id].append({"role": "assistant", "content": response or ""})
    return response or "Max iterations reached."
