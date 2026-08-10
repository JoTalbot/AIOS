"""
AIOS Triangular Arbitrage Engine
Сканирует 3-шаговые внутрибиржевые треугольные арбитражные цепочки (USDT -> Asset A -> Asset B -> USDT).
"""
from __future__ import annotations

import json
import logging
import urllib.request
import time
from typing import Dict, Any, List

logger = logging.getLogger("AIOS.TriangularArb")


class AIOSTriangularArbitrageEngine:
    """Двигатель внутрибиржевого треугольного арбитража."""

    @staticmethod
    def scan_triangular_opportunities(exchange: str = "binance") -> Dict[str, Any]:
        """Сканирует внутрибиржевые треугольники (USDT -> BTC -> ETH -> USDT и др.)."""
        # Запрашиваем цены со всех пар
        try:
            url = "https://api.binance.com/api/v3/ticker/bookTicker"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                prices = {}
                for d in data:
                    sym = d.get("symbol", "")
                    bid = float(d.get("bidPrice", 0.0))
                    ask = float(d.get("askPrice", 0.0))
                    if bid > 0 and ask > 0:
                        prices[sym] = {"bid": bid, "ask": ask}
        except Exception as e:
            logger.warning(f"Ошибка загрузки стаканов: {e}")
            return {"status": "error", "error": str(e)}

        # Цепочка #1: USDT -> BTC -> ETH -> USDT
        # 1. Покупаем BTC за USDT по ask: BTC_amount = 100 / BTCUSDT_ask
        # 2. Покупаем ETH за BTC по ask: ETH_amount = BTC_amount / ETHBTC_ask
        # 3. Продаем ETH за USDT по bid: final_usdt = ETH_amount * ETHUSDT_bid

        triangles = [
            ("BTC", "ETH"),
            ("BTC", "SOL"),
            ("ETH", "SOL"),
            ("BTC", "XRP"),
            ("ETH", "LINK")
        ]

        opportunities = []
        fee_per_leg = 0.00075 # 0.075% fee per trade
        total_fee_multiplier = (1 - fee_per_leg) ** 3 # ~0.99775

        for base_coin, quote_coin in triangles:
            pair1 = f"{base_coin}USDT"
            pair2 = f"{quote_coin}{base_coin}" # e.g. ETHBTC
            pair3 = f"{quote_coin}USDT"

            if pair1 in prices and pair2 in prices and pair3 in prices:
                p1_ask = prices[pair1]["ask"]
                p2_ask = prices[pair2]["ask"]
                p3_bid = prices[pair3]["bid"]

                if p1_ask > 0 and p2_ask > 0 and p3_bid > 0:
                    start_usdt = 100.0
                    step1_base = start_usdt / p1_ask
                    step2_quote = step1_base / p2_ask
                    step3_usdt = step2_quote * p3_bid

                    gross_usdt = step3_usdt
                    net_usdt = gross_usdt * total_fee_multiplier
                    net_pnl_usd = net_usdt - start_usdt
                    net_spread_pct = ((net_usdt - start_usdt) / start_usdt) * 100.0

                    opportunities.append({
                        "triangle": f"USDT ➔ {base_coin} ➔ {quote_coin} ➔ USDT",
                        "start_usdt": start_usdt,
                        "net_usdt": round(net_usdt, 4),
                        "net_pnl_usd": round(net_pnl_usd, 4),
                        "net_spread_pct": round(net_spread_pct, 4),
                        "viable": net_spread_pct > 0.02
                    })

        best_opp = max(opportunities, key=lambda x: x["net_spread_pct"]) if opportunities else {}

        return {
            "status": "success",
            "exchange": exchange.upper(),
            "triangles_scanned": len(opportunities),
            "best_opportunity": best_opp,
            "all_opportunities": opportunities
        }


if __name__ == "__main__":
    engine = AIOSTriangularArbitrageEngine()
    print("Triangular Scan:", json.dumps(engine.scan_triangular_opportunities("binance"), indent=2))
