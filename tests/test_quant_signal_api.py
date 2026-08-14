import json

from aios_core.api.monetization_routes import quant_signal_payload


def test_quant_signal_payload_filters_and_is_read_only(monkeypatch, tmp_path):
    path = tmp_path / "signals.json"
    path.write_text(
        json.dumps(
            {
                "generated_at": "x",
                "counts": {"WATCH_UP": 1},
                "signals": [{"symbol": "BTC", "label": "WATCH_UP"}, {"symbol": "ETH", "label": "NEUTRAL"}],
            }
        )
    )
    monkeypatch.setenv("AIOS_QUANT_SIGNAL_REPORT", str(path))
    monkeypatch.setattr("aios_core.api.monetization_routes.os.path.getmtime", lambda _p: 100.0)
    result = quant_signal_payload("watch_up", 10, now=200.0)
    assert result["status"] == "ok"
    assert result["execution"] == "read_only"
    assert result["trading_entry_mode"] == "freeze"
    assert [x["symbol"] for x in result["signals"]] == ["BTC"]
    assert result["stale"] is False
