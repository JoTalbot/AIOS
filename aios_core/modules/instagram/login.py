"""Instagram login-drive — best-effort драйв калибровки за логином.

Instagram (в отличие от OLX) закрывает ленту стеной входа, поэтому
generic ADB-драйв bootup натыкается на экран логина. Этот драйв:

1. открывает приложение и снимает дамп;
2. если обнаружен экран логина (resource-id/текстовые маркеры) —
   вводит логин/пароль через ADBKeyBoard-IME и ждёт загрузки;
3. снимает итоговый дамп (лента/поиск) и возвращает его калибровщику.

Учётные данные берутся ТОЛЬКО из окружения через
:mod:`aios_core.platforms.secrets`::

    export AIOS_SECRET__INSTAGRAM__USERNAME='jo.talbot@gmail.com'
    export AIOS_SECRET__INSTAGRAM__PASSWORD='•••'

Значения нигде не сохраняются и не логируются. Навигация по форме —
без координат (TAB/ENTER keyevents + focused input); при смене
верстки формы драйв честно падает на повторной детекции логина —
тогда нужен точечный драйв под конкретную сборку приложения.

Использование с bootup::

    from aios_core.modules.instagram import InstagramLoginDriver
    from aios_core.platforms import bootup_platform

    drv = InstagramLoginDriver(serial="emulator-5554")
    bootup_platform(
        apk_path="com.instagram.android", fetch=True,
        driver=drv.drive, query="sneakers",
    )
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Optional

from aios_core.modules.olx.adb import ADBController
from aios_core.platforms.secrets import required_secret

PACKAGE = "com.instagram.android"

#: Маркеры стены логина в дампе (resource-id + тексты кнопок).
_LOGIN_MARKERS = (
    "com.instagram.android:id/login",
    "log in",
    "log into",
    "sign up",
    "create new account",
    "creating an account",
    "увійти",
    "зареєструватися",
    "войти",
    "создать аккаунт",
)

_KEYEVENT_TAB = "61"
_KEYEVENT_ENTER = "66"


def login_screen_detected(xml: str) -> bool:
    """True, если дамп похож на экран входа Instagram."""
    lowered = (xml or "").lower()
    return any(marker in lowered for marker in _LOGIN_MARKERS)


class InstagramLoginDriver:
    """Драйв калибровки Instagram с авто-логином через env-секреты.

    Args:
        adb: Готовый ADBController (или None — создаётся по package/serial).
        package: Android-пакет Instagram.
        serial: ADB-serial устройства (из DevicePool).
        profile: Имя профиля для профильных секретов
            (``AIOS_SECRET__INSTAGRAM__<PROFILE>__PASSWORD``).
        open_wait_s: Пауза после запуска приложения.
        login_wait_s: Пауза после отправки формы логина.
    """

    def __init__(
        self,
        adb: Optional[ADBController] = None,
        package: str = PACKAGE,
        serial: str | None = None,
        profile: str | None = None,
        open_wait_s: float = 8.0,
        login_wait_s: float = 15.0,
        search_drive=None,
    ):
        """Initialize InstagramLoginDriver."""
        self.adb = adb or ADBController(package=package, serial=serial)
        self.profile = profile
        self.platform = "instagram"
        self.open_wait_s = open_wait_s
        self.login_wait_s = login_wait_s
        self.search_drive = search_drive  # PointDrive для поиска за логином

    def drive(self, package: str, query: str | None = None) -> str:
        """Сигнатура калибровочного драйва bootup: ``(package, query)->xml``.

        Открывает приложение, проходит логин при необходимости,
        опционально выполняет поиск (search_drive) и возвращает
        XML-дамп результирующего экрана.
        """
        opened = self.adb.open_app()
        if opened.get("code") != 0:
            raise ValueError(
                "adb open_app failed: " f"{(opened.get('stderr') or 'no device')[:160]}"
            )
        time.sleep(self.open_wait_s)
        xml = self._dump()
        if login_screen_detected(xml):
            self._login_flow()
            xml = self._dump()
            if login_screen_detected(xml):
                raise ValueError(
                    "instagram login flow did not pass the login wall — "
                    "check credentials, account verification screens or "
                    "provide a point-drive for this app build"
                )
        if query and self.search_drive is not None:
            xml = self.search_drive.search_in_open_app(query, xml)
        return xml

    def _login_flow(self) -> None:
        """Ввод логина/пароля: focused input → username → TAB → password → ENTER."""
        username = required_secret(
            self.platform,
            "USERNAME",
            profile=self.profile,
        )
        password = required_secret(
            self.platform,
            "PASSWORD",
            profile=self.profile,
        )
        self.adb.input_text(username)
        self.adb.run(f"{self.adb.adb} shell input keyevent {_KEYEVENT_TAB}")
        self.adb.input_text(password)
        self.adb.run(f"{self.adb.adb} shell input keyevent {_KEYEVENT_ENTER}")
        time.sleep(self.login_wait_s)

    def _dump(self) -> str:
        with tempfile.TemporaryDirectory(prefix="aios-ig-") as tmp:
            target = Path(tmp) / "screen.xml"
            result = self.adb.dump_ui(str(target))
            if result.get("code") != 0 or not target.exists():
                raise ValueError(
                    "adb dump_ui failed: " f"{(result.get('stderr') or 'dump unavailable')[:160]}"
                )
            return target.read_text(encoding="utf-8")
