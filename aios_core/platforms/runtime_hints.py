"""Runtime-парсеры из parser_hints: детальный экран и мессенджер.

Аналог :func:`parsergen.build_parser`, но для оставшихся экранов
паттерна OLX ``detail.py``/``messenger.py``: codegen-файлы не нужны —
подсказки калибровки (``extras.parser_hints.detail``/``messenger``)
полностью описывают платформенную разметку, runtime-адаптеры читают
их прямо из дескриптора (:func:`detail_parser_for`,
:func:`chat_list_parser_for`). Драйв отправки реализован через
:func:`build_sender` — низкоуровневый исполнитель (guarded-уровень
outbox/approval остаётся в ``OLXMessenger``-совместимых обёртках).
"""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from aios_core.modules.olx.text_utils import normalize_text, parse_price

_MIN_DESCRIPTION_LEN = 40


def _rid_tail(resource_id: str) -> str:
    """``com.demo:id/detailPrice`` → ``detailprice``."""
    return resource_id.rsplit("/", 1)[-1].lower()


def _rid_set(hints_section: Dict, key: str, nested: bool = False) -> set:
    values = set()
    raw = (hints_section or {}).get(key) or []
    if nested:  # [{resource_id, ...}, ...]
        raw = [item.get("resource_id") for item in raw if isinstance(item, dict)]
    for rid in raw:
        if rid:
            values.add(_rid_tail(str(rid)))
    return values


class HintDetailParser:
    """Runtime-парсер детального экрана из ``parser_hints.detail``.

    Маркеры: ``price_nodes`` (resource-id цены), ``seller_markers``
    (блок продавца), ``cta_markers`` (кнопки связи). Заголовок и
    описание — shape-эвристика (первый не-ценовой текст / самый
    длинный текст ≥ 40 символов).
    """

    def __init__(self, detail_hints: Dict):
        hints = detail_hints or {}
        self.price_ids = _rid_set(hints, "price_nodes", nested=True)
        self.seller_ids = _rid_set(hints, "seller_markers")
        self.cta_ids = _rid_set(hints, "cta_markers", nested=True)
        self.configured = bool(self.price_ids or self.seller_ids or self.cta_ids)

    def parse(self, xml_source: Union[str, Path, ET.Element]) -> Dict[str, object]:
        """Разбирает дамп детального экрана в структурированные поля."""
        from aios_core.platforms.calibrate import CalibrationAdvisor

        root = CalibrationAdvisor._root(xml_source)
        title: Optional[str] = None
        description: Optional[str] = None
        price: Optional[float] = None
        currency: Optional[str] = None
        seller: Optional[str] = None
        cta_texts: List[str] = []

        texts: List[str] = []
        for node in root.iter("node"):
            rid = _rid_tail(node.attrib.get("resource-id") or "")
            text = normalize_text(node.attrib.get("text"))
            if not text:
                continue
            texts.append(text)
            parsed = parse_price(text)
            if (
                price is None
                and parsed is not None
                and (not self.price_ids or rid in self.price_ids)
            ):
                price, currency = parsed
                continue
            if (
                rid
                and self.seller_ids
                and rid in self.seller_ids
                and seller is None
                and 2 <= len(text) <= 60
                and parsed is None
            ):
                seller = text
                continue
            if rid and self.cta_ids and rid in self.cta_ids:
                if text not in cta_texts:
                    cta_texts.append(text)

        # Shape-эвристика по оставшимся текстам:
        for text in texts:
            if parse_price(text) is not None or text in cta_texts:
                continue
            if len(text) >= _MIN_DESCRIPTION_LEN:
                if description is None or len(text) > len(description):
                    description = text
                continue
            if title is None and text != seller and 4 <= len(text) <= 80:
                title = text

        return {
            "title": title,
            "price": price,
            "currency": currency,
            "seller": seller,
            "description": description,
            "cta_texts": cta_texts,
            "texts_seen": len(texts),
        }


class HintSender:
    """Низкоуровневый драйв отправки сообщения по messenger-hints.

    Исполнитель для ``OLXMessenger._type_and_send``-совместимых
    обёрток: тап по полю ввода (EditText из hints/дампа) → ввод текста
    через ADBKeyBoard (Cyrillic-safe) → тап по кнопке отправки
    (send-маркер подсказок или content-desc «send»). Guarded-уровень
    (очередь/подтверждение) живёт выше; здесь честный отчёт о шагах.
    """

    def __init__(self, adb, messenger_hints: Optional[Dict] = None):
        self.adb = adb
        hints = messenger_hints or {}
        self.input_classes = [
            str(cls).lower() for cls in (hints.get("input_classes") or [])
        ] or ["edittext"]
        self.send_ids = _rid_set(hints, "send_markers", nested=True)
        self._send_text_markers = ("send", "надіслати", "отправить")

    def type_and_send(
        self,
        text: str,
        xml_source: Optional[Union[str, Path, ET.Element]] = None,
    ) -> Dict[str, object]:
        """Вводит и отправляет ``text`` в открытом диалоге.

        Args:
            text: Текст сообщения.
            xml_source: Дамп открытого диалога; None — снимается самим.

        Returns:
            {code, steps} — code последней adb-команды (0 при успехе).
        """
        from aios_core.modules.olx.messenger import _parse_bounds

        steps: List[Dict[str, object]] = []
        if xml_source is None:
            with tempfile.TemporaryDirectory(prefix="aios-send-") as tmp:
                target = Path(tmp) / "chat.xml"
                self.adb.dump_ui(str(target))
                if not target.exists():
                    return {"code": 1, "error": "dump_ui failed", "steps": steps}
                return self.type_and_send(text, target.read_text("utf-8"))

        from aios_core.platforms.calibrate import CalibrationAdvisor

        root = CalibrationAdvisor._root(xml_source)

        input_center = None
        send_center = None
        for node in root.iter("node"):
            rid = _rid_tail(node.attrib.get("resource-id") or "")
            klass = (node.attrib.get("class") or "").lower()
            desc = (node.attrib.get("content-desc") or "").strip()
            text_attr = (node.attrib.get("text") or "").strip()
            bounds = _parse_bounds(node.attrib.get("bounds"))
            if bounds is None:
                continue
            center = ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
            if input_center is None and any(
                marker in klass for marker in self.input_classes
            ):
                input_center = center
            combined = f"{rid} {desc.lower()} {text_attr.lower()}"
            if send_center is None and (
                rid in self.send_ids
                or any(marker in combined for marker in self._send_text_markers)
            ):
                send_center = center

        if input_center is not None:
            self.adb.tap(*input_center)
            steps.append({"action": "tap_input", "center": input_center})
        type_result = self.adb.input_text(text)
        steps.append({"action": "input_text", "code": type_result.get("code")})

        if send_center is not None:
            result = self.adb.tap(*send_center)
            steps.append(
                {
                    "action": "tap_send",
                    "center": send_center,
                    "code": result.get("code"),
                }
            )
        else:
            result = self.adb.run(f"{self.adb.adb} shell input keyevent 66")
            steps.append({"action": "keyevent_enter", "code": result.get("code")})
        return {"code": result.get("code"), "steps": steps}


def load_hints_section(platform_name: str, section: str, directory="platforms") -> Dict:
    """Секция ``extras.parser_hints`` из YAML-дескриптора платформы.

    Returns:
        Словарь секции (``detail``/``messenger``/...); пусто, если
        секция ещё не откалибрована.

    Raises:
        ValueError: Дескриптор платформы не найден.
    """
    import yaml

    yaml_path = Path(directory) / f"{platform_name}.yaml"
    if not yaml_path.exists():
        raise ValueError(f"descriptor not found: {yaml_path}")
    doc = yaml.safe_load(yaml_path.read_text("utf-8")) or {}
    hints = (doc.get("extras") or {}).get("parser_hints") or {}
    return hints.get(section) or {}


def detail_parser_for(platform_name: str, directory="platforms") -> HintDetailParser:
    """HintDetailParser из YAML-дескриптора платформы (секция detail)."""
    return HintDetailParser(load_hints_section(platform_name, "detail", directory))


def chat_list_parser_for(
    platform_name: str,
    directory="platforms",
):
    """ChatListParser с thread-маркерами из ``parser_hints.messenger``.

    Маркеры пузырей/строк диалога калибровки используются как
    substring-маркеры контейнеров чат-листа (формы текстов
    классифицируются общей логикой OLX messenger).
    """
    from aios_core.modules.olx.messenger import ChatListParser

    messenger = load_hints_section(platform_name, "messenger", directory)
    bubbles = _rid_set(messenger, "bubble_markers", nested=True)
    return ChatListParser(markers=tuple(sorted(bubbles)))
