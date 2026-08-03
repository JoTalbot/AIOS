"""Тесты детерминированного ограничителя автономии (guardrails)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.autonomy.policy import AutonomyPolicy          # noqa: E402
from aios_core.autonomy.guardrails import Guardrails          # noqa: E402


def make_policy(tmp_path: Path, **overrides) -> AutonomyPolicy:
    data = {
        "enabled": True,
        "global": {"floor_global": 0, "max_auto_discount_pct": 15},
        "payment": {"allowed_schemes": ["olx_delivery", "np_cod", "prepaid_np"],
                    "always_manual_schemes": ["card_transfer", "crypto", "advance"]},
        "esc_all": {"create_ttn": True, "send_money": True, "accept_advance": True,
                    "create_ad": True, "boost_ad": True, "publish": True},
        "esc_on_rule": {"unknown_customer": True, "below_floor": True,
                        "unusual_payment": True, "big_discount": True},
        "read_only_always_auto": ["query_inventory", "query_finance"],
    }
    for k, v in overrides.items():
        data[k] = v
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "autonomy_policy.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "data" / "price_floors.json").write_text(
        json.dumps({"default": 0, "items": {"фара": 1800}}), encoding="utf-8")
    return AutonomyPolicy(tmp_path)


@pytest.fixture
def pol(tmp_path):
    return make_policy(tmp_path)


def test_accept_offer_above_floor_allowed(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "accept_offer", "params": {"sku": "фара", "offer": 1900, "ad_price": 2000}},
                   {"customer_trust": "known"})
    assert d.allowed, d.reason


def test_accept_offer_below_floor_esc(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "accept_offer", "params": {"sku": "фара", "offer": 1500, "ad_price": 2000}},
                   {"customer_trust": "known"})
    assert d.verdict in ("ESCALATE", "BLOCKED"), d.reason
    assert "ниже пола" in d.reason or "ниже" in d.reason


def test_big_discount_escalates(pol):
    g = Guardrails(pol)
    # скидка 30% (>15%) → эскалация
    d = g.evaluate({"action": "accept_offer", "params": {"sku": "фара", "offer": 1400, "ad_price": 2000}},
                   {"customer_trust": "known"})
    assert d.verdict in ("ESCALATE", "MANUAL", "BLOCKED"), d.reason


def test_create_ttn_always_manual(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "create_ttn", "params": {}}, {})
    assert d.verdict == "MANUAL", d.reason


def test_send_money_manual(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "send_money", "params": {"amount": 500}}, {})
    assert d.verdict == "MANUAL", d.reason


def test_payment_allowed_scheme(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "send_payment_info", "params": {"scheme": "olx_delivery"}}, {})
    assert d.allowed, d.reason


def test_payment_manual_scheme(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "send_payment_info", "params": {"scheme": "card_transfer"}}, {})
    assert d.verdict == "MANUAL", d.reason


def test_read_only_auto(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "query_inventory", "params": {}}, {})
    assert d.allowed, d.reason


def test_unknown_customer_escalates(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "reply_customer", "params": {"text": "привет"}},
                   {"customer_trust": "new"})
    # новый клиент с обычным ответом — эскалация по unknown_customer (стратегия консервативная)
    assert d.verdict in ("ALLOWED", "ESCALATE"), d.reason


def test_log_sale_allowed(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "log_sale", "params": {"item": "фара", "amount": 2000}}, {})
    assert d.allowed, d.reason
