"""Тесты reaction engine (этап 4): правила, маскирование, действия, дедуп."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aios_core.phone_brain.queue_store import JobStore
from aios_core.phone_brain.reactions import ReactionEngine, _mask


class FakeGateway:
    def __init__(self, notifications: list[dict]):
        self._payload = {"status": "ok", "notifications": notifications}

    def notifications(self, limit: int = 50) -> dict:
        return self._payload


class Clock:
    def __init__(self) -> None:
        self.moment = datetime(2026, 8, 4, 15, 0, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, seconds: float) -> None:
        self.moment += timedelta(seconds=seconds)


class FakeEvents:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def append(self, event_type: str, data: dict) -> None:
        self.items.append({"type": event_type, "data": data})


def _write_rules(root: Path, rules: list[dict]) -> None:
    rules_dir = root / "phone_reactions"
    rules_dir.mkdir(parents=True, exist_ok=True)
    for rule in rules:
        (rules_dir / f"{rule['id']}.json").write_text(json.dumps(rule, ensure_ascii=False), "utf-8")


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / "data" / "android_gateway").mkdir(parents=True)
    return tmp_path


TELEGRAM_RULE = {
    "id": "bank_income", "title": "Поступление", "autonomy": "alert_only",
    "match": {"package": ["ua.com.abank"], "text_regex": "поповн"},
    "action": {"type": "telegram", "template": "💰 {label}: {text}"},
    "cooldown_seconds": 60,
}


def test_mask_hides_otp_and_cards() -> None:
    assert "4581" not in _mask("Код 4581, никому не говорите")
    assert "••••" in _mask("Код 4581, никому не говорите")
    assert "5555" not in _mask("Карта 4000 5555 6666 7777")


def test_telegram_rule_fires_masked(root: Path) -> None:
    _write_rules(root, [TELEGRAM_RULE])
    sent: list[str] = []
    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "ua.com.abank", "title": "A-Bank",
         "text": "Рахунок поповнено на 4581 грн, код 123456", "posted_at": "2026-08-04T14:59:00"},
    ]), sender=sent.append)
    result = engine.tick()
    assert result["matched"] == 1
    assert len(sent) == 1
    assert "A-Bank" in sent[0] and "поповнено" in sent[0]
    assert "4581" not in sent[0] and "123456" not in sent[0]  # только маски!


def test_dedupe_and_cooldown(root: Path) -> None:
    _write_rules(root, [TELEGRAM_RULE])
    sent: list[str] = []
    clock = Clock()
    notifications = [
        {"package": "ua.com.abank", "title": "A-Bank", "text": "Рахунок поповнено", "posted_at": "t1"},
    ]
    engine = ReactionEngine(root, gateway=FakeGateway(list(notifications)),
                            sender=sent.append, now_fn=clock)
    assert engine.tick()["matched"] == 1
    # тот же id повторно не обрабатывается
    assert engine.tick()["checked"] == 0
    # новое уведомление в пределах cooldown — подавляется (и помечается seen)
    notifications.append({"package": "ua.com.abank", "title": "A-Bank",
                          "text": "Рахунок поповнено 2", "posted_at": "t2"})
    engine2 = ReactionEngine(root, gateway=FakeGateway(list(notifications)),
                             sender=sent.append, now_fn=clock)
    assert engine2.tick()["matched"] == 0
    assert len(sent) == 1
    # после cooldown новое уведомление снова вызывает срабатывание
    clock.advance(61)
    notifications.append({"package": "ua.com.abank", "title": "A-Bank",
                          "text": "Рахунок поповнено 3", "posted_at": "t3"})
    engine3 = ReactionEngine(root, gateway=FakeGateway(list(notifications)),
                             sender=sent.append, now_fn=clock)
    assert engine3.tick()["matched"] == 1
    assert len(sent) == 2


def test_enqueue_draft_lands_need_confirm(root: Path) -> None:
    _write_rules(root, [{
        "id": "wa_reply_draft", "autonomy": "draft",
        "match": {"package": ["com.whatsapp"], "text_regex": "сервіс|услуг"},
        "action": {"type": "enqueue", "job": {"kind": "skill.run",
                                              "payload": {"skill": "whatsapp_send_draft",
                                                          "params": {"contact": "{title}",
                                                                     "text": "Здравствуйте! Уточню и отвечу."}}}},
    }])
    store = JobStore(root / "queue.db")
    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "com.whatsapp", "title": "Клиент №9", "text": "Какие услуги есть?", "posted_at": "t1"},
    ]), store=store, sender=lambda t: {"status": "ok"})
    result = engine.tick()
    assert result["matched"] == 1
    assert result["actions"][0]["job_id"] >= 1
    job = store.get(result["actions"][0]["job_id"])
    assert job["payload"].get("confirm") is None  # draft → владелец подтверждает сам


def test_enqueue_auto_confirms(root: Path) -> None:
    _write_rules(root, [{
        "id": "auto_collect", "autonomy": "auto",
        "match": {"package": ["com.whatsapp"]},
        "action": {"type": "enqueue", "job": {"kind": "notify.collect", "payload": {}}},
    }])
    store = JobStore(root / "queue.db")
    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "com.whatsapp", "title": "x", "text": "y", "posted_at": "t1"},
    ]), store=store, sender=lambda t: {"status": "ok"})
    assert engine.tick()["matched"] == 1
    job = store.list(limit=1)[0]
    assert job["kind"] == "notify.collect" and job["payload"].get("confirm") is True


def test_event_action_has_no_text(root: Path) -> None:
    _write_rules(root, [{
        "id": "otp_guard", "match": {"package": ["ua.privatbank.ap24"], "text_regex": "код"},
        "action": {"type": "event", "name": "otp_arrived"},
    }])
    events = FakeEvents()
    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "ua.privatbank.ap24", "title": "Privat24",
         "text": "Ваш код 998877", "posted_at": "t1"},
    ]), events=events, sender=lambda t: {"status": "ok"})
    assert engine.tick()["matched"] == 1
    fired = [e for e in events.items if e["type"] in ("otp_arrived",)]
    assert len(fired) == 1
    blob = json.dumps(events.items, ensure_ascii=False)
    assert "998877" not in blob  # код не утёк даже в журнал


def test_offline_is_graceful(root: Path) -> None:
    class OfflineGateway:
        def notifications(self, limit: int = 50) -> dict:
            return {"status": "offline"}

    engine = ReactionEngine(root, gateway=OfflineGateway(), sender=lambda t: {"status": "ok"})
    assert engine.tick()["status"] == "offline"


def test_broken_rule_skipped(root: Path) -> None:
    rules_dir = root / "phone_reactions"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "broken.json").write_text('{"id": "x"}', "utf-8")
    _write_rules(root, [TELEGRAM_RULE])
    engine = ReactionEngine(root, gateway=FakeGateway([]), sender=lambda t: {"status": "ok"})
    items = engine.list_rules()
    assert any(item["id"] == "bank_income" for item in items)
    assert any(item.get("error") for item in items)
