"""Human-like pacing — антибан-профилирование действий на устройстве.

``Pacer`` вставляет рандомизированные паузы между действиями коллектора
(свайпы/дампы) и обрубает цикл при превышении per-profile квот
(actions/hour, длина сессии): «too fast» — первый сигнал бана, поэтому
лимит — честный стоп, а не молчаливый обход.
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Callable, Optional, Tuple


class Pacer:
    """Контроллер темпа действий.

    Args:
        actions_per_hour: квота действий в час (0/None — без лимита).
        session_max_s: максимум секунд сессии (0/None — без лимита).
        jitter_s: (min, max) пауза перед действием; None — без пауз.
        rng: random.Random (тестам — seeded).
        sleeper: функция сна (тесты).
        now: фабрика времени (тесты).
    """

    def __init__(
        self,
        actions_per_hour: int | None = None,
        session_max_s: float | None = None,
        jitter_s: Optional[Tuple[float, float]] = (0.4, 1.6),
        rng: Optional[random.Random] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        now: Optional[Callable[[], float]] = None,
    ) -> None:
        """Initialize Pacer."""
        self.actions_per_hour = actions_per_hour or None
        self.session_max_s = session_max_s or 0.0
        self.jitter_s = jitter_s
        self._rng = rng or random.Random()
        self._sleep = sleeper or time.sleep
        self._now = now or time.time
        self._started = self._now()
        self._actions = 0
        self._window_started = self._started
        self._window_actions = 0

    def before_action(self) -> bool:
        """Пауза + счётчик перед действием. False — честный стоп цикла."""
        now = self._now()
        if now - self._window_started >= 3600.0:
            self._window_started = now
            self._window_actions = 0
        if self.actions_per_hour is not None and self._window_actions >= self.actions_per_hour:
            return False
        if self.session_max_s and now - self._started >= self.session_max_s:
            return False
        self._window_actions += 1
        self._actions += 1
        if self.jitter_s:
            low, high = self.jitter_s
            self._sleep(self._rng.uniform(low, high))
        return True

    def stats(self) -> dict:
        """Счётчики темпа для отчётов цикла."""
        return {
            "actions": self._actions,
            "window_actions": self._window_actions,
            "actions_per_hour": self.actions_per_hour or None,
            "session_s": round(self._now() - self._started, 3),
        }


def pacer_from_limits(
    prefix: str,
    limits,
    jitter_s: Optional[Tuple[float, float]] = (0.4, 1.6),
    **kwargs,
) -> Pacer:
    """Pacer из kv-лимитов DevicePool (``pacing:<profile>:...`` ключи).

    ``limits`` — callable(key, default)->int, как ``DevicePool.limit``.
    Отсутствующие ключи → без лимита (темп только по jitter).
    """
    actions = limits(f"pacing:{prefix}:actions_per_hour", 0)
    session = limits(f"pacing:{prefix}:session_max_s", 0)
    return Pacer(
        actions_per_hour=int(actions or 0) or None,
        session_max_s=float(session or 0) or None,
        jitter_s=jitter_s,
        **kwargs,
    )
