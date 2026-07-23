"""brain_computer test."""
def test(): from aios_core.brain_computer import BrainComputerInterface; s = BrainComputerInterface().stats(); assert isinstance(s, dict)
