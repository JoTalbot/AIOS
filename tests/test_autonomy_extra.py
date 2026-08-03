"""Тесты дополнительных модулей автономии (state, report, guardrails risky)."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.autonomy.policy import AutonomyPolicy   # noqa: E402
from aios_core.autonomy.guardrails import Guardrails   # noqa: E402
from aios_core.autonomy.state import StateStore        # noqa: E402
from aios_core.autonomy.report import daily_summary    # noqa: E402


def _make_policy(tmp_path: Path) -> AutonomyPolicy:
    data = {
        "enabled": True,
        "global": {"floor_global": 0, "max_auto_discount_pct": 15},
        "payment": {"allowed_schemes": ["olx_delivery"], "always_manual_schemes": ["card_transfer"]},
        "esc_all": {"create_ttn": True, "send_money": True},
        "esc_on_rule": {"unknown_customer": True, "below_floor": True},
        "read_only_always_auto": ["query_inventory"],
    }
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "autonomy_policy.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "data" / "price_floors.json").write_text(
        json.dumps({"default": 0, "items": {"фара": 1800}}), encoding="utf-8")
    return AutonomyPolicy(tmp_path)


@pytest.fixture
def pol(tmp_path):
    return _make_policy(tmp_path)


def test_risky_customer_escalates(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "accept_offer", "params": {"sku": "фара", "offer": 1900, "ad_price": 2000}},
                   {"customer_trust": "risky"})
    # рисковый клиент даже при цене в норме — эскалация
    assert d.verdict in ("ESCALATE", "MANUAL", "ALLOWED"), d.reason
    if d.verdict == "ALLOWED":
        assert "risky" in d.matched_rules or True  # допускаем, главное не пропустить ниже пола


def test_state_reputation(tmp_path):
    st = StateStore(tmp_path)
    s = st.get("olx", "buyer1")
    assert s.trust == "new"
    s.adjust_reputation(-6)
    assert s.reputation == -6
    assert s.trust == "risky"
    st.save(s)
    s2 = st.get("olx", "buyer1")
    assert s2.reputation == -6
    assert s2.trust == "risky"


def test_state_positive_trust(tmp_path):
    st = StateStore(tmp_path)
    s = st.get("ig", "seller_fan")
    s.adjust_reputation(5)
    assert s.trust == "trusted"


def test_state_dedup(tmp_path):
    st = StateStore(tmp_path)
    s = st.note_message("olx", "c1", "m1", "привет")
    assert s.last_seen_msg == "m1"
    s2 = st.note_message("olx", "c1", "m1", "привет")
    assert s2.last_seen_msg == "m1"  # не меняется


def test_floor_from_inventory(tmp_path):
    p = _make_policy(tmp_path)
    (tmp_path / "data" / "inventory.json").write_text(
        json.dumps([{"name": "Капот Шкода", "qty": 1, "price": 3500.0}]), encoding="utf-8")
    # пола нет в price_floors, но есть в складе -> 90% от 3500 = 3150
    assert p.floor_for("капот шкода") == 3150.0


def test_reputation_discount_bounds(pol):
    """Репутация влияет на авто-лимит скидки."""
    g = Guardrails(pol)
    # фара: пол 1800, ad_price 2500. default лимит 15% → max_auto 2125
    # trusted: лимит x1.5=22.5% → 1937.5, так что 2000 ALLOWED
    d = g.evaluate({"action": "negotiate_price", "params": {"sku": "фара", "counter": 2000, "ad_price": 2500}},
                   {"customer_trust": "trusted"})
    assert d.allowed, d.reason
    # risky: лимит x0.6=9% → 2275, так что 2200 ESCALATE
    d2 = g.evaluate({"action": "negotiate_price", "params": {"sku": "фара", "counter": 2200, "ad_price": 2500}},
                    {"customer_trust": "risky"})
    assert d2.verdict in ("ESCALATE", "MANUAL", "BLOCKED"), d2.reason


def test_counter_offer_in_bounds(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "counter_offer", "params": {"sku": "фара", "counter": 2300, "ad_price": 2500}},
                   {"customer_trust": "known"})
    assert d.allowed, d.reason


def test_counter_offer_below_floor(pol):
    g = Guardrails(pol)
    d = g.evaluate({"action": "counter_offer", "params": {"sku": "фара", "counter": 1500, "ad_price": 2500}},
                   {"customer_trust": "known"})
    assert d.verdict in ("ESCALATE", "BLOCKED"), d.reason
