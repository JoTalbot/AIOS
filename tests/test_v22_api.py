"""v22 Platform groundwork tests: APIMonetizationManager + OLX Price Intelligence."""
import sys

import pytest

sys.path.insert(0, "/root/AIOS")


def test_api_monetization_manager_balance(tmp_path):
    """APIMonetizationManager: генерация ключа, баланс, списание."""
    from aios_core.api_monetization import APIMonetizationManager

    mgr = APIMonetizationManager(data_dir=str(tmp_path))
    key_info = mgr.generate_api_key(client_name="Pytest Client", deposit_usd=1.0)
    key = key_info["api_key"]
    assert key.startswith("aios_live_")

    keys = mgr.load_keys()
    assert keys[key]["credits_usd"] == 1.0
    assert mgr.verify_and_charge(key, 0.40)
    keys = mgr.load_keys()
    assert abs(keys[key]["credits_usd"] - 0.60) < 1e-9
    assert keys[key]["total_requests"] == 1
    assert not mgr.verify_and_charge(key, 0.99)  # недостаточно средств
    assert not mgr.verify_and_charge("bogus_key", 0.01)


def test_olx_price_intel_fixture(tmp_path, monkeypatch):
    """OLX Price Intelligence против тестовой sqlite: статистика и фильтры."""
    import sqlite3
    from aios_core.api import monetization_routes as mon

    db = tmp_path / "olx_fixture.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ads (id INTEGER PRIMARY KEY, query TEXT, url TEXT, title TEXT, "
                "price_value REAL, price_currency TEXT, price_label TEXT, negotiable INTEGER, "
                "city TEXT, region TEXT, description TEXT, category TEXT, photos_json TEXT, user_id TEXT)")
    rows = [
        ("запчастини ваз", "http://x/1", "Радиатор ВАЗ 2109 медный", 950, "UAH", "Кропивницкий"),
        ("запчастини ваз", "http://x/2", "Радиатор ВАЗ 2109 алюминий", 1100, "UAH", "Киев"),
        ("запчастини ваз", "http://x/3", "Радиатор охлаждения ВАЗ", 850, "UAH", "Одесса"),
        ("фара bmw x5", "http://x/4", "Фара BMW X5 левая", 9000, "UAH", "Львов"),
        ("запчастини ваз", "http://x/5", "Проводка ВАЗ (без цены)", None, "UAH", "Киев"),
    ]
    con.executemany("INSERT INTO ads (query, url, title, price_value, price_currency, city) "
                    "VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()

    monkeypatch.setenv("AIOS_OLX_LIVE_DB", str(db))
    r = mon.olx_price_intel("радиатор")
    assert r["status"] == "ok"
    assert r["matches"] == 3
    assert r["stats"]["min"] == 850
    assert r["stats"]["max"] == 1100
    assert r["stats"]["median"] == 950
    assert r["stats"]["currency"] == "UAH"
    assert len(r["samples"]) == 3

    r2 = mon.olx_price_intel("несуществующая деталь")
    assert r2["matches"] == 0 and r2["stats"] is None
    r3 = mon.olx_price_intel("")
    assert r3["status"] == "error"


def test_monetization_routes_registered():
    """get_monetization_routes: 5 endpoint'ов, все под /api/v2/mon/."""
    from aios_core.api.monetization_routes import get_monetization_routes

    routes = get_monetization_routes()
    assert len(routes) == 5
    paths = {r.path for r in routes}
    assert "/api/v2/mon/olx-price" in paths
    assert "/api/v2/mon/products" in paths
    assert all(p.startswith("/api/v2/mon/") for p in paths)


def test_usage_ledger_written(tmp_path):
    """v22-B: charge пишет JSONL-ledger с продуктом и клиентом."""
    import json
    from aios_core.api_monetization import APIMonetizationManager

    mgr = APIMonetizationManager(data_dir=str(tmp_path))
    key = mgr.generate_api_key(client_name="Ledger Client", deposit_usd=5.0)["api_key"]
    assert mgr.verify_and_charge(key, 0.10, product="olx_price")
    assert mgr.verify_and_charge(key, 0.05, product="summarize")

    ledger = tmp_path / "api_usage_ledger.jsonl"
    assert ledger.exists()
    lines = [json.loads(x) for x in ledger.read_text().splitlines()]
    assert len(lines) == 2
    assert lines[0]["product"] == "olx_price" and lines[0]["client"] == "Ledger Client"
    assert abs(lines[1]["cost_usd"] - 0.05) < 1e-9


def test_rate_limiter_bucket(monkeypatch):
    """v22-B: token bucket исчерпывается и даёт 429-семантику (False)."""
    from aios_core.api import monetization_routes as mon

    monkeypatch.setattr(mon, "_RATE_RPM", 3.0)
    mon._buckets.clear()
    assert mon._rate_ok("k1") is True
    assert mon._rate_ok("k1") is True
    assert mon._rate_ok("k1") is True
    assert mon._rate_ok("k1") is False          # ёмкость исчерпана
    assert mon._rate_ok("k2") is True           # другой ключ — свой бакет


def test_usage_report_aggregation(tmp_path, monkeypatch):
    """api_usage_report: агрегация по клиентам/продуктам за окно."""
    import json, time, importlib
    sys.path.insert(0, "/root/AIOS/scripts")
    ledger = tmp_path / "api_usage_ledger.jsonl"
    now = time.time()
    events = [
        {"ts": now - 100, "client": "Авторазборка К", "key8": "x", "product": "olx_price", "cost_usd": 0.10},
        {"ts": now - 200, "client": "Авторазборка К", "key8": "x", "product": "olx_price", "cost_usd": 0.10},
        {"ts": now - 100, "client": "Demo Client", "key8": "y", "product": "code_audit", "cost_usd": 0.10},
        {"ts": now - 90000, "client": "Old Client", "key8": "z", "product": "olx_price", "cost_usd": 0.10},
    ]
    ledger.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
    monkeypatch.setenv("AIOS_DATA_DIR", str(tmp_path))
    import api_usage_report as rep
    importlib.reload(rep)

    r = rep.build_report(24.0)
    assert r["events"] == 3                      # старое событие (25ч) отброшено
    assert abs(r["revenue_usd"] - 0.30) < 1e-9
    assert r["by_client"]["Авторазборка К"]["requests"] == 2
    assert "olx_price" in r["by_product_usd"]
