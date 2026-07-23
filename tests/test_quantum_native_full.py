"""Quantum native full."""
from aios_core.quantum_native import QuantumNativeRuntime
def test(): s=QuantumNativeRuntime().stats(); assert isinstance(s,dict)
