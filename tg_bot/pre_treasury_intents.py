"""Pre-treasury текстовые интенты (seam из tg_bot/accounts.py, бюджет модуля).

Порядок важен: широкие фразы («трейдинг», «фриланс») перехватываются ДО
treasury-intent, у которого эти слова числятся ключевыми.
"""

from __future__ import annotations


def pre_treasury_intents(api, chat_id: int, text: str) -> bool:
    """True, если текст обработан здесь (до treasury)."""

    # Фриланс-сводка (v22.7): «фриланс», «что по фрилансу»
    try:
        from tg_bot.dashboard import _handle_freelance_summary_intent as _hfs
        if _hfs(api, chat_id, text):
            return True
    except Exception:
        pass

    # Кнопка «📈 Трейдинг» — человеческий отчёт
    from tg_bot.trading_report import handle_trading_text_intent
    return handle_trading_text_intent(api, chat_id, text)
