from typing import Any

from aios_core.ml.conversion_predictor import predictor


class RecommendationEngine:
    def __init__(self):
        self.threshold = 0.2

    def analyze_template(self, template: dict) -> dict[str, Any]:
        """Анализирует шаблон и дает рекомендации."""
        predicted_conversion = predictor.predict(template)
        recommendations = []

        if predicted_conversion < self.threshold:
            recommendations.append(
                {
                    "type": "low_conversion",
                    "message": f"Предсказанная конверсия: {predicted_conversion:.1%}. Рекомендуется A/B тестирование.",
                    "priority": "high",
                }
            )

        content = template.get("content", "")
        if len(content) < 50:
            recommendations.append(
                {
                    "type": "too_short",
                    "message": "Шаблон слишком короткий. Добавьте больше контекста.",
                    "priority": "medium",
                }
            )

        if "{{" not in content:
            recommendations.append(
                {
                    "type": "no_variables",
                    "message": "Шаблон не использует переменные. Добавьте персонализацию.",
                    "priority": "medium",
                }
            )

        return {
            "template_id": template.get("id"),
            "predicted_conversion": predicted_conversion,
            "recommendations": recommendations,
            "score": round(predicted_conversion * 100, 1),
        }

    def get_top_recommendations(self, templates: list[dict]) -> list[dict]:
        """Возвращает топ рекомендаций для всех шаблонов."""
        results = []
        for template in templates:
            analysis = self.analyze_template(template)
            if analysis["recommendations"]:
                results.append(analysis)

        results.sort(key=lambda x: len(x["recommendations"]), reverse=True)
        return results[:10]


recommendation_engine = RecommendationEngine()
