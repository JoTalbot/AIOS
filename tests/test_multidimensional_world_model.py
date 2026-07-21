"""Tests for Multi-Dimensional Universal World Model (Horizon 7.0)."""

import pytest
from aios_core.multidimensional_world_model import MultiDimensionalWorldModel


def test_world_model_counterfactual_simulation():
    model = MultiDimensionalWorldModel(simulation_horizon_steps=5)

    moderate_plan = {"complexity": 2.0, "scale": 2}
    sim_res = model.simulate_action_impact(moderate_plan)

    assert "is_safe_trajectory" in sim_res
    assert len(sim_res["simulated_trajectory"]) == 5
    assert sim_res["simulation_steps"] == 5
    assert model.stats()["rollouts_count"] == 1
