"""Instagram detail — парсер открытого поста/товара из parser_hints.

Runtime-адаптер над :class:`HintDetailParser`: маркеры цены/продавца/
CTA приходят из секции ``extras.parser_hints.detail`` дескриптора
(``aios platforms calibrate --detail post.xml --write``). До калибровки
парсер работает в shape-режиме (цена по parse_price, заголовок и
описание по форме текстов) — поля seller/cta будут пустыми.
"""

from __future__ import annotations

from typing import Dict, Optional

from aios_core.platforms.runtime_hints import HintDetailParser, load_hints_section

PACKAGE = "com.instagram.android"


class InstagramDetailParser:
    """Парсер детального экрана Instagram-поста.

    Args:
        detail_hints: Секция hints напрямую; None → из дескриптора
            ``platforms/instagram.yaml``.
        directory: Каталог YAML-дескрипторов.
    """

    def __init__(
        self,
        detail_hints: Optional[Dict] = None,
        directory: str = "platforms",
    ):
        if detail_hints is None:
            detail_hints = load_hints_section("instagram", "detail", directory)
        self._parser = HintDetailParser(detail_hints)

    @property
    def configured(self) -> bool:
        """True, если секция detail откалибрована (есть маркеры)."""
        return self._parser.configured

    def parse(self, xml_source) -> Dict[str, object]:
        """{title, price, currency, seller, description, cta_texts, texts_seen}."""
        return self._parser.parse(xml_source)
