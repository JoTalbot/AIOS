"""Tests for Bio-Digital Molecular DNA Runtime (Horizon 9.0)."""

import pytest

from aios_core.molecular_dna_runtime import MolecularDNARuntime


def test_dna_encoding_decoding_and_pcr():
    runtime = MolecularDNARuntime()

    original_text = "ARTICLE-I Identity is supreme"
    dna_seq = runtime.store_molecular_rule("rule_001", original_text)

    # DNA sequence consists only of nucleotide bases A, T, C, G
    assert all(base in "ATCG" for base in dna_seq)

    # Round-trip decoding
    decoded_text = runtime.decode_from_dna(dna_seq)
    assert decoded_text == original_text

    # Simulate PCR Amplification
    pcr_res = runtime.simulate_pcr_amplification("rule_001", amplification_cycles=5)
    assert pcr_res["success"] is True
    assert pcr_res["amplified_molecules_count"] == 32
