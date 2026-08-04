"""Тесты LLM-черновиков и подтверждения: полный цикл draft → need_confirm → confirm."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aios_core.phone_brain.handlers import Executor, Handler, JobContext
from aios_core.phone_brain.queue_store import JobStore
from aios_core.phone_brain.reactions import ReactionEngine


class FakeGateway:
    def __init__(self, notifications: list[dict]):
        self._payload = {"status": "ok", "notifications": notifications}

    def notifications(self, limit: int = 50) -> dict:
        return self._payload


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


LLM_RULE = {
    "id": "wa_llm_draft", "autonomy": "draft",
    "match": {"package": ["com.whatsapp"], "text_regex": "цен"},
    "action": {"type": "llm_enqueue", "prompt": "Ответь клиенту: {text}",
               "job": {"kind": "skill.run",
                       "payload": {"skill": "whatsapp_send_draft",
                                   "params": {"contact": "{title}", "text": "{draft}"}}},
               "notify": True},
    "cooldown_seconds": 60,
}


# --------------------------------------------------------------- confirm_job

def test_confirm_job_requeues_need_confirm(root: Path) -> None:
    store = JobStore(root / "queue.db")
    job = store.enqueue("skill.run", {"skill": "x"})
    claimed = store.claim()
    store.set_need_confirm(claimed["id"], claimed["lease_token"],
                           {"status": "need_confirm", "action": "phone_skill:x"})
    approved = store.confirm_job(job["id"])
    assert approved["status"] == "ok" and approved["kind"] == "skill.run"
    again = store.get(job["id"])
    assert again["status"] == "queued" and again["payload"]["confirm"] is True
    # повторное подтверждение идемпотентно (ok + note)
    repeat = store.confirm_job(job["id"])
    assert repeat["status"] == "ok" and repeat.get("note")


def test_confirm_job_only_pending_states(root: Path) -> None:
    store = JobStore(root / "queue.db")
    job = store.enqueue("device.status")
    # из queued тоже можно (задача ещё не ушла в работу — одобрение успевает)
    assert store.confirm_job(job["id"])["status"] == "ok"
    assert store.get(job["id"])["payload"]["confirm"] is True
    # повторное — идемпотентно
    assert store.confirm_job(job["id"])["status"] == "ok"
    # терминальные статусы — нельзя; несуществующая — ошибка
    claimed = store.claim()
    store.complete(claimed["id"], claimed["lease_token"])
    assert store.confirm_job(job["id"])["status"] == "error"
    assert store.confirm_job(9999)["status"] == "error"


def test_queue_confirm_handler(root: Path) -> None:
    store = JobStore(root / "queue.db")
    job = store.enqueue("skill.run", {"skill": "x"})
    claimed = store.claim()
    store.set_need_confirm(claimed["id"], claimed["lease_token"], {"action": "a"})
    ctx = JobContext(root=root, gateway=None,
                     supervisor=SimpleNamespace(is_online=lambda: True,
                                                companion_ready=lambda: True),
                     events=None, store=store)
    from aios_core.phone_brain.handlers import _h_queue_confirm
    result = _h_queue_confirm({"id": job["id"]}, ctx)
    assert result["status"] == "ok"
    assert _h_queue_confirm({}, ctx)["status"] == "error"
    assert _h_queue_confirm({"id": 424242}, ctx)["status"] == "error"


# --------------------------------------------------------------- llm_enqueue

def test_llm_draft_full_cycle(root: Path) -> None:
    """Правило → LLM-черновик → задача → одобрение владельца."""
    _write_rules(root, [LLM_RULE])
    store = JobStore(root / "queue.db")
    sent: list[str] = []
    events = FakeEvents()
    chat_calls: list[str] = []

    def fake_chat(messages: list, **kw) -> str:
        chat_calls.append(messages[0]["content"])
        return "Здравствуйте! Спасибо за обращение. Цена уточняется после диагностики — привозите устройство завтра после 12:00."

    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "com.whatsapp", "title": "Оксана Клиент",
         "text": "Добрый день, какая цена ремонта экрана?", "posted_at": "t1"},
    ]), store=store, events=events, sender=sent.append, chat=fake_chat)

    result = engine.tick()
    assert result["matched"] == 1
    action = result["actions"][0]
    assert action["type"] == "llm_enqueue" and action["autonomy"] == "draft"

    # задача создана с placeholder-заменами и БЕЗ confirm (draft)
    job = store.get(action["job_id"])
    assert job["kind"] == "skill.run"
    assert job["payload"]["params"]["contact"] == "Оксана Клиент"
    assert "диагностики" in job["payload"]["params"]["text"]
    assert job["payload"].get("confirm") is None

    # владельцу ушло уведомление с id и командой
    assert len(sent) == 1 and f"confirm {job['id']}" in sent[0]
    assert any(e["type"] == "llm_draft_ready" for e in events.items)

    # одобрение владельца → задача готова к выполнению
    assert store.confirm_job(job["id"])["status"] == "ok"
    assert store.get(job["id"])["payload"]["confirm"] is True


def test_llm_draft_llm_failure_no_job(root: Path) -> None:
    _write_rules(root, [LLM_RULE])
    store = JobStore(root / "queue.db")
    sent: list[str] = []

    def broken_chat(messages: list, **kw) -> str:
        raise RuntimeError("provider down")

    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "com.whatsapp", "title": "x", "text": "цена?", "posted_at": "t1"},
    ]), store=store, sender=sent.append, chat=broken_chat)
    result = engine.tick()
    assert result["matched"] == 0
    assert store.metrics()["queued"] == 0  # задача не создалась
    assert sent == []                       # и уведомления нет


def test_llm_draft_auto_autonomy(root: Path) -> None:
    rule = dict(LLM_RULE, id="wa_auto", autonomy="auto")
    _write_rules(root, [rule])
    store = JobStore(root / "queue.db")
    engine = ReactionEngine(root, gateway=FakeGateway([
        {"package": "com.whatsapp", "title": "x", "text": "цена работ?", "posted_at": "t9"},
    ]), store=store, sender=lambda t: None, chat=lambda m, **k: "черновик")
    result = engine.tick()
    job = store.get(result["actions"][0]["job_id"])
    assert job["payload"]["confirm"] is True
