"""adversarial boundary test."""
from aios_core.adversarial import AdversarialDefense

def test_initial_attacks(): assert AdversarialDefense().stats()['attacks_detected'] == 0
