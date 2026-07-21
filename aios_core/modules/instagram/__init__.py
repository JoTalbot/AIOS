"""Instagram marketplace agent — полный функционал поверх OLX-механик.

Хранилище унаследовано от OLXStorage: схема объявлений, история цен,
подписки/избранное, outbox, свои объявления, конкурентные связи, kv-профиль.

Функционал:

* :class:`InstagramCollector` — сбор карточек ленты/выдачи (драйв
  навигации + hints-парсер → InstagramStorage);
* :class:`InstagramDetailParser` — детальный экран из hints-detail;
* :class:`InstagramMessenger` — guarded Direct (outbox-очередь OLX,
  hints-driven ввод/отправка);
* :class:`InstagramLoginDriver` — прохождение стены входа через
  env-секреты + опциональный PointDrive поиска;
* :class:`InstagramBootstrap` — doctor-отчёт готовности.

Онбординг: ``docs/modules/instagram/ONBOARDING.md``.
"""

from .bootstrap import InstagramBootstrap
from .cards import InstagramCollector
from .detail import InstagramDetailParser
from .login import InstagramLoginDriver, login_screen_detected
from .messenger import InstagramMessenger
from .storage import InstagramStorage

__all__ = [
    "InstagramBootstrap",
    "InstagramCollector",
    "InstagramDetailParser",
    "InstagramLoginDriver",
    "InstagramMessenger",
    "InstagramStorage",
    "login_screen_detected",
]
