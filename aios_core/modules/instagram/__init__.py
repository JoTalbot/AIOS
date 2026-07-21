"""Instagram marketplace agent — скелет, сгенерированный scaffold.

Хранилище унаследовано от OLXStorage: схема объявлений, история цен,
подписки/избранное, outbox, свои объявления, конкурентные связи, kv-профиль.
Парсеры/коллекторы платформы добавляются сюда по мере калибровки под
её приложение (com.instagram.android).

Instagram закрывает ленту стеной входа: калибровочный login-драйв
(`InstagramLoginDriver`) проходит её через env-секреты
(`AIOS_SECRET__INSTAGRAM__USERNAME/PASSWORD`) — см.
``docs/modules/instagram/ONBOARDING.md``.
"""

from .login import InstagramLoginDriver, login_screen_detected
from .storage import InstagramStorage

__all__ = ["InstagramLoginDriver", "InstagramStorage", "login_screen_detected"]
