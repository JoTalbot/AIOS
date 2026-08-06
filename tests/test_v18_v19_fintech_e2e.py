"""
AIOS v18/v19 Fintech & Multi-Chain E2E Test Suite
Тестирование всех новых компонентов казначейства, смарт-ликвидности, арбитража и фиатного диспетчера.
"""
import pytest
import os
import sys
from pathlib import Path

# Корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.treasury_manager import AIOSTreasuryManager
from aios_core.smart_liquidity_router import AIOSSmartLiquidityRouter
from aios_core.dex_arbitrage_scanner import AIOSDEXArbitrageScanner
from aios_core.fiat_dispatcher import AIOSFiatDispatcher
from aios_core.kraken_client import AIOSKrakenClient
from aios_core.crypto_wallet import AIOSWalletManager


def test_wallet_manager_4_way_split():
    mgr = AIOSWalletManager(str(PROJECT_ROOT / "data"))
    summary = mgr.get_financial_summary()
    assert summary["policy"] == "4_WAY_25_PERCENT_PROFIT_SPLIT"
    assert "wallet_balances_usd" in summary
    assert "wallets_addresses" in summary
    balances = summary["wallet_balances_usd"]
    assert balances["1_developer_25pct"] > 0
    assert balances["2_investor_25pct"] > 0
    assert balances["3_personnel_25pct"] > 0
    assert balances["4_system_autonomous_25pct"] > 0


def test_treasury_audit_and_buffer():
    tm = AIOSTreasuryManager(str(PROJECT_ROOT / "data"))
    audit = tm.audit_reserves()
    assert audit["status"] == "success"
    assert audit["monthly_operating_cost_usd"] == 37.0
    assert audit["safety_buffer_3_months_usd"] == 111.0
    assert audit["system_budget_usd"] >= 0.0


def test_smart_liquidity_router_scan():
    router = AIOSSmartLiquidityRouter(str(PROJECT_ROOT / "data"))
    res = router.scan_multi_chain_yields()
    assert res["status"] == "success"
    assert "best_yield_strategy" in res
    assert len(res["all_opportunities"]) >= 3
    # Проверяем, что Base Compound V3 имеет высокую ставку
    best = res["best_yield_strategy"]
    assert best["apy_pct"] >= 2.0


def test_fiat_dispatcher_live_rate():
    dispatcher = AIOSFiatDispatcher(str(PROJECT_ROOT / "data"))
    res = dispatcher.get_fiat_exchange_rate(100.0)
    assert res["status"] == "success"
    assert res["from_amount_usdt"] == 100.0
    assert res["estimated_rate"] >= 40.0
    assert res["expected_amount_uah"] >= 4000.0


def test_kraken_client_ticker():
    client = AIOSKrakenClient(str(PROJECT_ROOT / "data"))
    ticker_res = client.get_ticker("XXBTZUSD")
    assert ticker_res["status"] == "success"
    assert "XXBTZUSD" in ticker_res.get("ticker", {})


def test_dex_arbitrage_scanner():
    scanner = AIOSDEXArbitrageScanner(str(PROJECT_ROOT / "data"))
    res = scanner.scan_arbitrage_opportunities()
    assert res["status"] == "success"
    assert res["pairs_scanned"] == 3
    for opp in res["opportunities"]:
        assert opp["ask"] >= opp["bid"]
        assert opp["spread_usd"] >= 0.0
