"""CalibrationAdvisor — авто-калибровка парсеров новой платформы.

По UIAutomator-дампу экрана поисковой выдачи чужого приложения агент
находит кандидатские маркеры:

* **контейнеры карточек** — resource-id, под которыми повторяются узлы,
  содержащие и цену (по ``parse_price`` из OLX text_utils), и длинный
  текст-заголовок;
* **валютные паттерны** — какие ценовые записи встретились и какие
  валюты распознались;
* **страница без карточек** → пустой результат с подсказкой.

Результат можно влить в дескриптор платформы (``extras.parser_hints``)
командой ``aios platforms calibrate`` — дальше генератор парсера
читает подсказки из каталога.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from aios_core.modules.olx.text_utils import parse_price

_MIN_TITLE_LEN = 10
_DURATION_RE = re.compile(r"^\d{1,2}:\d{2}$")
_VIDEO_RID_MARKERS = ("reel", "video", "clips")
_STORY_RID_MARKERS = ("story", "highlight")


class CalibrationAdvisor:
    """Ищет маркеры карточек/цен в UI-дампе новой платформы."""

    def analyze(self, xml_source: Union[str, Path, ET.Element]) -> Dict[str, object]:
        """Разбирает дамп и возвращает parser_hints.

        Returns:
            {card_markers: [{resource_id, occurrences, sample_titles}],
             prices_seen, currencies, titles_seen, hint}
        """
        root = self._root(xml_source)

        # Все текстовые узлы один раз — сводка по ценам и валютам.
        currencies: Counter = Counter()
        prices_seen = 0
        duration_labels = 0
        video_rids: Counter = Counter()
        story_rids: Counter = Counter()
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip()
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if resource_id:
                if any(m in resource_id for m in _VIDEO_RID_MARKERS):
                    video_rids[resource_id] += 1
                if any(m in resource_id for m in _STORY_RID_MARKERS):
                    story_rids[resource_id] += 1
            if not text:
                continue
            if _DURATION_RE.match(text):
                duration_labels += 1
            parsed = parse_price(text)
            if parsed is not None:
                prices_seen += 1
                currencies[parsed[1]] += 1

        # Считаем по каждому resource-id: сколько контейнеров выглядят
        # карточками (потомок-цена + потомок-заголовок).
        occurrences: Counter = Counter()
        samples: Dict[str, List[str]] = defaultdict(list)
        titles_seen = 0

        for node in root.iter("node"):
            resource_id = node.attrib.get("resource-id") or ""
            if not resource_id:
                continue
            texts = [
                (child.attrib.get("text") or "").strip() for child in node.iter("node")
            ]
            texts = [t for t in texts if t]
            if not texts:
                continue

            card_title: Optional[str] = None
            has_price = False
            for text in texts:
                if parse_price(text) is not None:
                    has_price = True
                elif len(text) >= _MIN_TITLE_LEN and card_title is None:
                    card_title = text

            if has_price and card_title is None and len(texts) >= 2:
                # Цена есть, длинного текста нет — всё равно может быть
                # карточкой: берём любой нечисловой текст как заголовок.
                for text in texts:
                    if parse_price(text) is None and len(text) >= 4:
                        card_title = text
                        break

            if has_price and card_title is not None:
                occurrences[resource_id] += 1
                titles_seen += 1
                if len(samples[resource_id]) < 3:
                    samples[resource_id].append(card_title)

        card_markers = [
            {
                "resource_id": rid,
                "occurrences": count,
                "sample_titles": samples[rid],
            }
            for rid, count in occurrences.most_common(5)
        ]
        return {
            "card_markers": card_markers,
            "prices_seen": prices_seen,
            "currencies": dict(currencies),
            "titles_seen": titles_seen,
            "content_categories": {
                "video_markers": [rid for rid, _ in video_rids.most_common(5)],
                "story_markers": [rid for rid, _ in story_rids.most_common(5)],
                # Reels/клипы помечены тайм-кодами (0:32) — их карточки
                # обычно без цены: отдельный класс контента платформы.
                "duration_labels": duration_labels,
            },
            "hint": (
                "маркеры найдены — запишите в extras.parser_hints"
                if card_markers
                else "карточки не обнаружены: нужен дамп поисковой выдачи "
                "с хотя бы одной ценой"
            ),
        }

    @staticmethod
    def _root(xml_source: Union[str, Path, ET.Element]) -> ET.Element:
        if isinstance(xml_source, ET.Element):
            return xml_source
        text_or_path = str(xml_source)
        if text_or_path.lstrip().startswith("<"):
            return ET.fromstring(text_or_path)
        return ET.parse(text_or_path).getroot()


def hints_to_yaml_doc(platform_name: str, hints: Dict[str, object]) -> str:
    """Фрагмент YAML с parser_hints для ручной вставки в дескриптор."""
    import yaml

    doc = {
        platform_name: {
            "extras": {"parser_hints": hints},
        }
    }
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)


def write_hints_to_descriptor(
    platform_name: str,
    hints: Dict[str, object],
    directory: Union[str, Path] = "platforms",
) -> str:
    """Записывает parser_hints в ``extras`` YAML-дескриптора платформы.

    Общий helper CLI ``platforms calibrate --write`` и E2E-пайплайна
    ``platforms bootup``. Файл пересохраняется целиком (safe_dump).

    Returns:
        Путь к обновлённому YAML-файлу.

    Raises:
        ValueError: Дескриптор ``<directory>/<platform>.yaml`` не найден.
    """
    import yaml

    yaml_path = Path(directory) / f"{platform_name}.yaml"
    if not yaml_path.exists():
        raise ValueError(f"descriptor not found: {yaml_path}")
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    doc.setdefault("extras", {})["parser_hints"] = hints
    yaml_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return str(yaml_path)


# --------------------------------------------------------------------------- #
# DetailCalibrationAdvisor — детальный экран объявления и мессенджер          #
# --------------------------------------------------------------------------- #

_SELLER_ID_MARKERS = ("seller", "user", "avatar", "author", "owner", "profile")
_CTA_TEXT_MARKERS = (
    "написати",
    "повідомлення",
    "зателефонувати",
    "message",
    "chat",
    "write",
    "call",
    "reply",
)
_SEND_MARKERS = ("send", "надіслати", "отправить")
_MIN_DESCRIPTION_LEN = 40


class DetailCalibrationAdvisor:
    """Ищет маркеры детального экрана и мессенджера новой платформы.

    Аналог :class:`CalibrationAdvisor`, но для двух оставшихся экранов
    паттерна OLX ``detail.py``/``messenger.py``: карточка товара с
    продавцом/CTA и диалог с полем ввода/кнопкой отправки/пузырями.
    """

    def analyze_detail(
        self, xml_source: Union[str, Path, ET.Element]
    ) -> Dict[str, object]:
        """Разбирает дамп детального экрана.

        Returns:
            {price_nodes, seller_markers, cta_markers, description_nodes,
             hint} — resource-id кандидатов для detail-парсера платформы.
        """
        root = CalibrationAdvisor._root(xml_source)
        price_nodes: Counter = Counter()
        seller_markers: Counter = Counter()
        cta_markers: List[Dict[str, str]] = []
        description_nodes = 0

        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            text = (node.attrib.get("text") or "").strip()
            desc = (node.attrib.get("content-desc") or "").lower()
            combined = f"{text} {desc}".lower()

            if text and parse_price(text) is not None and resource_id:
                price_nodes[resource_id] += 1
            if resource_id and any(
                marker in resource_id for marker in _SELLER_ID_MARKERS
            ):
                seller_markers[resource_id] += 1
            if len(text) >= _MIN_DESCRIPTION_LEN:
                description_nodes += 1
            if resource_id and any(marker in combined for marker in _CTA_TEXT_MARKERS):
                if len(cta_markers) < 5 and all(
                    m["resource_id"] != resource_id for m in cta_markers
                ):
                    cta_markers.append(
                        {
                            "resource_id": resource_id,
                            "text": text[:60],
                        }
                    )

        found = bool(price_nodes or seller_markers or cta_markers)
        return {
            "price_nodes": [
                {"resource_id": rid, "price_occurrences": count}
                for rid, count in price_nodes.most_common(5)
            ],
            "seller_markers": [rid for rid, _ in seller_markers.most_common(5)],
            "cta_markers": cta_markers,
            "description_nodes": description_nodes,
            "hint": (
                "detail-маркеры найдены"
                if found
                else "детальный экран не распознан: нужен дамп открытого "
                "объявления (цена/продавец/кнопка связи)"
            ),
        }

    def analyze_messenger(
        self, xml_source: Union[str, Path, ET.Element]
    ) -> Dict[str, object]:
        """Разбирает дамп диалога мессенджера.

        Returns:
            {input_classes, send_markers, bubble_markers, hint}
        """
        root = CalibrationAdvisor._root(xml_source)
        input_classes: Counter = Counter()
        send_markers: List[Dict[str, str]] = []
        bubbles: Counter = Counter()

        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            klass = (node.attrib.get("class") or "").strip()
            text = (node.attrib.get("text") or "").strip()
            desc = (node.attrib.get("content-desc") or "").lower()
            combined = f"{resource_id} {desc} {text.lower()}"

            if "edittext" in klass.lower():
                input_classes[klass] += 1
            if any(marker in combined for marker in _SEND_MARKERS):
                if (
                    resource_id
                    and len(send_markers) < 5
                    and all(m["resource_id"] != resource_id for m in send_markers)
                ):
                    send_markers.append(
                        {
                            "resource_id": resource_id,
                            "hint_text": (desc or text)[:60],
                        }
                    )
            if resource_id and text:
                bubbles[resource_id] += 1

        bubble_markers = [
            {"resource_id": rid, "occurrences": count}
            for rid, count in bubbles.most_common(5)
            if count >= 2
        ]
        found = bool(input_classes or send_markers)
        return {
            "input_classes": [cls for cls, _ in input_classes.most_common(3)],
            "send_markers": send_markers,
            "bubble_markers": bubble_markers,
            "hint": (
                "messenger-маркеры найдены"
                if found
                else "диалог не распознан: нужен дамп переписки (поле "
                "ввода/кнопка отправки)"
            ),
        }

    _TAB_BAR_MARKERS = ("tab_bar", "bottom_nav", "navigation_bar", "tabbar")
    _TAB_NODE_MARKERS = ("_tab", "tab_")
    _REELS_MARKERS = ("reel", "clips", "video")

    def analyze_navigation(
        self,
        xml_source,
    ) -> Dict[str, object]:
        """Извлекает navigation-подсказки из дампа домашнего экрана.

        Ищет нижний tab-bar (resource-id ``tab_bar``/``bottom_nav``/...),
        перечисляет вкладки (rid хвосты с ``_tab``/``tab_``, подписи
        text/content-desc) и распознаёт видео-вкладку (reel/clips/video
        в rid или подписи) — результат готов для секции
        ``navigation.reels_tab`` дескриптора (см. ReelsTabDriver).

        Args:
            xml_source: uiautomator-дамп домашнего экрана.

        Returns:
            {reels_tab: {rid_markers, text_markers, bounds?},
             tab_bar_markers, tabs: [{resource_id, label}],
             hint}: reels_tab пуст, если видео-вкладка не найдена
             (честный сигнал оператору — дефолты ReelsTabDriver).
        """
        root = CalibrationAdvisor._root(xml_source)
        tab_bar_markers: List[Dict[str, object]] = []
        tabs: List[Dict[str, object]] = []
        reels_rid: List[Dict[str, object]] = []
        reels_texts: List[str] = []
        reels_bounds: Optional[str] = None

        for node in root.iter("node"):
            resource_id = node.attrib.get("resource-id") or ""
            rid_tail = resource_id.rsplit("/", 1)[-1].lower()
            text = (node.attrib.get("text") or "").strip()
            desc = (node.attrib.get("content-desc") or "").strip()
            bounds = node.attrib.get("bounds")
            if any(m in rid_tail for m in self._TAB_BAR_MARKERS):
                if not any(m["resource_id"] == resource_id for m in tab_bar_markers):
                    tab_bar_markers.append({"resource_id": resource_id})
            is_tab = (
                bool(rid_tail) and any(m in rid_tail for m in self._TAB_NODE_MARKERS)
            ) or (desc.lower() in ("home", "search", "reels", "clips", "video"))
            if not is_tab or bounds is None:
                continue
            label = desc or text
            tabs.append(
                {
                    "resource_id": resource_id,
                    "label": label,
                    "bounds": bounds,
                }
            )
            combined = f"{rid_tail} {text.lower()} {desc.lower()}"
            if any(m in combined for m in self._REELS_MARKERS):
                if resource_id and not any(
                    m["resource_id"] == resource_id for m in reels_rid
                ):
                    reels_rid.append({"resource_id": resource_id})
                if label and label.lower() not in (t.lower() for t in reels_texts):
                    reels_texts.append(label)
                if reels_bounds is None:
                    reels_bounds = bounds

        reels_tab: Dict[str, object] = {}
        if reels_rid:
            reels_tab["rid_markers"] = reels_rid
        if reels_texts:
            reels_tab["text_markers"] = reels_texts
        if reels_bounds:
            reels_tab["bounds"] = reels_bounds
        return {
            "reels_tab": reels_tab,
            "tab_bar_markers": tab_bar_markers,
            "tabs": tabs,
            "hint": (
                "видео-вкладка найдена"
                if reels_tab
                else (
                    "tab-bar есть, видео-вкладка не распознана"
                    if tab_bar_markers
                    else "tab-bar не найден: нужен дамп домашнего экрана"
                )
            ),
        }


def merge_hints(
    card_hints: Dict[str, object],
    detail: Optional[Dict[str, object]] = None,
    messenger: Optional[Dict[str, object]] = None,
    navigation: Optional[Dict[str, object]] = None,
    content_categories: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Объединяет подсказки калибровки всех экранов в один документ.

    Итог (ключи ``detail``/``messenger``/``navigation`` добавляются
    только при наличии) кладётся в ``extras.parser_hints`` дескриптора
    платформы.
    """
    merged = dict(card_hints or {})
    if detail:
        merged["detail"] = detail
    if messenger:
        merged["messenger"] = messenger
    if navigation:
        merged["navigation"] = navigation
    if content_categories:
        merged["content_categories"] = content_categories
    return merged
