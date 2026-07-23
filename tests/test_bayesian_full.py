"""Bayesian inference full."""
from aios_core.bayesian import BayesianInference
def test(): s=BayesianInference().stats(); assert isinstance(s,dict)
