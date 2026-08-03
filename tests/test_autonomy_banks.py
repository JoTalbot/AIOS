"""Тесты банковских действий автономии (безопасность переводов)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.autonomy import AutonomyCore  # noqa: E402


def _core():
    return AutonomyCore()


def test_bank_transfer_always_manual():
    c = _core()
    d = c.guardrails.evaluate({"action": "bank_transfer",
                               "params": {"bank": "privat", "recipient": "4149", "amount": 1000}}, {})
    assert d.verdict == "MANUAL", d.reason


def test_bank_balance_auto():
    c = _core()
    d = c.guardrails.evaluate({"action": "bank_balance", "params": {"bank": "abank"}}, {})
    assert d.allowed, d.reason


def test_bank_transactions_auto():
    c = _core()
    d = c.guardrails.evaluate({"action": "bank_transactions", "params": {"bank": "privat"}}, {})
    assert d.allowed, d.reason


def test_bank_transfer_blocked_even_for_risky():
    c = _core()
    # даже рисковый клиент / странный запрос не должен авто-переводить
    d = c.guardrails.evaluate({"action": "bank_transfer", "params": {"bank": "abank", "amount": 99999}},
                              {"customer_trust": "risky"})
    assert d.verdict == "MANUAL", d.reason


def test_bank_actions_in_known_actions():
    from aios_core.autonomy.planner import KNOWN_ACTIONS
    assert "bank_transfer" in KNOWN_ACTIONS
    assert "bank_balance" in KNOWN_ACTIONS


def test_registry_has_banks():
    from aios_core.platforms.registry import PlatformRegistry
    r = PlatformRegistry()
    assert "abank" in r.list_available_platforms()
    assert "privat" in r.list_available_platforms()
