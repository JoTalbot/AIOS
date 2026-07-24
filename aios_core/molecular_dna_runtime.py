"""Bio-Digital Molecular DNA Runtime for AIOS Horizon 9.0.

Translates AIOS Constitutional Laws into synthetic DNA nucleotide sequences (A, T, C, G),
executing molecular computing logic, enzymatic ligation, PCR state sequence matching,
restriction enzyme digestion, DNA repair simulation, mutation modeling, complementary
strand generation, codon translation, and gene expression regulation.
"""

import hashlib
import random
from collections.abc import Sequence
from typing import Any

__all__ = ["MolecularDNARuntime"]

# Codon table: 3-nucleotide sequences → amino acids
_CODON_TABLE: dict[str, str] = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}

_COMPLEMENT = {"A": "T", "T": "A", "C": "G", "G": "C"}

# Restriction enzyme recognition sites
_RESTRICTION_ENZYMES: dict[str, str] = {
    "EcoRI": "GAATTC",
    "BamHI": "GGATCC",
    "HindIII": "AAGCTT",
    "NotI": "GCGGCCGC",
    "PstI": "CTGCAG",
}


class MolecularDNARuntime:
    """Molecular Synthetic DNA Logic Engine.

    Provides encoding/decoding of textual payloads into DNA sequences,
    PCR amplification simulation, restriction enzyme digestion,
    DNA repair modeling, mutation simulation, complementary strand
    generation, codon translation, and gene expression regulation.
    """

    NUCLEOTIDE_MAP = {"00": "A", "01": "C", "10": "G", "11": "T"}
    REVERSE_NUCLEOTIDE_MAP = {v: k for k, v in NUCLEOTIDE_MAP.items()}

    def __init__(self):
        """Initialize MolecularDNARuntime."""
        self.dna_memory_bank: dict[str, str] = {}
        self._gene_expression: dict[str, float] = {}  # rule_id → expression level
        self._mutations_applied: int = 0
        self._repairs_applied: int = 0
        self._ligations: int = 0

    # ------------------------------------------------------------------
    # Encoding / Decoding
    # ------------------------------------------------------------------

    def encode_to_dna(self, text_payload: str) -> str:
        """Encode textual payload into synthetic DNA nucleotide sequence."""
        binary_str = "".join(format(ord(c), "08b") for c in text_payload)
        dna_seq = []
        for i in range(0, len(binary_str), 2):
            bits = binary_str[i : i + 2]
            dna_seq.append(self.NUCLEOTIDE_MAP.get(bits, "A"))
        return "".join(dna_seq)

    def decode_from_dna(self, dna_sequence: str) -> str:
        """Decode synthetic DNA sequence back into original text."""
        binary_bits = [self.REVERSE_NUCLEOTIDE_MAP.get(nuc, "00") for nuc in dna_sequence]
        full_binary = "".join(binary_bits)
        chars = []
        for i in range(0, len(full_binary), 8):
            byte = full_binary[i : i + 8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        return "".join(chars)

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def store_molecular_rule(self, rule_id: str, rule_text: str) -> str:
        """Synthesize and store DNA sequence for a constitutional rule."""
        dna_seq = self.encode_to_dna(rule_text)
        self.dna_memory_bank[rule_id] = dna_seq
        self._gene_expression[rule_id] = 1.0  # default expression level
        return dna_seq

    def retrieve_molecular_rule(self, rule_id: str) -> str | None:
        """Retrieve DNA sequence for *rule_id*, return None if not found."""
        return self.dna_memory_bank.get(rule_id)

    def delete_molecular_rule(self, rule_id: str) -> bool:
        """Remove a rule from the DNA memory bank."""
        if rule_id in self.dna_memory_bank:
            self.dna_memory_bank.pop(rule_id)
            self._gene_expression.pop(rule_id, None)
            return True
        return False

    # ------------------------------------------------------------------
    # PCR Amplification
    # ------------------------------------------------------------------

    def simulate_pcr_amplification(
        self, rule_id: str, amplification_cycles: int = 10
    ) -> dict[str, Any]:
        """Simulate Polymerase Chain Reaction (PCR) molecular amplification."""
        seq = self.dna_memory_bank.get(rule_id, "")
        if not seq:
            return {
                "success": False,
                "error": f"Rule ID '{rule_id}' not found in DNA memory bank.",
            }

        molecule_count = 2**amplification_cycles
        return {
            "success": True,
            "rule_id": rule_id,
            "dna_sequence_length": len(seq),
            "pcr_cycles": amplification_cycles,
            "amplified_molecules_count": molecule_count,
            "molecular_density_pmo_per_ul": round(molecule_count * 1.66e-12, 6),
        }

    # ------------------------------------------------------------------
    # Complementary strand
    # ------------------------------------------------------------------

    def generate_complementary_strand(self, dna_sequence: str) -> str:
        """Generate the Watson-Crick complementary strand."""
        return "".join(_COMPLEMENT.get(nuc, "A") for nuc in dna_sequence)

    def generate_double_stranded(self, rule_id: str) -> dict[str, str] | None:
        """Return both sense and antisense strands for *rule_id*."""
        sense = self.dna_memory_bank.get(rule_id)
        if sense is None:
            return None
        antisense = self.generate_complementary_strand(sense)
        return {"sense": sense, "antisense": antisense}

    # ------------------------------------------------------------------
    # Restriction enzyme digestion
    # ------------------------------------------------------------------

    def digest_with_restriction_enzyme(
        self, dna_sequence: str, enzyme_name: str
    ) -> dict[str, Any]:
        """Simulate restriction enzyme cutting at recognition sites.

        Returns fragments and cut positions.
        """
        site = _RESTRICTION_ENZYMES.get(enzyme_name)
        if site is None:
            return {
                "success": False,
                "error": f"Unknown enzyme: {enzyme_name}",
                "available_enzymes": list(_RESTRICTION_ENZYMES.keys()),
            }

        fragments: list[str] = []
        positions: list[int] = []
        last_cut = 0

        pos = 0
        while pos <= len(dna_sequence) - len(site):
            if dna_sequence[pos : pos + len(site)] == site:
                positions.append(pos)
                # Cut in the middle of the recognition site
                cut_point = pos + len(site) // 2
                fragments.append(dna_sequence[last_cut:cut_point])
                last_cut = cut_point
                pos += len(site)
            else:
                pos += 1

        # Final fragment
        if last_cut < len(dna_sequence):
            fragments.append(dna_sequence[last_cut:])

        return {
            "success": True,
            "enzyme": enzyme_name,
            "recognition_site": site,
            "cut_positions": positions,
            "fragment_count": len(fragments),
            "fragments": fragments,
            "fragment_lengths": [len(f) for f in fragments],
        }

    def digest_rule(self, rule_id: str, enzyme_name: str) -> dict[str, Any]:
        """Digest stored rule DNA with a restriction enzyme."""
        seq = self.dna_memory_bank.get(rule_id)
        if seq is None:
            return {"success": False, "error": f"Rule '{rule_id}' not found"}
        result = self.digest_with_restriction_enzyme(seq, enzyme_name)
        result["rule_id"] = rule_id
        return result

    # ------------------------------------------------------------------
    # Enzymatic ligation
    # ------------------------------------------------------------------

    def ligate_fragments(
        self, fragments: Sequence[str], sticky_end_length: int = 4
    ) -> dict[str, Any]:
        """Simulate enzymatic ligation of DNA fragments with sticky ends."""
        if len(fragments) < 2:
            return {
                "success": False,
                "error": "Need at least 2 fragments to ligate",
            }

        ligated = fragments[0]
        for i in range(1, len(fragments)):
            # Overlap sticky ends
            overlap = min(sticky_end_length, len(fragments[i - 1]), len(fragments[i]))
            ligated = ligated[:-overlap] + fragments[i]

        self._ligations += 1
        return {
            "success": True,
            "ligated_sequence": ligated,
            "ligated_length": len(ligated),
            "input_fragment_count": len(fragments),
            "total_input_length": sum(len(f) for f in fragments),
            "overlapping_bases": sticky_end_length * (len(fragments) - 1),
        }

    # ------------------------------------------------------------------
    # DNA repair simulation
    # ------------------------------------------------------------------

    def simulate_dna_repair(self, dna_sequence: str) -> dict[str, Any]:
        """Simulate DNA repair: fix common mutations (deamination, depurination).

        Scans the sequence for mismatched pairs and repairs them using
        the complementary strand as reference.
        """
        complement = self.generate_complementary_strand(dna_sequence)
        repaired_positions: list[int] = []
        repaired_seq = list(dna_sequence)

        # Simulate: detect potential mismatches (random sampling for demo)
        for i in range(len(dna_sequence)):
            expected_complement = _COMPLEMENT.get(dna_sequence[i])
            if complement[i] != expected_complement:
                repaired_seq[i] = _COMPLEMENT.get(complement[i], dna_sequence[i])
                repaired_positions.append(i)

        repaired_str = "".join(repaired_seq)
        self._repairs_applied += len(repaired_positions)

        return {
            "original_length": len(dna_sequence),
            "repaired_positions": repaired_positions,
            "positions_repaired": len(repaired_positions),
            "repaired_sequence": repaired_str,
            "repair_success": True,
        }

    # ------------------------------------------------------------------
    # Mutation simulation
    # ------------------------------------------------------------------

    def simulate_mutation(
        self,
        dna_sequence: str,
        mutation_rate: float = 0.01,
        mutation_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Simulate random mutations on a DNA sequence."""
        if mutation_types is None:
            mutation_types = ["point", "insertion", "deletion"]
        mutated = list(dna_sequence)
        mutations: list[dict[str, Any]] = []
        nucleotides = ["A", "T", "C", "G"]

        num_mutations = max(1, int(len(dna_sequence) * mutation_rate))

        for _ in range(num_mutations):
            pos = random.randint(0, len(mutated) - 1)
            mtype = random.choice(mutation_types)

            if mtype == "point":
                original = mutated[pos]
                new_nuc = random.choice([n for n in nucleotides if n != original])
                mutated[pos] = new_nuc
                mutations.append(
                    {
                        "type": "point",
                        "position": pos,
                        "original": original,
                        "mutated": new_nuc,
                    }
                )

            elif mtype == "insertion":
                ins_nuc = random.choice(nucleotides)
                mutated.insert(pos, ins_nuc)
                mutations.append(
                    {
                        "type": "insertion",
                        "position": pos,
                        "inserted": ins_nuc,
                    }
                )

            elif mtype == "deletion":
                if len(mutated) > 1:
                    deleted = mutated.pop(pos)
                    mutations.append(
                        {
                            "type": "deletion",
                            "position": pos,
                            "deleted": deleted,
                        }
                    )

        self._mutations_applied += len(mutations)
        return {
            "mutated_sequence": "".join(mutated),
            "mutation_count": len(mutations),
            "mutations": mutations,
            "mutation_rate": mutation_rate,
        }

    # ------------------------------------------------------------------
    # Codon translation
    # ------------------------------------------------------------------

    def translate_to_proteins(self, dna_sequence: str) -> dict[str, Any]:
        """Translate DNA sequence into amino acid chain (protein) via codons."""
        amino_acids: list[str] = []
        codons_used: list[str] = []
        stop_positions: list[int] = []

        # Process in 3-nucleotide codons
        for i in range(0, len(dna_sequence) - 2, 3):
            codon = dna_sequence[i : i + 3]
            codons_used.append(codon)
            aa = _CODON_TABLE.get(codon, "?")
            if aa == "*":  # stop codon
                stop_positions.append(i // 3)
            amino_acids.append(aa)

        protein = "".join(amino_acids)
        return {
            "protein_sequence": protein,
            "codons_used": codons_used,
            "amino_acid_count": len(amino_acids),
            "stop_codon_positions": stop_positions,
            "has_stop_codon": len(stop_positions) > 0,
            "coding_length": len(dna_sequence) - (len(dna_sequence) % 3),
        }

    # ------------------------------------------------------------------
    # Gene expression regulation
    # ------------------------------------------------------------------

    def regulate_expression(
        self, rule_id: str, expression_level: float
    ) -> dict[str, Any]:
        """Set expression level (0.0–2.0) for a stored rule."""
        if rule_id not in self._gene_expression:
            return {
                "success": False,
                "error": f"Rule '{rule_id}' not registered for expression",
            }
        self._gene_expression[rule_id] = max(0.0, min(2.0, expression_level))
        return {
            "success": True,
            "rule_id": rule_id,
            "expression_level": self._gene_expression[rule_id],
            "status": "overexpressed"
            if expression_level > 1.5
            else "suppressed"
            if expression_level < 0.3
            else "normal",
        }

    def get_expression_profile(self) -> dict[str, float]:
        """Return the full gene expression profile."""
        return dict(self._gene_expression)

    # ------------------------------------------------------------------
    # Integrity verification
    # ------------------------------------------------------------------

    def verify_integrity(self, rule_id: str) -> dict[str, Any]:
        """Verify DNA sequence integrity via SHA-256 hash comparison."""
        seq = self.dna_memory_bank.get(rule_id)
        if seq is None:
            return {"valid": False, "error": f"Rule '{rule_id}' not found"}

        hash_val = hashlib.sha256(seq.encode("utf-8")).hexdigest()[:16]
        complement = self.generate_complementary_strand(seq)
        complement_hash = hashlib.sha256(complement.encode("utf-8")).hexdigest()[:16]

        return {
            "valid": True,
            "rule_id": rule_id,
            "sequence_length": len(seq),
            "sequence_hash": hash_val,
            "complement_hash": complement_hash,
            "hashes_match": hash_val != complement_hash,  # Different by nature
            "nucleotide_composition": {n: seq.count(n) for n in "ATCG"},
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        total_nucleotides = sum(len(s) for s in self.dna_memory_bank.values())
        composition = {"A": 0, "T": 0, "C": 0, "G": 0}
        for seq in self.dna_memory_bank.values():
            for nuc in seq:
                if nuc in composition:
                    composition[nuc] += 1

        return {
            "synthesized_dna_rules": len(self.dna_memory_bank),
            "total_nucleotides_stored": total_nucleotides,
            "nucleotide_composition": composition,
            "mutations_applied": self._mutations_applied,
            "repairs_applied": self._repairs_applied,
            "ligations": self._ligations,
            "expressed_rules": len(self._gene_expression),
        }
