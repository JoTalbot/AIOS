# -*- coding: utf-8 -*-
"""v21.0 Scale: тесты OLX Pipeline (склад→объявление→продажа→ТТН).

Изолированные tmp-копии данных: боевой склад не трогаем.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path("/root/AIOS")


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Изолированная среда пайплайна: tmp-inventory + tmp-state."""
    pipe = _load("olx_pipeline", "run_olx_pipeline.py")
    inv_mod = _load("run_inventory", "run_inventory.py")
    inv_file = tmp_path / "inventory.json"
    inv_file.write_text(json.dumps([
        {"name": "Деталь А", "qty": 2, "price": 100.0, "reservations": [], "reserved_qty": 0, "stock_status": "in_stock"},
        {"name": "Деталь Б", "qty": 0, "price": 50.0, "reservations": [], "reserved_qty": 0, "stock_status": "out_of_stock"},
    ], ensure_ascii=False), encoding="utf-8")
    # главный редирект: все операции inventory (reserve/commit/_load/_save) → tmp-файл
    real_path = inv_mod._path
    monkeypatch.setattr(inv_mod, "_path", lambda data_path=None: inv_file if data_path is None else real_path(data_path))
    monkeypatch.setattr(pipe, "inv", inv_mod)
    sales_file = tmp_path / "sales_lifecycle.json"
    sales_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(pipe, "PUBLISHED", tmp_path / "olx_published.json")
    monkeypatch.setattr(pipe, "STATE", tmp_path / "state.json")
    # data точка для sales
    data_dir = tmp_path
    monkeypatch.setattr(pipe, "DATA", data_dir)
    return pipe, inv_file, sales_file


def test_scan_only_available(env, capsys):
    pipe, *_ = env
    r = pipe.cmd_scan()
    assert r["unpublished_count"] == 1
    assert r["items"][0]["name"] == "Деталь А"


def test_sold_reserve_and_substring_match(env, capsys):
    pipe, inv_file, _ = env
    r = pipe.cmd_sold("Деталь", 1, "sale-T1", "2045001")
    assert r.get("status") == "ok"
    item = json.loads(inv_file.read_text())[0]
    assert item.get("reserved_qty") == 1 or any(res.get("sale_id") == "sale-T1" for res in item.get("reservations", []))


def test_cycle_commit_idempotent(env, capsys):
    pipe, inv_file, sales_file = env
    pipe.cmd_sold("Деталь А", 1, "sale-T2", "")
    sales_file.write_text(json.dumps([{"id": "sale-T2", "item": "Деталь А", "status": "in_transit"}]))
    r1 = pipe.cmd_cycle(notify=False)
    assert any(a["action"] == "stock_committed" for a in r1["stock_actions"])
    r2 = pipe.cmd_cycle(notify=False)
    assert r2["stock_actions"] == []  # второй прогон — идемпотентно
    item = json.loads(inv_file.read_text())[0]
    assert item["qty"] == 1


def test_report_structure(env, capsys):
    pipe, *_ = env
    r = pipe.cmd_report()
    assert r["inventory"]["positions"] == 2
    assert r["inventory"]["available_qty"] == 2
    assert r["inventory"]["value_uah"] == 200.0


def test_olx_price_rules(monkeypatch):
    """v21.3: цена склада > модель в названии; явная валюта доверяется."""
    import run_olx_ad_gen as adgen

    monkeypatch.setattr(adgen, "_llm", lambda p: json.dumps(
        {"title": "Тестовая деталь 16+ символов", "description": "б/у", "price": ""}))
    monkeypatch.setattr(adgen, "_inventory_price",
                        lambda part: 950.0 if "Радиатор" in part else None)

    cases = [
        ("Радиатор охлаждения ВАЗ 2109", "950"),   # цена склада бьёт номер модели
        ("Крыло ВАЗ 2114", None),                   # голая 4-зн. модель — не цена
        ("Рессора ГАЗель 1800", None),              # 4-зн. без валюты — не цена
        ("Глушитель ВАЗ 2107 750 грн", "750"),      # явная валюта — цена
        ("Стекло фары 320 грн.", "320"),
    ]
    for part, want in cases:
        got = adgen.generate(part).get("price") or None
        assert got == want, f"{part}: {got} != {want}"
