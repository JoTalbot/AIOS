"""Test dictionary learning."""
from aios_core.ai_safety_dictionary_learning import DictionaryLearner
def test_dict(): assert DictionaryLearner().stats() is not None
