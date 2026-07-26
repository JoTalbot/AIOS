
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime

class ConversionPredictor:
    def __init__(self):
        self.weights = None
        self.trained = False
    
    def extract_features(self, template: Dict) -> np.ndarray:
        """Извлекает фичи из шаблона для предсказания."""
        content = template.get("content", "")
        features = np.array([
            len(content),
            content.count("{{"),
            1 if "скидка" in content.lower() else 0,
            1 if "здравствуйте" in content.lower() else 0,
            1 if "!" in content else 0,
            len(content.split()),
        ])
        return features
    
    def predict(self, template: Dict) -> float:
        """Предсказывает конверсию шаблона."""
        if not self.trained:
            return 0.1
        
        features = self.extract_features(template)
        if self.weights is None:
            self.weights = np.array([0.001, 0.05, 0.15, 0.1, 0.05, 0.002])
        
        prediction = np.dot(features, self.weights)
        return min(max(prediction, 0.0), 1.0)
    
    def train(self, templates: List[Dict], conversions: List[float]):
        """Обучает модель на исторических данных."""
        if len(templates) < 10:
            return
        
        X = np.array([self.extract_features(t) for t in templates])
        y = np.array(conversions)
        
        self.weights = np.linalg.lstsq(X, y, rcond=None)[0]
        self.trained = True

predictor = ConversionPredictor()
