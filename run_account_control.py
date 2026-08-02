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
from datetime import datetime
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
    gsc = gg.add_parser("screenshot")
    gsc.add_argument("service", nargs="?")
    gopen = gg.add_parser("open")
    gopen.add_argument("service", nargs="?")

    ig = sub.add_parser("instagram")
    igg = ig.add_subparsers(dest="action", required=True)
    igg.add_parser("profile")
    igp = igg.add_parser("posts")
    igp.add_argument("n", nargs="?", type=int, default=5)
    igd = igg.add_parser("post")
    igd.add_argument("code")
    igg.add_parser("screenshot")

    args = parser.parse_args()

    try:
        if args.account == "google":
            if args.action == "whoami":
                out(asyncio.run(google_whoami()))
            elif args.action == "gmail_list":
                out(gmail_list(args.n, args.unread))
            elif args.action == "gmail_send":
                out(gmail_send(args.to, args.subject, args.body, args.confirm, args.dry_run))
            elif args.action == "screenshot":
                service = args.service or "gmail"
                out(asyncio.run(google_screenshot(service)))
            elif args.action == "open":
                svc = getattr(args, "service", None) or "gmail"
                out({"status": "ok", "service": svc,
                     "url": GOOGLE_URLS.get(svc, "unknown")})
        elif args.account == "instagram":
            if args.action == "profile":
                out(asyncio.run(instagram_profile()))
            elif args.action == "posts":
                out(asyncio.run(instagram_posts(args.n)))
            elif args.action == "post":
                out(asyncio.run(instagram_post(args.code)))
            elif args.action == "screenshot":
                out(asyncio.run(instagram_screenshot()))
    except Exception as e:
        out({"status": "error", "error": str(e)[:400]})


if __name__ == "__main__":
    main()
