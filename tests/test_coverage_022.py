"""Test formal verification."""
from aios_core.ai_safety_formal_verification import FormalVerifier
def test_formal(): assert FormalVerifier().stats() is not None
