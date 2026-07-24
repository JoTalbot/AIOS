"""Instagram collector — сбор карточек ленты/выдачи по hints-парсеру.

Полный цикл как у OLXCollector (дамп → парсер → свайп → дедупликация),
но навигация к выдаче — через инъецируемый драйв
(:class:`InstagramLoginDriver` за стеной входа или
:class:`~aios_core.platforms.pointdrive.PointDrive`), а парсер карточек
резолвится из ``parser_hints`` дескриптора платформы (``parser_for``).

Хранилище — :class:`InstagramStorage` (полная схема OLX: история цен,
неактивные объявления, подписки) через тот же ``collect_to_storage``.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.collector import OLXCollector
from aios_core.modules.olx.models import AdCard
from aios_core.platforms import parser_for

PACKAGE = "com.instagram.android"


class InstagramCollector:
    """Collector карточек Instagram (лента/поиск постов-магазинов).

    Args:
        adb: ADBController (с serial-привязкой). По умолчанию создаётся
            для ``com.instagram.android``.
        parser: Парсер карточек; None → ``parser_for("instagram")``
            (runtime-парсер из extras.parser_hints дескриптора).
        driver: Необязательный драйв навигации к выдаче
            ``(package, query)->xml`` перед сбором (login и/или поиск).
        directory: Каталог YAML-дескрипторов для parser_for.
    """

    def __init__(
        self,
        adb: Optional[ADBController] = None,
        parser=None,
        driver=None,
        serial: str | None = None,
        directory: str = "platforms",
        max_swipes: int = 40,
        swipe_pause_s: float = 0.0,
        screen_width: int = 1080,
        screen_height: int = 2400,
        pacer=None,
    ):
        """Initialize InstagramCollector."""
        self.adb = adb or ADBController(package=PACKAGE, serial=serial)
        self.parser = parser
        self.driver = driver
        self.directory = directory
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pacer = pacer

    def resolve_parser(self) -> None:
        """Парсер карточек: явный или runtime из дескриптора платформы."""
        if self.parser is not None:
            return self.parser
        try:
            return parser_for("instagram", directory=self.directory)
        except ValueError as exc:
            raise ValueError(
                "instagram card parser unavailable: run "
                "'aios platforms bootup --apk com.instagram.android --fetch' "
                f"or calibrate --write first ({exc})"
            ) from None

    def _collector(self) -> OLXCollector:
        return OLXCollector(
            adb=self.adb,
            parser=self.resolve_parser(),
            max_swipes=self.max_swipes,
            swipe_pause_s=self.swipe_pause_s,
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            pacer=self.pacer,
        )

    def _drive(self, query: str | None) -> None:
        if self.driver is not None:
            package = getattr(self.adb, "package", PACKAGE)
            self.driver(package, query)

    def collect(
        self,
        query: str | None = None,
        max_cards: int = 100,
        progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> List[AdCard]:
        """Собирает дедуплицированные карточки с текущей выдачи."""
        self._drive(query)
        return self._collector().collect(
            query=query,
            max_cards=max_cards,
            progress=progress,
        )

    def collect_to_storage(
        self,
        storage,
        query: str | None = None,
        max_cards: int = 100,
        progress: Optional[Callable[[int, int, int], None]] = None,
    ):
        """Сбор + персист в InstagramStorage (как OLXCollector)."""
        self._drive(query)
        return self._collector().collect_to_storage(
            storage,
            query=query,
            max_cards=max_cards,
            progress=progress,
        )
