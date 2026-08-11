from __future__ import annotations

from scripts import telegram_colab_canary as canary


def test_owner_canary_sends_silently_and_auto_deletes(tmp_path, monkeypatch):
    import aios_core.llm_balancer as balancer_module
    import tg_bot.api as api_module
    import tg_bot.outbox as outbox_module
    import tg_bot.metrics as metrics_module

    sent: dict = {}
    deleted: list[tuple[int, int]] = []

    class FakeBalancer:
        def __init__(self):
            self.last_route = {}

        def chat(self, *_args, **_kwargs):
            self.last_route = {
                "provider": "colab",
                "model": "colab/qwen2.5-coder",
            }
            return "ok"

    class FakeAPI:
        def __init__(self, _token):
            pass

        def delete_message(self, chat_id, message_id):
            deleted.append((chat_id, message_id))
            return {"ok": True}

    class FakeOutbox:
        def __init__(self, api, path):
            self.api = api
            self.path = path

        def start(self):
            return None

        def stop(self):
            return None

        def enqueue(self, **kwargs):
            sent.update(kwargs)
            return True

        def wait(self, _key, timeout):
            assert timeout == 25
            return {"status": "sent", "attempts": 1, "telegram_message_id": 321}

    monkeypatch.setattr(balancer_module, "LLMBalancer", FakeBalancer)
    monkeypatch.setattr(api_module, "TelegramAPI", FakeAPI)
    monkeypatch.setattr(outbox_module, "TelegramOutbox", FakeOutbox)
    monkeypatch.setattr(canary, "STATE_FILE", tmp_path / "canary.json")
    monkeypatch.setattr(metrics_module, "METRICS_FILE", tmp_path / "metrics.jsonl")
    monkeypatch.setattr(metrics_module, "SUMMARY_FILE", tmp_path / "summary.json")
    monkeypatch.setenv("AIOS_TELEGRAM_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "777")
    monkeypatch.delenv("TELEGRAM_CANARY_CHAT_ID", raising=False)

    result = canary.run_canary(send_telegram=True)

    assert result["ok"] is True
    assert result["telegram"]["deleted"] is True
    assert sent["disable_notification"] is True
    assert sent["metric_event"] == "canary_delivery"
    assert sent["chat_id"] == 777
    assert deleted == [(777, 321)]
