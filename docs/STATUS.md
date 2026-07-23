# AIOS Documentation Status

**Версия пакета:** 9.3.0 | **Дата аудита:** 23 июля 2026

## Статус документации

| Раздел | Статус | Файлов |
|--------|--------|--------|
| Главная (index) | ✅ Актуально | 1 |
| Быстрый старт | ✅ Создано | 1 |
| Установка | ✅ Актуально | 1 |
| Использование | ✅ Актуально | 1 |
| Развёртывание | ✅ Актуально | 1 |
| Production Exploitation | ✅ Создано | 1 |
| CHANGELOG | ✅ Обновлено | 1 |
| Архитектура | ✅ Актуально | 5 |
| Core / Ядро | ✅ Актуально | 30 |
| Конституция | ✅ Полная | 72 |
| Платформы | ✅ Актуально | 7 |
| Память и знания | ✅ Актуально | 4 |
| MCP и API | ✅ Актуально | 3 |
| Оркестрация | ✅ Актуально | 3 |
| Тестирование | ✅ Актуально | 3 |
| Приложения | ✅ Актуально | 5 |
| Модели | ✅ Актуально | 2 |
| Роадмап | ✅ Актуально | 3 |
| Ревью | ✅ Актуально | 1 |

## Инструменты документации

| Инструмент | Статус | Файл |
|-----------|--------|------|
| MkDocs (сайт) | ✅ Создано | `mkdocs.yml` |
| Sphinx (PDF) | ✅ Обновлено | `docs/source/conf.py` |
| Material Theme | ✅ Настроено | mkdocs.yml → theme: material |
| Search | ✅ Включено | mkdocs.yml → plugins: search |
| Versioning (mike) | ✅ Настроено | mkdocs.yml → extra: version |

## Метрики

- **Всего markdown-файлов:** 162
- **Статьи конституции:** 67
- **Модули ядра:** 30+
- **Платформы документированы:** 9 (OLX, Instagram, FB, TikTok, Viber, WhatsApp, Prom, Bigl, Shafa)
- **API-маршруты:** 143
- **Тесты:** 1255 пройдены; 1 не блокирующее предупреждение (см. `../TEST_AUDIT_2026-07-23.md`)

## Сборка

### MkDocs (локально)

```bash
pip install mkdocs mkdocs-material mkdocs-minify-plugin
mkdocs serve        # http://localhost:8000
mkdocs build        # site/
```

### Sphinx PDF

```bash
pip install sphinx sphinx-rtd-theme
cd docs/source
make latexpdf       # _build/latex/AIOS.pdf
```

### GitHub Pages (mike)

```bash
mike deploy 9.2.0 latest --push
```
