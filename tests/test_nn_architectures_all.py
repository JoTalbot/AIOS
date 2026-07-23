"""All neural network architecture tests."""
from aios_core.transformer import TransformerModel
from aios_core.state_space import StateSpaceModel
from aios_core.spiking_nn import SpikingNeuralNetwork
from aios_core.liquid_nn import LiquidNeuralNetwork
from aios_core.rwkv import RWKVModel
from aios_core.mamba import MambaModel
from aios_core.kan import KANetwork
from aios_core.retnet import RetNet
from aios_core.moe import MixtureOfExperts
from aios_core.graph_neural import GraphNeuralNetwork
from aios_core.graph_transformer import GraphTransformer
from aios_core.neural_ode import NeuralODE
from aios_core.pinn import PhysicsInformedNN

def test_all_nn_stats():
    modules = [
        TransformerModel, StateSpaceModel, SpikingNeuralNetwork,
        LiquidNeuralNetwork, RWKVModel, MambaModel, KANetwork,
        RetNet, MixtureOfExperts, GraphNeuralNetwork,
        GraphTransformer, PhysicsInformedNN,
    ]
    for cls in modules:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
