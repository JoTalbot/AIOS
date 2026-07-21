"""AI-советник Direct-ответов: draft-only генерация черновиков в outbox.

Guarded-дизайн H3.11:

* советник **только** ставит черновики в guarded outbox (``enqueue_outbox``)
  — на устройство ничего не попадает без человеческого одобрения и
  ``dm-flush``;
* дополнительная защёлка: если у платформы нет compliance-политики,
  советник честно отказывается (``deny-by-default``);
* каждый черновик попадает в audit-log (``advise.draft``,
  ``advise.denied``);
* исполнитель текста подменяемый: по умолчанию — детерминированный
  шаблонный движок (нет сети, нет галлюцинаций); LLM подключается как
  callable (``composer``) и явно фиксируется в отчёте. Хардкод-фасада
  в репо пока нет — это осознанная честная прореха, см. ROADMAP H3.11.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from aios_core.platforms.compliance import compliance_block

_LANGUAGE_TRIGGERS = {
    "en": ("actual", "available", "price", "hello", "hi ", "still"),
    "ru": ("актуально", "цена", "здравствуйте", "привет", "продаётся"),
}
_PRICE_TRIGGERS = ("цена", "скільки", "сколько", "price", "стоимость",
                   "вартість", "trade", "обмен", "обмін")
_AVAILABILITY_TRIGGERS = ("актуально", "актуальн", "still", "available",
                          "в наличии", "є в наявності")

_TEMPLATES = {
    "uk": {
        "availability": (
            "Добрий день, {name}! Так, «{ad}» ще актуально. "
            "Можу відповісти на запитання або домовитись про перегляд."),
        "price": (
            "Добрий день, {name}! По «{ad}» актуальна ціна в оголошенні; "
            "за швидку домовленість можу зробити невелику знижку. "
            "Напишіть, будь ласка, коли зручно обговорити."),
        "generic": (
            "Добрий день, {name}! Дякую за інтерес до «{ad}». "
            "Чим можу допомогти? Відповім на запитання чи дам деталі."),
    },
    "en": {
        "availability": (
            "Hello {name}! Yes, \"{ad}\" is still available. "
            "Happy to answer questions or arrange a viewing."),
        "price": (
            "Hello {name}! The listed price for \"{ad}\" is current; "
            "I can offer a small discount for a quick deal. "
            "Let me know what works for you."),
        "generic": (
            "Hello {name}! Thanks for your interest in \"{ad}\". "
            "How can I help? I can answer questions or share details."),
    },
}


def _classify(text: str) -> str:
    """Грубая детерминированная классификация намерения сообщения."""
    low = (text or "").lower()
    if any(trigger in low for trigger in _PRICE_TRIGGERS):
        return "price"
    if any(trigger in low for trigger in _AVAILABILITY_TRIGGERS):
        return "availability"
    return "generic"


def reply_draft(
    interlocutor: str,
    snippet: str,
    ad_title: Optional[str] = None,
    *,
    locale: str = "uk-UA",
) -> str:
    """Единичный шаблонный черновик (без платформы/стореджа).

    Args:
        interlocutor: имя собеседника (как видно в чате).
        snippet: последнее сообщение (текст).
        ad_title: связанное объявление (если распознано).
        locale: ``uk-UA``/``en``; сообщение на латинице с en-триггерами
            переключает на английские шаблоны.

    Returns:
        Текст черновика.
    """
    language = locale.split("-")[0].split("_")[0].lower()
    if language not in _TEMPLATES:
        language = "uk"
    low = (snippet or "").lower()
    if any(trigger in low for trigger in _LANGUAGE_TRIGGERS["en"]):
        language = "en"
    templates = _TEMPLATES[language]
    intent = _classify(snippet)
    name = (interlocutor or "").strip() or ("there" if language == "en"
                                            else "друже")
    ad = (ad_title or "").strip() or ("the listing" if language == "en"
                                      else "оголошення")
    return templates[intent].format(name=name, ad=ad)


def advise_drafts(
    threads: Iterable,
    storage,
    platform: str,
    *,
    directory: str = "platforms",
    locale: str = "uk-UA",
    composer=None,
    audit: bool = True,
) -> Dict[str, object]:
    """Ставит draft-черновики в outbox по непрочитанным тредам.

    Args:
        threads: итерация ChatThread-подобных объектов (есть
            ``interlocutor``, ``snippet``, ``ad_title``, ``unread_count``,
            ``key``).
        storage: платформенное хранилище (OLXStorage-наследник) —
            должно принимать ``enqueue_outbox``.
        platform: имя платформы (compliance + аудит).
        locale: локаль шаблонов.
        composer: необязательный callable(interlocutor, snippet,
            ad_title, locale) -> str. Без него — шаблонный движок.
        audit: писать события в audit-log (olx_audit).

    Returns:
        {platform, enqueued, skipped, denied, engine, entries[...]}.
    """
    policy = compliance_block(platform, directory)
    engine = "composer" if composer is not None else "template"
    report: Dict[str, object] = {
        "platform": platform, "enqueued": 0, "skipped": 0,
        "denied": 0, "engine": engine, "entries": [],
    }
    if not policy:
        report["denied_reason"] = (
            "нет extras.compliance в дескрипторе — deny-by-default")
        if audit and hasattr(storage, "audit"):
            storage.audit("advise.denied",
                          detail=str(report["denied_reason"]),
                          ref=platform)
        report["denied"] = len(list(threads))
        return report

    for thread in threads:
        unread = int(getattr(thread, "unread_count", 0) or 0)
        snippet = (getattr(thread, "snippet", "") or "").strip()
        if unread <= 0 or not snippet:
            report["skipped"] += 1
            continue
        if composer is not None:
            draft = composer(
                getattr(thread, "interlocutor", ""),
                snippet,
                getattr(thread, "ad_title", None),
                locale,
            )
        else:
            draft = reply_draft(
                getattr(thread, "interlocutor", ""),
                snippet,
                getattr(thread, "ad_title", None),
                locale=locale,
            )
        if not draft or not str(draft).strip():
            report["skipped"] += 1
            continue
        outbox_id = storage.enqueue_outbox(
            thread.key, str(draft),
            interlocutor=getattr(thread, "interlocutor", None),
        )
        if audit and hasattr(storage, "audit"):
            storage.audit(
                "advise.draft",
                detail=f"engine={engine} draft for "
                       f"{getattr(thread, 'interlocutor', '?')}",
                ref=str(outbox_id),
            )
        report["enqueued"] += 1
        report["entries"].append({
            "outbox_id": outbox_id,
            "chat_key": thread.key,
            "interlocutor": getattr(thread, "interlocutor", None),
            "draft": str(draft),
        })
    return report
