"""Autonomy Intent — классификация намерений клиента/владельца.

Сначала быстрый keyword-префильтр (детерминированный), при неоднозначности —
LLM-уточнение. Возвращает структуру:
    {intent, action_hint, params, risk, aggressive, bulk}
"""
from __future__ import annotations

from typing import Any

# Ключевые слова для быстрой классификации (RU/UK/EN)
_BUY = ("куплю", "хочу купить", "интересует", "актуально", "возьму", "куплю",
        "хочу", "купить", "придбав", "купить", "куплю", "интересует", "актуальн")
_NEGOTIATE = ("торг", "дешевле", "скидк", "уступи", "сбрось", "дешевше", "по дешевле",
              "можешь дешевле", "знижк", "торг", "сделайте скидку", "сколько последняя",
              "цена вопроса", "ваш прайс", "не дорого", "дешево", "цена до")
_PRICE = ("сколько стоит", "цена", "прайс", "вартість", "почем", "по чем", "цiна", "сколько")
_SHIP = ("доставк", "пересилка", "відправ", "відправити", "нова пошта", "новою поштою",
         "отправка", "можете отправить", "пересылка", "упакуете")
_BULK = ("оптом", "гуртом", "партия", "партія", "несколько", "кілька", "все что есть",
         "опт", "весь склад", "скидка опт")
_THANKS = ("спасибо", "дякую", "супер", "отлично", "ок", "окей", "добре")
_GREET = ("здравств", "привет", "добрий день", "добрый день", "вітаю", "хай", "hi", "hello")


def classify(text: str) -> dict[str, Any]:
    t = (text or "").lower()
    aggressive = any(w in t for w in ("срочно", "быстро отв", "сейчас же", "нервн",
                                      "не хочу ждать", "терміново", "ага", "ну и"))
    bulk = any(w in t for w in _BULK)
    params: dict = {}
    intent = "other"

    if any(w in t for w in _NEGOTIATE):
        intent = "negotiate"
        action_hint = "negotiate_price"
    elif any(w in t for w in _PRICE):
        intent = "price_check"
        action_hint = "query_price_history"
    elif any(w in t for w in _BUY):
        intent = "buy_intent"
        action_hint = "reply_customer"
    elif any(w in t for w in _SHIP):
        intent = "shipping_ask"
        action_hint = "reply_customer"
    elif any(w in t for w in _THANKS):
        intent = "acknowledge"
        action_hint = "reply_customer"
    elif any(w in t for w in _GREET):
        intent = "greeting"
        action_hint = "reply_customer"
    else:
        intent = "other"
        action_hint = "reply_customer"

    risk = "medium" if aggressive else ("low" if intent in ("greeting", "acknowledge") else "medium")

    return {
        "intent": intent,
        "action_hint": action_hint,
        "params": params,
        "risk": risk,
        "aggressive": aggressive,
        "bulk": bulk,
    }
