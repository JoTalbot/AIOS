
TRANSLATIONS = {
    "en": {
        "dashboard_title": "AIOS Dashboard",
        "templates": "Templates",
        "metrics": "Metrics",
        "chat": "Agent Chat",
        "editor": "Template Editor",
        "api_docs": "API Docs"
    },
    "uk": {
        "dashboard_title": "Панель керування AIOS",
        "templates": "Шаблони",
        "metrics": "Метрики",
        "chat": "Чат агентів",
        "editor": "Редактор шаблонів",
        "api_docs": "Документація API"
    },
    "ru": {
        "dashboard_title": "Панель управления AIOS",
        "templates": "Шаблоны",
        "metrics": "Метрики",
        "chat": "Чат агентов",
        "editor": "Редактор шаблонов",
        "api_docs": "Документация API"
    }
}

def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)
