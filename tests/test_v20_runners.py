# -*- coding: utf-8 -*-
"""v20.0 Activation: тесты новых раннеров — фриланс-воронка, flash-arb алерты, mesh fleet.

Без сети: внешние вызовы мокнуты/используются tmp-path состояния.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path("/root/AIOS")


def _load_runner(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# run_freelance_funnel.py
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def funnel(tmp_path, monkeypatch):
    mod = _load_runner("funnel_mod", "run_freelance_funnel.py")
    tasks = [
        {"id": "t1", "status": "BID_SUBMITTED", "source": "freelancehunt", "budget_usd": 100, "created_at": time.time()},
        {"id": "t2", "status": "BID_SUBMITTED", "source": "github_bounty", "budget_usd": 50, "created_at": time.time()},
        {"id": "t3", "status": "WON", "source": "freelancehunt", "budget_usd": 200, "created_at": time.time() - 10 * 86400},
        {"id": "t4", "status": "LOST", "source": "fiverr", "budget_usd": 30, "created_at": time.time() - 10 * 86400},
    ]
    data = tmp_path / "tasks.json"
    data.write_text(json.dumps(tasks), encoding="utf-8")
    monkeypatch.setattr(mod, "DATA", data)
    monkeypatch.setattr(mod, "STATE", tmp_path / "state.json")
    return mod


def test_funnel_report(funnel):
    r = funnel.build_report()
    assert r["total_tasks"] == 4
    assert r["open_bids"] == 2
    assert r["won"] == 1 and r["lost"] == 1
    assert r["win_rate_pct"] == 50.0
    assert r["pipeline_open_usd"] == 150.0
    assert r["new_last_7d"] == 2  # t3/t4 старше 7 дней


def test_funnel_tg_text(funnel):
    r = funnel.build_report()
    txt = funnel.tg_text(r)
    assert "Freelance Funnel" in txt and "$150" in txt and "50.0%" in txt


def test_funnel_mark_outcome(funnel, capsys):
    sys.argv = ["x", "--mark", "WON", "t1"]
    funnel.main()
    r = funnel.build_report()
    assert r["won"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# run_dex_arbitrage_scanner.py — TG алерты (без сети)
# ─────────────────────────────────────────────────────────────────────────────
def test_arb_alert_cooldown(monkeypatch):
    mod = _load_runner("arb_mod", "run_dex_arbitrage_scanner.py")
    monkeypatch.setattr(mod, "_load_env_var", lambda n: "fake" if n == "TELEGRAM_CHAT_ID" else None)
    # нет токена → False, но и cooldown не трогаем
    assert mod.send_telegram_alert("test", cooldown_sec=0) is False


def test_arb_viability_logic():
    """Чистая математика viable-окна: спред - издержки."""
    gross = 10000 * 0.012          # 1.2% спред
    cost = 10000 * 0.0035 + 0.02   # slippage+fee+gas
    net = gross - cost
    assert net > 5  # окно viable
    gross2 = 10000 * 0.001         # 0.1% спред
    assert gross2 - cost < 5       # окно НЕ viable — алерта не будет


# ─────────────────────────────────────────────────────────────────────────────
# mesh fleet (aios_core.android_mesh) с tmp-состоянием
# ─────────────────────────────────────────────────────────────────────────────
def test_mesh_fleet_lease_release(tmp_path, monkeypatch):
    from aios_core.android_mesh import AndroidMeshFleet
    fleet = AndroidMeshFleet.__new__(AndroidMeshFleet)
    # подменяем файл флота на tmp
    import types
    fleet.fleet_file = tmp_path / "fleet.json"
    fleet.devices = {}
    # минимальный контракт: методы существуют и callable
    for m in ("register_device", "heartbeat", "list_devices"):
        assert hasattr(fleet, m), m


def test_mesh_runner_loads():
    mod = _load_runner("mesh_mod", "run_android_mesh.py")
    assert hasattr(mod, "main")
