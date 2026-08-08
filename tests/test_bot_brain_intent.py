# -*- coding: utf-8 -*-
"""🧪 Тесты текстовых команд Phone Brain в Telegram-боте (батч B).

Проверяет «подтверди N», «черновики» и «мозг» без импорта всего бота:
функции извлекаются AST-разбором и исполняются в изолированном namespace.
HTTP-вызовы подменяются стабом _phone_brain_api_request.
"""

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHONE_PATH = REPO_ROOT / "tg_bot" / "phone.py"

SOURCE_FUNCS = ["_phone_brain_api_request", "_handle_phone_brain_intent"]


def _load_funcs() -> dict:
    """Вырезает функции phone-brain из tg_bot/phone.py (AST, без импорта всего бота)."""
    tree = ast.parse(PHONE_PATH.read_text(encoding="utf-8"))
    keep: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in SOURCE_FUNCS:
            keep.append(node)
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "_PHONE_BRAIN_API" in names:
                keep.append(node)
    found = [n.name for n in keep if isinstance(n, ast.FunctionDef)]
    for name in SOURCE_FUNCS:
        if name not in found:
            raise RuntimeError(f"❌ Не найдена функция {name} в tg_bot/phone.py")
    mod = ast.Module(body=keep, type_ignores=[])
    ast.fix_missing_locations(mod)
    import html
    import json
    import os
    import re
    import urllib.error
    import urllib.request

    ns = {
        "os": os, "re": re, "html": html, "json": json,
        "urllib.request": urllib.request, "urllib.error": urllib.error,
    }
    exec(compile(mod, str(PHONE_PATH), "exec"), ns)  # noqa: S102
    # _esc_tg берём из tg_bot.common напрямую
    from tg_bot.common import _esc_tg
    ns["_esc_tg"] = _esc_tg
    return ns


class _FakeAPI:
    """📨 Фейковый Telegram-API: запоминает отправленные сообщения."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send_message(self, chat_id: int, text: str, **_: object) -> dict:
        self.sent.append(text)
        return {"ok": True, "result": {"message_id": len(self.sent)}}


class _BrainStub:
    """🧠 Стаб ответов Phone Brain API по (method, path)."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], dict] = {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, method: str, path: str, body=None, req_timeout: float = 4.0) -> dict:
        self.calls.append((method, path))
        return self.routes.get((method, path),
                               {"status": "error", "error": "демон не отвечает"})


def _health(connected: bool = False) -> dict:
    """🏥 Типовой ответ /health работающего демона."""
    return {
        "status": "ok", "version": "0.1.0",
        "daemon": {"started_at": "2026-08-04T15:00:00+00:00",
                   "uptime_seconds": 754, "busy_job": None},
        "device": {"status": "offline",
                   "device": {"connected": connected},
                   "brain": {"backoff_seconds": 900}},
        "queue": {"done": 4, "need_confirm": 2},
    }


class PhoneBrainIntentTests(unittest.TestCase):
    """🔤 Сценарии текстового интерфейса очереди Phone Brain."""

    def setUp(self) -> None:
        self.ns = _load_funcs()
        self.api = _FakeAPI()
        self.brain = _BrainStub()
        self.ns["_phone_brain_api_request"] = self.brain
        self.handle = self.ns["_handle_phone_brain_intent"]

    def test_confirm_job_success(self) -> None:
        """✅ «подтверди 5» подтверждает задачу через API."""
        self.brain.routes[("POST", "/jobs/5/confirm")] = {"status": "ok", "job": {"id": 5}}
        self.assertTrue(self.handle(self.api, 1, "подтверди 5"))
        self.assertIn("подтверждён", self.api.sent[-1])
        self.assertIn("#5", self.api.sent[-1])

    def test_confirm_job_rejected(self) -> None:
        """⚠️ API отказал — пользователь получает текст ошибки."""
        self.brain.routes[("POST", "/jobs/7/confirm")] = {
            "status": "error", "error": "Задача в статусе done"}
        self.assertTrue(self.handle(self.api, 1, "подтвердить 7"))
        self.assertIn("⚠️", self.api.sent[-1])
        self.assertIn("#7", self.api.sent[-1])

    def test_confirm_without_number_ignored(self) -> None:
        """🚫 «подтверди» без номера не перехватывается."""
        self.assertFalse(self.handle(self.api, 1, "подтверди"))
        self.assertFalse(self.handle(self.api, 1, "подтверди abc"))
        self.assertEqual(self.api.sent, [])

    def test_drafts_lists_need_confirm(self) -> None:
        """📝 «черновики» показывает задачи из очереди need_confirm."""
        self.brain.routes[("GET", "/jobs?status=need_confirm&limit=10")] = {
            "status": "ok",
            "jobs": [
                {"id": 5, "kind": "plan.run",
                 "result": {"status": "need_confirm", "action": "phone_plan_run"}},
                {"id": 2, "kind": "app.open",
                 "result": {"status": "need_confirm", "action": "android_app_open"}},
            ],
        }
        self.assertTrue(self.handle(self.api, 1, "черновики"))
        text = self.api.sent[-1]
        self.assertIn("Черновиков на одобрение: 2", text)
        self.assertIn("#5", text)
        self.assertIn("phone_plan_run", text)
        self.assertIn("подтверди 5", text)

    def test_drafts_empty(self) -> None:
        """📭 Пустая очередь черновиков — понятный ответ."""
        self.brain.routes[("GET", "/jobs?status=need_confirm&limit=10")] = {
            "status": "ok", "jobs": []}
        self.assertTrue(self.handle(self.api, 1, "покажи черновики"))
        self.assertIn("Черновиков на одобрение нет", self.api.sent[-1])

    def test_drafts_brain_offline(self) -> None:
        """🔌 «черновики» при мёртвом демоне — честное сообщение."""
        self.assertTrue(self.handle(self.api, 1, "черновики"))
        self.assertIn("недоступен", self.api.sent[-1])

    def test_brain_status(self) -> None:
        """🧠 «мозг» показывает версию, очередь, устройство и правила."""
        self.brain.routes[("GET", "/health")] = _health()
        self.brain.routes[("GET", "/reactions")] = {
            "status": "ok", "enabled": True,
            "rules": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}]}
        self.assertTrue(self.handle(self.api, 1, "мозг"))
        text = self.api.sent[-1]
        self.assertIn("Phone Brain", text)
        self.assertIn("0.1.0", text)
        self.assertIn("need_confirm:2", text)
        self.assertIn("офлайн", text)
        self.assertIn("правил реакций: 3", text)

    def test_brain_offline(self) -> None:
        """🔌 Недоступный API — честное сообщение вместо исключения."""
        self.assertTrue(self.handle(self.api, 1, "мозг"))
        self.assertIn("недоступен", self.api.sent[-1])

    def test_unrelated_text_not_captured(self) -> None:
        """💬 Обычный текст проходит мимо хендлера."""
        self.assertFalse(self.handle(self.api, 1, "привет, как дела?"))
        self.assertEqual(self.api.sent, [])


if __name__ == "__main__":
    unittest.main()
