"""Task-type classification used to select focused prompt guidance."""

from __future__ import annotations

from enum import StrEnum


class TaskType(StrEnum):
    BUGFIX = "bugfix"
    FEATURE = "feature"
    REFACTOR = "refactor"
    SECURITY = "security"
    TEST = "test"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    RESEARCH = "research"
    UNKNOWN = "unknown"


_KEYWORDS: dict[TaskType, tuple[str, ...]] = {
    TaskType.BUGFIX: ("bug", "fix", "исправ", "ошиб", "баг", "exception", "crash"),
    TaskType.FEATURE: ("feature", "добав", "реализ", "implement", "нов", "функц"),
    TaskType.REFACTOR: ("refactor", "рефактор", "перепис", "упрост", "cleanup"),
    TaskType.SECURITY: ("security", "безопас", "auth", "secret", "injection", "уязв"),
    TaskType.TEST: ("test", "тест", "pytest", "coverage"),
    TaskType.DOCUMENTATION: ("docs", "documentation", "документац", "readme"),
    TaskType.PERFORMANCE: ("performance", "perf", "быстр", "оптимиз", "latency"),
    TaskType.RESEARCH: ("research", "исслед", "анализ", "сравн", "изуч"),
}


TASK_GUIDANCE: dict[TaskType, str] = {
    TaskType.BUGFIX: "Сначала воспроизведи дефект или найди подтверждение причины; исправляй причину, а не симптом.",
    TaskType.FEATURE: "Сначала проверь существующий API и паттерны; добавляй только необходимый surface area.",
    TaskType.REFACTOR: "Поведение до и после должно быть эквивалентным; сначала зафиксируй regression-проверки.",
    TaskType.SECURITY: "Моделируй угрозу, докажи влияние и проверь, что исправление не создаёт обходной путь.",
    TaskType.TEST: "Тест должен ловить реальный дефект/контракт и не быть зелёным только из-за слабых assertions.",
    TaskType.DOCUMENTATION: "Каждое утверждение сверяй с текущим кодом, CLI/API и конфигурацией.",
    TaskType.PERFORMANCE: "Сначала измерь baseline, затем изменение; без измерения не называй результат оптимизацией.",
    TaskType.RESEARCH: "Отделяй факты от гипотез и фиксируй пути/источники, по которым можно воспроизвести вывод.",
    TaskType.UNKNOWN: "Не угадывай тип задачи; придерживайся минимального scope и зафиксируй неоднозначности.",
}


def classify_task(description: str) -> TaskType:
    text = description.lower()
    scores = {kind: sum(text.count(word) for word in words) for kind, words in _KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] else TaskType.UNKNOWN


def guidance_for(description: str) -> tuple[TaskType, str]:
    kind = classify_task(description)
    return kind, TASK_GUIDANCE[kind]
