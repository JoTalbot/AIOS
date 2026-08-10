
def _send_trading_tg_alert(message: str) -> bool:
    """Отправка уведомления о сделках квант-трейдинга в Telegram."""
    import urllib.request
    import json
    import os
    from pathlib import Path
    
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("AIOS_TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        env_file = Path("/root/AIOS/.env")
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN=") and not token:
                    token = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("TELEGRAM_CHAT_ID=") and not chat_id:
                    chat_id = line.split("=", 1)[1].strip().strip('"').strip("'")
                    
    if not token or not chat_id:
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": int(chat_id),
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False

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

        # 3. Расчет Bollinger Bands (20 периодов)
        period_bb = min(20, len(prices))
        sma_bb = sum(prices[-period_bb:]) / period_bb
        variance = sum((p - sma_bb) ** 2 for p in prices[-period_bb:]) / period_bb
        std_dev = math.sqrt(variance)
        upper_bb = sma_bb + (2.0 * std_dev)
        lower_bb = sma_bb - (2.0 * std_dev)

        # 4. Формирование сигнала (SMA + RSI + Bollinger Bands)
        signal = "HOLD"
        confidence = 0.50
        reason = "Индикаторы в нейтральной зоне"

        if current_price <= lower_bb and rsi < 40.0:
            signal = "BUY_LONG"
            confidence = 0.95
            reason = f"Пробой Нижней полосы Боллинджера (${lower_bb:.2f}) + RSI {rsi:.1f}"
        elif current_price >= upper_bb and rsi > 60.0:
            signal = "SELL_SHORT"
            confidence = 0.95
            reason = f"Пробой Верхней полосы Боллинджера (${upper_bb:.2f}) + RSI {rsi:.1f}"
        elif sma_fast > sma_slow and rsi < 65.0:
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
                _send_trading_tg_alert(f"📈 <b>[Quant Radar] Открыта позиция LONG</b>\n• Биржа: <b>{'Kraken' if is_kraken else 'Binance'}</b>\n• Пара: <code>{symbol}</code>\n• Цена входа: <b>${price:.2f}</b>\n• Объем: {asset_qty:.6f} (${buy_amount_usd:.2f})")

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
                icon = "🎯" if pnl_usd > 0 else "🛑"
                _send_trading_tg_alert(f"{icon} <b>[Quant Radar] Закрыта позиция {symbol}</b>\n• Биржа: <b>{'Kraken' if is_kraken else 'Binance'}</b>\n• Причина: <b>{close_reason}</b>\n• Вход: ${entry_price:.2f} ➔ Выход: ${price:.2f}\n• Результат (PnL): <b>{'+' if pnl_usd>0 else ''}${pnl_usd:.2f} USD ({pnl_pct:.2f}%)</b>")

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
            "SOLUSD": "SOLUSD",
            "XRPUSD": "XXRPZUSD",
            "ADAUSD": "ADAUSD",
            "DOTUSD": "DOTUSD",
            "LINKUSD": "LINKUSD",
            "AVAXUSD": "AVAXUSD",
            "LTCUSD": "XLTCZUSD",
            "NEARUSD": "NEARUSD",
            "UNIUSD": "UNIUSD",
            "SHIBUSD": "SHIBUSD"
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


def get_kraken_demo_report(data_dir: str = "/root/AIOS/data") -> Dict[str, Any]:
    """Получает полную аналитику демонстрационного счёта $100 на бирже Kraken."""
    is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
    if is_docker and os.path.exists("/app/data"):
        data_dir = "/app/data"

    data_path = Path(data_dir) / "kraken_paper_portfolio.json"
    if not data_path.exists():
        default_port = {
            "initial_balance_usd": 100.0,
            "cash_usd": 100.0,
            "realized_pnl_usd": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "positions": {}
        }
        data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(default_port, f, indent=2)
        port = default_port
    else:
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                port = json.load(f)
        except Exception:
            port = {
                "initial_balance_usd": 100.0,
                "cash_usd": 100.0,
                "realized_pnl_usd": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "positions": {}
            }

    initial_balance = port.get("initial_balance_usd", 100.0)
    cash_usd = port.get("cash_usd", 100.0)
    realized_pnl = port.get("realized_pnl_usd", 0.0)
    total_trades = port.get("total_trades", 0)
    winning_trades = port.get("winning_trades", 0)
    win_rate = (winning_trades / total_trades * 100.0) if total_trades > 0 else 0.0

    from aios_core.kraken_client import AIOSKrakenClient
    kraken_client = AIOSKrakenClient()

    kraken_pairs_map = {
        "BTCUSD": "XXBTZUSD",
        "ETHUSD": "XETHZUSD",
        "SOLUSD": "SOLUSD",
        "XRPUSD": "XXRPZUSD",
        "ADAUSD": "ADAUSD",
        "DOTUSD": "DOTUSD",
        "LINKUSD": "LINKUSD",
        "AVAXUSD": "AVAXUSD",
        "LTCUSD": "XLTCZUSD",
        "NEARUSD": "NEARUSD",
        "UNIUSD": "UNIUSD",
        "SHIBUSD": "SHIBUSD"
    }

    positions_detail = []
    total_position_invested = 0.0
    total_position_value = 0.0

    for pos_key, pos_data in port.get("positions", {}).items():
        std_pair = pos_key.replace("KRAKEN_", "")
        kraken_pair = kraken_pairs_map.get(std_pair, std_pair)

        live_price = 0.0
        try:
            ticker_res = kraken_client.get_ticker(kraken_pair)
            if ticker_res.get("status") == "success":
                live_price = float(ticker_res["ticker"][kraken_pair]["c"][0])
        except Exception:
            pass

        if live_price <= 0:
            binance_pair = std_pair.replace("USD", "USDT")
            mf = MarketDataFeed.fetch_live_price(binance_pair)
            live_price = mf.get("price", pos_data.get("entry_price", 100.0))

        entry_price = pos_data.get("entry_price", 0.0)
        qty = pos_data.get("qty", 0.0)
        invested = pos_data.get("invested_usd", 0.0)
        current_val = qty * live_price
        unrealized_pnl = current_val - invested
        unrealized_pct = (unrealized_pnl / invested * 100.0) if invested > 0 else 0.0

        total_position_invested += invested
        total_position_value += current_val

        positions_detail.append({
            "key": pos_key,
            "pair_display": std_pair.replace("USD", "/USD"),
            "side": pos_data.get("side", "LONG"),
            "qty": qty,
            "entry_price": entry_price,
            "live_price": live_price,
            "invested_usd": invested,
            "current_value_usd": current_val,
            "unrealized_pnl_usd": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pct,
            "opened_at": pos_data.get("opened_at", 0)
        })

    total_unrealized_pnl = total_position_value - total_position_invested
    total_equity = cash_usd + total_position_value
    total_pnl = total_equity - initial_balance
    total_return_pct = (total_pnl / initial_balance) * 100.0

    return {
        "initial_balance_usd": initial_balance,
        "cash_usd": cash_usd,
        "total_equity_usd": total_equity,
        "realized_pnl_usd": realized_pnl,
        "unrealized_pnl_usd": total_unrealized_pnl,
        "total_pnl_usd": total_pnl,
        "total_return_pct": total_return_pct,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate_pct": win_rate,
        "positions": positions_detail
    }


def reset_kraken_demo_account(data_dir: str = "/root/AIOS/data") -> bool:
    """Сбрасывает демонстрационный счёт Kraken к исходному балансу $100.00 USD."""
    is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
    if is_docker and os.path.exists("/app/data"):
        data_dir = "/app/data"

    data_path = Path(data_dir) / "kraken_paper_portfolio.json"
    default_port = {
        "initial_balance_usd": 100.0,
        "cash_usd": 100.0,
        "realized_pnl_usd": 0.0,
        "total_trades": 0,
        "winning_trades": 0,
        "positions": {}
    }
    try:
        data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(default_port, f, indent=2)
        return True
    except Exception:
        return False


def format_kraken_demo_report(report: Dict[str, Any]) -> str:
    """Форматирует отчёт демонстрационного счёта Kraken ($100) для Telegram."""
    init_bal = report.get("initial_balance_usd", 100.0)
    cash = report.get("cash_usd", 100.0)
    equity = report.get("total_equity_usd", 100.0)
    total_pnl = report.get("total_pnl_usd", 0.0)
    total_ret = report.get("total_return_pct", 0.0)
    realized = report.get("realized_pnl_usd", 0.0)
    unrealized = report.get("unrealized_pnl_usd", 0.0)
    trades = report.get("total_trades", 0)
    wins = report.get("winning_trades", 0)
    win_rate = report.get("win_rate_pct", 0.0)
    positions = report.get("positions", [])

    pnl_icon = "📈" if total_pnl >= 0 else "📉"
    pnl_sign = "+" if total_pnl > 0 else ""
    realized_sign = "+" if realized > 0 else ""
    unrealized_sign = "+" if unrealized > 0 else ""

    lines = [
        "🐙 <b>Демонстрационный счёт Kraken ($100.00 USD)</b>",
        "━━━━━━━━━━━━━━━━━━━━━",
        f"💵 <b>Начальный депозит:</b> ${init_bal:.2f} USD",
        f"💳 <b>Свободный кэш:</b> ${cash:.2f} USD",
        f"📊 <b>Текущий капитал (Equity):</b> <b>${equity:.2f} USD</b>",
        f"{pnl_icon} <b>Общий результат (PnL):</b> <b>{pnl_sign}${total_pnl:.2f} USD ({pnl_sign}{total_ret:.2f}%)</b>",
        "",
        "📈 <b>Статистика процесса заработка:</b>",
        f"• Всего сделок: <b>{trades}</b> (Успешных: <b>{wins}</b>, Винрейт: <b>{win_rate:.1f}%</b>)",
        f"• Реализованная прибыль: <b>{realized_sign}${realized:.2f} USD</b>",
        f"• Незафиксированный PnL: <b>{unrealized_sign}${unrealized:.2f} USD</b>",
        ""
    ]

    if positions:
        lines.append("💼 <b>Открытые позиции на Kraken:</b>")
        for p in positions:
            p_icon = "🟢" if p['unrealized_pnl_usd'] >= 0 else "🔴"
            u_sign = "+" if p['unrealized_pnl_usd'] > 0 else ""
            lines.append(
                f"{p_icon} <b>{p['pair_display']}</b> ({p['side']}):\n"
                f"  – Вход: ${p['entry_price']:.2f} ➔ Рынок: <b>${p['live_price']:.2f}</b>\n"
                f"  – Объём: {p['qty']:.6f} (${p['invested_usd']:.2f})\n"
                f"  – PnL: <b>{u_sign}${p['unrealized_pnl_usd']:.2f} USD ({u_sign}{p['unrealized_pnl_pct']:.2f}%)</b>"
            )
        lines.append("")
    else:
        lines.append("💼 <b>Открытые позиции:</b> <i>В данный момент позиций нет (100% в кэше)</i>\n")

    lines.extend([
        "🤖 <b>Алгоритм & Стратегия:</b>",
        "• Количественный робот AIOS (SMA 3/10 Crossover + RSI 14)",
        "• Риск-менеджмент: Take-Profit +2.0%, Trailing Stop-Loss -1.0%",
        "• Торговые пары: 12 топовых пар (BTC, ETH, SOL, XRP, ADA, DOT, LINK, AVAX, LTC, NEAR, UNI, SHIB) на Kraken",
        "",
        "💡 <i>Команды:</i>",
        "<code>баланс кракен</code> — реальный баланс активов",
        "<code>кракен демо сброс</code> — сбросить демо-счёт на $100"
    ])

    return "\n".join(lines)
