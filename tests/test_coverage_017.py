"""Test weak-to-strong generalization."""
from aios_core.ai_safety_weak_to_strong import WeakToStrongGeneralization
def test_w2s(): assert WeakToStrongGeneralization().stats() is not None
