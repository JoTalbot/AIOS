# Исторические новости: сбор, сентимент, тест связи с ценой

**Дата:** 2026-08-16 | Ветка: agent/20260815-quant-oos-profit

## Пайплайн (протестирован локально перед деплоем)
1. **Сбор** — `scripts/fetch_historical_news.py`: RSS-снапшоты CoinTelegraph из Wayback
   Machine (11 648 снапшотов за год) → 1545 уникальных заголовков (2025-08-01..2026-07-18)
   с реальными датами публикации (pubDate) → `data/quant/news_historical.jsonl`;
2. **Сентимент** — `scripts/score_historical_sentiment.py`: Gemini 2.5 Flash, батчи по 8,
   resume-safe (merge по url), ключи: только 1 из 3 рабочих (остальные 404);
   `data/quant/news_historical_scored.jsonl`;
3. **Тест связи** — `scripts/sentiment_price_historical.py`: новость → движение цены
   (1h/24h/3d/7d) → корреляция сентимент→доходность по монетам.

## Локальное тестирование (перед продом)
- `tests/test_news_pipeline.py` — 30 тестов (парсинг RSS, выбор снапшотов, парсинг
  ответа Gemini, merge/resume, detect_coins, end-to-end на синтетике, валидация ключей):
  **30/30 PASS** локально и на сервере (против прод-скриптов).
- Найденные и исправленные баги: (а) валидация ключей отбрасывала рабочие при 429 —
  теперь только 401/403/404; (б) скоринг продолжал ретраить при мёртвой квоте — теперь
  break с сохранением прогресса; (в) пауза 5→12с (rate limit 1 ключа).

## Статус
- Сбор: ✅ 1545 заголовков;
- Сентимент: ⏳ квота Gemini исчерпана сегодня (429 "exceeded quota") — таймер
  `aios-news-scoring.timer` (каждые 30 мин) догонит автоматически, когда квота
  обновится (resume-safe);
- Тест связи: ожидает завершения скоринга.

## Воспроизводимость
```bash
# тесты
cd /root/AIOS && /opt/aios/.venv/bin/python tests/test_news_pipeline.py
# пайплайн
python scripts/fetch_historical_news.py
python scripts/score_historical_sentiment.py
python scripts/sentiment_price_historical.py
```
