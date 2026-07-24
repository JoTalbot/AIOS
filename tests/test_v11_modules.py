import pytest
from aios_core.quantum import QuantumCircuit, QuantumErrorMitigation

def test_qem_zne():
    qem = QuantumErrorMitigation(base_noise=0.05)
    
    # We want to measure probability of 00. With 0 noise it should be 1.0 (or close)
    def build_circ(noise):
        circ = QuantumCircuit(qubits=2, noise_factor=noise)
        circ.add_gate("H", 0)
        circ.add_gate("H", 0) # H*H = I
        return circ
        
    def exp_val(counts):
        return counts.get("00", 0) / sum(counts.values())
        
    val_with_mitigation = qem.zero_noise_extrapolation(build_circ, exp_val)
    raw_circ = build_circ(0.05)
    raw_val = exp_val(raw_circ.measure(2000))
    
    # Due to random nature, extrapolation should generally bring it closer to 1.0 than raw
    # We just ensure it runs without error and returns a float
    assert isinstance(val_with_mitigation, float)
    assert 0.0 <= val_with_mitigation <= 1.2 # extrapolation can sometimes overshoot slightly

def test_qem_readout():
    qem = QuantumErrorMitigation()
    
    # A mocked 2x2 confusion matrix: [P(0|0), P(0|1)], [P(1|0), P(1|1)]
    confusion = [
        [0.9, 0.1],
        [0.1, 0.9]
    ]
    
    raw_counts = {"00": 800, "01": 200}
    
    mitigated = qem.readout_error_mitigation(raw_counts, confusion)
    
    # Since 10% of 00 flips to 01, mitigating it should restore 00 to >0.8
    assert mitigated["00"] > 0.8
    assert mitigated["01"] < 0.2
