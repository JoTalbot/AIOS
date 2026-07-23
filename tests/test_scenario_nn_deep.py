"""NN architectures deep scenario."""
from aios_core.transformer import TransformerModel
from aios_core.state_space import StateSpaceModel
from aios_core.spiking_nn import SpikingNeuralNetwork
from aios_core.liquid_nn import LiquidNeuralNetwork
from aios_core.mamba import MambaModel
from aios_core.rwkv import RWKVModel
from aios_core.retnet import RetNet
from aios_core.moe import MixtureOfExperts
from aios_core.kan import KANetwork

def test_nn_stack():
    for cls in [TransformerModel, StateSpaceModel, SpikingNeuralNetwork,
                LiquidNeuralNetwork, MambaModel, RWKVModel, RetNet,
                MixtureOfExperts, KANetwork]:
        s = cls().stats()
        assert isinstance(s, dict)
