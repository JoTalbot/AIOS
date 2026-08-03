#!/usr/bin/env python3
"""
Viber Desktop control — автоматизация десктоп-приложения Viber
(работает под Xvfb :1, окно "Rakuten Viber") через xdotool + tesseract OCR.

Команды (вызываются из run_account_control.py):
  viber chats          — список чатов (OCR левой панели)
  viber read <chat>    — прочитать последние сообщения чата
  viber send <chat> <text> [--confirm] — отправить сообщение

Примечание: автоматизация нативный-окна хрупкая; работает через
координатный клик по распознанному тексту.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

DISPLAY = os.environ.get("VIBER_DISPLAY", ":1")
WINDOW_TITLE = "Rakuten Viber"
SHOTS = Path("/tmp")
LOCK_FILE = Path("/tmp/aios_viber_desktop.lock")
_UI_NOISE = {
    "viber", "rakuten", "поиск", "search", "чаты", "чат", "звонки", "вызовы",
    "контакты", "настройки", "избранное", "недавние", "сообщения", "more", "settings",
}


@contextmanager
def _ui_lock():
    """Не давать нескольким процессам одновременно кликать по Viber UI."""
    LOCK_FILE.touch(exist_ok=True)
    with LOCK_FILE.open("a+", encoding="utf-8") as lock:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except Exception:
            pass
        try:
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass


def _serialized(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with _ui_lock():
            return func(*args, **kwargs)
    return wrapper


def _run(cmd, timeout=20):
    env = dict(os.environ, DISPLAY=DISPLAY)
    env.setdefault("XAUTHORITY", "/root/.Xauthority")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.stdout, r.stderr
    except Exception as e:
        return "", str(e)


def win_id() -> str | None:
    out, _ = _run(["xdotool", "search", "--name", WINDOW_TITLE])
    ids = [x.strip() for x in out.split() if x.strip()]
    return ids[-1] if ids else None


def _shot(name: str) -> str:
    path = SHOTS / f"viber_{name}_{int(time.time() * 1000)}.png"
    _run(["scrot", "-o", str(path)])
    return str(path)


def _ocr(path: str) -> list[dict]:
    out, _ = _run(["tesseract", path, "-", "tsv"])
    words = []
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        txt = parts[11].strip()
        if not txt:
            continue
        try:
            conf = float(parts[10])
            x0, y0, w, h = int(parts[6]), int(parts[7]), int(parts[8]), int(parts[9])
        except ValueError:
            continue
        if conf >= 40:
            words.append({"text": txt, "x0": x0, "y0": y0, "w": w, "h": h,
                          "cx": x0 + w // 2, "cy": y0 + h // 2, "conf": conf})
    return words


def _find_phrase(words: list[dict], phrase: str, region: tuple | None = None):
    """Найти фразу (несколько слов) среди OCR-слов; вернуть центр."""
    q = phrase.lower().split()
    best = None
    for i, w in enumerate(words):
        if w["text"].lower() != q[0]:
            continue
        # собрать последовательность слов слева направо
        chain = [w]
        for j in range(1, len(q)):
            nxt = None
            for k in range(len(words)):
                o = words[k]
                if o["y0"] == w["y0"] and o["x0"] >= chain[-1]["x0"] + chain[-1]["w"] - 5 \
                        and o["x0"] < chain[-1]["x0"] + 200:
                    if o["text"].lower() == q[j]:
                        nxt = o
                        break
            if not nxt:
                break
            chain.append(nxt)
        if len(chain) >= len(q):
            cx = sum(c["cx"] for c in chain) // len(chain)
            cy = chain[0]["cy"]
            if region and not (region[0] <= cx <= region[2] and region[1] <= cy <= region[3]):
                continue
            return cx, cy
    return None


def _click(x: int, y: int) -> None:
    _run(["xdotool", "mousemove", str(x), str(y)])
    time.sleep(0.2)
    _run(["xdotool", "click", "1"])
    time.sleep(0.3)


def _type_text(text: str) -> None:
    _run(["xdotool", "type", "--delay", "30", text])
    time.sleep(0.3)


def _key(key: str) -> None:
    _run(["xdotool", "key", key])


def _activate() -> str | None:
    wid = win_id()
    if not wid:
        return None
    _run(["xdotool", "windowactivate", wid])
    _run(["xdotool", "windowraise", wid])
    time.sleep(0.8)
    return wid


# --------------------------------------------------------------- public


def status() -> dict:
    """Read-only проверка, что Viber Desktop доступен на VNC-дисплее."""
    wid = win_id()
    return {
        "status": "ok" if wid else "error",
        "ready": bool(wid),
        "display": DISPLAY,
        "error": "Окно Viber не найдено" if not wid else "",
    }


@_serialized
def chats() -> dict:
    wid = _activate()
    if not wid:
        return {"status": "error", "error": "Окно Viber не найдено (запущен ли Viber?)"}
    path = _shot("chats")
    words = _ocr(path)
    # левая панель чатов (примерно 1/3 ширины)
    seen = []
    added = set()
    for w in sorted(words, key=lambda x: (x["y0"], x["x0"])):
        if w["cx"] > 640:
            continue
        # чаты — строки с большим шрифтом; берём слова как имена (капитализированные)
        name = w["text"].strip()
        if len(name) < 2 or name.casefold() in _UI_NOISE or name in added:
            continue
        # Служебные одиночные цифры обычно являются временем/счётчиком, а не именем.
        if name.isdigit():
            continue
        added.add(name)
        seen.append({"name": name, "x": w["cx"], "y": w["cy"]})
    return {"status": "ok", "chats": seen[:20], "screenshot": path}


@_serialized
def read_chat(chat: str, limit: int = 15) -> dict:
    wid = _activate()
    if not wid:
        return {"status": "error", "error": "Окно Viber не найдено"}
    path = _shot("read_before")
    words = _ocr(path)
    pos = _find_phrase(words, chat, region=(0, 0, 640, 1080))
    if not pos:
        # ищем одиночное слово (имя может быть одним словом)
        for w in words:
            if w["text"].lower() == chat.lower() and w["cx"] < 640:
                pos = (w["cx"], w["cy"])
                break
    if not pos:
        return {"status": "error", "error": f"Чат «{chat}» не найден в списке",
                "screenshot": path}
    _click(pos[0], pos[1])
    time.sleep(1.5)
    path2 = _shot("read")
    words2 = _ocr(path2)
    # сообщения — правая область (x > 640), выводим строки
    lines = {}
    for w in words2:
        if w["cx"] < 640:
            continue
        key = w["y0"] // 25  # группировка по строкам
        lines.setdefault(key, []).append((w["x0"], w["text"]))
    msgs = []
    for key in sorted(lines):
        row_words = sorted(lines[key])
        row = " ".join(t for _, t in row_words)
        if len(row) > 1:
            # В Viber входящие пузыри находятся слева, исходящие — справа.
            # Это эвристика для автоответа; при сомнении считаем сообщение входящим.
            avg_x = sum(x for x, _ in row_words) / len(row_words)
            msgs.append({"text": row, "mine": avg_x >= 1260})
    return {"status": "ok", "chat": chat, "messages": msgs[-limit:],
            "screenshot": path2}


@_serialized
def send_chat(chat: str, text: str, confirm: bool) -> dict:
    wid = _activate()
    if not wid:
        return {"status": "error", "error": "Окно Viber не найдено"}
    if not confirm:
        return {"status": "need_confirm", "action": "viber_send", "chat": chat,
                "text": text[:200]}
    path = _shot("send_before")
    words = _ocr(path)
    pos = _find_phrase(words, chat, region=(0, 0, 640, 1080))
    if not pos:
        for w in words:
            if w["text"].lower() == chat.lower() and w["cx"] < 640:
                pos = (w["cx"], w["cy"])
                break
    if not pos:
        return {"status": "error", "error": f"Чат «{chat}» не найден"}
    _click(pos[0], pos[1])
    time.sleep(1.2)
    # кликнуть в поле ввода (низ окна, центр)
    _click(1100, 1045)
    time.sleep(0.3)
    _type_text(text)
    time.sleep(0.3)
    _key("Return")
    time.sleep(0.8)
    return {"status": "sent", "chat": chat, "text": text[:200]}
