"""Neural ODE full."""
from aios_core.neural_ode import NeuralODE
def test(): s=NeuralODE(lambda x: [v*2 for v in x]).stats(); assert isinstance(s,dict)
