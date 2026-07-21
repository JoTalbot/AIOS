"""PointDrive — точечный драйв поиска поверх generic ADB-драйва.

Generic-драйв bootup открывает приложение и дампит стартовую ленту;
для калибровки поисковой выдачи нужен конкретный запрос. PointDrive
находит в дампе поисковый инпут (EditText из hints или resource-id с
«search»), тапает по центру его bounds, вводит запрос (ADBKeyBoard,
Cyrillic-safe) и жмёт ENTER — без координатных констант.

Используется и как самостоятельный драйв
(``driver=PointDrive(adb).drive``), и как post-login шаг Instagram
(``InstagramLoginDriver(search_drive=PointDrive(adb))``).
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

_SEARCH_RID_MARKERS = ("search", "query", "пошук", "поиск")


class PointDrive:
    """Драйв «открой → найди поиск → введи запрос → дамп выдачи».

    Args:
        adb: ADBController (с serial-привязкой из пула).
        input_classes: class-маркеры поля ввода (по умолчанию EditText;
            из ``parser_hints.messenger.input_classes``/extras).
        open_wait_s: Пауза после запуска приложения.
        search_wait_s: Пауза после отправки запроса.
    """

    def __init__(
        self,
        adb,
        input_classes: Optional[List[str]] = None,
        open_wait_s: float = 6.0,
        search_wait_s: float = 5.0,
    ):
        self.adb = adb
        self.input_classes = [
            cls.lower() for cls in (input_classes or ["edittext"])
        ]
        self.open_wait_s = open_wait_s
        self.search_wait_s = search_wait_s

    def drive(self, package: str, query: Optional[str] = None) -> str:
        """Сигнатура калибровочного драйва bootup: ``(package, query)->xml``."""
        opened = self.adb.open_app()
        if opened.get("code") != 0:
            raise ValueError(
                "adb open_app failed: "
                f"{(opened.get('stderr') or 'no device')[:160]}"
            )
        time.sleep(self.open_wait_s)
        xml = self._dump()
        if query:
            xml = self.search_in_open_app(query, xml)
        return xml

    def search_in_open_app(
        self, query: str, xml: Optional[str] = None
    ) -> str:
        """Выполняет поиск из уже открытого приложения.

        Returns:
            Дамп выдачи после запроса; если строка поиска не найдена —
            исходный дамп (verify-шаг bootup честно покажет 0 карточек).
        """
        xml = xml or self._dump()
        center = self._find_search_center(xml)
        if center is None:
            return xml
        self.adb.tap(*center)
        self.adb.input_text(query)
        self.adb.run(f"{self.adb.adb} shell input keyevent 66")
        time.sleep(self.search_wait_s)
        return self._dump()

    def _find_search_center(self, xml: str):
        """Центр bounds первого подходящего поискового инпута."""
        from aios_core.modules.olx.messenger import _parse_bounds
        from aios_core.platforms.calibrate import CalibrationAdvisor

        root = CalibrationAdvisor._root(xml)
        edit_center = None
        for node in root.iter("node"):
            rid = (node.attrib.get("resource-id") or "").lower()
            klass = (node.attrib.get("class") or "").lower()
            bounds = _parse_bounds(node.attrib.get("bounds"))
            if bounds is None:
                continue
            center = ((bounds[0] + bounds[2]) // 2,
                      (bounds[1] + bounds[3]) // 2)
            if any(marker in rid for marker in _SEARCH_RID_MARKERS):
                return center  # rid-подсказка приоритетнее класса
            if edit_center is None and any(
                marker in klass for marker in self.input_classes
            ):
                edit_center = center
        return edit_center

    def _dump(self) -> str:
        with tempfile.TemporaryDirectory(prefix="aios-point-") as tmp:
            target = Path(tmp) / "screen.xml"
            result = self.adb.dump_ui(str(target))
            if result.get("code") != 0 or not target.exists():
                raise ValueError(
                    "adb dump_ui failed: "
                    f"{(result.get('stderr') or 'dump unavailable')[:160]}"
                )
            return target.read_text(encoding="utf-8")
