from __future__ import annotations

from scripts import telegram_colab_canary as canary


def test_human_action_mode_uses_free_managed_qwen_without_colab(monkeypatch, tmp_path):
    import aios_core.llm_balancer as module

    observed: dict[str, str] = {}

    class FakeBalancer:
        def __init__(self):
            self.providers = {"colab": object(), "groq": object()}
            self.last_route = {}

        def chat(self, _messages, *, model, **_kwargs):
            observed["model"] = model
            observed["colab_present"] = str("colab" in self.providers)
            self.last_route = {"provider": "groq", "model": model}
            return "ok"

    monkeypatch.setattr(module, "LLMBalancer", FakeBalancer)
    monkeypatch.setattr(canary, "STATE_FILE", tmp_path / "canary.json")
    monkeypatch.setattr(canary, "_colab_mode", lambda: "human_action_required")
    monkeypatch.setenv("AIOS_FREE_QWEN_MODEL", "qwen/qwen3.6-27b")
    monkeypatch.delenv("AIOS_TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path / "missing"))

    result = canary.run_canary(send_telegram=False)

    assert observed == {
        "model": "qwen/qwen3.6-27b",
        "colab_present": "False",
    }
    assert result["mode"] == "human_action_required"
    assert result["route"]["ok"] is True
    assert result["colab"]["ok"] is False
    assert result["telegram"]["status"] == "missing_token"
