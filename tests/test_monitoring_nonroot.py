from __future__ import annotations

from pathlib import Path


def test_alertmanager_and_receiver_are_nonroot_with_tmpfs_credentials():
    root = Path(__file__).resolve().parents[1]
    compose = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")
    receiver = compose.split("  aios-alert-canary-receiver:", 1)[1].split(
        "\n  alertmanager:", 1
    )[0]
    alertmanager = compose.split("\n  alertmanager:", 1)[1].split(
        "\n  aios-exporter:", 1
    )[0]
    assert 'user: "65534:65534"' in receiver
    assert 'user: "65534:65534"' in alertmanager
    assert "/run/aios-docker-credentials/telegram_token:" in receiver
    assert "/run/aios-docker-credentials/telegram_token:" in alertmanager
    assert "/etc/aios/credentials/telegram_token:" not in receiver
    assert "/etc/aios/credentials/telegram_token:" not in alertmanager
