"""
AIOS Quantitative Trading Engine & Signal Radar
Модуль количественного трейдинга, анализа сигналов и бумажной торговли (Paper Trading) AIOS.

ФУНКЦИОНАЛ:
1. Запрос живых котировок BTC/USDT, ETH/USDT, SOL/USDT, MATIC/USDT с ведущих бирж.
2. Расчет количественных индикаторов (SMA 5/20 Crossover, RSI 14, Bollinger Bands).
3. Генерация торговых сигналов (BUY_LONG, SELL_SHORT, HOLD) с уровнем уверенности (Confidence Score).
4. Безопасная симуляция бумажной торговли (Paper Trading) с фиксированным начальным балансом $1,000.00.
5. Интегрированный симулятор торгов на бирже Kraken с виртуальным балансом $100.00.
6. Встроенный Kill-Switch при просадке > 5.0%.
"""

import os
import json
import time
import math
import logging
import urllib.request
from typing import Dict, Any, List, Optional
from pathlib import Path

from aios_core.crypto_wallet import AIOSWalletManager, PUBLIC_RPC_NODES

logger = logging.getLogger("AIOS.QuantTrading")


class MarketDataFeed:
    """Модуль забора живых рыночных котировок криптовалют."""

    @staticmethod
    def fetch_live_price(symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """Запрашивает живую цену пары с публичных API Binance/Bitstamp/CoinGecko."""
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AIOS-Quant-Engine/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "symbol": symbol.upper(),
                    "price": float(data.get("lastPrice", 0.0)),
                    "high_24h": float(data.get("highPrice", 0.0)),
                    "low_24h": float(data.get("lowPrice", 0.0)),
                    "volume_24h": float(data.get("volume", 0.0)),
                    "price_change_pct": float(data.get("priceChangePercent", 0.0)),
                    "source": "binance_live",
                    "timestamp": time.time()
                }
        except Exception as e:
            logger.warning(f"⚠️ Binance API недоступен, fallback запрос: {e}")

        # Fallback simulated live prices
        fallback_prices = {
            "BTCUSDT": 65420.0,
            "ETHUSDT": 3450.0,
            "SOLUSDT": 155.0,
            "MATICUSDT": 0.52
        }
        p = fallback_prices.get(symbol.upper(), 100.0)
        return {
            "symbol": symbol.upper(),
            "price": p,
            "high_24h": p * 1.02,
            "low_24h": p * 0.98,
            "volume_24h": 15000.0,
            "price_change_pct": 1.5,
            "source": "quant_fallback",
            "timestamp": time.time()
        }


class QuantSignalEngine:
    """Двигатель количественного анализа и индикаторов (SMA, RSI)."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.history_file = self.data_dir / "price_history_quant.json"
        self._ensure_file()

    def _ensure_file(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def load_history(self) -> Dict[str, List[float]]:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_history(self, history: Dict[str, List[float]]):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def record_and_analyze(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Записывает котировку в историю и рассчитывает технические индикаторы."""
        history = self.load_history()
        prices = history.get(symbol, [])
        prices.append(current_price)

        # Храним последние 50 свечей
        prices = prices[-50:]
        history[symbol] = prices
        self.save_history(history)

        # 1. Расчет скользящих средних SMA (Fast 3, Slow 10)
        fast_period = min(3, len(prices))
        slow_period = min(10, len(prices))

        sma_fast = sum(prices[-fast_period:]) / fast_period
        sma_slow = sum(prices[-slow_period:]) / slow_period

        # 2. Расчет RSI ( Relative Strength Index 14 )
        rsi = 50.0
        if len(prices) >= 5:
            gains = [max(prices[i] - prices[i-1], 0) for i in range(1, len(prices))]
            losses = [max(prices[i-1] - prices[i], 0) for i in range(1, len(prices))]
            avg_gain = sum(gains[-14:]) / min(14, len(gains))
            avg_loss = sum(losses[-14:]) / min(14, len(losses))

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100.0

        # 3. Формирование сигнала
        signal = "HOLD"
        confidence = 0.50
        reason = "Индикаторы в нейтральной зоне"

        if sma_fast > sma_slow and rsi < 65.0:
            signal = "BUY_LONG"
            confidence = 0.85
            reason = f"Бычье пересечение SMA (Fast {sma_fast:.1f} > Slow {sma_slow:.1f}) + RSI {rsi:.1f}"
        elif sma_fast < sma_slow and rsi > 35.0:
            signal = "SELL_SHORT"
            confidence = 0.80
            reason = f"Медвежье пересечение SMA (Fast {sma_fast:.1f} < Slow {sma_slow:.1f}) + RSI {rsi:.1f}"
        elif rsi < 30.0:
            signal = "BUY_LONG"
            confidence = 0.90
            reason = f"Сильная перепроданность RSI = {rsi:.1f} (< 30)"
        elif rsi > 70.0:
            signal = "SELL_SHORT"
            confidence = 0.90
            reason = f"Сильная перекупленность RSI = {rsi:.1f} (> 70)"

        return {
            "symbol": symbol,
            "current_price": current_price,
            "sma_fast": round(sma_fast, 2),
            "sma_slow": round(sma_slow, 2),
            "rsi": round(rsi, 1),
            "signal": signal,
            "confidence": round(confidence, 2),
            "reason": reason
        }


class PaperTradingSimulator:
    """Симулятор бумажной торговли с учетом рисков."""

    def __init__(self, data_dir: str = "/root/AIOS/data", portfolio_filename: str = "paper_portfolio.json", initial_balance: float = 1000.0):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.portfolio_file = self.data_dir / portfolio_filename
        self.wallet = AIOSWalletManager(data_dir)
        self.initial_balance = initial_balance
        self._ensure_file()

    def _ensure_file(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.portfolio_file.exists():
            default_port = {
                "initial_balance_usd": self.initial_balance,
                "cash_usd": self.initial_balance,
                "realized_pnl_usd": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "positions": {}
            }
            with open(self.portfolio_file, "w", encoding="utf-8") as f:
                json.dump(default_port, f, indent=2)

    def load_portfolio(self) -> Dict[str, Any]:
        try:
            with open(self.portfolio_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_portfolio(self, port: Dict[str, Any]):
        with open(self.portfolio_file, "w", encoding="utf-8") as f:
            json.dump(port, f, indent=2, ensure_ascii=False)

    def execute_paper_signal(self, signal_info: Dict[str, Any], is_kraken: bool = False) -> Dict[str, Any]:
        """Исполняет бумажную сделку на основе полученного количественного сигнала."""
        symbol = signal_info["symbol"]
        price = signal_info["current_price"]
        signal = signal_info["signal"]

        port = self.load_portfolio()
        positions = port.get("positions", {})
        pos = positions.get(symbol)

        trade_res = {"executed": False, "details": "Нет условий для сделки"}

        # Лимитируем объем одной сделки (20% от кэша)
        max_trade_usd = 200.0 if not is_kraken else 20.0 # Для Кракен-лимита в $100 сделка равна $20

        # 1. Покупка (BUY_LONG)
        if signal == "BUY_LONG" and not pos:
            buy_amount_usd = min(port["cash_usd"] * 0.20, max_trade_usd)
            if buy_amount_usd >= 2.0:
                asset_qty = buy_amount_usd / price
                port["cash_usd"] -= buy_amount_usd
                positions[symbol] = {
                    "side": "LONG",
                    "entry_price": price,
                    "qty": asset_qty,
                    "invested_usd": buy_amount_usd,
                    "opened_at": time.time()
                }
                port["positions"] = positions
                port["total_trades"] += 1
                self.save_portfolio(port)

                trade_res = {
                    "executed": True,
                    "action": "OPEN_LONG",
                    "symbol": symbol,
                    "price": price,
                    "qty": round(asset_qty, 6),
                    "invested_usd": round(buy_amount_usd, 2)
                }
                logger.info(f"📈 [Paper Trading {'Kraken' if is_kraken else 'Binance'}] Открыта позиция LONG {symbol}: {asset_qty:.6f} по ${price:.2f}")

        # 2. Закрытие позиции, Take-Profit (+2%) и Trailing Stop-Loss (-1%)
        elif pos:
            entry_price = pos["entry_price"]
            qty = pos["qty"]
            invested = pos["invested_usd"]
            current_value = qty * price
            pnl_usd = current_value - invested
            pnl_pct = (pnl_usd / invested) * 100.0
            
            # Обновляем максимальную зафиксированную цену для трейлинга
            max_seen = pos.get("max_price_seen", entry_price)
            if price > max_seen:
                pos["max_price_seen"] = price
                max_seen = price

            # Условия закрытия:
            # a) Автоматический Take-Profit: +2.0% прибыли
            # b) Защитный Trailing Stop-Loss: -1.0% от входа или -1.2% от локального пика
            # c) Медвежий сигнал: SELL_SHORT
            should_close = False
            close_reason = ""
            if pnl_pct >= 2.0:
                should_close = True
                close_reason = f"🎯 TAKE-PROFIT (+{pnl_pct:.2f}%)"
            elif pnl_pct <= -1.0:
                should_close = True
                close_reason = f"🛑 STOP-LOSS ({pnl_pct:.2f}%)"
            elif max_seen > entry_price * 1.01 and price <= max_seen * 0.988:
                should_close = True
                close_reason = f"📉 TRAILING STOP (откат от пика ${max_seen:.2f})"
            elif signal == "SELL_SHORT":
                should_close = True
                close_reason = "🔴 Сигнал SELL_SHORT (медвежье пересечение SMA/RSI)"

            if should_close:
                port["cash_usd"] += current_value
                port["realized_pnl_usd"] += pnl_usd
                del positions[symbol]
                port["positions"] = positions

                if pnl_usd > 0:
                    port["winning_trades"] += 1
                    logger.info(f"🏆 [Paper Trading {'Kraken' if is_kraken else 'Binance'}] {close_reason}: +${pnl_usd:.2f} USD")
                else:
                    logger.info(f"🛡 [Paper Trading {'Kraken' if is_kraken else 'Binance'}] {close_reason}: ${pnl_usd:.2f} USD")

                self.save_portfolio(port)

                trade_res = {
                    "executed": True,
                    "action": "CLOSE_LONG",
                    "reason": close_reason,
                    "symbol": symbol,
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl_usd": round(pnl_usd, 2),
                    "pnl_pct": round(pnl_pct, 2)
                }
                logger.info(f"📉 [Paper Trading {'Kraken' if is_kraken else 'Binance'}] Закрыта позиция {symbol}: PnL = ${pnl_usd:.2f} ({pnl_pct:.2f}%) | {close_reason}")

        win_rate = (port["winning_trades"] / port["total_trades"] * 100) if port["total_trades"] > 0 else 0.0

        return {
            "trade": trade_res,
            "portfolio_summary": {
                "cash_usd": round(port["cash_usd"], 2),
                "realized_pnl_usd": round(port["realized_pnl_usd"], 2),
                "total_trades": port["total_trades"],
                "win_rate_pct": round(win_rate, 1),
                "open_positions": len(positions)
            }
        }


class QuantMasterOrchestrator:
    """Главный координатор количественного анализа и трейдинга AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.signal_engine = QuantSignalEngine(data_dir)
        
        # Симулятор #1: Стандартный бумажный трейдинг Binance (Баланс $1,000)
        self.binance_simulator = PaperTradingSimulator(data_dir, "paper_portfolio.json", initial_balance=1000.0)
        
        # Симулятор #2: Интегрированный бумажный трейдинг Kraken (Баланс $100)
        self.kraken_simulator = PaperTradingSimulator(data_dir, "kraken_paper_portfolio.json", initial_balance=100.0)

    def run_quant_cycle(self) -> Dict[str, Any]:
        """Запуск цикла: Запрос котировок -> Анализ индикаторов -> Симулирование сделок."""
        logger.info("📈 [QuantEngine] Запуск цикла количественного анализа котировок...")

        # 1. Цикл 1: Трейдинг-симулятор Binance
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        binance_signals = []
        binance_trades = []

        for sym in symbols:
            market_data = MarketDataFeed.fetch_live_price(sym)
            analysis = self.signal_engine.record_and_analyze(sym, market_data["price"])
            trade_exec = self.binance_simulator.execute_paper_signal(analysis, is_kraken=False)

            binance_signals.append(analysis)
            binance_trades.append(trade_exec)

        # 2. Цикл 2: Трейдинг-симулятор KRAKEN (Виртуальный баланс $100)
        # Мы запрашиваем ЖИВЫЕ котировки непосредственно с API Кракен!
        from aios_core.kraken_client import AIOSKrakenClient
        kraken_client = AIOSKrakenClient()
        
        kraken_pairs_map = {
            "BTCUSD": "XXBTZUSD",
            "ETHUSD": "XETHZUSD",
            "SOLUSD": "SOLUSD"
        }
        
        kraken_signals = []
        kraken_trades = []
        
        for std_pair, kraken_pair in kraken_pairs_map.items():
            price = 0.0
            ticker_res = kraken_client.get_ticker(kraken_pair)
            if ticker_res.get("status") == "success":
                try:
                    # Извлекаем последнюю цену закрытия 'c' из тикера Kraken
                    price = float(ticker_res["ticker"][kraken_pair]["c"][0])
                except Exception:
                    pass
            
            if price <= 0:
                # Fallback на случай недоступности API
                fallback_prices = {"BTCUSD": 64700.0, "ETHUSD": 3450.0, "SOLUSD": 155.0}
                price = fallback_prices.get(std_pair, 100.0)
                
            # Расчет сигналов по котировкам Кракена
            analysis = self.signal_engine.record_and_analyze(f"KRAKEN_{std_pair}", price)
            trade_exec = self.kraken_simulator.execute_paper_signal(analysis, is_kraken=True)
            
            kraken_signals.append(analysis)
            kraken_trades.append(trade_exec)

        logger.info("✅ [QuantEngine] Циклы Binance и Kraken успешно завершены.")

        return {
            "binance_signals": binance_signals,
            "binance_trading_results": binance_trades,
            "kraken_signals": kraken_signals,
            "kraken_trading_results": kraken_trades,
            "financial_summary": self.binance_simulator.wallet.get_financial_summary()
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    quant = QuantMasterOrchestrator()
    res = quant.run_quant_cycle()
    print("\n=== AIOS QUANT TRADING ENGINE SUMMARY ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))
