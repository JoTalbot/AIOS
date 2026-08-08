"""Тесты модуля OLX-команд tg_bot/olx_cmds.py (выделен из монолита)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from tg_bot import olx_cmds


@pytest.fixture
def olx_db(tmp_path):
    """Создать тестовую БД OLX с парой объявлений."""
    db = tmp_path / "olx_test.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE ads (id INTEGER PRIMARY KEY, query TEXT, url TEXT, title TEXT,"
                " price_value REAL, price_currency TEXT, price_label TEXT, negotiable INT,"
                " city TEXT, region TEXT, description TEXT, category TEXT, photos_json TEXT,"
                " user_id INT, user_name TEXT, business INT, is_new INT, promoted INT,"
                " urgent INT, top_ad INT, created_time TEXT, last_refresh_time TEXT,"
                " first_seen TEXT, collected_at TEXT, active INT)")
    con.execute("CREATE TABLE collection_runs (ts TEXT PRIMARY KEY, queries TEXT,"
                " parsed INT, inserted INT, deactivated INT)")
    con.executemany(
        "INSERT INTO ads (id, query, url, title, price_value, price_currency, city, active) VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, "фара", "https://olx.ua/1", "Фара ВАЗ 2109", 500.0, "UAH", "Київ", 1),
            (2, "фара", "https://olx.ua/2", "Фара ВАЗ 2110", 700.0, "UAH", "Львів", 1),
            (3, "фара", "https://olx.ua/3", "Фара старая", 200.0, "UAH", "Одеса", 0),
        ],
    )
    con.execute("INSERT INTO collection_runs (ts, queries, parsed, inserted, deactivated) VALUES (?,?,?,?,?)",
                ("2026-08-08T10:00:00", "[]", 3, 3, 0))
    con.commit()
    con.close()
    return db


def test_cmd_olx_stats(olx_db, monkeypatch):
    monkeypatch.setenv("AIOS_OLX_HTTP_DB", str(olx_db))
    out = olx_cmds.cmd_olx("")
    assert "OLX Статистика" in out
    assert "3" in out  # всего собрано
    assert "2" in out  # активных


def test_cmd_olx_latest_query(olx_db, monkeypatch):
    monkeypatch.setenv("AIOS_OLX_HTTP_DB", str(olx_db))
    out = olx_cmds.cmd_olx_latest("фара", 1)
    assert "фара" in out
    assert "olx.ua/2" in out  # активное, последнее


def test_cmd_olx_analytics(olx_db, monkeypatch):
    monkeypatch.setenv("AIOS_OLX_HTTP_DB", str(olx_db))
    out = olx_cmds.cmd_olx_analytics("фара")
    assert "AI-аналитика цен" in out
    assert "Мин" in out


def test_cmd_olx_db_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_OLX_HTTP_DB", str(tmp_path / "nope.sqlite"))
    assert "не найдена" in olx_cmds.cmd_olx("")


def test_get_ads_db_ok(olx_db, monkeypatch):
    monkeypatch.setenv("AIOS_OLX_HTTP_DB", str(olx_db))
    conn, err = olx_cmds._get_ads_db()
    assert err is None and conn is not None
    conn.close()
