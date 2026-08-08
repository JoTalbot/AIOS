"""Smoke-тесты для run_swarm_backtester.py (раннер бэктеста квант-стратегий).

Импорт модуля инициализирует ChromaDB (PersistentClient) — блокирует на медленном диске,
поэтому в тестах chromadb подменяется фейком ДО импорта, а LLMSwarm (OpenRouter-сеть)
мокается, чтобы тест не зависел от сети.
"""
from __future__ import annotations

import sys
import types
import tempfile


def _install_fake_chromadb() -> None:
    """Подменяем chromadb в sys.modules, чтобы импорт не трогал реальную БД."""

    class _Collection:
        def query(self, *a, **k):
            return {"documents": [[]]}

        def add(self, *a, **k):
            return None

    class _Client:
        def get_or_create_collection(self, name):
            return _Collection()

    fake = types.ModuleType("chromadb")
    fake.PersistentClient = lambda *a, **k: _Client()
    sys.modules["chromadb"] = fake


def test_runner_imports_and_has_main():
    """Раннер импортируется и экспортирует main() без сети."""
    _install_fake_chromadb()
    import run_swarm_backtester as runner

    assert callable(runner.main)


def test_backtester_simulation_returns_dict(monkeypatch):
    """Симуляция с мокнутым LLMSwarm возвращает структуру без обращения к сети."""
    _install_fake_chromadb()
    import aios_core.swarm_quant_backtester as m

    class FakeSwarm:
        def __init__(self):
            self.agents = {}

        def start_debate(self, topic: str) -> str:
            return "consensus ok"

    monkeypatch.setattr(m, "LLMSwarm", FakeSwarm)

    with tempfile.TemporaryDirectory() as d:
        bt = m.SwarmQuantBacktester(data_dir=d)
        res = bt.run_backtest_simulation()
        assert res["status"] == "success"
        assert "simulation_metrics" in res
        assert "swarm_consensus" in res
        assert res["swarm_consensus"] == "consensus ok"
