from __future__ import annotations

import json
import sqlite3
import time

from tg_bot import metrics


def test_prometheus_export_has_latency_queues_and_canary_without_content(tmp_path, monkeypatch):
    metrics_file = tmp_path / "telegram_metrics.jsonl"
    monkeypatch.setattr(metrics, "ROOT", tmp_path)
    monkeypatch.setattr(metrics, "METRICS_FILE", metrics_file)
    monkeypatch.setattr(metrics, "SUMMARY_FILE", tmp_path / "summary.json")

    now = time.time()
    metrics.record_telegram_event(
        {
            "event": "telegram_send",
            "status": "sent",
            "provider": "colab",
            "model": "colab/qwen2.5-coder",
            "gen_sec": 1.2,
            "send_sec": 0.2,
            "total_sec": 1.4,
            "timestamp": now,
            "text": "must never be exported",
        }
    )

    outbox_db = tmp_path / "outbox.sqlite3"
    generation_db = tmp_path / "generation.sqlite3"
    with sqlite3.connect(outbox_db) as db:
        db.execute("CREATE TABLE telegram_outbox (status TEXT)")
        db.execute("INSERT INTO telegram_outbox VALUES ('failed_unknown')")
    with sqlite3.connect(generation_db) as db:
        db.execute("CREATE TABLE telegram_generation (status TEXT)")
        db.executemany("INSERT INTO telegram_generation VALUES (?)", [("pending",), ("pending",)])
    monkeypatch.setenv("TELEGRAM_OUTBOX_DB", str(outbox_db))
    monkeypatch.setenv("TELEGRAM_GENERATION_DB", str(generation_db))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "telegram_colab_canary.json").write_text(
        json.dumps({"ok": True, "timestamp": now, "consecutive_failures": 0}),
        encoding="utf-8",
    )

    rendered = metrics.render_telegram_prometheus()

    assert 'aios_telegram_provider_events{provider="colab"} 1' in rendered
    assert 'aios_telegram_queue_jobs{queue="outbox",status="failed_unknown"} 1' in rendered
    assert 'aios_telegram_queue_jobs{queue="generation",status="pending"} 2' in rendered
    assert "aios_telegram_canary_ok 1" in rendered
    assert "must never be exported" not in rendered


def test_grafana_dashboard_is_valid_json():
    path = metrics.ROOT / "deploy" / "monitoring" / "grafana-telegram-llm.json"
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    assert dashboard["uid"] == "aios-telegram-llm"
    assert len(dashboard["panels"]) >= 6


def test_sidecar_exporter_can_bind_ephemeral_port(monkeypatch):
    from tg_bot.metrics_exporter import _create_server

    monkeypatch.setenv("TELEGRAM_PROMETHEUS_ENABLED", "1")
    monkeypatch.setenv("TELEGRAM_PROMETHEUS_HOST", "127.0.0.1")
    monkeypatch.setenv("TELEGRAM_PROMETHEUS_PORT", "0")
    server = _create_server()
    assert server is not None
    assert server.server_address[1] > 0
    server.server_close()
