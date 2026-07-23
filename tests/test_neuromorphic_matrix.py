"""Tests for Neuromorphic Spiking Neural Network (SNN) Matrix Engine (Horizon 6.0)."""

import pytest

from aios_core.neuromorphic_matrix import LIFNeuron, NeuromorphicMatrixEngine


def test_lif_neuron_spike():
    neuron = LIFNeuron("n1", v_threshold=1.0, tau=10.0)

    # Below threshold -> no spike
    spiked_1 = neuron.integrate_current(0.5)
    assert spiked_1 is False

    # Above threshold -> spike fired and reset
    spiked_2 = neuron.integrate_current(0.8)
    assert spiked_2 is True
    assert neuron.spike_count == 1
    assert neuron.v_membrane == neuron.v_rest


def test_neuromorphic_matrix_simulation_and_stdp():
    engine = NeuromorphicMatrixEngine(size=4)

    # Provide high input current to neuron 0
    spikes_t1 = engine.step_simulation({0: 2.0}, dt_ms=1.0)
    assert 0 in spikes_t1

    # In next step, STDP plasticity adjusts weights
    spikes_t2 = engine.step_simulation({1: 2.0}, dt_ms=1.0)
    assert 1 in spikes_t2

    stats = engine.stats()
    assert stats["matrix_size"] == 4
    assert stats["total_spikes_fired"] >= 2
