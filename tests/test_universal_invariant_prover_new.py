"""universal_invariant_prover test."""
def test(): from aios_core.universal_invariant_prover import UniversalInvariantProver; s = UniversalInvariantProver().stats(); assert isinstance(s, dict)
