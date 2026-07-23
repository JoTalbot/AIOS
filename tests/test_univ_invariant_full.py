"""Universal invariant full."""
from aios_core.universal_invariant_prover import UniversalInvariantProver
def test(): s=UniversalInvariantProver().stats(); assert isinstance(s,dict)
