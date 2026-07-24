"""Scroll-цикл видео-ленты (Reels / короткие видео) любой платформы.

``ReelsCollector`` открывает видео-ленту (опциональный driver), затем в
цикле «дамп → парсинг видео-карточек → свайп» собирает уникальные карточки
до достижения лимита или пока свайпы перестают давать новые карточки.
``collect_to_storage`` пишет квитанции в storage (category="video") —
дедупликация между циклами без загрязнения таблицы объявлений.
"""

from __future__ import annotations

import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from aios_core.modules.olx.adb import ADBController
from aios_core.platforms.descriptor import PlatformDescriptor
from aios_core.platforms.runtime_hints import load_hints_section
from aios_core.platforms.videocards import HintVideoParser, VideoCard


class ReelsCollector:
    """Generic коллектор видео-ленты (reels-коллектор).

    Args:
        platform: дескриптор платформы.
        adb: контроллер устройства (по умолчанию новый).
        store: необязательный реестр профилей (для будущих квот); квитанции
            пишутся только в переданный ``storage``.
        directory: каталог YAML-дескрипторов (по умолчанию "platforms").
        parser: явный парсер видео-карточек; иначе из video_markers hints.
        driver: callable(adb)->bool для открытия видео-вкладки (необяз.).
        notifier: опциональный WebhookNotifier — событие ``video-new``
            при новых карточках цикла.
        screen_width/screen_height: геометрия экрана для свайпов.
    """

    def __init__(
        self,
        platform: PlatformDescriptor,
        adb: ADBController | None = None,
        store=None,
        directory: str = "platforms",
        parser: HintVideoParser | None = None,
        driver: Callable[[ADBController], bool] | None = None,
        notifier=None,
        screen_width: int = 1080,
        screen_height: int = 2400,
        pacer=None,
    ) -> None:
        """Initialize ReelsCollector."""
        self.platform = platform
        self.adb = adb or ADBController()
        self.store = store  # опционально; квитанции пишутся в storage
        self.directory = directory
        self._parser = parser
        self.driver = driver
        self.notifier = notifier
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pacer = pacer

    def resolve_parser(self) -> HintVideoParser:
        """Парсер видео из ``content_categories.video_markers`` дескриптора.

        Если секция ещё не откалибрована — дефолтные маркеры
        reel/video/clips (HintVideoParser). Если дескриптора нет вовсе —
        ValueError с рецептом калибровки.
        """
        if self._parser is not None:
            return self._parser
        try:
            categories = load_hints_section(
                self.platform.name,
                "content_categories",
                self.directory,
            )
        except ValueError as err:
            raise ValueError(
                f"дескриптор «{self.platform.name}» не найден в «{self.directory}» — "
                f"выполните `aios platforms bootup/calibrate --write` "
                f"или передайте parser=..."
            ) from err
        self._parser = HintVideoParser(categories.get("video_markers") or None)
        return self._parser

    def collect(
        self,
        max_cards: int = 200,
        max_swipes: int | None = None,
        stop_after_empty: int = 1,
        query: str | None = None,
    ) -> list[VideoCard]:
        """Скролл-цикл по видео-ленте: дамп → новые карточки → свайп.

        Args:
            max_cards: максимум уникальных карточек за цикл.
            max_swipes: максимум свайпов (по умолчанию = max_cards).
            stop_after_empty: стоп после N подряд дампов без новых карточек.
            query: необязательная метка запроса для карточек.

        Returns:
            Список уникальных видео-карточек в порядке появления.
        """
        parser = self.resolve_parser()
        if self.driver is not None and not self.driver(self.adb):
            raise RuntimeError(
                f"driver не смог открыть видео-ленту «{self.platform.name}»"
            )
        swipe_limit = max_swipes if max_swipes is not None else max_cards
        cards: list[VideoCard] = []
        seen = set()
        swipes = 0
        empties = 0
        with tempfile.TemporaryDirectory(prefix="aios_reels_") as tmp_dir:
            dump_path = Path(tmp_dir) / "screen.xml"
            while len(cards) < max_cards:
                result = self.adb.dump_ui(str(dump_path))
                if isinstance(result, dict) and result.get("code") not in (None, 0):
                    break
                if not dump_path.exists():
                    break
                fresh: list[VideoCard] = []
                for card in parser.parse(dump_path, query=query):
                    if card.fingerprint and card.fingerprint not in seen:
                        seen.add(card.fingerprint)
                        fresh.append(card)
                        cards.append(card)
                        if len(cards) >= max_cards:
                            break
                dump_path.unlink(missing_ok=True)
                empties = 0 if fresh else empties + 1
                if (
                    empties >= stop_after_empty
                    or len(cards) >= max_cards
                    or swipes >= swipe_limit
                ):
                    break
                if self.pacer is not None and not self.pacer.before_action():
                    break  # pacing-лимит — честный стоп цикла
                self._swipe_feed()
                swipes += 1
        return cards

    def _swipe_feed(self) -> None:
        """Свайп вверх по центру ленты, чтобы подгрузить новые карточки."""
        x = self.screen_width // 2
        y_from = int(self.screen_height * 0.8)
        y_to = int(self.screen_height * 0.2)
        self.adb.swipe(x, y_from, x, y_to, duration=400)

    def collect_to_storage(
        self,
        storage,
        max_cards: int = 200,
        max_swipes: int | None = None,
        stop_after_empty: int = 1,
        query: str | None = None,
        category: str = "video",
    ) -> tuple[int, list[VideoCard]]:
        """Цикл + квитанции в storage (дедуп между циклами).

        Returns:
            (число новых карточек, все карточки цикла).
        """
        cards = self.collect(
            max_cards=max_cards,
            max_swipes=max_swipes,
            stop_after_empty=stop_after_empty,
            query=query,
        )
        written = sum(
            1
            for card in cards
            if storage.check_and_record(card.fingerprint, kind=category, ref=query)
        )
        if written and self.notifier is not None:
            self.notifier.send(
                "video-new",
                {
                    "platform": self.platform.name,
                    "new": written,
                    "seen": len(cards),
                    "query": query,
                    "sample": [card.title for card in cards[:3]],
                },
            )
        return written, cards


# ---------------------------------------------------------------------------
# ReelsTabDriver: калибруемый тап по вкладке Reels перед scroll-циклом
# ---------------------------------------------------------------------------

_DEFAULT_TAB_RID_MARKERS = ("reels_tab", "clips_tab", "reels")
_DEFAULT_TAB_TEXT_MARKERS = ("reels", "reels tab")


class ReelsTabDriver:
    """Открывает видео-вкладку (Reels) тапом по найденному узлу.

    Маркеры калибруются через секцию ``extras.parser_hints.navigation``
    YAML-дескриптора (``reels_tab.rid_markers``/``text_markers``), дефолт —
    типовые resource-id хвосты reels/clips и подписи «Reels». Поиск узла —
    с bounds (тап по центру, без хардкода координат), как у HintSender.

    Args:
        adb: контроллер устройства (можно передать и в ``drive``).
        rid_markers: substring-маркеры resource-id узла вкладки.
        text_markers: подписи вкладки (text/content-desc, lower-case).
        open_wait_s: пауза после тапа (ожидание открытия ленты).
        sleeper: функция сна (тесты).
    """

    def __init__(
        self,
        adb: ADBController | None = None,
        rid_markers: list[str] | None = None,
        text_markers: list[str] | None = None,
        open_wait_s: float = 1.0,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        """Initialize ReelsTabDriver."""
        self.adb = adb
        self.rid_markers = tuple(
            str(m).rsplit("/", 1)[-1].lower()
            for m in (rid_markers or _DEFAULT_TAB_RID_MARKERS)
            if m
        )
        self.text_markers = tuple(
            str(t).strip().lower()
            for t in (text_markers or _DEFAULT_TAB_TEXT_MARKERS)
            if t
        )
        self.open_wait_s = open_wait_s
        self._sleep = sleeper or time.sleep

    def drive(self, adb: ADBController | None = None) -> bool:
        """Дамп → поиск узла вкладки → тап по центру. True — вкладка тапнута."""
        from aios_core.modules.olx.messenger import _parse_bounds
        from aios_core.platforms.calibrate import CalibrationAdvisor

        adb = adb or self.adb
        if adb is None:
            raise ValueError("ReelsTabDriver: adb не передан")
        with tempfile.TemporaryDirectory(prefix="aios_reels_tab_") as tmp_dir:
            dump_path = Path(tmp_dir) / "home.xml"
            result = adb.dump_ui(str(dump_path))
            if isinstance(result, dict) and result.get("code") not in (None, 0):
                return False
            if not dump_path.exists():
                return False
            root = CalibrationAdvisor._root(dump_path)
            for node in root.iter("node"):
                bounds = _parse_bounds(node.attrib.get("bounds"))
                if bounds is None:
                    continue
                rid_tail = (
                    (node.attrib.get("resource-id") or "").rsplit("/", 1)[-1].lower()
                )
                text = (node.attrib.get("text") or "").strip().lower()
                desc = (node.attrib.get("content-desc") or "").strip().lower()
                hit = any(marker in rid_tail for marker in self.rid_markers)
                if not hit:
                    hit = any(
                        value == marker or value.startswith(marker)
                        for marker in self.text_markers
                        for value in (text, desc)
                        if value
                    )
                if not hit:
                    continue
                center = ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
                adb.tap(*center)
                if self.open_wait_s:
                    self._sleep(self.open_wait_s)
                return True
        return False


def reels_driver_for(
    platform_name: str,
    adb: ADBController | None = None,
    directory: str = "platforms",
    open_wait_s: float = 1.0,
    sleeper: Callable[[float], None] | None = None,
) -> ReelsTabDriver:
    """ReelsTabDriver из секции ``navigation.reels_tab`` YAML-дескриптора.

    Секция не откалибрована → типовые дефолтные маркеры. Дескриптор
    отсутствует → ValueError (как у прочих *_for резолверов).
    """
    nav = load_hints_section(platform_name, "navigation", directory)
    tab = nav.get("reels_tab") or {}

    def _tails(items) -> list[str]:
        tails: list[str] = []
        for item in items or []:
            value = item.get("resource_id") if isinstance(item, dict) else item
            if value:
                tails.append(str(value))
        return tails

    return ReelsTabDriver(
        adb=adb,
        rid_markers=_tails(tab.get("rid_markers")) or None,
        text_markers=_tails(tab.get("text_markers")) or None,
        open_wait_s=open_wait_s,
        sleeper=sleeper,
    )
