"""Y-test 3531."""
from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.theory_of_mind import TheoryOfMind
from aios_core.metacognition import MetacognitionEngine
from aios_core.social_intelligence import SocialIntelligence
from aios_core.creativity import CreativeEngine
from aios_core.personalization import PersonalizationEngine
from aios_core.embodied_ai import EmbodiedAgent
from aios_core.brain_computer import BrainComputerInterface
from aios_core.voice_interface import VoiceInterface
from aios_core.multimodal import MultimodalProcessor
from aios_core.natural_language import NLProcessor

def test():
    for o in [EmotionalIntelligence(),TheoryOfMind(),MetacognitionEngine(),
              SocialIntelligence(),CreativeEngine(),PersonalizationEngine(),
              EmbodiedAgent(),BrainComputerInterface(),VoiceInterface(),
              MultimodalProcessor(),NLProcessor()]:
        s = o.stats()
        assert isinstance(s, dict)
