"""Y-test 3737."""
from aios_core.transformer import TransformerModel
from aios_core.state_space import StateSpaceModel
from aios_core.spiking_nn import SpikingNeuralNetwork
from aios_core.liquid_nn import LiquidNeuralNetwork
from aios_core.mamba import MambaModel
from aios_core.rwkv import RWKVModel
from aios_core.retnet import RetNet
from aios_core.moe import MixtureOfExperts
from aios_core.kan import KANetwork
from aios_core.neural_ode import NeuralODE
from aios_core.pinn import PhysicsInformedNN
from aios_core.score_based import ScoreBasedModel
from aios_core.graph_neural import GraphNeuralNetwork
from aios_core.graph_transformer import GraphTransformer

def test():
    for o in [TransformerModel(),StateSpaceModel(),SpikingNeuralNetwork(),
              LiquidNeuralNetwork(),MambaModel(),RWKVModel(),RetNet(),
              MixtureOfExperts(),KANetwork(),
              NeuralODE(lambda x:[v*2 for v in x]),PhysicsInformedNN(),
              ScoreBasedModel(),GraphNeuralNetwork(),GraphTransformer()]:
        s = o.stats()
        assert isinstance(s, dict)
