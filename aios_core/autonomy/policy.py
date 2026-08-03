"""Autonomy Policy — загрузка и валидация политики автономии.

Единственный источник настроек ограничителя (guardrails). Политика хранится в
``data/autonomy_policy.json``, ценовые полы в ``data/price_floors.json``.
Никакая логика принятия решений здесь не выполняется — только чтение.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


class AutonomyPolicy:
    """Политика автономии (неизменяемая загрузка из JSON)."""

    def __init__(self, root: Path | None = None):
        self.root = root or PROJECT_ROOT
        self.policy_path = self.root / "data" / "autonomy_policy.json"
        self.floors_path = self.root / "data" / "price_floors.json"
        self.data: dict = _read_json(self.policy_path, {})
        self.floors: dict = _read_json(self.floors_path, {})

    @property
    def enabled(self) -> bool:
        return bool(self.data.get("enabled", True))

    @property
    def global_cfg(self) -> dict:
        return self.data.get("global", {})

    @property
    def floor_global(self) -> float:
        return float(self.global_cfg.get("floor_global", 0) or 0)

    @property
    def max_auto_discount_pct(self) -> float:
        return float(self.global_cfg.get("max_auto_discount_pct", 15))

    @property
    def negotiation_rounds_max(self) -> int:
        return int(self.global_cfg.get("negotiation_rounds_max", 3))

    @property
    def reply_timeout_sec(self) -> int:
        return int(self.global_cfg.get("reply_timeout_sec", 1800))

    @property
    def rate_limit_per_hour(self) -> int:
        return int(self.global_cfg.get("rate_limit_per_hour", 120))

    @property
    def allowed_schemes(self) -> list[str]:
        return list(self.data.get("payment", {}).get("allowed_schemes", []))

    @property
    def always_manual_schemes(self) -> list[str]:
        return list(self.data.get("payment", {}).get("always_manual_schemes", []))

    @property
    def esc_all(self) -> dict:
        return self.data.get("esc_all", {})

    @property
    def esc_on_rule(self) -> dict:
        return self.data.get("esc_on_rule", {})

    @property
    def read_only_always_auto(self) -> list[str]:
        return list(self.data.get("read_only_always_auto", []))

    def is_always_manual(self, action: str) -> bool:
        return bool(self.esc_all.get(action, False))

    def is_esc_rule_on(self, rule: str) -> bool:
        return bool(self.esc_on_rule.get(rule, False))

    def is_read_only(self, action: str) -> bool:
        return action in self.read_only_always_auto

    # ---- Ценовые полы ----
    def floor_for(self, sku: str) -> float:
        """Пол для конкретной детали (по названию/артикулу).

        Если конкретного пола нет — пробуем вывести из цены в складе
        (90% от прайса) как безопасный fallback. Если и склада нет —
        глобальный пол.
        """
        sku_l = (sku or "").strip().lower()
        items = self.floors.get("items", {})
        if sku_l:
            for key, val in items.items():
                if sku_l == key or key in sku_l or sku_l in key:
                    return float(val)
        # fallback из склада
        inv_floor = self._floor_from_inventory(sku_l)
        if inv_floor:
            return inv_floor
        return self.floor_global

    def _floor_from_inventory(self, sku_l: str) -> float:
        try:
            import json
            inv = json.loads((self.root / "data" / "inventory.json").read_text(encoding="utf-8"))
        except Exception:
            return 0.0
        if not sku_l:
            return 0.0
        for it in inv:
            name = str(it.get("name") or "").lower()
            price = float(it.get("price") or 0)
            if price <= 0:
                continue
            if sku_l in name or name in sku_l:
                return round(price * 0.9)
        return 0.0

    def refresh(self) -> None:
        self.data = _read_json(self.policy_path, self.data)
        self.floors = _read_json(self.floors_path, self.floors)
