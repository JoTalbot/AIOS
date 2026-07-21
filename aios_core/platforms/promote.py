"""Own-promote — guarded план продвижения собственных постов/объявлений.

Stagnant-анализ (:meth:`OwnAdsTracker.stagnant`) → **только план**
(DRY-RUN по умолчанию): какие посты продвигать, в каком порядке, с
какой оценкой дневного бюджета. Реального платёжного/промоут-флоу для
Instagram нет — честно сообщаем это, не имитируя действия.
"""

from __future__ import annotations

from typing import Dict, List, Optional


def promotion_plan(
    stagnant_items: List[Dict],
    daily_budget: Optional[float] = None,
    currency: str = "UAH",
    max_items: int = 5,
) -> Dict[str, object]:
    """Собирает DRY-RUN план продвижения по застоявшимся постам.

    Args:
        stagnant_items: элементы OwnAdsTracker.stagnant().
        daily_budget: дневной бюджет; None → бюджет не задан (только
            очередь кандидатов). Расходится равномерно по кандидатам.
        currency: валюта бюджета.
        max_items: ограничение плана.

    Returns:
        {"dry_run": True, "candidates": [{fingerprint, title,
        views_per_day, action, est_daily_cost}], "note": ...}
    """
    candidates = stagnant_items[:max_items]
    per_item = None
    if daily_budget and candidates:
        per_item = round(float(daily_budget) / len(candidates), 2)
    return {
        "dry_run": True,
        "candidates": [
            {
                "fingerprint": item.get("fingerprint"),
                "title": item.get("title"),
                "views_per_day": item.get("views_per_day"),
                "age_days": item.get("age_days"),
                "action": "boost",
                "est_daily_cost": per_item,
            }
            for item in candidates
        ],
        "budget": daily_budget,
        "currency": currency,
        "note": (
            "DRY-RUN: промоут-флоу для платформы не реализован — план "
            "только для подтверждения; исполнение — отдельным confirm-шагом"
        ),
    }
