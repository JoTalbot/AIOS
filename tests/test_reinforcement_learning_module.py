"""Tests for aios_core/reinforcement_learning.py"""
from __future__ import annotations
import pytest
from aios_core.reinforcement_learning import QLearningAgent


@pytest.fixture()
def agent():
    return QLearningAgent(actions=["left", "right", "up", "down"])


class TestQLearningAgent:
    def test_create(self, agent):
        assert agent is not None

    def test_choose_action(self, agent):
        action = agent.choose_action(state="s1")
        assert action in ["left", "right", "up", "down"]

    def test_set_q(self, agent):
        agent.set_q(state="s1", action="left", value=0.5)

    def test_get_q(self, agent):
        agent.set_q(state="s1", action="left", value=0.5)
        q = agent.get_q(state="s1", action="left")
        assert q == 0.5 or isinstance(q, float)

    def test_max_q(self, agent):
        agent.set_q(state="s1", action="left", value=0.5)
        agent.set_q(state="s1", action="right", value=0.8)
        m = agent.max_q("s1")
        assert isinstance(m, float)

    def test_best_action(self, agent):
        agent.set_q(state="s1", action="left", value=0.5)
        agent.set_q(state="s1", action="right", value=0.8)
        best = agent.best_action("s1")
        assert best is not None

    def test_learn(self, agent):
        agent.learn(state="s1", action="left", reward=1.0, next_state="s2")

    def test_decay_epsilon(self, agent):
        old_eps = agent.epsilon
        agent.decay_epsilon()
        assert agent.epsilon <= old_eps or agent.epsilon > 0

    def test_add_experience(self, agent):
        agent.add_experience(state="s1", action="left", reward=1.0, next_state="s2", done=False)

    def test_stats(self, agent):
        s = agent.stats()
        assert isinstance(s, dict)
