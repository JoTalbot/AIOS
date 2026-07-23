"""Instagram own-posts — свои посты: парсер профиля + guarded-публикация.

Аналог OLX own_ads/promotion для Instagram: снапшот собственных постов
(счётчики лайков/комментариев/просмотров → ``OwnAdsTracker``/застой —
transition через ``to_own_ad()``) и публикация нового поста.

Публикация — по философии guarded-actions: **DRY-RUN по умолчанию**
(точный план шагов без касания устройства), реальный прогон только с
``confirm=True``. Навигация текстовая (подписи кнопок Next/Share),
без координатных констант; при дрейфе верстки — честная ошибка шага.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.messenger import _parse_bounds
from aios_core.modules.olx.own_ads import OwnAd
from aios_core.modules.olx.text_utils import normalize_text
from aios_core.platforms.videocards import parse_counter_text

PACKAGE = "com.instagram.android"
MEDIA_REMOTE = "/sdcard/aios_post_input"
CREATE_DEEP_LINK = "instagram://library"

NEXT_LABELS = ("next", "далі", "дальше", "continue")
SHARE_LABELS = ("share", "поділитися", "поделиться", "опублікувати", "опубликовать")
_COMMENT_RE = re.compile(
    r"^(\d[\d\s\u00a0,.]*)\s*(коментар\w*|comments?)$", re.IGNORECASE
)

#: Дефолтные маркеры ячеек сетки профиля (после калибровки — из hints).
DEFAULT_GRID_MARKERS = ("row_profile", "grid_item", "profile_media")


def _parse_comment_counter(text: str) -> Optional[int]:
    match = _COMMENT_RE.match(text.strip())
    if not match:
        return None
    return int(re.sub(r"[^\d]", "", match.group(1)))


@dataclass
class OwnPost:
    """Свой пост Instagram со счётчиками."""

    caption: str
    likes: int = 0
    comments: int = 0
    views: int = 0
    post_id: Optional[str] = None
    posted_text: Optional[str] = None

    @property
    def fingerprint(self) -> str:
        if self.post_id:
            base = f"own:ig:id:{self.post_id.strip().lower()}"
        else:
            base = f"own:ig:{(self.caption or '').strip().lower()[:80]}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]

    def to_own_ad(self) -> OwnAd:
        """Маппинг в OwnAd для общего OwnAdsTracker/застой-контура."""
        return OwnAd(
            title=(self.caption or "")[:120],
            price=None,
            currency=None,
            views=self.views,
            favorites=self.likes,
            messages=self.comments,
            status="active",
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "fingerprint": self.fingerprint,
            "caption": self.caption,
            "likes": self.likes,
            "comments": self.comments,
            "views": self.views,
            "post_id": self.post_id,
            "posted_text": self.posted_text,
        }


class OwnPostsParser:
    """Парсер сетки/постов своего профиля Instagram.

    Args:
        markers: substring-маркеры resource-id контейнера поста
            (после калибровки — из hints секции ``own_grid``); дефолт
            ``DEFAULT_GRID_MARKERS``.
    """

    def __init__(self, markers: Optional[Tuple[str, ...]] = None):
        self.markers = tuple(m.lower() for m in (markers or DEFAULT_GRID_MARKERS))

    def parse(self, xml_source: Union[str, Path, ET.Element]) -> List[OwnPost]:
        from aios_core.platforms.calibrate import CalibrationAdvisor

        root = CalibrationAdvisor._root(xml_source)
        posts: List[OwnPost] = []
        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if not any(m in resource_id for m in self.markers):
                continue
            texts = [normalize_text(child.attrib.get("text")) for child in node.iter()]
            texts = [t for t in texts if t]
            if not texts:
                continue
            post = self.post_from_texts(texts)
            if post is not None:
                posts.append(post)
        return posts

    @staticmethod
    def post_from_texts(texts: List[str]) -> Optional[OwnPost]:
        """Классификация текстов ячейки: счётчики/подпись поста."""
        likes = comments = views = 0
        leftovers: List[str] = []
        for raw in texts:
            counter = parse_counter_text(raw)
            if counter is not None:
                kind, number = counter
                if kind == "views":
                    views = views or number
                else:
                    likes = likes or number
                continue
            comment_count = _parse_comment_counter(raw)
            if comment_count is not None:
                comments = comments or comment_count
                continue
            if raw not in leftovers:
                leftovers.append(raw)
        if not leftovers:
            return None
        return OwnPost(
            caption=leftovers[0],
            likes=likes,
            comments=comments,
            views=views,
            posted_text=leftovers[1] if len(leftovers) > 1 else None,
        )


class PostComposer:
    """Guarded-публикация поста Instagram (DRY-RUN по умолчанию).

    Args:
        adb: ADBController (с serial-привязкой профиля).
        wait_s: Паузы между этапами публикации.
    """

    def __init__(self, adb: Optional[ADBController] = None, wait_s: float = 6.0):
        self.adb = adb or ADBController(package=PACKAGE)
        self.wait_s = wait_s

    def publish_plan(self, image_path: str, caption: str) -> List[str]:
        """План шагов публикации (какой экран, что нажимаем)."""
        return [
            f"push {image_path} -> {MEDIA_REMOTE}",
            f"open {CREATE_DEEP_LINK} (create flow)",
            f"tap text in {NEXT_LABELS}",
            f"input caption ({len(caption)} chars) via ADBKeyBoard",
            f"tap text in {SHARE_LABELS}",
        ]

    def publish(
        self,
        image_path: str,
        caption: str,
        confirm: bool = False,
        directory: str = "platforms",
    ) -> Dict[str, object]:
        """Публикует пост. Без ``confirm`` — только DRY-RUN план.

        Даже с ``confirm=True`` публикация проходит compliance-контур
        платформы (``extras.compliance.autopost_allowed`` в дескрипторе):
        запрещённый автопостинг честно отклоняется — guarded не только
        технически, но и правово.

        Raises:
            ValueError: пустой caption/несуществующий image при confirm.
        """
        if not caption.strip():
            raise ValueError("empty caption")
        if confirm and not Path(image_path).exists():
            raise ValueError(f"image not found: {image_path}")
        plan = self.publish_plan(image_path, caption)
        if not confirm:
            return {
                "status": "dry-run",
                "plan": plan,
                "note": "nothing touched the device; " "pass confirm=True to execute",
            }

        from aios_core.platforms.compliance import compliance_guard

        check = compliance_guard("instagram", "autopost", directory=directory)
        if not check["allowed"]:
            return {
                "status": "denied",
                "plan": plan,
                "error": check["reason"],
                "compliance": check,
                "note": "publish refused by extras.compliance — " "device untouched",
            }

        steps: List[Dict[str, object]] = []
        ext = Path(image_path).suffix or ".jpg"
        remote = f"{MEDIA_REMOTE}{ext}"
        pushed = self.adb.run(f"{self.adb.adb} push '{image_path}' {remote}")
        steps.append({"action": "push", "code": pushed.get("code")})
        if pushed.get("code") != 0:
            return {"status": "error", "error": "push failed", "steps": steps}

        opened = self.adb.run(
            f"{self.adb.adb} shell am start "
            f'-a android.intent.action.VIEW -d "{CREATE_DEEP_LINK}"'
        )
        steps.append({"action": "open_create", "code": opened.get("code")})
        time.sleep(self.wait_s)

        if not self._tap_text(NEXT_LABELS):
            return {
                "status": "error",
                "error": "next button not found — layout drift, " "recalibrate labels",
                "steps": steps,
            }
        steps.append({"action": "tap_next", "code": 0})
        time.sleep(self.wait_s / 2)

        typed = self.adb.input_text(caption)
        steps.append({"action": "input_caption", "code": typed.get("code")})
        time.sleep(self.wait_s / 4)

        if not self._tap_text(SHARE_LABELS):
            return {
                "status": "error",
                "error": "share button not found — layout drift",
                "steps": steps,
            }
        steps.append({"action": "tap_share", "code": 0})
        return {"status": "published", "steps": steps}

    def _tap_text(self, labels: Tuple[str, ...]) -> bool:
        """Тап по центру первого узла с текстом-подписью из labels."""
        with tempfile.TemporaryDirectory(prefix="aios-ig-post-") as tmp:
            target = Path(tmp) / "screen.xml"
            result = self.adb.dump_ui(str(target))
            if result.get("code") != 0 or not target.exists():
                return False
            root = ET.parse(target).getroot()
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip().lower()
            if text not in labels:
                continue
            bounds = _parse_bounds(node.attrib.get("bounds"))
            if bounds is None:
                continue
            self.adb.tap((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
            return True
        return False
