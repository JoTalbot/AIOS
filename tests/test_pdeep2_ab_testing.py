"""Parametrized deep: ab_testing."""
import pytest
from aios_core.ab_testing import ABTest

@pytest.mark.parametrize("w",[{"a":0.5,"b":0.5},{"a":0.8,"b":0.2},{"a":1.0}])
def test_ab(w):
    ab = ABTest("t",w)
    v = ab.assign_variant("u")
    assert v in w
