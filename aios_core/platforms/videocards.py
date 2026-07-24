"""VideoCards — экстрактор видео-карточек (Reels/клипы) из UI-дампов.

Продуктовые карточки распознаются по цене; видео-контент (Instagram
Reels и аналоги) цены не имеет — его «поля карточки» это тайм-код,
просмотры/лайки и подпись. Экстрактор зеркалит контракт CardParser:
контейнеры находятся по video-маркерам (из
``content_categories.video_markers`` калибровки или дефолтным reel/
video/clips), поля классифицируются по форме текстов — платформенного
кода снова нет.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from aios_core.modules.olx.text_utils import normalize_text

_DURATION_RE = re.compile(r"^\d{1,2}:\d{2}$")
# «1 234 перегляди» / «56 вподобань» / «12 comments» / «7 likes»
_COUNT_RE = re.compile(
    r"^(\d[\d\s\u00a0,.]*)\s*"
    r"(перегляд\w*|просмотр\w*|views?|вподобан\w*|лайк\w*|likes?)$",
    re.IGNORECASE,
)
_DEFAULT_MARKERS = ("reel", "video", "clips")
_VIEWS_KEYS = ("перегляд", "просмотр", "view")


@dataclass
class VideoCard:
    """Одна видео-карточка ленты (Reels/клипы)."""

    title: str
    duration: str | None = None
    views: int | None = None
    likes: int | None = None
    marker: str | None = None
    query: str | None = None
    raw_texts: tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        """Execute fingerprint."""
        base = f"video:{(self.title or '').strip().lower()}|{self.duration or ''}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "duration": self.duration,
            "views": self.views,
            "likes": self.likes,
            "marker": self.marker,
            "query": self.query,
        }


def parse_counter_text(text: str) -> tuple[str, int] | None:
    """«1 234 перегляди» → ("views", 1234); «56 лайків» → ("likes", 56)."""
    match = _COUNT_RE.match(text.strip())
    if not match:
        return None
    number = int(re.sub(r"[^\d]", "", match.group(1)))
    unit = match.group(2).lower()
    kind = "views" if any(k in unit for k in _VIEWS_KEYS) else "likes"
    return kind, number


class HintVideoParser:
    """Парсер видео-карточек по video-маркерам hints/дефолту.

    Args:
        video_markers: substring-маркеры resource-id контейнера
            (из ``content_categories.video_markers`` калибровки или
            секции hints); None → дефолт reel/video/clips.
    """

    def __init__(self, video_markers: list[str] | None = None):
        """Initialize HintVideoParser."""
        markers = video_markers or list(_DEFAULT_MARKERS)
        self.markers = (
            tuple(str(m).rsplit("/", 1)[-1].lower() for m in markers if m)
            or _DEFAULT_MARKERS
        )

    def parse(
        self,
        xml_source: str | Path | ET.Element,
        query: str | None = None,
    ) -> list[VideoCard]:
        """Разбирает дамп ленты на видео-карточки (хотя бы тайм-код/текст)."""
        from aios_core.platforms.calibrate import CalibrationAdvisor

        root = CalibrationAdvisor._root(xml_source)
        cards: list[VideoCard] = []
        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if not any(marker in resource_id for marker in self.markers):
                continue
            texts = [normalize_text(child.attrib.get("text")) for child in node.iter()]
            texts = [t for t in texts if t]
            if not texts:
                continue
            card = self.card_from_texts(
                texts,
                marker=resource_id,
                query=query,
            )
            if card is not None:
                cards.append(card)
        return cards

    @staticmethod
    def card_from_texts(
        texts: list[str],
        marker: str | None = None,
        query: str | None = None,
    ) -> VideoCard | None:
        """Классификация текстов карточки: тайм-код/счётчики/подпись."""
        duration: str | None = None
        views: int | None = None
        likes: int | None = None
        leftovers: list[str] = []

        for raw in texts:
            if duration is None and _DURATION_RE.match(raw):
                duration = raw
                continue
            counter = parse_counter_text(raw)
            if counter is not None:
                kind, number = counter
                if kind == "views" and views is None:
                    views = number
                elif kind == "likes" and likes is None:
                    likes = number
                else:
                    continue
                continue
            if raw not in leftovers:
                leftovers.append(raw)

        title = leftovers[0] if leftovers else ""
        if not title and duration is None:
            return None  # ни подписи, ни признака видео — не карточка
        return VideoCard(
            title=title,
            duration=duration,
            views=views,
            likes=likes,
            marker=marker,
            query=query,
            raw_texts=tuple(texts),
        )


def video_parser_for(platform_name: str, directory="platforms") -> HintVideoParser:
    """HintVideoParser из ``content_categories.video_markers`` дескриптора."""
    from aios_core.platforms.runtime_hints import load_hints_section

    categories = load_hints_section(
        platform_name,
        "content_categories",
        directory,
    )
    return HintVideoParser(categories.get("video_markers") or None)
