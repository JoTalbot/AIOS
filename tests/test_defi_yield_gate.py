from scripts.check_defi_yield_gate import evaluate


def test_mock_volatile_destination_is_blocked():
    state = {
        "current_network": "Polygon",
        "current_allocation": {"Polygon": {"balance_usd": 100, "is_mock": False}, "Solana": {"is_mock": True}},
        "all_opportunities": [{"network": "Solana", "type": "native_staking", "apy_pct": 7}],
        "bridge_quote": {"provider": "stub"},
    }
    r = evaluate(state)
    assert not r["ready"]
    assert r["best"]["risk_adjusted_apy_pct"] == -13
    assert not r["checks"]["destination_live"]
