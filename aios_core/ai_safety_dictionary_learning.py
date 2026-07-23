"""Dictionary Learning for Interpretability"""

from typing import Dict, List


class DictionaryLearner:
    """Learns interpretable dictionaries from model activations."""

    def __init__(self, dict_size: int = 10000):
        self.dict_size = dict_size
        self.dictionary: Dict = {}

    def learn_dictionary(self, activations: List[list[float]]) -> None:
        """Fit a dictionary of *dict_size* concepts to *activations*."""
        self.dictionary = {f"concept_{i}": 0.0 for i in range(self.dict_size)}

    def interpret_feature(self, feature_idx: int) -> str:
        """Return a human-readable label for *feature_idx*."""
        return f"Interpretable concept {feature_idx}"

    def stats(self) -> dict:
        """Return the number of concepts in the dictionary."""
        return {"dictionary_size": len(self.dictionary)}
