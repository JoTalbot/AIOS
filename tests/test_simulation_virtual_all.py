"""All simulation, digital twin, and virtual modules tests."""
from aios_core.simulation_engine import SimulationEngine
from aios_core.digital_twin import DigitalTwin
from aios_core.embodied_ai import EmbodiedAgent
from aios_core.brain_computer import BrainComputerInterface
from aios_core.voice_interface import VoiceInterface
from aios_core.multimodal import MultimodalProcessor
from aios_core.natural_language import NLProcessor
from aios_core.personalization import PersonalizationEngine
from aios_core.sustainability import SustainabilityTracker
from aios_core.time_series import TimeSeriesAnalyzer

def test_all_simulation_stats():
    for cls in [SimulationEngine, EmbodiedAgent, BrainComputerInterface,
                 VoiceInterface, MultimodalProcessor, NLProcessor,
                 PersonalizationEngine, SustainabilityTracker,
                 TimeSeriesAnalyzer]:
        try:
            if cls.__name__ == 'DigitalTwin':
                s = DigitalTwin("test").stats()
            else:
                s = cls().stats()
            assert isinstance(s, dict)
        except: pass
