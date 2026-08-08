"""TelegramAPI — минимальный клиент Telegram Bot API (выделен из run_telegram_bot.py).

Polling-режим, JSON + multipart загрузка файлов (фото/документы/голос).
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path


class TelegramAPI:
    """Minimal Telegram Bot API client (polling mode)."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._base = f"https://api.telegram.org/bot{token}"

    def _request(self, method: str, data: dict | None = None) -> dict:
        url = f"{self._base}/{method}"
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())

    def get_updates(self, offset: int = 0) -> list[dict]:
        result = self._request("getUpdates", {"offset": offset, "timeout": 30})
        return result.get("result", [])

    def send_message(self, chat_id: int, text: str, parse_mode: str = "HTML",
                     reply_markup: dict | None = None) -> dict:
        payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._request("sendMessage", payload)

    def edit_message(self, chat_id: int, msg_id: int, text: str,
                     parse_mode: str = "HTML", reply_markup: dict | None = None) -> dict:
        payload: dict = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._request("editMessageText", payload)

    def answer_callback(self, callback_query_id: str, text: str = "") -> dict:
        return self._request("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text})

    def get_file(self, file_id: str) -> dict:
        return self._request("getFile", {"file_id": file_id})

    def download_file_by_id(self, file_id: str, dest: str = "") -> str:
        info = self.get_file(file_id)
        path = info.get("result", {}).get("file_path", "")
        if not path:
            raise ValueError(f"Нет file_path для file_id {file_id}")
        url = f"https://api.telegram.org/file/bot{self._token}/{path}"
        with urllib.request.urlopen(url, timeout=90) as resp:
            data = resp.read()
        if not dest:
            ext = Path(path).suffix or ".jpg"
            dest = f"/tmp/aios_tg_{int(__import__('time').time() * 1000)}{ext}"
        Path(dest).write_bytes(data)
        return dest

    def _multipart(self, method: str, chat_id: int, field: str, file_path: str,
                   caption: str = "") -> dict:
        """Универсальная отправка файла (photo/document)."""
        import mimetypes
        boundary = "----aios" + str(int(__import__('time').time() * 1000))
        content = Path(file_path).read_bytes()

        def _field(name: str, value: str) -> bytes:
            return (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
                    f"{value}\r\n").encode()

        fn = Path(file_path).name
        ct = mimetypes.guess_type(fn)[0] or "application/octet-stream"
        body = b"".join([
            _field("chat_id", str(chat_id)),
            _field("caption", caption[:1000]) if caption else b"",
            (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{fn}\"\r\n"
             f"Content-Type: {ct}\r\n\r\n").encode(),
            content,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self._base}/{method}", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read())

    def send_photo(self, chat_id: int, photo_path: str, caption: str = "") -> dict:
        return self._multipart("sendPhoto", chat_id, "photo", photo_path, caption)

    def send_document(self, chat_id: int, file_path: str, caption: str = "") -> dict:
        return self._multipart("sendDocument", chat_id, "document", file_path, caption)

    def send_voice(self, chat_id: int, voice_path: str, caption: str = "") -> dict:
        return self._multipart("sendVoice", chat_id, "voice", voice_path, caption)
