"""Molecular DNA full."""
from aios_core.molecular_dna_runtime import MolecularDNARuntime
def test(): s=MolecularDNARuntime().stats(); assert isinstance(s,dict)
