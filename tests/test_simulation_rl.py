"""Tests for simulation, digital twin, and RL modules."""

from aios_core.simulation_engine import SimulationEngine
from aios_core.digital_twin import DigitalTwin
from aios_core.reinforcement_learning import RLAgent


def test_simulation_engine_stats():
    se = SimulationEngine()
    s = se.stats()
    assert isinstance(s, dict)


def test_digital_twin_stats():
    dt = DigitalTwin("test-twin")
    s = dt.stats()
    assert isinstance(s, dict)


def test_rl_agent_stats():
    rl = RLAgent()
    s = rl.stats()
    assert isinstance(s, dict)
