"""Brain-computer full."""
from aios_core.brain_computer import BrainComputerInterface
def test(): s=BrainComputerInterface().stats(); assert isinstance(s,dict)
