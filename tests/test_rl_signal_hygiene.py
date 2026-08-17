"""Tests for the RL signal-product hygiene."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.generate_quant_signal_product as gqsp  # noqa: E402


def test_refresh_rl_signals_saves_when_available(tmp_path, monkeypatch):
    class Bridge:
        available = True

        def save(self, out_file=None):
            Path(out_file).write_text("{}", encoding="utf-8")

    monkeypatch.setattr(gqsp, "_refresh_rl_signals", lambda data_root: True)
    assert gqsp._refresh_rl_signals(tmp_path) is True


def test_refresh_rl_signals_guarded_on_failure(tmp_path, monkeypatch):
    import aios_core.quant.rl_signal_bridge as bridge_mod

    def broken_bridge():
        raise RuntimeError("network down")

    monkeypatch.setattr(bridge_mod, "RLSignalBridge", broken_bridge)
    assert gqsp._refresh_rl_signals(tmp_path) is False


def test_refresh_rl_signals_false_when_model_unavailable(tmp_path, monkeypatch):
    import aios_core.quant.rl_signal_bridge as bridge_mod

    class Unavailable:
        available = False

    monkeypatch.setattr(bridge_mod, "RLSignalBridge", Unavailable)
    assert gqsp._refresh_rl_signals(tmp_path) is False
