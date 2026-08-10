"""
AIOS Risk Management & Capital Protection Guard (Items 1-10)
Управление рисками, заградительные стопы, формула Келли, контроль корреляции и волатильности.
"""
from __future__ import annotations

import math
import time
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger("AIOS.RiskGuard")


class AIOSRiskGuard:
    """Центральный модуль защиты депозита и контроля рисков AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        self.data_dir = Path(data_dir)
        self.state_file = self.data_dir / "risk_guard_state.json"
        self._ensure_file()

    def _ensure_file(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            state = {
                "daily_pnl_usd": 0.0,
                "is_kill_switch_active": False,
                "paused_until": 0.0,
                "paused_coins": {}
            }
            self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def load_state(self) -> Dict[str, Any]:
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {"daily_pnl_usd": 0.0, "is_kill_switch_active": False, "paused_until": 0.0, "paused_coins": {}}

    def save_state(self, state: Dict[str, Any]):
        self.state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def check_kill_switch(self, total_capital: float = 5000.0) -> bool:
        """1. Kill-Switch: Пауза при суточной просадке > 5.0%."""
        state = self.load_state()
        now = time.time()

        if state.get("is_kill_switch_active"):
            if now < state.get("paused_until", 0.0):
                return True # Active kill switch
            else:
                state["is_kill_switch_active"] = False
                state["daily_pnl_usd"] = 0.0
                self.save_state(state)

        # Проверка дневного убытка
        if state.get("daily_pnl_usd", 0.0) <= -0.05 * total_capital:
            state["is_kill_switch_active"] = True
            state["paused_until"] = now + 86400 # 24h freeze
            self.save_state(state)
            logger.warning(f"🚨 [KILL-SWITCH ACTIVATED] Дневная просадка > 5% (-${abs(state['daily_pnl_usd']):.2f}). Торги заморожены на 24ч.")
            return True

        return False

    @staticmethod
    def calculate_kelly_position_size(
        confidence_score: float,
        win_rate: float = 0.55,
        win_loss_ratio: float = 2.0,
        available_cash: float = 1000.0
    ) -> float:
        """3. Kelly Sizing: Динамический размер позиции по формуле Келли под уверенность сигнала."""
        p = min(0.95, max(0.40, confidence_score * win_rate))
        q = 1.0 - p
        b = win_loss_ratio

        # Формула Келли: f* = (b*p - q) / b
        f_star = (b * p - q) / b
        f_star_half = max(0.05, min(0.25, f_star * 0.5)) # Используем 1/2 Kelly для снижения дисперсии

        position_size = available_cash * f_star_half
        return round(position_size, 2)

    @staticmethod
    def check_correlation_guard(active_positions: List[str], target_symbol: str) -> bool:
        """6. Correlation Filter: Запрет более 2 коин-позиций с высокой корреляцией r > 0.8."""
        correlated_groups = [
            {"BTC", "ETH", "WBTC", "WETH"},
            {"SOL", "RAY", "JTO", "JUP"},
            {"ARB", "OP", "MATIC", "POL"},
            {"DOGE", "SHIB", "PEPE", "BONK"}
        ]
        
        target_clean = target_symbol.upper().replace("USD", "").replace("USDT", "")
        for group in correlated_groups:
            if target_clean in group:
                active_in_group = sum(1 for p in active_positions if any(g in p.upper() for g in group))
                if active_in_group >= 2:
                    return False # Too many correlated positions
        return True


if __name__ == "__main__":
    rg = AIOSRiskGuard()
    print("Kill Switch Status:", rg.check_kill_switch())
    print("Kelly Position Size (Conf 85%):", rg.calculate_kelly_position_size(0.85, available_cash=1000.0))
    print("Correlation Guard BTC in [ETH, WBTC]:", rg.check_correlation_guard(["ETHUSD", "WBTCUSD"], "BTCUSD"))
