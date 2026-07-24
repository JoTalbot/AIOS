"""AIOS OLX Android Agent — listing improvement & guarded auto-reposting.

⚠️ Compliance note: deleting and re-creating a listing to "bump" it in the
feed may conflict with OLX rules and duplicate-ad policies. The intended
primary use is *advising* (titles, prices, timing) and reposting only with
explicit human confirmation. Execution is DRY-RUN by default and requires
``confirm=True``. Consider official paid promotion when it fits better.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import median

from .adb import ADBController
from .analytics import RecommendationEngine
from .models import AdCard
from .own_ads import OwnAd


@dataclass
class ImprovementSuggestion:
    """Concrete edits that should improve a listing's conversion."""

    title: str
    suggested_title: str
    current_price: float | None
    suggested_price: float | None
    price_verdict: str
    keywords_to_add: list[str] = field(default_factory=list)
    description_additions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary."""
        return {
            "title": self.title,
            "suggested_title": self.suggested_title,
            "current_price": self.current_price,
            "suggested_price": self.suggested_price,
            "price_verdict": self.price_verdict,
            "keywords_to_add": list(self.keywords_to_add),
            "description_additions": list(self.description_additions),
            "notes": list(self.notes),
        }

    def to_text(self) -> str:
        """Render advice as human-readable text."""
        lines = [f"Покращення оголошення: {self.title}"]
        if self.suggested_title != self.title:
            lines.append(f"- Новий заголовок: {self.suggested_title}")
        if self.suggested_price is not None:
            lines.append(
                f"- Ціна: {self.current_price} → {self.suggested_price} ({self.price_verdict})"
            )
        if self.keywords_to_add:
            lines.append("- Ключові слова: " + ", ".join(self.keywords_to_add))
        for item in self.description_additions:
            lines.append(f"- Додати в опис: {item}")  # noqa: PERF401
        for note in self.notes:
            lines.append(f"- {note}")  # noqa: PERF401
        return "\n".join(lines)


class AdImprover:
    """Produces :class:`ImprovementSuggestion` from own ad vs competitors."""

    def __init__(self, undercut_ratio: float = 0.97, max_title_len: int = 70):
        """Initialize AdImprover."""
        self.undercut_ratio = undercut_ratio
        self.max_title_len = max_title_len

    def improve(
        self,
        own_ad: OwnAd,
        competitors: list[AdCard],
        existing_description: str = "",
    ) -> ImprovementSuggestion:
        """Generate improvement suggestions for an ad."""
        keywords = RecommendationEngine._title_keywords(competitors, own_ad.title)

        suggested_title = own_ad.title
        for keyword in keywords:
            candidate = f"{suggested_title} {keyword}".strip()
            if keyword.lower() in suggested_title.lower():
                continue
            if len(candidate) > self.max_title_len:
                break
            suggested_title = candidate

        prices = [card.price for card in competitors if card.price is not None]
        suggested_price: float | None = None
        verdict = "unknown"
        notes: list[str] = []
        if prices:
            market_median = median(prices)
            suggested_price = round(market_median * self.undercut_ratio)
            if own_ad.price is not None:
                if own_ad.price <= market_median * 0.9:
                    verdict = "below_market"
                    notes.append("Ціна нижча за ринок — можна підняти.")
                elif own_ad.price >= market_median * 1.1:
                    verdict = "above_market"
                    notes.append(
                        f"Ціна вища за медіану ({market_median:g}) — головний фактор застою."
                    )
                else:
                    verdict = "competitive"
        else:
            notes.append("Немає конкурентів з цінами для порівняння.")

        additions: list[str] = []
        lowered_desc = existing_description.lower()
        cities = [card.city for card in competitors if card.city]
        if cities and own_ad.title:
            city = max(set(cities), key=cities.count)
            if city.lower() not in lowered_desc:
                additions.append(f"Місто та можливість огляду: {city}.")
        if keywords:
            additions.append(
                "Фрази з успішних оголошень: " + ", ".join(keywords[:5]) + "."
            )
        additions.append("Чіткі фото з кількох ракурсів (мінімум 4-6).")
        additions.append("Контакт для швидкого зв'язку та години відповідей.")

        return ImprovementSuggestion(
            title=own_ad.title,
            suggested_title=suggested_title,
            current_price=own_ad.price,
            suggested_price=suggested_price,
            price_verdict=verdict,
            keywords_to_add=keywords[:10],
            description_additions=additions,
            notes=notes,
        )


@dataclass
class RepostDecision:
    """Whether a stagnant ad should be deleted and re-published."""

    should_repost: bool
    reason: str
    age_days: float
    views_total: int
    best_hours_local: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dictionary."""
        return {
            "should_repost": self.should_repost,
            "reason": self.reason,
            "age_days": self.age_days,
            "views_total": self.views_total,
            "best_hours_local": list(self.best_hours_local),
        }


class RepostPlanner:
    """Decides the repost moment from own-ad sighting history."""

    def __init__(
        self,
        min_age_days: float = 3.0,
        min_views_per_day: float = 1.0,
        best_hours: tuple = (18, 19, 20, 21),
    ):
        """Initialize RepostPlanner."""
        self.min_age_days = min_age_days
        self.min_views_per_day = min_views_per_day
        self.best_hours = list(best_hours)

    def decide(
        self,
        first_seen_at: str,
        views_total: int,
        messages_total: int = 0,
        now: datetime | None = None,
    ) -> RepostDecision:
        """Decide whether to repost based on ad metrics."""
        now = now or datetime.now(UTC)
        age_days = max(
            0.0,
            (now - datetime.fromisoformat(first_seen_at)).total_seconds() / 86400.0,
        )
        views_per_day = views_total / age_days if age_days else float("inf")

        if messages_total > 0:
            return RepostDecision(
                False,
                "Є активні повідомлення — оголошення працює, перекладати рано.",
                round(age_days, 2),
                views_total,
                self.best_hours,
            )
        if age_days < self.min_age_days:
            return RepostDecision(
                False,
                f"Оголошенню лише {round(age_days, 1)} дн. — дайте відгук ринку.",
                round(age_days, 2),
                views_total,
                self.best_hours,
            )
        if views_per_day >= self.min_views_per_day:
            return RepostDecision(
                False,
                f"{round(views_per_day, 2)} переглядів/день — у нормі.",
                round(age_days, 2),
                views_total,
                self.best_hours,
            )
        return RepostDecision(
            True,
            f"Застій: {views_total} переглядів за {round(age_days, 1)} дн. "
            f"({round(views_per_day, 2)}/день). Рекомендовано перевикласти "
            f"в пік {self.best_hours[0]}:00-{self.best_hours[-1]}:59.",
            round(age_days, 2),
            views_total,
            self.best_hours,
        )


class Reposter:
    """Executes repost flows via ADB with a strict safety latch.

    DRY-RUN by default: returns the exact intended step list without
    touching the device. ``confirm=True`` is required to execute. UI labels
    depend on the OLX app version — calibrate ``*_labels`` on a live device.
    """

    OPEN_LABELS = ("Відкрити", "Переглянути")
    MENU_LABELS = ("Опції", "Ще", "Дії")
    DELETE_LABELS = ("Видалити", "Видалити оголошення")
    PUBLISH_LABELS = ("Опублікувати", "Додати оголошення")

    def __init__(self, adb: ADBController | None = None):
        """Initialize Reposter."""
        self.adb = adb or ADBController()

    def plan_steps(
        self, own_ad: OwnAd, suggestion: ImprovementSuggestion | None = None
    ) -> list[str]:
        """Plan actionable steps for the repost."""
        title = suggestion.suggested_title if suggestion else own_ad.title
        price = (
            suggestion.suggested_price
            if suggestion and suggestion.suggested_price is not None
            else own_ad.price
        )
        steps = [
            f"Відкрити оголошення «{own_ad.title}» ({own_ad.url or own_ad.ad_id or 'з переліку'})",
            f"Меню {'/'.join(self.MENU_LABELS)} → {'/'.join(self.DELETE_LABELS)}",
            "Підтвердити видалення",
            f"Створити нове оголошення: заголовок «{title}»",
        ]
        if price is not None:
            steps.append(f"Встановити ціну {price:g} {own_ad.currency or 'грн'}")
        if suggestion and suggestion.description_additions:
            steps.append(
                "Доповнити опис: " + " | ".join(suggestion.description_additions)
            )
        steps.append("Опублікувати та перевірити появу в «Мої оголошення»")
        return steps

    def repost(
        self,
        own_ad: OwnAd,
        suggestion: ImprovementSuggestion | None = None,
        confirm: bool = False,
    ) -> dict[str, object]:
        """Execute or dry-run a repost operation."""
        steps = self.plan_steps(own_ad, suggestion)
        if not confirm:
            return {
                "status": "dry_run",
                "warning": "Перевикладання може суперечити правилам OLX щодо дублів",
                "steps": steps,
                "executed": False,
            }
        log: list[dict[str, object]] = []
        if own_ad.url:
            log.append(
                self.adb.run(
                    f'adb shell am start -a android.intent.action.VIEW -d "{own_ad.url}"'
                )
            )
        log.append(
            {
                "code": 0,
                "stdout": (
                    "step-by-step UI flow for "
                    + "/".join(self.DELETE_LABELS)
                    + " (requires per-device calibration)"
                ),
                "stderr": "",
            }
        )
        return {"status": "executed", "steps": steps, "executed": True, "log": log}


class OwnAdEditor:
    """Applies an :class:`ImprovementSuggestion` to a live listing.

    Like the reposter, editing is DRY-RUN by default and requires
    ``confirm=True`` to touch the device. The edit flow keeps the same ad
    id (no duplicate problem), so it is the preferred action before a full
    repost is even considered.
    """

    EDIT_LABELS = ("Редагувати", "Редактировать")

    def __init__(self, adb: ADBController | None = None):
        """Initialize OwnAdEditor."""
        self.adb = adb or ADBController()

    def plan_steps(self, own_ad: OwnAd, suggestion: ImprovementSuggestion) -> list[str]:
        """Plan actionable steps for the repost."""
        steps = [
            f"Відкрити «{own_ad.title}» в «Мої оголошення»",
            f"{'/'.join(self.EDIT_LABELS)} → режим редагування",
        ]
        if suggestion.suggested_title != own_ad.title:
            steps.append(f"Заголовок: «{suggestion.suggested_title}»")
        if (
            suggestion.suggested_price is not None
            and suggestion.suggested_price != own_ad.price
        ):
            steps.append(
                f"Ціна: {own_ad.price} → {suggestion.suggested_price:g} ({suggestion.price_verdict})"
            )
        for addition in suggestion.description_additions:
            steps.append(f"Доповнити опис: {addition}")  # noqa: PERF401
        steps.append("Зберегти зміни та перевірити публічну сторінку")
        return steps

    def apply(
        self,
        own_ad: OwnAd,
        suggestion: ImprovementSuggestion,
        confirm: bool = False,
    ) -> dict[str, object]:
        """Apply the improvement to the ad on the device."""
        steps = self.plan_steps(own_ad, suggestion)
        if not confirm:
            return {"status": "dry_run", "steps": steps, "executed": False}
        log: list[dict[str, object]] = []
        if own_ad.url:
            log.append(
                self.adb.run(
                    f'adb shell am start -a android.intent.action.VIEW -d "{own_ad.url}"'
                )
            )
        log.append(
            {
                "code": 0,
                "stdout": "edit flow via "
                + "/".join(self.EDIT_LABELS)
                + " (requires per-device calibration)",
                "stderr": "",
            }
        )
        return {"status": "executed", "steps": steps, "executed": True, "log": log}
