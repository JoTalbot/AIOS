"""AIOS OLX Android Agent — personal chats: reading and guarded replies.

Reads the chat list and open conversations from UIAutomator dumps and sends
replies through ADB. Sending is *guarded*: replies are enqueued into the
outbox first and only reach the device with an explicit ``auto_send=True``
(or per-call confirmation), so nothing goes out silently.

Note: typing Cyrillic text on a real device requires an IME that accepts
``adb shell input text`` (e.g. ADBKeyBoard); without it only ASCII sends are
reliable. Coordinate-based flows need one-time calibration per app version.
"""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .adb import ADBController
from .text_utils import normalize_text

_CHAT_MARKERS = ("chatitem", "conversationitem", "chat_item", "chatroot")
_MESSAGE_MARKERS = ("message", "bubble")
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
_UNREAD_RE = re.compile(r"^\d{1,3}$")
_DATE_HINT_RE = re.compile(
    r"(сьогодні|сегодня|вчора|вчера|\d{1,2}\s+[а-яіїєґ]+)", re.IGNORECASE
)
_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")

_AVAILABILITY_RE = re.compile(
    r"(актуальн|є в наявності|в наличии|ще прода|еще прода|доступн)",
    re.IGNORECASE,
)
_BARGAIN_RE = re.compile(
    r"(віддасте|отдадите|задешево|подешевле|торг|знижк|скидк|останн. ціна|крайня ціна)",
    re.IGNORECASE,
)
_MEETING_RE = re.compile(
    r"(зустріч|встреч|подивитись|посмотреть|огляд|переглянуть|доставк|отправк|відправ)",
    re.IGNORECASE,
)
_PRICE_NUM_RE = re.compile(r"(\d[\d\s]{1,9})")
_GREETING_RE = re.compile(r"(добрий|добрый|вітаю|привіт|здравств|hello)", re.IGNORECASE)


def _parse_bounds(raw: str | None) -> tuple[int, int, int, int] | None:
    if not raw:
        return None
    match = _BOUNDS_RE.search(raw)
    if not match:
        return None
    return tuple(int(value) for value in match.groups())


@dataclass
class ChatThread:
    """One row of the OLX chat list."""

    interlocutor: str
    ad_title: str | None = None
    snippet: str = ""
    unread_count: int = 0
    updated_text: str | None = None
    tap_center: tuple[int, int] | None = None

    @property
    def key(self) -> str:
        """Execute key."""
        base = "|".join(
            [
                (self.interlocutor or "").strip().lower(),
                (self.ad_title or "").strip().lower(),
            ]
        )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "key": self.key,
            "interlocutor": self.interlocutor,
            "ad_title": self.ad_title,
            "snippet": self.snippet,
            "unread_count": self.unread_count,
            "updated_text": self.updated_text,
        }


@dataclass
class Message:
    """One message bubble; ``author`` is ``me`` or ``them``."""

    author: str
    text: str
    ts_text: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {"author": self.author, "text": self.text, "ts_text": self.ts_text}


class ChatListParser:
    """Parses the chat list screen into :class:`ChatThread` rows.

    ``markers`` — substring-маркеры resource-id контейнера чата;
    по умолчанию OLX-маркеры. Платформы (Instagram и далее) передают
    свои — из ``parser_hints.messenger`` калибровки (bubble/thread
    resource-id), форма текстов классифицируется общей логикой.
    """

    def __init__(self, markers: tuple[str, ...] = _CHAT_MARKERS):
        """Initialize ChatListParser."""
        self.markers = tuple(m.lower() for m in markers) or _CHAT_MARKERS

    def parse(self, xml_source: str | Path | ET.Element) -> list[ChatThread]:
        """Execute parse."""
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            root = (
                ET.fromstring(text_or_path)
                if text_or_path.lstrip().startswith("<")
                else ET.parse(text_or_path).getroot()
            )

        threads: list[ChatThread] = []
        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if not any(marker in resource_id for marker in self.markers):
                continue
            texts: list[str] = []
            for child in node.iter():
                text = normalize_text(child.attrib.get("text"))
                if text:
                    texts.append(text)
            thread = self.thread_from_texts(texts)
            if thread is not None:
                bounds = _parse_bounds(node.attrib.get("bounds"))
                if bounds:
                    x1, y1, x2, y2 = bounds
                    thread.tap_center = ((x1 + x2) // 2, (y1 + y2) // 2)
                threads.append(thread)
        return threads

    @staticmethod
    def thread_from_texts(texts: list[str]) -> ChatThread | None:
        """Execute thread from texts."""
        if not texts:
            return None
        unread = 0
        updated: str | None = None
        content: list[str] = []
        for raw in texts:
            if _TIME_RE.match(raw) or _DATE_HINT_RE.search(raw):
                updated = updated or raw
                continue
            if _UNREAD_RE.match(raw) and len(content) > 0:
                unread = int(raw)
                continue
            content.append(raw)
        if not content:
            return None
        return ChatThread(
            interlocutor=content[0],
            ad_title=content[1] if len(content) > 2 else None,
            snippet=content[-1] if len(content) > 1 else "",
            unread_count=unread,
            updated_text=updated,
        )


class ChatViewParser:
    """Parses an open conversation; direction is inferred from alignment."""

    def __init__(self, screen_width: int = 1080, me_side_ratio: float = 0.6):
        """Initialize ChatViewParser."""
        self.screen_width = screen_width
        self.me_side_ratio = me_side_ratio

    def parse(self, xml_source: str | Path | ET.Element) -> list[Message]:
        """Execute parse."""
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            root = (
                ET.fromstring(text_or_path)
                if text_or_path.lstrip().startswith("<")
                else ET.parse(text_or_path).getroot()
            )

        elements: list[tuple[str, tuple[int, int, int, int] | None]] = []
        for node in root.iter("node"):
            text = normalize_text(node.attrib.get("text"))
            if not text:
                continue
            resource_id = (node.attrib.get("resource-id") or "").lower()
            bounds = _parse_bounds(node.attrib.get("bounds"))
            elements.append((text, bounds, resource_id))
        return self.messages_from_elements(elements)

    def messages_from_elements(self, elements) -> list[Message]:
        """Classify ``(text, bounds[, resource_id])`` tuples into messages."""
        messages: list[Message] = []
        pending_ts: str | None = None
        for element in elements:
            text, bounds = element[0], element[1]
            if _TIME_RE.match(text):
                pending_ts = text
                continue
            author = "them"
            if bounds is not None:
                x1, _y1, x2, _y2 = bounds
                center = (x1 + x2) / 2
                if center >= self.screen_width * self.me_side_ratio:
                    author = "me"
            messages.append(Message(author=author, text=text, ts_text=pending_ts))
            pending_ts = None
        return messages


class ReplySuggester:
    """Rule-based reply drafts for common buyer intents (uk locale)."""

    def __init__(self, min_price_ratio: float = 0.85):
        """Initialize ReplySuggester."""
        self.min_price_ratio = min_price_ratio

    def suggest(
        self,
        messages: list[Message],
        my_price: float | None = None,
        title: str | None = None,
        city: str | None = None,
    ) -> str | None:
        """Draft a reply to the last incoming message (None = no reply needed)."""
        incoming = [message for message in messages if message.author == "them"]
        if not incoming:
            return None
        if messages and messages[-1].author == "me":
            return None  # we already replied
        last = incoming[-1].text

        item = f"«{title}»" if title else "оголошення"
        if _AVAILABILITY_RE.search(last):
            return f"Добрий день! Так, {item} ще актуальне. Коли зручно подивитись?"
        if _BARGAIN_RE.search(last) or self._looks_like_offer(last, my_price):
            return self._bargain_reply(last, my_price, item)
        if _MEETING_RE.search(last):
            place = f" ({city})" if city else ""
            return (
                f"Можна подивитись{place}. Пропоную будній вечір або вихідні — "
                "напишіть, будь ласка, коли вам зручно."
            )
        if _GREETING_RE.search(last):
            return (
                f"Добрий день! Дякую за інтерес до {item}. "
                "З радістю відповім на запитання."
            )
        return "Добрий день! Дякую за повідомлення. Що саме вас цікавить?"

    def _looks_like_offer(self, text: str, my_price: float | None) -> bool:
        return my_price is not None and self._extract_offer(text) is not None

    @staticmethod
    def _extract_offer(text: str) -> float | None:
        numbers = _PRICE_NUM_RE.findall(text)
        values = [float(num.replace(" ", "")) for num in numbers]
        values = [value for value in values if value >= 100]
        return max(values) if values else None

    def _bargain_reply(self, last: str, my_price: float | None, item: str) -> str:
        offer = self._extract_offer(last)
        if my_price is None:
            return f"По {item} можливий невеликий торг при огляді."
        if offer is not None and offer >= my_price * self.min_price_ratio:
            return f"Добре, домовились за {int(offer)} грн. Коли зручно забрати товар?"
        counter = round(my_price * 0.95)
        if offer is not None:
            return (
                f"За {int(offer)} грн, на жаль, не вийде. "
                f"Мінімальна ціна {int(counter)} грн — можемо зустрітись посередині?"
            )
        return (
            f"По {item} можливий невеликий торг. "
            f"Орієнтовно готовий(-а) віддати за {int(counter)} грн."
        )


class OLXMessenger:
    """ADB driver for the OLX messenger with a guarded outbox."""

    def __init__(
        self,
        adb: ADBController | None = None,
        storage=None,
        suggester: ReplySuggester | None = None,
        screen_width: int = 1080,
    ):
        """Initialize OLXMessenger."""
        self.adb = adb or ADBController()
        self.storage = storage
        self.suggester = suggester or ReplySuggester()
        self.screen_width = screen_width

    def open_chats(self) -> dict[str, object]:
        """Open the chats tab of the OLX app."""
        return self.adb.run(
            'adb shell am start -a android.intent.action.VIEW -d "https://www.olx.ua/myaccount/messages/"'
        )

    def list_chats(self, dump_path: str = "chats.xml") -> list[ChatThread]:
        """Execute list chats."""
        import os
        import tempfile

        with tempfile.TemporaryDirectory(prefix="aios_olx_chats_") as tmp:
            path = os.path.join(tmp, dump_path)
            self.adb.dump_ui(path)
            if not os.path.exists(path):
                return []
            return ChatListParser().parse(path)

    def read_chat(
        self, thread: ChatThread, dump_path: str = "chat.xml"
    ) -> list[Message]:
        """Execute read chat."""
        import os
        import tempfile

        if thread.tap_center:
            x, y = thread.tap_center
            self.adb.run(f"adb shell input tap {x} {y}")
        with tempfile.TemporaryDirectory(prefix="aios_olx_chat_") as tmp:
            path = os.path.join(tmp, dump_path)
            self.adb.dump_ui(path)
            if not os.path.exists(path):
                return []
            return ChatViewParser(screen_width=self.screen_width).parse(path)

    def send_reply(
        self,
        chat_key: str,
        text: str,
        interlocutor: str | None = None,
        auto_send: bool = False,
    ) -> dict[str, object]:
        """Queue a reply; only sends to the device with ``auto_send=True``."""
        if not text.strip():
            return {"status": "error", "error": "empty text"}
        if not auto_send:
            outbox_id = None
            if self.storage is not None:
                outbox_id = self.storage.enqueue_outbox(
                    chat_key, text, interlocutor=interlocutor
                )
            return {"status": "queued", "outbox_id": outbox_id, "text": text}
        result = self._type_and_send(text)
        if self.storage is not None:
            outbox_id = self.storage.enqueue_outbox(
                chat_key, text, interlocutor=interlocutor
            )
            self.storage.outbox_mark(
                outbox_id,
                "sent" if result.get("code") == 0 else "failed",
                result=str(result.get("stderr") or "")[:500],
            )
            return {"status": "sent", "outbox_id": outbox_id, "adb": result}
        return {"status": "sent", "adb": result}

    def flush_outbox(self) -> list[dict[str, object]]:
        """Send every pending outbox entry; returns per-entry results."""
        results: list[dict[str, object]] = []
        if self.storage is None:
            return results
        for item in self.storage.outbox_pending():
            result = self._type_and_send(item["text"])
            ok = result.get("code") == 0
            self.storage.outbox_mark(
                item["id"],
                "sent" if ok else "failed",
                result=str(result.get("stderr") or "")[:500],
            )
            results.append({"id": item["id"], "status": "sent" if ok else "failed"})
        return results

    def _type_and_send(self, text: str) -> dict[str, object]:
        escaped = text.replace("'", r"\'").replace('"', r"\"").replace(" ", "%s")
        type_result = self.adb.run(f"adb shell input text '{escaped}'")
        if type_result.get("code") != 0:
            return type_result
        # Enter sends the message in OLX chat when the keyboard action key is SEND.
        return self.adb.run("adb shell input keyevent 66")
