import pytest
from aios_core.neuromorphic_matrix import NeuromorphicMatrixEngine, LIFNeuron

def test_lif_neuron_integration():
    neuron = LIFNeuron("n1", v_threshold=1.0, v_rest=0.0, tau=10.0)
    
    # Add small current, shouldn't spike
    spiked = neuron.integrate_current(0.5, dt_ms=1.0)
    assert spiked is False
    assert neuron.v_membrane > 0.0
    
    # Add large current, should spike
    spiked = neuron.integrate_current(1.5, dt_ms=1.0)
    assert spiked is True
    assert neuron.spike_count == 1
    assert neuron.v_membrane == 0.0 # reset

def test_neuromorphic_matrix_stdp_learning():
    engine = NeuromorphicMatrixEngine(size=3)
    
    # Force neuron 0 to spike at t=0
    engine.step_simulation({0: 2.0, 1: 0.0, 2: 0.0})
    
    # Immediately after, force neuron 1 to spike at t=1 (simulating pre->post sequence)
    # The STDP window should catch this and strengthen connection 0->1
    initial_weight = engine.synaptic_weights[(0, 1)]
    engine.step_simulation({0: 0.0, 1: 2.0, 2: 0.0})
    
    # Connection from 0 to 1 should be strengthened (potentiation)
    assert engine.synaptic_weights[(0, 1)] > initial_weight
    
    # Connection from 1 to 0 should be weakened (depression) because post fired before pre 
    # (actually pre=1 fired, post=0 fired earlier, meaning 1 is post in STDP check)
    assert engine.synaptic_weights[(1, 0)] < engine.synaptic_weights[(0, 1)]
    
    stats = engine.stats()
    assert stats["total_spikes_fired"] == 2
