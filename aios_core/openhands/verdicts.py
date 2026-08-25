"""Парсинг вердиктов ролей из событий OpenHands-разговора.

Вердикт — машиночитаемый маркер в последнем сообщении агента:
``APPROVED`` или ``CHANGES_REQUESTED`` (требуется в промптах Reviewer/Security/QA,
см. ``profiles.build_prompt``). Консервативное правило: при наличии обоих
маркеров побеждает CHANGES_REQUESTED.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .models import ReviewDecision

APPROVED_TOKEN = "APPROVED"
CHANGES_REQUESTED_TOKEN = "CHANGES_REQUESTED"


def _iter_strings(node: Any) -> Iterator[str]:
    """Рекурсивно отдать все строковые значения из dict/list-структуры."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _iter_strings(value)
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _iter_strings(item)


def parse_review_verdict(events_payload: dict[str, Any]) -> ReviewDecision | None:
    """Извлечь вердикт из ответа ``events_search``.

    Сканирует тексты событий с конца (последний вердикт важнее).
    Возвращает None, если маркер не найден (caller решает fallback).
    """
    events = events_payload.get("events", [])
    texts = [text for event in reversed(events) for text in _iter_strings(event)]
    for text in texts:
        if CHANGES_REQUESTED_TOKEN in text:
            return ReviewDecision.CHANGES_REQUESTED
        if APPROVED_TOKEN in text:
            return ReviewDecision.APPROVED
    return None
