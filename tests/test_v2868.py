"""V-test 2868."""
from aios_core.transformer import TransformerModel
from aios_core.state_space import StateSpaceModel
from aios_core.spiking_nn import SpikingNeuralNetwork
from aios_core.graph_neural import GraphNeuralNetwork
from aios_core.graph_transformer import GraphTransformer

def test():
    for o in [TransformerModel(),StateSpaceModel(),SpikingNeuralNetwork(),GraphNeuralNetwork(),GraphTransformer()]:
        s = o.stats()
        assert isinstance(s, dict)
