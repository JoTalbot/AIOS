"""Regression: hard stoploss fraction must be a sane protective level (<50%)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _stoploss_value(path: Path) -> float:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "stoploss":
                    val = ast.literal_eval(node.value)
                    return float(val)
    raise AssertionError(f"stoploss не найден в {path}")


def test_t2_stoploss_is_sane_protective_level():
    v = _stoploss_value(Path("scripts/freqtrade_t2.py"))
    assert -0.5 < v < 0, v
    assert abs(v) >= 0.01, "стоп слишком близко к цене (шумовые выбивания)"


def test_no_99pct_stop_anywhere_in_strategy_files():
    for name in ("scripts/freqtrade_t2.py", "scripts/freqtrade_t2_hyper.py"):
        src = Path(name).read_text(encoding="utf-8")
        assert "stoploss = -0.99" not in src, f"{name}: ловушка −99% осталась"
