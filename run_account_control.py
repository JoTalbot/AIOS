#!/usr/bin/env python3
"""
AIOS Account Control — управление Google и Instagram аккаунтами.
Вызывается ботом через subprocess под xvfb-run -a (браузерным операциям нужен X).

Google:
  google whoami                       — кто залогинен в Google (email из Chrome)
  google gmail_list [N] [--unread]    — последние N писем INBOX (IMAP, надёжно)
  google gmail_send --to E --subject S --body B [--confirm|--dry-run]
                                      — отправить письмо (SMTP)
  google screenshot <service>         — скриншот сервиса (gmail|calendar|drive|...)
  google open <service>               — URL сервиса (без запуска браузера)
Instagram:
  instagram profile                   — инфо профиля (имя, followers/following/posts)
  instagram posts [N]                 — последние посты
  instagram post <CODE>               — детали поста
  instagram screenshot                — скриншот профиля

Вывод: JSON в stdout. Скриншоты сохраняются в /tmp/aios_acct_*.png, путь в JSON.
"""
from __future__ import annotations

import argparse
import asyncio
import email
import email.utils
import imaplib
import json
import os
import re
import smtplib
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

GOOGLE_EMAIL = "jo.talbot@gmail.com"
SHOTS = Path("/tmp")

GOOGLE_URLS = {
    "gmail": "https://mail.google.com/mail/u/0/#inbox",
    "calendar": "https://calendar.google.com/calendar/u/0/r",
    "drive": "https://drive.google.com/drive/u/0/my-drive",
    "docs": "https://docs.google.com/document/u/0/",
    "sheets": "https://docs.google.com/spreadsheets/u/0/",
    "slides": "https://docs.google.com/presentation/u/0/",
    "contacts": "https://contacts.google.com/",
    "photos": "https://photos.google.com/",
    "youtube": "https://www.youtube.com/",
    "translate": "https://translate.google.com/",
    "keep": "https://keep.google.com/",
}


# --------------------------------------------------------------------------
# Утилиты
# --------------------------------------------------------------------------

def _env(key: str) -> str:
    v = os.environ.get(key, "")
    if v:
        return v
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def app_password() -> str:
    """Google app password из .env (для IMAP/SMTP)."""
    for key in ("AIOS_SECRET__GOOGLE__APP_PASSWORD_NOSPACES",
                "GOOGLE_APP_PASSWORD",
                "AIOS_SECRET__GOOGLE__APP_PASSWORD"):
        pw = _env(key)
        if pw:
            return pw.replace(" ", "")
    return ""


def out(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def _cleanup_browser_locks() -> None:
    """Убрать lock-файлы Chrome-профиля (если остались после падения)."""
    profile = ROOT / "data" / "chrome_twin" / "default"
    for f in list(profile.glob("Singleton*")) + [profile / "Default" / "LOCK"]:
        try:
            if f.is_file() or f.is_symlink():
                f.unlink()
        except Exception:
            pass
    subprocess.run(["pkill", "-9", "chrome"], capture_output=True)  # страховка
    for p in list(Path("/tmp").glob(".org.chromium.*")) + list(Path("/tmp").glob(".com.google.Chrome.*")) + list(Path("/tmp").glob("com.google.Chrome.*")):
        try:
            subprocess.run(["rm", "-rf", str(p)], capture_output=True)
        except Exception:
            pass


# --------------------------------------------------------------------------
# Gmail через IMAP/SMTP (надёжно, без браузера)
# --------------------------------------------------------------------------

def _decode_header(value) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    out_parts = []
    for data, enc in parts:
        if isinstance(data, bytes):
            try:
                out_parts.append(data.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out_parts.append(data.decode("utf-8", errors="replace"))
        else:
            out_parts.append(data)
    return "".join(out_parts)


def _clean(text: str, limit: int = 200) -> str:
    text = text or ""
    # если это HTML — вырезаем теги
    if "<" in text and ">" in text:
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def gmail_list(n: int = 5, unread_only: bool = False) -> dict:
    pw = app_password()
    if not pw:
        return {"status": "error", "error": "Google app password не задан в .env"}
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        M.login(GOOGLE_EMAIL, pw)
        M.select("INBOX")
        typ, data = M.search(None, "UNSEEN" if unread_only else "ALL")
        ids = data[0].split()
        total = len(ids)
        unread_total = 0
        try:
            _, uu = M.search(None, "UNSEEN")
            unread_total = len(uu[0].split())
        except Exception:
            pass
        ids = ids[-n:]
        emails = []
        for i in reversed(ids):
            try:
                typ, msg_data = M.fetch(i, "(RFC822)")
                raw = msg_data[0][1] if msg_data and msg_data[0] else None
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)
                from_name, from_addr = email.utils.parseaddr(_decode_header(msg.get("From")))
                subj = _decode_header(msg.get("Subject"))
                date_raw = msg.get("Date", "")
                body_text = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body_text = part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8", errors="replace")
                                break
                            except Exception:
                                continue
                else:
                    try:
                        body_text = msg.get_payload(decode=True).decode(
                            msg.get_content_charset() or "utf-8", errors="replace")
                    except Exception:
                        body_text = str(msg.get_payload())
                flags = b""
                try:
                    _, fl = M.fetch(i, "(FLAGS)")
                    flags = fl[0] or b""
                except Exception:
                    pass
                emails.append({
                    "id": i.decode(),
                    "from": f"{from_name} <{from_addr}>".strip() if from_name else from_addr,
                    "from_addr": from_addr,
                    "subject": subj or "(без темы)",
                    "date": date_raw,
                    "unread": b"\\Seen" not in flags,
                    "snippet": _clean(body_text, 220),
                })
            except Exception as e:
                emails.append({"error": str(e)[:150]})
        M.logout()
        return {
            "status": "ok",
            "account": GOOGLE_EMAIL,
            "total": total,
            "unread_total": unread_total,
            "emails": emails,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def _fetch_email_items(M, ids, n: int = 5, unread_only: bool = False) -> list:
    """Общий загрузчик писем из IMAP-сессии (используется gmail_list / gmail_search)."""
    items = []
    for i in reversed(ids[-n:]):
        try:
            typ, msg_data = M.fetch(i, "(RFC822 FLAGS)")
            raw = msg_data[0][1] if msg_data and msg_data[0] else None
            flags = msg_data[0][0] if msg_data and msg_data[0] else b""
            if not raw:
                continue
            msg = email.message_from_bytes(raw)
            from_name, from_addr = email.utils.parseaddr(_decode_header(msg.get("From")))
            subj = _decode_header(msg.get("Subject"))
            date_raw = msg.get("Date", "")
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body_text = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="replace")
                            break
                        except Exception:
                            continue
            else:
                try:
                    body_text = msg.get_payload(decode=True).decode(
                        msg.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    body_text = str(msg.get_payload())
            items.append({
                "id": i.decode(),
                "from": f"{from_name} <{from_addr}>".strip() if from_name else from_addr,
                "from_addr": from_addr,
                "subject": subj or "(без темы)",
                "date": date_raw,
                "unread": b"\\Seen" not in flags,
                "snippet": _clean(body_text, 220),
            })
        except Exception as e:
            items.append({"error": str(e)[:150]})
    return items


def gmail_read(msg_id: str, max_chars: int = 3000) -> dict:
    """Прочитать полное тело письма по ID (IMAP)."""
    pw = app_password()
    if not pw:
        return {"status": "error", "error": "Google app password не задан в .env"}
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        M.login(GOOGLE_EMAIL, pw)
        M.select("INBOX")
        typ, data = M.fetch(msg_id, "(RFC822 FLAGS)")
        if not data or not data[0]:
            return {"status": "error", "error": "Письмо не найдено"}
        raw = data[0][1]
        flags = data[0][0]
        msg = email.message_from_bytes(raw)
        from_name, from_addr = email.utils.parseaddr(_decode_header(msg.get("From")))
        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                if ct == "text/plain":
                    try:
                        body_parts.append(part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"))
                    except Exception:
                        continue
                elif ct == "text/html" and not body_parts:
                    try:
                        body_parts.append(part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"))
                    except Exception:
                        continue
        else:
            try:
                body_parts.append(msg.get_payload(decode=True).decode(
                    msg.get_content_charset() or "utf-8", errors="replace"))
            except Exception:
                body_parts.append(str(msg.get_payload()))
        body = "\n".join(body_parts)
        if "<" in body and ">" in body:
            body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.DOTALL | re.IGNORECASE)
            body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n\s*\n+", "\n", body).strip()
        M.logout()
        return {
            "status": "ok",
            "id": msg_id,
            "from": f"{from_name} <{from_addr}>".strip() if from_name else from_addr,
            "subject": _decode_header(msg.get("Subject")),
            "date": msg.get("Date", ""),
            "unread": b"\\Seen" not in flags,
            "body": body[:max_chars],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def gmail_reply(msg_id: str, text: str, confirm: bool) -> dict:
    """Ответить на письмо (SMTP с In-Reply-To/References)."""
    pw = app_password()
    if not pw:
        return {"status": "error", "error": "Google app password не задан в .env"}
    text = (text or "").strip()
    if not text:
        return {"status": "error", "error": "Пустой текст ответа"}
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        M.login(GOOGLE_EMAIL, pw)
        M.select("INBOX")
        typ, data = M.fetch(msg_id, "(RFC822)")
        if not data or not data[0]:
            return {"status": "error", "error": "Письмо не найдено"}
        orig = email.message_from_bytes(data[0][1])
        M.logout()
        orig_subj = _decode_header(orig.get("Subject")) or "(без темы)"
        orig_msg_id = orig.get("Message-ID", "")
        in_reply_to = orig_msg_id
        refs = (orig.get("References") or "")
        if refs:
            refs = f"{refs} {orig_msg_id}".strip()
        else:
            refs = orig_msg_id
        to = orig.get("Reply-To") or orig.get("From")
        if not confirm:
            return {"status": "need_confirm", "action": "gmail_reply", "msg_id": msg_id,
                    "to": to, "subject": f"Re: {orig_subj}", "text": text[:200]}
        msg = email.message.EmailMessage()
        msg["From"] = GOOGLE_EMAIL
        msg["To"] = to
        msg["Subject"] = f"Re: {orig_subj}"
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if refs:
            msg["References"] = refs
        msg.set_content(text)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(GOOGLE_EMAIL, pw)
            s.send_message(msg)
        return {"status": "sent", "to": to, "subject": f"Re: {orig_subj}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def gmail_search(query: str, n: int = 5) -> dict:
    """Поиск писем по теме/тексту через IMAP."""
    pw = app_password()
    if not pw:
        return {"status": "error", "error": "Google app password не задан в .env"}
    query = (query or "").strip().strip('"')
    if not query:
        return {"status": "error", "error": "Пустой запрос"}
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        M.login(GOOGLE_EMAIL, pw)
        M.select("INBOX")
        ids = []
        for cmd in (f'OR (SUBJECT "{query}") (BODY "{query}")', f'TEXT "{query}"'):
            try:
                typ, data = M.search(None, cmd)
                if data and data[0]:
                    ids = data[0].split()
                    break
            except Exception:
                continue
        total = len(ids)
        items = _fetch_email_items(M, ids, n=n)
        M.logout()
        return {"status": "ok", "query": query, "total": total, "emails": items}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def gmail_send(to: str, subject: str, body: str, confirm: bool, dry_run: bool = False) -> dict:
    pw = app_password()
    if not pw:
        return {"status": "error", "error": "Google app password не задан в .env"}
    if not to or "@" not in to:
        return {"status": "error", "error": f"Некорректный адрес: {to!r}"}
    if not confirm and not dry_run:
        return {"status": "need_confirm", "to": to, "subject": subject, "body_preview": body[:200]}
    msg = email.message.EmailMessage()
    msg["From"] = GOOGLE_EMAIL
    msg["To"] = to
    msg["Subject"] = subject or "(без темы)"
    msg.set_content(body or "")
    if dry_run:
        return {"status": "dry_run", "to": to, "subject": subject, "body_len": len(body or "")}
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(GOOGLE_EMAIL, pw)
            s.send_message(msg)
        return {"status": "sent", "to": to, "subject": subject}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


# --------------------------------------------------------------------------
# Google браузер (Chrome Twin)
# --------------------------------------------------------------------------

async def _launch_google():
    """ChromeTwinAdapter с исправленным _ensure_browser (системный Chrome + no-sandbox)."""
    from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter

    async def fixed_ensure(self):
        if self._page and self._context:
            return self._page
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("Playwright не установлен")
        self._playwright = await async_playwright().start()
        exe = "/usr/bin/google-chrome-stable"
        for c in (exe, "/usr/bin/google-chrome", "/usr/bin/chromium-browser", "/usr/bin/chromium"):
            if Path(c).exists():
                exe = c
                break
        kwargs = dict(
            user_data_dir=str((ROOT / "data" / "chrome_twin" / "default").resolve()),
            executable_path=exe,
            headless=False,
            slow_mo=100,
            args=["--disable-blink-features=AutomationControlled", "--no-first-run",
                  "--no-default-browser-check", "--disable-dev-shm-usage", "--no-sandbox"],
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        )
        self._context = await self._playwright.chromium.launch_persistent_context(**kwargs)
        self._browser = self._context
        self._page = self._context.pages[0] if len(self._context.pages) > 0 else await self._context.new_page()
        return self._page

    ChromeTwinAdapter._ensure_browser = fixed_ensure
    return ChromeTwinAdapter()


async def google_whoami() -> dict:
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto(GOOGLE_URLS["gmail"], wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        info = ""
        try:
            info = await page.eval_on_selector(
                "a[aria-label*='Google Account'], a[aria-label*='Аккаунт Google'], "
                "a[aria-label*='Обліковий запис Google']",
                "el => el.getAttribute('aria-label') || el.getAttribute('title') || ''")
        except Exception:
            pass
        if not info:
            try:
                info = await page.evaluate(
                    """() => { const els=[...document.querySelectorAll('[aria-label]')];
                        const m = els.find(e => (e.getAttribute('aria-label')||'').includes('@'));
                        return m ? m.getAttribute('aria-label') : ''; }""")
            except Exception:
                pass
        email_match = re.search(r"([\w.+-]+@[\w-]+\.[\w.]+)", info or "")
        return {"status": "ok", "raw": info[:200], "email": email_match.group(1) if email_match else None}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_screenshot(service: str) -> dict:
    url = GOOGLE_URLS.get(service)
    if not url:
        return {"status": "error", "error": f"Неизвестный сервис: {service}. Доступны: {list(GOOGLE_URLS)}"}
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(7000)
        title = await page.title()
        path = f"{SHOTS}/aios_acct_google_{service}_{int(time.time())}.png"
        await page.screenshot(path=path)
        return {"status": "ok", "service": service, "url": page.url, "title": title, "screenshot": path}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_calendar_events() -> dict:
    """Список событий на сегодня (day view, aria-labels) + скриншот."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://calendar.google.com/calendar/u/0/r/day",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(7000)
        title = await page.title()
        labels = []
        try:
            labels = await page.eval_on_selector_all(
                "[role='button'][aria-label]",
                "els => els.map(e => e.getAttribute('aria-label'))")
        except Exception:
            pass
        events = []
        seen = set()
        for lab in labels or []:
            lab = (lab or "").strip()
            if not lab or not re.search(r"\d{1,2}:\d{2}", lab):
                continue
            # пустые слоты: "пт, 2 авг 2026 г., 12:00 – 13:00" без текста события
            tail = re.sub(r"^.*?\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\s*", "", lab).strip()
            if not tail:
                continue
            if lab not in seen:
                seen.add(lab)
                events.append(lab)
        shot = f"{SHOTS}/aios_acct_cal_events_{int(time.time())}.png"
        await page.screenshot(path=shot)
        return {"status": "ok", "title": title, "events": events[:30], "screenshot": shot}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_calendar_week() -> dict:
    """События на ближайшие 7 дней (week view) + скриншот."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://calendar.google.com/calendar/u/0/r/week",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(8000)
        title = await page.title()
        labels = []
        try:
            labels = await page.eval_on_selector_all(
                "[role='button'][aria-label]",
                "els => els.map(e => e.getAttribute('aria-label'))")
        except Exception:
            pass
        events = []
        seen = set()
        for lab in labels or []:
            lab = (lab or "").strip()
            if not re.search(r"\d{1,2}:\d{2}", lab):
                continue
            tail = re.sub(r"^.*?\d{1,2}:\d{2}\s*[–—-]\s*\d{1,2}:\d{2}\s*", "", lab).strip()
            if not tail or lab in seen:
                continue
            seen.add(lab)
            events.append(lab)
        shot = f"{SHOTS}/aios_acct_cal_week_{int(time.time())}.png"
        await page.screenshot(path=shot)
        return {"status": "ok", "title": title, "events": events[:40], "screenshot": shot}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


_DRIVE_JS = """() => {
    const vis = [...document.body.querySelectorAll('div, span')]
        .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
        .filter(e => !e.closest('[role="button"], nav, header'));
    const out = [];
    for (const e of vis) {
        if (e.querySelector('div, span')) continue;
        const t = (e.textContent || '').trim().replace(/\\s+/g, ' ');
        if (t && t.length < 120 && t.length > 1) out.push(t);
    }
    return out;
}"""

_DRIVE_NOISE = ("перейти к основному контенту", "быстрые клавиши", "отзыв о специальных возможностях",
                "фильтры не применены", "название", "дата изменения", "посмотреть параметры сортировки",
                "другие действия (alt + a)", "поделиться", "скачать", "переименовать", "предоставить доступ")


def _is_drive_date(text: str) -> bool:
    low = text.lower()
    months = ("янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")
    if any(m in low for m in months):
        return True
    return bool(re.fullmatch(r"\d{1,2}\s+\w{2,12}\.?(?:\s+\d{4})?", low))


async def google_drive_list(limit: int = 20) -> dict:
    """Список файлов/папок Google Диска (My Drive) — имена из видимых текстов."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://drive.google.com/drive/u/0/my-drive",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(9000)
        shot = f"{SHOTS}/aios_acct_drive_list_{int(time.time())}.png"
        await page.screenshot(path=shot)
        texts = await page.evaluate(_DRIVE_JS) or []
        names = []
        seen = set()
        for t in texts:
            low = t.lower()
            if any(n in low for n in _DRIVE_NOISE) or _is_drive_date(t):
                continue
            if t in seen:
                continue
            seen.add(t)
            names.append(t)
            if len(names) >= limit:
                break
        return {"status": "ok", "files": [{"title": n} for n in names], "screenshot": shot}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_drive_download(file_ref: str) -> dict:
    """Скачать файл с Диска по ID или имени (через сессию браузера)."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        # если не ID — поищем имя в списке
        file_id = file_ref.strip()
        if not re.fullmatch(r"[\w-]{10,}", file_id):
            await page.goto("https://drive.google.com/drive/u/0/my-drive",
                            wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(8000)
            links = await page.eval_on_selector_all(
                "a[href*='/file/d/']",
                """els => els.map(e => ({href: e.getAttribute('href'), text: (e.textContent||'').trim()}))""")
            found = None
            for l in links:
                if file_ref.lower() in (l["text"] or "").lower():
                    m = re.search(r"/file/d/([\w-]+)", l["href"] or "")
                    if m:
                        found = m.group(1)
                        break
            if not found:
                return {"status": "error", "error": f"Файл «{file_ref}» не найден на Диске"}
            file_id = found
        # скачивание через export URL (куки сессии браузера)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = await a._context.request.get(url)
        if resp.status != 200:
            return {"status": "error", "error": f"HTTP {resp.status} при скачивании"}
        content = await resp.body()
        # имя файла из Content-Disposition
        cd = resp.headers.get("content-disposition", "")
        m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
        fname = (m.group(1) if m else f"drive_{file_id}").replace('"', "")
        path = f"{SHOTS}/aios_acct_drive_dl_{int(time.time())}_{fname}"
        Path(path).write_bytes(content)
        return {"status": "ok", "file_id": file_id, "path": path, "size": len(content),
                "name": fname}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_calendar_add(title: str, date: str, time_str: str, desc: str,
                              confirm: bool) -> dict:
    """Создать событие календаря через eventedit-URL + кнопку «Зберегти»."""
    a = await _launch_google()
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        start_dt = datetime.strptime(f"{date} {time_str or '12:00'}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(hours=1)
        url = ("https://calendar.google.com/calendar/u/0/r/eventedit"
               f"?text={urllib.parse.quote(title or 'Новая запись')}"
               f"&dates={start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}")
        if desc:
            url += f"&details={urllib.parse.quote(desc)}"
        page = await a._ensure_browser()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        shot = f"{SHOTS}/aios_acct_cal_add_{int(time.time())}.png"
        await page.screenshot(path=shot)
        if not confirm:
            return {"status": "need_confirm", "title": title, "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(), "screenshot": shot}
        saved = False
        for name in ("Зберегти", "Сохранить", "Save"):
            try:
                await page.get_by_role("button", name=name).first.click(timeout=4000)
                saved = True
                break
            except Exception:
                continue
        if not saved:
            return {"status": "error", "error": "Кнопка сохранения не найдена"}
        await page.wait_for_timeout(4000)
        return {"status": "ok", "title": title, "start": start_dt.isoformat(),
                "end": end_dt.isoformat(), "url": page.url}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_docs_create(title: str, content: str) -> dict:
    """Создать Google-документ (содержимое и название)."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://docs.google.com/document/create",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(9000)
        url = page.url
        if content:
            try:
                editor = page.locator("div[contenteditable='true']").first
                await editor.wait_for(state="visible", timeout=15000)
                await editor.click()
                await page.keyboard.type(content, delay=5)
            except Exception:
                pass
        if title:
            try:
                ti = page.locator(".docs-title-input, input[aria-label*='азвание' i], "
                                  "input[aria-label*='Name' i]").first
                await ti.wait_for(state="visible", timeout=8000)
                await ti.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.type(title, delay=5)
            except Exception:
                pass
        await page.wait_for_timeout(2000)
        return {"status": "ok", "url": url, "title": title, "content_len": len(content or "")}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


# --------------------------------------------------------------------------
# Instagram (Chrome Twin адаптер)
# --------------------------------------------------------------------------

async def _instagram_adapter():
    from aios_core.platforms.instagram_chrome_twin_adapter import InstagramChromeTwinAdapter
    return InstagramChromeTwinAdapter()


async def instagram_profile() -> dict:
    a = await _instagram_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Instagram не залогинен", "login": login}
        info = await a.get_profile_info()
        username = info.get("username")
        # скриншот профиля
        shot = None
        try:
            page = await a._ensure_browser()
            await a._goto_ig(page, f"{username}/")
            await page.wait_for_timeout(3000)
            shot = f"{SHOTS}/aios_acct_ig_{int(time.time())}.png"
            await page.screenshot(path=shot)
        except Exception:
            pass
        result = {"status": "ok", "profile": info}
        if shot:
            result["screenshot"] = shot
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_posts(limit: int = 5) -> dict:
    a = await _instagram_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Instagram не залогинен"}
        posts = await a.get_my_posts(limit=limit)
        return {"status": "ok", "username": login.get("username"), "posts": posts}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_post(code: str) -> dict:
    a = await _instagram_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Instagram не залогинен"}
        detail = await a.get_post_details(code)
        # скриншот поста
        shot = None
        try:
            page = await a._ensure_browser()
            await a._goto_ig(page, f"p/{code}/")
            await page.wait_for_timeout(3000)
            shot = f"{SHOTS}/aios_acct_ig_post_{int(time.time())}.png"
            await page.screenshot(path=shot)
        except Exception:
            pass
        result = {"status": "ok", "post": detail}
        if shot:
            result["screenshot"] = shot
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_screenshot() -> dict:
    a = await _instagram_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Instagram не залогинен"}
        page = await a._ensure_browser()
        username = login.get("username")
        await a._goto_ig(page, f"{username}/")
        await page.wait_for_timeout(3000)
        path = f"{SHOTS}/aios_acct_ig_shot_{int(time.time())}.png"
        await page.screenshot(path=path)
        return {"status": "ok", "username": username, "screenshot": path}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def _ig_find_like_button(page):
    """Найти кнопку лайка и вернуть (locator, label)."""
    for sel in ("svg[aria-label*='Like']", "svg[aria-label*='Лайк']",
                "svg[aria-label*='Подобає']", "button[aria-label*='Like']",
                "button[aria-label*='Лайк']", "span[aria-label*='Like']",
                "span[aria-label*='Лайк']", "span[aria-label*='Подобає']"):
        try:
            loc = page.locator(sel).first
            await loc.wait_for(state="visible", timeout=3500)
            label = ""
            try:
                label = await loc.get_attribute("aria-label") or ""
            except Exception:
                pass
            return loc, label
        except Exception:
            continue
    return None, ""


async def instagram_like(url: str, confirm: bool) -> dict:
    """Лайкнуть пост по URL. Если уже лайкнут — вернёт already_liked."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        path = url.replace("https://www.instagram.com/", "").lstrip("/") if url.startswith("http") else url.lstrip("/")
        await a._goto_ig(page, path)
        await page.wait_for_timeout(3000)
        loc, label = await _ig_find_like_button(page)
        if not loc:
            return {"status": "error", "error": "Кнопка лайка не найдена (пост недоступен или уже лайкнут)"}
        low = label.lower()
        already = any(k in low for k in ("unlike", "скасувати подоба", "убрать", "не нравится", "не подоба"))
        if already:
            return {"status": "already_liked", "url": url, "label": label}
        if not confirm:
            shot = f"{SHOTS}/aios_acct_ig_like_{int(time.time())}.png"
            try:
                await page.screenshot(path=shot)
            except Exception:
                shot = None
            return {"status": "need_confirm", "action": "like", "url": url,
                    "screenshot": shot}
        await loc.click()
        await page.wait_for_timeout(1500)
        return {"status": "liked", "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_unlike(url: str, confirm: bool) -> dict:
    """Убрать лайк с поста."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        path = url.replace("https://www.instagram.com/", "").lstrip("/") if url.startswith("http") else url.lstrip("/")
        await a._goto_ig(page, path)
        await page.wait_for_timeout(3000)
        loc, label = await _ig_find_like_button(page)
        if not loc:
            return {"status": "error", "error": "Кнопка лайка не найдена"}
        low = label.lower()
        liked = any(k in low for k in ("unlike", "скасувати подоба", "убрать", "не нравится", "не подоба"))
        if not liked:
            return {"status": "not_liked", "url": url}
        if not confirm:
            return {"status": "need_confirm", "action": "unlike", "url": url}
        await loc.click()
        await page.wait_for_timeout(1500)
        return {"status": "unliked", "url": url}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


# --------------------------------------------------------------- Direct (DM)
_DM_NOISE = {
    "primary", "general", "requests", "що нового", "ваша нотатка", "повідомлення",
    "сообщения", "search", "пошук", "переглянути профіль", "instagram", "сьогодні",
    "вчора", "вчера", "yesterday", "today", "·", "1 рік", "7 р.",
}


def _clean_dm_line(line: str) -> str:
    line = (line or "").strip()
    if not line or len(line) < 2:
        return ""
    low = line.lower()
    if low in _DM_NOISE:
        return ""
    if re.fullmatch(r"[\d\s.,:—–\-]+", line):
        return ""
    return line


_DM_ROW_JS = """els => els.map(e => {
    const spans = [...e.querySelectorAll('span')]
        .map(s => (s.textContent || '').trim())
        .filter(t => t && t !== '·');
    const uniq = [];
    for (const s of spans) if (!uniq.includes(s)) uniq.push(s);
    return uniq.slice(0, 3);
})"""

_DM_HEADER_ROWS = {"jo.talbot", "нове повідомлення", "новое сообщение",
                   "написати повідомлення", "написать сообщение", "запити", "запросы",
                   "ваша нотатка", "ваша заметка"}


async def instagram_dm_list(limit: int = 10) -> dict:
    """Список чатов Direct (имя, превью, время) через DOM строк диалогов."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        await a._goto_ig(page, "direct/inbox/")
        await page.wait_for_timeout(6000)
        rows = await page.eval_on_selector_all("div[role='button']", _DM_ROW_JS)
        threads = []
        for row in rows:
            if not row or not row[0]:
                continue
            name = row[0]
            if name.lower() in _DM_HEADER_ROWS or name.lower().startswith("що нового"):
                continue
            threads.append({
                "name": name,
                "preview": row[1] if len(row) > 1 else "",
                "time": row[2] if len(row) > 2 else "",
            })
            if len(threads) >= limit:
                break
        return {"status": "ok", "threads": threads}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def _open_thread(page, thread: str):
    """Открыть чат по имени (клик) или по id (URL)."""
    thread = (thread or "").strip()
    if thread.isdigit():
        await page.goto(f"https://www.instagram.com/direct/t/{thread}/",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(4000)
        return
    # по имени: идём в inbox и кликаем по тексту
    await page.goto("https://www.instagram.com/direct/inbox/",
                    wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)
    el = page.locator(f"text={thread}").first
    await el.wait_for(state="visible", timeout=8000)
    await el.click()
    await page.wait_for_timeout(5000)


_MSG_JS = """() => {
    const visible = [...document.body.querySelectorAll('div, span, p, section, main')]
        .filter(e => {
            const r = e.getBoundingClientRect();
            const st = getComputedStyle(e);
            return r.width > 0 && r.height > 0 && st.visibility !== 'hidden' && st.display !== 'none';
        })
        .filter(e => !e.closest('[role="button"], nav, header, [role="navigation"]'));
    const texts = [];
    for (const e of visible) {
        if (e.querySelector('div, span, p, section, main')) continue;
        const t = (e.textContent || '').trim().replace(/\\s+/g, ' ');
        if (t && t.length > 0 && t.length < 300 && !t.startsWith('{') && !t.startsWith('[')) texts.push(t);
    }
    return texts;
}"""

_MSG_NOISE = ("переглянути профіль", "повідомлення", "схваліть", "пошук",
              "надіслати повідомлення", "сьогодні", "вчора", "yesterday", "today",
              "ваша нотатка", "підтвердіть", "відеодзвінок", "сповіщення", "новий допис",
              "професійна панель", "налаштування", "також від meta", "повідомлення...",
              "значок із шевроном", "головна", "reels", "· instagram", "instagram")


async def _extract_messages(page, limit: int = 15) -> list[dict]:
    """Извлечь сообщения чата: видимые листовые тексты вне сайдбара."""
    msgs = []
    seen = set()
    try:
        texts = await page.evaluate(_MSG_JS)
        for t in texts or []:
            t = (t or "").strip()
            low = t.lower()
            if any(k in low for k in _MSG_NOISE):
                continue
            if len(t) < 2 or t in seen:
                continue
            seen.add(t)
            msgs.append({"text": t})
    except Exception:
        pass
    if not msgs:
        try:
            body = await page.inner_text("body")
            for l in body.splitlines():
                l = _clean_dm_line(l)
                low = l.lower()
                if l and l not in seen and not any(k in low for k in _MSG_NOISE):
                    seen.add(l)
                    msgs.append({"text": l})
        except Exception:
            pass
    return msgs[-limit:]


async def instagram_dm_read(thread: str, limit: int = 15) -> dict:
    """Прочитать последние сообщения чата."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        await _open_thread(page, thread)
        msgs = await _extract_messages(page, limit)
        return {"status": "ok", "thread": thread, "messages": msgs,
                "url": page.url}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_dm_send(thread: str, text: str, confirm: bool) -> dict:
    """Отправить сообщение в существующий чат."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        await _open_thread(page, thread)
        composer = page.locator("div[role=textbox][contenteditable=true]").first
        await composer.wait_for(state="visible", timeout=10000)
        await composer.click()
        if not confirm:
            return {"status": "need_confirm", "action": "dm_send", "thread": thread,
                    "text": text[:200]}
        await page.keyboard.type(text, delay=20)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        return {"status": "sent", "thread": thread, "text": text[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_dm_new(username: str, text: str, confirm: bool) -> dict:
    """Новый чат: поиск пользователя в /direct/new/ и отправка."""
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        await page.goto("https://www.instagram.com/direct/new/",
                        wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        # поле поиска
        search = page.locator("input[placeholder*='Пошук'], input[placeholder*='Search'], input[aria-label*='Пошук']").first
        await search.wait_for(state="visible", timeout=10000)
        await search.fill(username)
        await page.wait_for_timeout(3000)
        # клик по результату (обычно div с username)
        res = page.locator(f"text={username}").first
        await res.wait_for(state="visible", timeout=8000)
        await res.click()
        await page.wait_for_timeout(2000)
        # кнопка «Чат» / «Далі»
        for name in ("Чат", "Chat", "Далі", "Далее", "Next"):
            try:
                btn = page.get_by_role("button", name=name).first
                await btn.click(timeout=2500)
                break
            except Exception:
                continue
        await page.wait_for_timeout(3000)
        composer = page.locator("div[role=textbox][contenteditable=true]").first
        await composer.wait_for(state="visible", timeout=10000)
        await composer.click()
        if not confirm:
            return {"status": "need_confirm", "action": "dm_new", "username": username,
                    "text": text[:200]}
        await page.keyboard.type(text, delay=20)
        await page.wait_for_timeout(500)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        return {"status": "sent", "username": username, "text": text[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


# --------------------------------------------------------------------------
# Google Contacts (Chrome Twin)
# --------------------------------------------------------------------------

_CONTACTS_JS = """els => els.map(e => {
    const id = e.getAttribute('data-id') || '';
    const t = (e.innerText || '').trim().replace(/\\s+/g, ' ');
    const emailM = t.match(/[\\w.+-]+@[\\w-]+\\.[\\w.]+/);
    const email = emailM ? emailM[0] : null;
    let name = t.split(' star')[0].replace(/^drag_indicator\\s*/, '').trim();
    if (email && name.includes(email)) name = name.replace(email, '').trim();
    name = name.replace(/\\s*(Отправить письмо в новом окне|content_copy|Ещё).*/g, '').trim();
    return {id, name: name.slice(0, 60), email};
}).filter(x => x.id && x.id.startsWith('c') && x.name && x.name !== 'drag_indicator')"""


async def google_contacts_list(limit: int = 25) -> dict:
    """Список контактов Google (имена + email из списка)."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://contacts.google.com/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(8000)
        items = await page.eval_on_selector_all("[data-id]", _CONTACTS_JS)
        seen = set()
        contacts = []
        for it in items or []:
            name = it.get("name")
            if name in seen:
                continue
            seen.add(name)
            contacts.append({"name": name, "email": it.get("email")})
            if len(contacts) >= limit:
                break
        shot = f"{SHOTS}/aios_acct_contacts_{int(time.time())}.png"
        try:
            await page.screenshot(path=shot)
        except Exception:
            shot = None
        return {"status": "ok", "contacts": contacts, "count": len(contacts),
                "screenshot": shot}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_contacts_search(query: str, limit: int = 10) -> dict:
    """Поиск контакта (фильтр списка) + детали: email/телефон."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://contacts.google.com/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(8000)
        # поле поиска (вверху справа)
        try:
            box = page.locator("input[type='search'], input[placeholder*='Поиск'], input[placeholder*='Search']").first
            await box.wait_for(state="visible", timeout=8000)
            await box.fill(query)
            await page.wait_for_timeout(2500)
        except Exception:
            pass
        items = await page.eval_on_selector_all("[data-id]", _CONTACTS_JS)
        filtered = []
        for it in items or []:
            name = it.get("name") or ""
            if query.lower() in name.lower() or (it.get("email") or "").lower() in query.lower():
                filtered.append(it)
            if len(filtered) >= limit:
                break
        if not filtered:
            # fallback: всё, что видно после поиска
            filtered = [it for it in (items or [])[:limit]]
        # детали первого найденного
        detail = {}
        if filtered:
            try:
                el = page.locator(f"[data-id^='c']:has-text('{filtered[0]['name'][:30]}')").first
                await el.click(force=True, timeout=5000)
                await page.wait_for_timeout(2500)
                detail = await page.evaluate("""() => {
                    const text = document.body.innerText;
                    const emails = text.match(/[\\w.+-]+@[\\w-]+\\.[\\w.]+/g) || [];
                    const phones = text.match(/\\+?[\\d][\\d\\s().-]{7,}/g) || [];
                    return {emails: [...new Set(emails)].slice(0, 5), phones: [...new Set(phones)].slice(0, 5)};
                }""")
            except Exception:
                pass
        result = {"status": "ok", "query": query, "contacts": filtered,
                  "count": len(filtered)}
        if detail:
            result["detail"] = detail
        return result
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def google_contacts_add(name: str, email: str = "", phone: str = "") -> dict:
    """Создать новый контакт (кнопка «Новый контакт» → форма)."""
    a = await _launch_google()
    try:
        page = await a._ensure_browser()
        await page.goto("https://contacts.google.com/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        # кнопка «Новый контакт» (div[aria-label*=Новый контакт])
        btn = page.locator("div[aria-label*='Новый контакт'], div[aria-label*='New contact'], [data-tooltip*='Новый контакт']").first
        await btn.wait_for(state="visible", timeout=8000)
        await btn.click()
        await page.wait_for_timeout(3000)
        # поле имени
        name_input = page.locator("input[placeholder*='Имя'], input[placeholder*='Name'], input[placeholder*=\"Ім'я\"]").first
        await name_input.wait_for(state="visible", timeout=8000)
        await name_input.fill(name)
        if email:
            em = page.locator("input[placeholder*='Email'], input[type=email]").first
            try:
                await em.wait_for(state="visible", timeout=4000)
                await em.fill(email)
            except Exception:
                pass
        if phone:
            ph = page.locator("input[placeholder*='Телефон'], input[placeholder*='Phone'], input[type=tel]").first
            try:
                await ph.wait_for(state="visible", timeout=4000)
                await ph.fill(phone)
            except Exception:
                pass
        await page.wait_for_timeout(500)
        # сохранить: кнопка «Сохранить»
        for sel in ("button[aria-label*='Сохранить']", "div[aria-label*='Сохранить']",
                    "button:has-text('Сохранить')", "div:has-text('Сохранить')"):
            try:
                sv = page.locator(sel).first
                await sv.click(timeout=4000)
                await page.wait_for_timeout(1500)
                return {"status": "ok", "name": name, "email": email, "phone": phone}
            except Exception:
                continue
        return {"status": "draft", "note": "Форма заполнена, кнопка «Сохранить» не найдена — проверьте вручную",
                "name": name}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


# --------------------------------------------------------------------------
# Viber (desktop)
# --------------------------------------------------------------------------
def viber_chats() -> dict:
    """Список чатов Viber (OCR окна десктоп-приложения)."""
    try:
        import viber_control as vc
        return vc.chats()
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def viber_read(chat: str, limit: int = 15) -> dict:
    try:
        import viber_control as vc
        return vc.read_chat(chat, limit)
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


def viber_send(chat: str, text: str, confirm: bool) -> dict:
    try:
        import viber_control as vc
        return vc.send_chat(chat, text, confirm)
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


async def prom_profile() -> dict:
    """Prom.ua: информация аккаунта (Chrome Twin)."""
    try:
        from aios_core.platforms.prom_chrome_twin_adapter import PromChromeTwinAdapter
        a = PromChromeTwinAdapter()
        try:
            return await a.account_info()
        finally:
            await a.close()
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}


# --------------------------------------------------------------------------
# Telegram userbot (личный аккаунт)
# --------------------------------------------------------------------------

def _tg_userbot(args: list) -> dict:
    """Вызвать tg_userbot.py (Telethon, личный Telegram)."""
    import subprocess
    r = subprocess.run(["/opt/aios/.venv/bin/python", str(ROOT / "tg_userbot.py")] + args,
                       capture_output=True, text=True, timeout=90, cwd=str(ROOT))
    out = (r.stdout or "").strip()
    start = out.find("{")
    if start >= 0:
        try:
            return json.loads(out[start:])
        except Exception:
            pass
    return {"status": "error", "error": (r.stderr or out)[-300:]}


def tg_dialogs(limit: int = 15) -> dict:
    return _tg_userbot(["dialogs", str(limit)])


def tg_read(ref: str, limit: int = 12) -> dict:
    return _tg_userbot(["read", ref, str(limit)])


def tg_send(ref: str, text: str, confirm: bool) -> dict:
    args = ["send", ref, text]
    if confirm:
        args.append("--confirm")
    return _tg_userbot(args)


def tg_bot(bot: str, command: str, confirm: bool) -> dict:
    args = ["bot", bot, command]
    if confirm:
        args.append("--confirm")
    return _tg_userbot(args)


# --------------------------------------------------------------------------
# Facebook / TikTok / OLX (Chrome Twin)
# --------------------------------------------------------------------------

async def _fb_adapter():
    from aios_core.platforms.facebook_chrome_twin_adapter import FacebookChromeTwinAdapter
    return FacebookChromeTwinAdapter()


async def _tt_adapter():
    from aios_core.platforms.tiktok_chrome_twin_adapter import TiktokChromeTwinAdapter
    return TiktokChromeTwinAdapter()


async def _olx_adapter():
    from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
    return OLXChromeTwinAdapter(config={"olx_login": os.getenv("OLX_LOGIN", "959052288")})


async def facebook_profile() -> dict:
    a = await _fb_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Facebook не залогинен", "login": login}
        info = await a.get_profile_info()
        notif = await a.get_notifications_count()
        info["notifications"] = notif
        info["logged_in"] = True
        return {"status": "ok", "facebook": info}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def facebook_feed(limit: int = 5) -> dict:
    a = await _fb_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Facebook не залогинен"}
        feed = await a.get_feed(limit)
        return {"status": "ok", "feed": feed}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def messenger_list(limit: int = 10) -> dict:
    a = await _fb_adapter()
    try:
        chats = await a.messenger_list(limit)
        return {"status": "ok", "chats": chats}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def messenger_read(chat: str, limit: int = 12) -> dict:
    a = await _fb_adapter()
    try:
        msgs = await a.messenger_read(chat, limit)
        return {"status": "ok", "chat": chat, "messages": msgs}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def messenger_send(chat: str, text: str, confirm: bool) -> dict:
    a = await _fb_adapter()
    try:
        return await a.messenger_send(chat, text, confirm)
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def tiktok_profile() -> dict:
    a = await _tt_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "TikTok не залогинен", "login": login}
        info = await a.get_profile_info()
        info["logged_in"] = True
        return {"status": "ok", "tiktok": info}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def tiktok_feed(limit: int = 5) -> dict:
    a = await _tt_adapter()
    try:
        login = await a.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "TikTok не залогинен"}
        feed = await a.get_feed(limit)
        return {"status": "ok", "feed": feed}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def tiktok_upload(video_path: str, caption: str, confirm: bool) -> dict:
    a = await _tt_adapter()
    try:
        return await a.upload_video(video_path, caption, confirm)
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def olx_profile() -> dict:
    a = await _olx_adapter()
    try:
        info = await a.account_info()
        if info.get("status") != "ok":
            return info
        return {"status": "ok", "olx": info}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


async def instagram_follow(username: str, action: str, confirm: bool) -> dict:
    a = await _instagram_adapter()
    try:
        page = await a._ensure_browser()
        await a._goto_ig(page, f"{username}/")
        await page.wait_for_timeout(3000)

        follow_sel = ("button:has-text('Стежити')", "button:has-text('Подписаться')",
                      "button:has-text('Follow')", "button:has-text('Follow Back')")
        unfollow_sel = ("button:has-text('Відстежується')", "button:has-text('Відстежуватися')",
                        "button:has-text('Подписки')", "button:has-text('Following')")

        btn = None
        cur_state = None
        for sel in follow_sel if action == "follow" else unfollow_sel:
            try:
                b = page.locator(sel).first
                await b.wait_for(state="visible", timeout=3000)
                btn = b
                cur_state = sel
                break
            except Exception:
                continue
        if not btn:
            # определить противоположное состояние
            for sel in (follow_sel if action == "unfollow" else unfollow_sel):
                try:
                    b = page.locator(sel).first
                    await b.wait_for(state="visible", timeout=2500)
                    btn = b
                    cur_state = sel
                    break
                except Exception:
                    continue
            if btn:
                state_txt = (await btn.text_content() or "").strip()
                if action == "follow":
                    return {"status": "already_following", "username": username, "button": state_txt}
                return {"status": "not_following", "username": username, "button": state_txt}
            return {"status": "error", "error": "Кнопка подписки не найдена"}
        state_txt = (await btn.text_content() or "").strip()

        if not confirm:
            shot = f"{SHOTS}/aios_acct_ig_follow_{int(time.time())}.png"
            try:
                await page.screenshot(path=shot)
            except Exception:
                shot = None
            return {"status": "need_confirm", "action": action, "username": username,
                    "button": state_txt, "screenshot": shot}
        await btn.click()
        await page.wait_for_timeout(2000)
        # при отписке может быть попап подтверждения
        if action == "unfollow":
            for name in ("Відписатися", "Отписаться", "Unfollow", "Підтвердити", "Подтвердить"):
                try:
                    pop = page.get_by_role("button", name=name).first
                    await pop.click(timeout=2000)
                    break
                except Exception:
                    continue
            await page.wait_for_timeout(1500)
        return {"status": "ok", "action": action, "username": username}
    except Exception as e:
        return {"status": "error", "error": str(e)[:300]}
    finally:
        await a.close()


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AIOS Account Control")
    sub = parser.add_subparsers(dest="account", required=True)

    g = sub.add_parser("google")
    gg = g.add_subparsers(dest="action", required=True)
    gg.add_parser("whoami")
    gl = gg.add_parser("gmail_list")
    gl.add_argument("n", nargs="?", type=int, default=5)
    gl.add_argument("--unread", action="store_true")
    gs = gg.add_parser("gmail_send")
    gs.add_argument("--to", required=True)
    gs.add_argument("--subject", default="")
    gs.add_argument("--body", default="")
    gs.add_argument("--confirm", action="store_true")
    gs.add_argument("--dry-run", action="store_true", dest="dry_run")
    gsearch = gg.add_parser("gmail_search")
    gsearch.add_argument("query")
    gsearch.add_argument("n", nargs="?", type=int, default=5)
    gsc = gg.add_parser("screenshot")
    gsc.add_argument("service", nargs="?")
    gopen = gg.add_parser("open")
    gopen.add_argument("service", nargs="?")
    gce = gg.add_parser("calendar_events")
    gcw = gg.add_parser("calendar_week")
    gca = gg.add_parser("calendar_add")
    gca.add_argument("--title", required=True)
    gca.add_argument("--date", default="")
    gca.add_argument("--time", default="")
    gca.add_argument("--desc", default="")
    gca.add_argument("--confirm", action="store_true")
    gdc = gg.add_parser("docs_create")
    gdc.add_argument("--title", default="")
    gdc.add_argument("--content", default="")
    grd = gg.add_parser("gmail_read")
    grd.add_argument("id")
    grd.add_argument("--max", type=int, default=3000)
    grp = gg.add_parser("gmail_reply")
    grp.add_argument("id")
    grp.add_argument("text")
    grp.add_argument("--confirm", action="store_true")
    gdl = gg.add_parser("drive_list")
    gdl.add_argument("--limit", type=int, default=20)
    gdd = gg.add_parser("drive_download")
    gdd.add_argument("file_ref")
    gcl = gg.add_parser("contacts_list")
    gcl.add_argument("--limit", type=int, default=25)
    gcs = gg.add_parser("contacts_search")
    gcs.add_argument("query")
    gca = gg.add_parser("contacts_add")
    gca.add_argument("--name", required=True)
    gca.add_argument("--email", default="")
    gca.add_argument("--phone", default="")

    ig = sub.add_parser("instagram")
    igg = ig.add_subparsers(dest="action", required=True)
    igg.add_parser("profile")
    igp = igg.add_parser("posts")
    igp.add_argument("n", nargs="?", type=int, default=5)
    igd = igg.add_parser("post")
    igd.add_argument("code")
    igg.add_parser("screenshot")
    igl = igg.add_parser("like")
    igl.add_argument("url")
    igl.add_argument("--confirm", action="store_true")
    igu = igg.add_parser("unlike")
    igu.add_argument("url")
    igu.add_argument("--confirm", action="store_true")
    igf = igg.add_parser("follow")
    igf.add_argument("username")
    igf.add_argument("--action", choices=["follow", "unfollow"], default="follow")
    igf.add_argument("--confirm", action="store_true")
    igdl = igg.add_parser("dm_list")
    igdl.add_argument("n", nargs="?", type=int, default=10)
    igdr = igg.add_parser("dm_read")
    igdr.add_argument("thread")
    igdr.add_argument("--limit", type=int, default=15)
    igds = igg.add_parser("dm_send")
    igds.add_argument("thread")
    igds.add_argument("text")
    igds.add_argument("--confirm", action="store_true")
    igdn = igg.add_parser("dm_new")
    igdn.add_argument("username")
    igdn.add_argument("text")
    igdn.add_argument("--confirm", action="store_true")

    fb = sub.add_parser("facebook")
    fbg = fb.add_subparsers(dest="action", required=True)
    fbg.add_parser("profile")
    fbf = fbg.add_parser("feed")
    fbf.add_argument("n", nargs="?", type=int, default=5)
    fbml = fbg.add_parser("messenger_list")
    fbml.add_argument("--limit", type=int, default=10)
    fbmr = fbg.add_parser("messenger_read")
    fbmr.add_argument("chat")
    fbmr.add_argument("--limit", type=int, default=12)
    fbms = fbg.add_parser("messenger_send")
    fbms.add_argument("chat")
    fbms.add_argument("text")
    fbms.add_argument("--confirm", action="store_true")

    tt = sub.add_parser("tiktok")
    ttg = tt.add_subparsers(dest="action", required=True)
    ttg.add_parser("profile")
    ttf = ttg.add_parser("feed")
    ttf.add_argument("n", nargs="?", type=int, default=5)
    ttu = ttg.add_parser("upload")
    ttu.add_argument("video")
    ttu.add_argument("--caption", default="")
    ttu.add_argument("--confirm", action="store_true")

    olx = sub.add_parser("olx")
    olxg = olx.add_subparsers(dest="action", required=True)
    olxg.add_parser("profile")

    vb = sub.add_parser("viber")
    vbg = vb.add_subparsers(dest="action", required=True)
    vbg.add_parser("chats")
    vbr = vbg.add_parser("read")
    vbr.add_argument("chat")
    vbr.add_argument("--limit", type=int, default=15)
    vbs = vbg.add_parser("send")
    vbs.add_argument("chat")
    vbs.add_argument("text")
    vbs.add_argument("--confirm", action="store_true")

    prom = sub.add_parser("prom")
    promg = prom.add_subparsers(dest="action", required=True)
    promg.add_parser("profile")

    tg = sub.add_parser("tg")
    tgg = tg.add_subparsers(dest="action", required=True)
    tgd = tgg.add_parser("dialogs")
    tgd.add_argument("n", nargs="?", type=int, default=15)
    tgr = tgg.add_parser("read")
    tgr.add_argument("ref")
    tgr.add_argument("--limit", type=int, default=12)
    tgs = tgg.add_parser("send")
    tgs.add_argument("ref")
    tgs.add_argument("text")
    tgs.add_argument("--confirm", action="store_true")
    tgb = tgg.add_parser("bot")
    tgb.add_argument("bot")
    tgb.add_argument("command")
    tgb.add_argument("--confirm", action="store_true")

    args = parser.parse_args()

    try:
        if args.account == "google":
            if args.action == "whoami":
                out(asyncio.run(google_whoami()))
            elif args.action == "gmail_list":
                out(gmail_list(args.n, args.unread))
            elif args.action == "gmail_send":
                out(gmail_send(args.to, args.subject, args.body, args.confirm, args.dry_run))
            elif args.action == "gmail_search":
                out(gmail_search(args.query, args.n))
            elif args.action == "screenshot":
                service = args.service or "gmail"
                out(asyncio.run(google_screenshot(service)))
            elif args.action == "open":
                svc = getattr(args, "service", None) or "gmail"
                out({"status": "ok", "service": svc,
                     "url": GOOGLE_URLS.get(svc, "unknown")})
            elif args.action == "calendar_events":
                out(asyncio.run(google_calendar_events()))
            elif args.action == "calendar_week":
                out(asyncio.run(google_calendar_week()))
            elif args.action == "calendar_add":
                out(asyncio.run(google_calendar_add(args.title, args.date, args.time,
                                                    args.desc, args.confirm)))
            elif args.action == "docs_create":
                out(asyncio.run(google_docs_create(args.title, args.content)))
            elif args.action == "gmail_read":
                out(gmail_read(args.id, args.max))
            elif args.action == "gmail_reply":
                out(gmail_reply(args.id, args.text, args.confirm))
            elif args.action == "drive_list":
                out(asyncio.run(google_drive_list(args.limit)))
            elif args.action == "drive_download":
                out(asyncio.run(google_drive_download(args.file_ref)))
            elif args.action == "contacts_list":
                out(asyncio.run(google_contacts_list(args.limit)))
            elif args.action == "contacts_search":
                out(asyncio.run(google_contacts_search(args.query)))
            elif args.action == "contacts_add":
                out(asyncio.run(google_contacts_add(args.name, args.email, args.phone)))
        elif args.account == "instagram":
            if args.action == "profile":
                out(asyncio.run(instagram_profile()))
            elif args.action == "posts":
                out(asyncio.run(instagram_posts(args.n)))
            elif args.action == "post":
                out(asyncio.run(instagram_post(args.code)))
            elif args.action == "screenshot":
                out(asyncio.run(instagram_screenshot()))
            elif args.action == "like":
                out(asyncio.run(instagram_like(args.url, args.confirm)))
            elif args.action == "unlike":
                out(asyncio.run(instagram_unlike(args.url, args.confirm)))
            elif args.action == "follow":
                out(asyncio.run(instagram_follow(args.username, args.action, args.confirm)))
            elif args.action == "dm_list":
                out(asyncio.run(instagram_dm_list(args.n)))
            elif args.action == "dm_read":
                out(asyncio.run(instagram_dm_read(args.thread, args.limit)))
            elif args.action == "dm_send":
                out(asyncio.run(instagram_dm_send(args.thread, args.text, args.confirm)))
            elif args.action == "dm_new":
                out(asyncio.run(instagram_dm_new(args.username, args.text, args.confirm)))
        elif args.account == "facebook":
            if args.action == "profile":
                out(asyncio.run(facebook_profile()))
            elif args.action == "feed":
                out(asyncio.run(facebook_feed(args.n)))
            elif args.action == "messenger_list":
                out(asyncio.run(messenger_list(args.limit)))
            elif args.action == "messenger_read":
                out(asyncio.run(messenger_read(args.chat, args.limit)))
            elif args.action == "messenger_send":
                out(asyncio.run(messenger_send(args.chat, args.text, args.confirm)))
        elif args.account == "tiktok":
            if args.action == "profile":
                out(asyncio.run(tiktok_profile()))
            elif args.action == "feed":
                out(asyncio.run(tiktok_feed(args.n)))
            elif args.action == "upload":
                out(asyncio.run(tiktok_upload(args.video, args.caption, args.confirm)))
        elif args.account == "olx":
            if args.action == "profile":
                out(asyncio.run(olx_profile()))
        elif args.account == "viber":
            if args.action == "chats":
                out(viber_chats())
            elif args.action == "read":
                out(viber_read(args.chat, args.limit))
            elif args.action == "send":
                out(viber_send(args.chat, args.text, args.confirm))
        elif args.account == "prom":
            if args.action == "profile":
                out(asyncio.run(prom_profile()))
        elif args.account == "tg":
            if args.action == "dialogs":
                out(tg_dialogs(args.n))
            elif args.action == "read":
                out(tg_read(args.ref, args.limit))
            elif args.action == "send":
                out(tg_send(args.ref, args.text, args.confirm))
            elif args.action == "bot":
                out(tg_bot(args.bot, args.command, args.confirm))
    except Exception as e:
        out({"status": "error", "error": str(e)[:400]})


if __name__ == "__main__":
    main()
