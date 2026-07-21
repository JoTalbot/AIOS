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

import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from aios_core.modules.olx.text_utils import parse_price

_MIN_TITLE_LEN = 10


class CalibrationAdvisor:
    """Ищет маркеры карточек/цен в UI-дампе новой платформы."""

    def analyze(
        self, xml_source: Union[str, Path, ET.Element]
    ) -> Dict[str, object]:
        """Разбирает дамп и возвращает parser_hints.

        Returns:
            {card_markers: [{resource_id, occurrences, sample_titles}],
             prices_seen, currencies, titles_seen, hint}
        """
        root = self._root(xml_source)

        # Все текстовые узлы один раз — сводка по ценам и валютам.
        currencies: Counter = Counter()
        prices_seen = 0
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip()
            if not text:
                continue
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
                (child.attrib.get("text") or "").strip()
                for child in node.iter("node")
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


def hints_to_yaml_doc(
    platform_name: str, hints: Dict[str, object]
) -> str:
    """Фрагмент YAML с parser_hints для ручной вставки в дескриптор."""
    import yaml

    doc = {
        platform_name: {
            "extras": {"parser_hints": hints},
        }
    }
    return yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
