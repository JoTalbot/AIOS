"""Тесты новых операционных фич: usage-трекинг, мониторы, автопилот."""
import json
from pathlib import Path

import pytest


# ---------- 1. LLM usage hook ----------

def test_usage_log_written_on_chat(monkeypatch, tmp_path):
    """После успешного chat() в usage.jsonl появляется запись."""
    import aios_core.llm_balancer as lb

    # фейковый ответ
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

    class FakeReq:
        @staticmethod
        def post(*a, **kw):
            return FakeResp()

    import requests
    monkeypatch.setattr(requests, "post", FakeReq.post)

    # реальный лог проекта; запомним размер до
    log = Path("/root/AIOS/data/llm/usage.jsonl")
    before = log.stat().st_size if log.exists() else 0

    b = lb.LLMBalancer()
    ans = b.chat(messages=[{"role": "user", "content": "hi"}],
                 model="llama-3.1-8b-instant", max_tokens=10)
    assert ans == "ok"

    assert log.exists()
    assert log.stat().st_size > before, "usage.jsonl не дописан"
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert rec["provider"] == "groq"
    assert rec["total_tokens"] == 15
    assert rec["key_tail"]  # хвост ключа

    # откатываем дописанную строку (не загрязняем прод-лог)
    lines = log.read_text(encoding="utf-8").splitlines()
    if before == 0:
        log.unlink()
    else:
        with log.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines[:-1]) + ("\n" if len(lines) > 1 else ""))


# ---------- 2. 2captcha monitor ----------

def test_2captcha_monitor_low_balance(monkeypatch, tmp_path):
    """При балансе ниже порога монитор помечает alerted (без реальной сети)."""
    import run_2captcha_balance as m

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "STATE", tmp_path / "captcha_balance_state.json")
    monkeypatch.setattr(m, "THRESHOLD", 5.0)
    monkeypatch.setattr(m, "CAPTCHA_KEY_FILE", tmp_path / ".2captcha_key")
    (tmp_path / ".2captcha_key").write_text("test-key")

    calls = []

    def fake_fetch(key):
        return 3.0  # ниже порога

    def fake_send(text):
        calls.append(text)
        return True

    monkeypatch.setattr(m, "_fetch_balance", fake_fetch)
    monkeypatch.setattr(m, "_send", fake_send)

    res = m.check(alert=True)
    assert res["balance"] == 3.0
    assert res["alerted"] is True
    assert calls, "алерт не отправлен"
    assert "2captcha" in calls[0]


def test_2captcha_monitor_no_spam(monkeypatch, tmp_path):
    """Повторный низкий баланс не шлёт алерт повторно (state)."""
    import run_2captcha_balance as m

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "STATE", tmp_path / "captcha_balance_state.json")
    monkeypatch.setattr(m, "THRESHOLD", 5.0)
    monkeypatch.setattr(m, "CAPTCHA_KEY_FILE", tmp_path / ".2captcha_key")
    (tmp_path / ".2captcha_key").write_text("test-key")
    (tmp_path / "captcha_balance_state.json").write_text(
        json.dumps({"last_alerted_balance": 3.0, "last_alert_at": 0}))

    calls = []
    monkeypatch.setattr(m, "_fetch_balance", lambda k: 3.0)
    monkeypatch.setattr(m, "_send", lambda t: calls.append(t) or True)

    m.check(alert=True)
    assert calls == [], "повторный алерт не должен уходить"


# ---------- 3. Disk monitor ----------

def test_disk_monitor_threshold(monkeypatch, tmp_path):
    """Монитор диска шлёт алерт при заполнении > 85%."""
    import run_disk_monitor as m

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "STATE", tmp_path / "disk_state.json")

    class FakeUsage:
        total = 100 * 1024**3
        used = 90 * 1024**3
        free = 10 * 1024**3

    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: FakeUsage())
    calls = []
    monkeypatch.setattr(m, "_send", lambda t: calls.append(t) or True)

    res = m.check(alert=True)
    assert res["pct"] == 90.0
    assert res["alerted"] is True
    assert "Диск" in calls[0]


# ---------- 4. Groq autopilot logic ----------

def test_autopilot_decision(monkeypatch, tmp_path):
    """При 8 ключах автопилот не создаёт новый (порог 6)."""
    import run_groq_key_autopilot as m

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "STATE", tmp_path / "groq_autopilot_state.json")
    monkeypatch.setattr(m, "MIN_KEYS", 6)

    keys = [f"gsk_test{i}" for i in range(8)]
    monkeypatch.setattr(m, "_groq_keys", lambda: keys)

    created = []
    monkeypatch.setattr(m, "_create_key_via_browser", lambda ck: created.append(1) or "gsk_new")
    monkeypatch.setattr(m, "_remaining_requests", lambda k: 999.0)

    res = m.check(alert=False)
    assert res["action"] == "none"
    assert created == [], "не должно создаваться при 8 ключах"


def test_autopilot_creates_when_low(monkeypatch, tmp_path):
    """При остатке < порога автопилот создаёт ключ."""
    import run_groq_key_autopilot as m

    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "STATE", tmp_path / "groq_autopilot_state.json")
    monkeypatch.setattr(m, "MIN_KEYS", 6)
    monkeypatch.setattr(m, "RPM_THRESHOLD", 200)

    keys = [f"gsk_test{i}" for i in range(6)]
    monkeypatch.setattr(m, "_groq_keys", lambda: keys)
    monkeypatch.setattr(m, "_remaining_requests", lambda k: 50.0)

    appended = []
    monkeypatch.setattr(m, "_create_key_via_browser", lambda ck: "gsk_newkey123456")
    monkeypatch.setattr(m, "_append_key", lambda k, n: appended.append(k))
    monkeypatch.setattr(m, "_captcha_key", lambda: "cap-123")
    monkeypatch.setattr(m, "_send", lambda t: True)

    res = m.check(alert=False)
    assert res["action"] == "created"
    assert appended == ["gsk_newkey123456"]
