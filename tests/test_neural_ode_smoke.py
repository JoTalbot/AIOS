"""neural_ode smoke test."""
def test_node(): from aios_core.neural_ode import NeuralODE; s = NeuralODE(lambda x: [v*2 for v in x]).stats(); assert isinstance(s, dict)
