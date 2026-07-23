"""Tests for neural network architectures — transformers, SSMs, GNNs."""

from aios_core.transformer import TransformerModel
from aios_core.state_space import StateSpaceModel
from aios_core.spiking_nn import SpikingNeuralNetwork


def test_transformer_stats():
    tm = TransformerModel()
    s = tm.stats()
    assert isinstance(s, dict)


def test_state_space_model_stats():
    ssm = StateSpaceModel()
    s = ssm.stats()
    assert isinstance(s, dict)


def test_spiking_nn_stats():
    snn = SpikingNeuralNetwork()
    s = snn.stats()
    assert isinstance(s, dict)
