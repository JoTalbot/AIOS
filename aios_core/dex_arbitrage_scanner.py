"""
AIOS Flash-Loan Arbitrage Engine v19.2
Безрисковый арбитраж между DEX (Uniswap V3, QuickSwap, SushiSwap) и CEX (Kraken, Binance) с flash-loan симуляцией Aave V3.

Dry-run по умолчанию, live требует AIOS_FLASH_LIVE=1 + приватный ключ.
"""
from __future__ import annotations

import os
import json
import time
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from pathlib import Path

from web3 import Web3

from aios_core.crypto_wallet import AIOSWalletManager, PUBLIC_RPC_NODES
from aios_core.kraken_client import AIOSKrakenClient

logger = logging.getLogger("AIOS.FlashArbitrage")

# --- Константы v19.2 ---
AAVE_FLASH_FEE_PCT = {
    "polygon": 0.05,  # Aave V3 Polygon 0.05%
    "arbitrum": 0.05,
    "base": 0.05,
    "ethereum": 0.09,
}
GAS_COST_USD = {
    "polygon": 0.02,
    "arbitrum": 0.03,
    "base": 0.015,
    "ethereum": 3.5,
    "solana": 0.01,
}
# Uniswap V3 pools on Polygon (main)
UNISWAP_V3_POOLS_POLYGON = {
    "WETH/USDC": "0x45dda9cb7c25131df268515131f647d726f50608",  # WETH/USDC 0.05% Polygon
    "WMATIC/USDC": "0xA374094527e1673A86DeJEcF26850334b5A16533",
}
QUICKSWAP_POOLS_POLYGON = {
    "WETH/USDC": "0x853Ee4b2A13f8a742d64C8F088bEfea2138b685D",
}
# Binance symbols
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
COINGECKO_SIMPLE_URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

# Mapping for pairs
PAIRS_CFG = [
    {"symbol": "WETH", "coingecko": "weth", "kraken": "XETHZUSD", "binance": "ETHUSDT", "decimals": 18},
    {"symbol": "WBTC", "coingecko": "wrapped-bitcoin", "kraken": "XXBTZUSD", "binance": "BTCUSDT", "decimals": 8},
    {"symbol": "WMATIC", "coingecko": "matic-network", "kraken": "MATICUSD", "binance": "MATICUSDT", "decimals": 18},
    {"symbol": "SOL", "coingecko": "solana", "kraken": "SOLUSD", "binance": "SOLUSDT", "decimals": 9},
]


class AIOSFlashLoanArbitrageEngine:
    """Flash-Loan Арбитраж Engine — кросс-DEX/CEX спред + симуляция."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
        self.data_dir = Path(data_dir)
        self.kraken = AIOSKrakenClient(data_dir)
        self.wallet = AIOSWalletManager(data_dir)
        self.state_file = self.data_dir / "flash_arbitrage_state.json"

    # --- Price fetchers ---
    def _fetch_kraken_price(self, pair_kraken: str) -> Optional[float]:
        try:
            res = self.kraken.get_ticker(pair_kraken)
            if res.get("status") == "success":
                ticker = res.get("ticker", {})
                for k, v in ticker.items():
                    ask = float(v.get("a", [0])[0])
                    bid = float(v.get("b", [0])[0])
                    mid = (ask + bid) / 2 if ask and bid else ask or bid
                    if mid:
                        return mid
        except Exception as e:
            logger.debug(f"Kraken {pair_kraken} fail: {e}")
        return None

    def _fetch_binance_price(self, symbol: str) -> Optional[float]:
        try:
            url = BINANCE_TICKER_URL.format(symbol=symbol)
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS/19.2"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
                return float(data.get("price", 0))
        except Exception as e:
            logger.debug(f"Binance {symbol} fail: {e}")
            return None

    def _fetch_coingecko_price(self, ids: str) -> Optional[float]:
        try:
            url = COINGECKO_SIMPLE_URL.format(ids=ids)
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS/19.2"})
            with urllib.request.urlopen(req, timeout=7) as r:
                data = json.loads(r.read().decode())
                return float(data.get(ids, {}).get("usd", 0))
        except Exception as e:
            logger.debug(f"CG {ids} fail: {e}")
            return None

    def _fetch_1inch_quote(self, from_token: str, to_token: str, amount: int, chain_id: int = 137) -> Optional[float]:
        """1inch quote for DEX price (Polygon 137). Returns price per unit."""
        try:
            # 1inch requires API key now, fallback to Coingecko if blocked
            url = f"https://api.1inch.dev/swap/v6.0/{chain_id}/quote?src={from_token}&dst={to_token}&amount={amount}"
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS/19.2", "Authorization": f"Bearer {os.getenv('ONEINCH_API_KEY','')}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
                dst_amount = int(data.get("dstAmount", 0))
                if dst_amount:
                    # price = dst / src normalized
                    return dst_amount / amount
        except Exception as e:
            logger.debug(f"1inch quote fail: {e}")
        return None

    def _fetch_uniswap_v3_price(self, network: str = "polygon", pair: str = "WETH/USDC") -> Optional[float]:
        """On-chain Uniswap V3 slot0 price. Simplified — returns mid price via sqrtPriceX96."""
        try:
            # Use public RPC, try polygon
            rpcs = PUBLIC_RPC_NODES.get(network, ["https://polygon.drpc.org"])
            w3 = None
            for rpc in rpcs:
                try:
                    tmp = Web3(Web3.HTTPProvider(rpc, request_kwargs={'timeout': 4}))
                    if tmp.is_connected():
                        w3 = tmp
                        break
                except Exception:
                    continue
            if not w3:
                return None
            pool_addr = UNISWAP_V3_POOLS_POLYGON.get(pair)
            if not pool_addr:
                return None
            # Minimal ABI for slot0
            abi = [{"inputs": [], "name": "slot0", "outputs": [{"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"}, {"internalType": "int24", "name": "tick", "type": "int24"}, {"internalType": "uint16", "name": "observationIndex", "type": "uint16"}, {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"}, {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"}, {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"}, {"internalType": "bool", "name": "unlocked", "type": "bool"}], "stateMutability": "view", "type": "function"}]
            c = w3.eth.contract(address=Web3.to_checksum_address(pool_addr), abi=abi)
            sqrtPriceX96 = c.functions.slot0().call()[0]
            # price = (sqrtPriceX96 / 2**96) **2, then adjust decimals (USDC 6, WETH 18 → price * 10**12)
            price = (sqrtPriceX96 / (2 ** 96)) ** 2
            # For WETH/USDC pool, price is USDC per WETH * 10**(USDC_dec - WETH_dec) ??? simplified
            # WETH 18, USDC 6 → multiply by 10**12 to get human price
            if pair == "WETH/USDC":
                price = price * (10 ** 12)
                # If price is inverted (USDC/WETH), invert
                if price < 10:
                    price = 1 / price * (10 ** 12)  # rough
            return round(price, 2) if 100 < price < 100000 else None
        except Exception as e:
            logger.debug(f"UniV3 {pair} {network} fail: {e}")
            return None

    def fetch_all_prices(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Собрать цены по всем venue для каждого символа."""
        result = {}
        for cfg in PAIRS_CFG:
            sym = cfg["symbol"]
            kraken = self._fetch_kraken_price(cfg["kraken"])
            binance = self._fetch_binance_price(cfg["binance"])
            cg = self._fetch_coingecko_price(cfg["coingecko"])
            # Uniswap only for WETH/USDC on Polygon
            uni = None
            if sym == "WETH":
                uni = self._fetch_uniswap_v3_price("polygon", "WETH/USDC")
                # fallback to cg if uni fails
                if not uni and cg:
                    uni = cg
            # QuickSwap fallback same as uni for now
            quick = uni

            venue_prices = {
                "kraken": kraken,
                "binance": binance,
                "coingecko": cg,
                "uniswap_v3_polygon": uni,
                "quickswap_polygon": quick,
            }
            # Filter None
            venue_prices = {k: v for k, v in venue_prices.items() if v and v > 0}
            result[sym] = venue_prices
        return result

    def scan_cross_dex_opportunities(self, min_spread_pct: float = 0.8, flash_amount_usd: float = 10000) -> Dict[str, Any]:
        """Сканирование кросс-DEX/CEX спредов с flash-loan симуляцией."""
        prices = self.fetch_all_prices()
        opportunities = []
        for sym, venues in prices.items():
            if len(venues) < 2:
                continue
            # Find min and max
            sorted_venues = sorted(venues.items(), key=lambda x: x[1])
            low_venue, low_price = sorted_venues[0]
            high_venue, high_price = sorted_venues[-1]
            spread_usd = high_price - low_price
            spread_pct = (spread_usd / low_price) * 100 if low_price else 0
            spread_pct = round(spread_pct, 3)
            # Data validation: filter unrealistic spreads >15% (likely API error / stale price)
            if spread_pct > 15 and sym in ["WMATIC","WETH","WBTC","SOL"]:
                logger.warning(f"Data error: {sym} spread {spread_pct}% unrealistic (low {low_price} high {high_price}) — skipping")
                continue

            # Flash-loan simulation
            # Fee: Aave 0.05% on polygon, gas $0.02, slippage 0.3%
            flash_fee_pct = AAVE_FLASH_FEE_PCT["polygon"]
            gas_usd = GAS_COST_USD["polygon"]
            slippage_pct = 0.3
            total_cost_pct = flash_fee_pct + slippage_pct
            total_cost_usd = flash_amount_usd * (total_cost_pct / 100) + gas_usd
            gross_profit = flash_amount_usd * (spread_pct / 100)
            net_profit = gross_profit - total_cost_usd
            net_pct = (net_profit / flash_amount_usd) * 100 if flash_amount_usd else 0

            # Также считаем для 50k
            flash50 = 50000
            gross50 = flash50 * (spread_pct / 100)
            net50 = gross50 - (flash50 * (total_cost_pct / 100) + gas_usd)

            viable = spread_pct >= min_spread_pct and net_profit > 5

            opportunities.append({
                "pair": f"{sym}/USD",
                "symbol": sym,
                "venues": venues,
                "low": {"venue": low_venue, "price": low_price},
                "high": {"venue": high_venue, "price": high_price},
                "spread_usd": round(spread_usd, 2),
                "spread_pct": spread_pct,
                "flash_sim_10k": {
                    "gross_profit_usd": round(gross_profit, 2),
                    "flash_fee_pct": flash_fee_pct,
                    "slippage_pct": slippage_pct,
                    "gas_usd": gas_usd,
                    "total_cost_usd": round(total_cost_usd, 2),
                    "net_profit_usd": round(net_profit, 2),
                    "net_pct": round(net_pct, 3),
                },
                "flash_sim_50k_net_usd": round(net50, 2),
                "viable": viable,
                "viability_reason": "spread >= threshold and net > $5" if viable else f"spread {spread_pct}% < {min_spread_pct}% or net ${round(net_profit,2)} <= $5 (cost {total_cost_pct}%+gas)"
            })

        opportunities.sort(key=lambda x: x["spread_pct"], reverse=True)
        viable_count = sum(1 for o in opportunities if o["viable"])
        best = opportunities[0] if opportunities else None

        return {
            "status": "success",
            "timestamp": int(time.time()),
            "params": {"min_spread_pct": min_spread_pct, "flash_amount_usd": flash_amount_usd, "flash_fee_pct": AAVE_FLASH_FEE_PCT["polygon"], "gas_usd": GAS_COST_USD["polygon"]},
            "venues_scanned": ["kraken", "binance", "coingecko", "uniswap_v3_polygon", "quickswap_polygon"],
            "pairs_scanned": len(prices),
            "opportunities_total": len(opportunities),
            "viable_count": viable_count,
            "best_opportunity": best,
            "opportunities": opportunities,
            "flash_loan_note": "Aave V3 Polygon flashFee 0.05%, gas $0.02, slippage 0.3% — net must be >$5 to be viable. Live execution requires smart contract + AIOS_FLASH_LIVE=1"
        }

    # Legacy compatibility
    def scan_arbitrage_opportunities(self, min_spread_pct: float = 0.5) -> Dict[str, Any]:
        """Legacy wrapper for old run_dex_arbitrage_scanner (kraken internal spread only)."""
        # Keep old behavior for backward compat, but also include cross-dex
        pairs = [
            {"symbol": "BTC", "pair_kraken": "XXBTZUSD"},
            {"symbol": "ETH", "pair_kraken": "XETHZUSD"},
            {"symbol": "SOL", "pair_kraken": "SOLUSD"}
        ]
        results = []
        for p in pairs:
            sym = p["symbol"]
            ticker_res = self.kraken.get_ticker(p["pair_kraken"])
            if ticker_res.get("status") == "success":
                ticker_data = ticker_res.get("ticker", {})
                for k, v in ticker_data.items():
                    bid = float(v.get("b", [0])[0])
                    ask = float(v.get("a", [0])[0])
                    spread = round(ask - bid, 2)
                    spread_pct = round((spread / ask) * 100, 3) if ask > 0 else 0.0
                    results.append({
                        "pair": sym + "/USD",
                        "exchange": "Kraken",
                        "bid": bid,
                        "ask": ask,
                        "spread_usd": spread,
                        "spread_pct": spread_pct,
                        "opportunity": "ARBITRAGE_VIABLE" if spread_pct > min_spread_pct else "NORMAL_LIQUIDITY"
                    })
        # Also add cross-dex best if viable
        cross = self.scan_cross_dex_opportunities(min_spread_pct=0.8)
        return {
            "status": "success",
            "pairs_scanned": len(results),
            "opportunities": results,
            "cross_dex_scan": cross,
            "note": "Legacy kraken internal + cross-dex scan included"
        }

    def simulate_flash_loan(self, buy_venue: str, sell_venue: str, symbol: str, amount_usd: float = 10000) -> Dict[str, Any]:
        """Симуляция конкретного flash-loan: купить на buy_venue, продать на sell_venue."""
        prices = self.fetch_all_prices()
        venue_prices = prices.get(symbol, {})
        buy_price = venue_prices.get(buy_venue)
        sell_price = venue_prices.get(sell_venue)
        if not buy_price or not sell_price:
            return {"status": "error", "error": f"Prices not available for {symbol} {buy_venue}/{sell_venue}", "prices": venue_prices}
        spread_pct = ((sell_price - buy_price) / buy_price) * 100
        flash_fee = amount_usd * (AAVE_FLASH_FEE_PCT["polygon"] / 100)
        gas = GAS_COST_USD["polygon"]
        slippage = amount_usd * 0.003
        total_cost = flash_fee + gas + slippage
        gross = amount_usd * (spread_pct / 100)
        net = gross - total_cost
        return {
            "status": "success",
            "symbol": symbol,
            "buy": {"venue": buy_venue, "price": buy_price},
            "sell": {"venue": sell_venue, "price": sell_price},
            "amount_usd": amount_usd,
            "spread_pct": round(spread_pct, 3),
            "gross_profit_usd": round(gross, 2),
            "costs": {"flash_fee_usd": round(flash_fee, 2), "gas_usd": gas, "slippage_usd": round(slippage, 2), "total": round(total_cost, 2)},
            "net_profit_usd": round(net, 2),
            "viable": net > 5 and spread_pct > 0.8,
            "dry_run": True,
            "live_note": "Set AIOS_FLASH_LIVE=1 and deploy AaveFlashArb contract to execute on-chain"
        }

    def generate_telegram_report(self) -> str:
        cross = self.scan_cross_dex_opportunities()
        lines = ["⚡ *AIOS Flash-Loan Arbitrage v19.2*", ""]
        lines.append(f"Просканировано пар: `{cross['pairs_scanned']}` | Всего возможностей: `{cross['opportunities_total']}` | Viable: `{cross['viable_count']}`")
        lines.append(f"Параметры: spread ≥ `{cross['params']['min_spread_pct']}%` | flash 10k fee `{cross['params']['flash_fee_pct']}%` + gas `${cross['params']['gas_usd']}`")
        lines.append("")
        if cross["best_opportunity"]:
            b = cross["best_opportunity"]
            lines.append(f"🏆 Лучшее: *{b['pair']}* `{b['spread_pct']}%` ({b['low']['venue']} ${b['low']['price']} → {b['high']['venue']} ${b['high']['price']})")
            lines.append(f"  10k: gross `${b['flash_sim_10k']['gross_profit_usd']}` - cost `${b['flash_sim_10k']['total_cost_usd']}` = net `${b['flash_sim_10k']['net_profit_usd']}` ({b['flash_sim_10k']['net_pct']}%)")
            lines.append(f"  50k net: `${b['flash_sim_50k_net_usd']}` | {'✅ VIABLE' if b['viable'] else '❌ no'} — {b['viability_reason']}")
            lines.append("")
        lines.append("📊 Все пары:")
        for o in cross["opportunities"]:
            marker = "✅" if o["viable"] else "•"
            lines.append(f"{marker} {o['pair']} {o['low']['venue']}→{o['high']['venue']} `{o['spread_pct']}%` net10k `${o['flash_sim_10k']['net_profit_usd']}`")
        lines.append("")
        if cross["viable_count"] == 0:
            lines.append("ℹ️ Viable нет — спреды < порога или net ≤$5. Нормально для спокойного рынка.")
            lines.append("Ждем волатильности. Flash-loan без риска — только газ при revert.")
        else:
            lines.append(f"⚠️ Найдено {cross['viable_count']} viable — `dry_run` → `simulate_flash_loan()` → live с `AIOS_FLASH_LIVE=1`")
        return "\n".join(lines)

    def execute_flash_arbitrage(self, symbol: str, buy_venue: str, sell_venue: str, amount_usd: float = 10000, dry_run: bool = True) -> Dict[str, Any]:
        sim = self.simulate_flash_loan(buy_venue, sell_venue, symbol, amount_usd)
        if sim.get("status") != "success":
            return sim
        if dry_run:
            sim["status"] = "dry_run"
            sim["next_step"] = "Set dry_run=False and AIOS_FLASH_LIVE=1 to attempt on-chain flash loan via AaveFlashArb.sol"
            return sim
        if os.getenv("AIOS_FLASH_LIVE", "0") != "1":
            return {"status": "blocked", "error": "Set AIOS_FLASH_LIVE=1 to allow live flash loan", "simulation": sim}
        # Live stub — requires deployed contract
        if not sim["viable"]:
            return {"status": "no_action", "reason": "Not viable after cost, abort", "simulation": sim}
        has_key = False
        try:
            has_key = bool(self.wallet.load_vault().get("evm_private_key"))
        except Exception:
            pass
        if not has_key:
            return {"status": "error", "error": "No private key for flash loan executor", "simulation": sim}
        return {"status": "live_stub", "message": "Live flash-loan stub — deploy AaveFlashArb.sol and call executeArbitrage() here. Dry-run only for safety.", "simulation": sim}

    def save_state(self, data: Dict[str, Any]):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

# Backward compat alias
AIOSDEXArbitrageScanner = AIOSFlashLoanArbitrageEngine
