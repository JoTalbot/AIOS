"""Text normalisation & parsing helpers for OLX UI dumps (uk/ru locales)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

# Space-like characters OLX uses inside price strings.
_SPACE_RE = re.compile(r"[    -   　]+")

# Tokens meaning "no numeric price".
_NO_PRICE_TOKENS = (
    "договірна",
    "договорная",
    "безкоштовно",
    "бесплатно",
    "безоплатно",
    "обмін",
    "обмен",
    "free",
)

_AMOUNT_RE = re.compile(r"(\d[\d\s]*(?:[.,]\d{1,2})?)")

_CURRENCY_SUFFIXES = {
    "грн": "UAH",
    "uah": "UAH",
    "$": "USD",
    "usd": "USD",
    "дол": "USD",
    "€": "EUR",
    "eur": "EUR",
    "zł": "PLN",
}

_MONTHS = {
    # Ukrainian
    "січня": 1,
    "лютого": 2,
    "березня": 3,
    "квітня": 4,
    "травня": 5,
    "червня": 6,
    "липня": 7,
    "серпня": 8,
    "вересня": 9,
    "жовтня": 10,
    "листопада": 11,
    "грудня": 12,
    # Russian
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

_TODAY_RE = re.compile(
    r"(?:сьогодні|сегодня)\s*(?:[воу]\s*)?(\d{1,2}:\d{2})", re.IGNORECASE
)
_YESTERDAY_RE = re.compile(
    r"(?:вчора|вчера)\s*(?:[воу]\s*)?(\d{1,2}:\d{2})", re.IGNORECASE
)
_DATE_RE = re.compile(r"(\d{1,2})\s+([а-яіїєґА-ЯІЇЄҐ]+)\s+(\d{4})")


def normalize_text(text: str | None) -> str:
    """Collapse exotic whitespace into plain single spaces."""
    if not text:
        return ""
    return _SPACE_RE.sub(" ", text).strip()


def parse_price(text: str | None) -> tuple[float, str] | None:
    """Extract ``(amount, currency)`` from an OLX price label.

    Handles ``"7 000 грн"``, ``"1 500 $"``, ``"$ 2 000"``, ``"900 €"`` and
    returns ``None`` for negotiable/free/exchange listings.
    """
    raw = normalize_text(text)
    if not raw:
        return None
    lowered = raw.lower()
    if any(token in lowered for token in _NO_PRICE_TOKENS):
        return None

    # Suffix form: "7 000 грн", "1 500 $", "900 €", "2 000 usd"
    match = _AMOUNT_RE.search(raw)
    if not match:
        return None
    amount_raw = match.group(1)
    tail = lowered[match.end() :].lstrip(" .,")
    head = lowered[: match.start()].rstrip()

    currency: str | None = None
    for token, iso in _CURRENCY_SUFFIXES.items():
        if tail.startswith(token) or head.endswith(token) or head == token:
            currency = iso
            break
        # Prefix form: "$ 2 000" — currency symbol sits before the amount.
        if head.endswith(token):
            currency = iso
            break
    if currency is None:
        return None

    amount = float(amount_raw.replace(" ", "").replace(",", "."))
    return amount, currency


def parse_published(text: str | None, now: datetime | None = None) -> str | None:
    """Normalise an OLX publication label to an ISO-8601 timestamp.

    Supports ``"Сьогодні в 11:26"``, ``"Вчора о 18:02"`` and explicit dates
    such as ``"21 липня 2026"`` / ``"3 марта 2026"``. Returns ``None`` when
    the text is not a recognisable publication label.
    """
    raw = normalize_text(text)
    if not raw:
        return None
    now = now or datetime.now()

    match = _TODAY_RE.search(raw)
    if match:
        hour, minute = map(int, match.group(1).split(":"))
        return now.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        ).isoformat()

    match = _YESTERDAY_RE.search(raw)
    if match:
        hour, minute = map(int, match.group(1).split(":"))
        yesterday = now - timedelta(days=1)
        return yesterday.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        ).isoformat()

    match = _DATE_RE.search(raw)
    if match:
        day = int(match.group(1))
        month = _MONTHS.get(match.group(2).lower())
        year = int(match.group(3))
        if month:
            return datetime(year, month, day).isoformat()
    return None


def is_no_price_label(text: str | None) -> bool:
    """Whether the text is a non-numeric price label (negotiable/free/exchange)."""
    lowered = normalize_text(text).lower()
    return bool(lowered) and any(token in lowered for token in _NO_PRICE_TOKENS)


def is_top_text(text: str | None) -> bool:
    """Whether the text is a TOP promotion badge."""
    return normalize_text(text).lower() in {"top", "топ"}
