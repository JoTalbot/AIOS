# ML & Recommendations

## ML Conversion Predictor
Предсказывает конверсию шаблонов на основе:
- Длины контента
- Количества переменных
- Наличия ключевых слов (скидка, приветствие)
- Эмоциональных маркеров

API:
- GET /api/v1/ml/predict?template={...}

## Recommendation Engine
Анализирует шаблоны и дает рекомендации:
- Низкая конверсия → A/B тестирование
- Слишком короткий → добавить контекст
- Нет переменных → добавить персонализацию

API:
- GET /api/v1/recommendations
- GET /api/v1/recommendations/template/{id}

## Новые платформы
Добавлены адаптеры для:
- TikTok
- LinkedIn
- eBay
- TikTok Shop

Всего поддерживается 10 платформ.
