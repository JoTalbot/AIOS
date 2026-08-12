from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import yaml

from scripts.render_alertmanager_config import render

ROOT = Path(__file__).resolve().parents[1]


def _load_receiver():
    path = ROOT / "deploy/monitoring/alertmanager_canary_receiver.py"
    spec = importlib.util.spec_from_file_location("alert_canary_receiver", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_alertmanager_config_is_rendered_without_token(tmp_path):
    owner = tmp_path / "owner"
    owner.write_text("123456\n", encoding="utf-8")
    output = tmp_path / "alertmanager.yml"
    render(
        ROOT / "deploy/monitoring/alertmanager/alertmanager.yml.tmpl",
        owner,
        output,
    )
    config = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert config["receivers"][0]["telegram_configs"][0]["chat_id"] == 123456
    assert config["receivers"][0]["telegram_configs"][0]["bot_token_file"] == (
        "/run/secrets/telegram_token"
    )
    assert "__TELEGRAM_OWNER_CHAT_ID__" not in output.read_text(encoding="utf-8")
    assert output.stat().st_mode & 0o777 == 0o600


def test_internal_receiver_sends_silent_message_and_deletes(monkeypatch, tmp_path):
    receiver = _load_receiver()
    token = tmp_path / "token"
    chat = tmp_path / "chat"
    state = tmp_path / "state.json"
    token.write_text("not-a-real-token\n", encoding="utf-8")
    chat.write_text("123\n", encoding="utf-8")
    monkeypatch.setattr(receiver, "TOKEN_FILE", token)
    monkeypatch.setattr(receiver, "CHAT_FILE", chat)
    monkeypatch.setattr(receiver, "STATE_FILE", state)
    calls: list[tuple[str, dict]] = []

    def telegram(method: str, payload: dict) -> dict:
        calls.append((method, payload))
        if method == "sendMessage":
            return {"ok": True, "result": {"message_id": 77}}
        return {"ok": True, "result": True}

    monkeypatch.setattr(receiver, "_telegram", telegram)
    result = receiver.deliver("abcdef123456")
    assert result["ok"] and result["deleted"]
    assert calls[0][1]["disable_notification"] is True
    assert calls[1] == ("deleteMessage", {"chat_id": 123, "message_id": 77})
    stored = json.loads(state.read_text(encoding="utf-8"))
    assert "chat_id" not in stored and "token" not in stored


def test_metrics_sidecar_has_minimal_mounts_and_pinned_images():
    for relative in ("docker-compose.prod.yml", "deploy/production/docker-compose.prod.yml"):
        compose = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
        service = compose["services"]["aios-telegram-exporter"]
        mounts = "\n".join(service["volumes"])
        assert ":/app" not in mounts
        assert "/root/AIOS" not in mounts
        assert "telegram_exporter_server.py" in mounts
        assert "/var/lib/aios-telegram-metrics" in mounts
        assert service["user"] == "65534:65534"
        assert service["cap_drop"] == ["ALL"]
        for value in compose["services"].values():
            environment = value.get("environment", {})
            rendered_environment = json.dumps(environment)
            assert "${AIOS_TELEGRAM_TOKEN" not in rendered_environment
            assert "${TELEGRAM_BOT_TOKEN" not in rendered_environment
            image = value.get("image")
            if image and image.startswith(("python:", "prom/", "grafana/")):
                assert "@sha256:" in image
                assert ":latest" not in image
