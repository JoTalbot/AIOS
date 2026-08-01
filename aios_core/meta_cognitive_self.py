# aios_core/tests/test_meta_cognitive_self.py

import pytest
from aios_core import meta_cognitive_self
from aios_core.meta_cognitive_self import CognitiveState

@pytest.fixture
def cognitive_state():
    """Return a CognitiveState instance."""
    return CognitiveState()

def test_meta_cognitive_self_init(cognitive_state):
    """Test initialization of CognitiveState."""
    assert cognitive_state.state == "initial"

def test_meta_cognitive_self_update_state(cognitive_state):
    """Test updating of CognitiveState."""
    cognitive_state.update_state("active")
    assert cognitive_state.state == "active"

def test_meta_cognitive_self_update_state_invalid(cognitive_state):
    """Test updating of CognitiveState with invalid state."""
    with pytest.raises(ValueError):
        cognitive_state.update_state("invalid")

def test_meta_cognitive_self_get_state(cognitive_state):
    """Test getting of CognitiveState."""
    cognitive_state.update_state("active")
    assert cognitive_state.get_state() == "active"

def test_meta_cognitive_self_get_state_initial(cognitive_state):
    """Test getting of CognitiveState in initial state."""
    assert cognitive_state.get_state() == "initial"

if __name__ == '__main__':
    pytest.main([__file__])