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
