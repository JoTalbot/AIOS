#!/usr/bin/env python3
"""
Groq Key Autopilot: автоматическое создание новых API-ключей Groq
при приближении к исчерпанию лимитов.

Логика:
1. Раз в час проверяет x-ratelimit-remaining всех ключей из .env.
2. Если средний остаток < порога (RPM) ИЛИ есть 429-ошибки — создаёт новый ключ:
   - открывает console.groq.com/login в Chrome (CDP 9222)
   - отправляет magic-link на почту
   - забирает письмо из Gmail (та же сессия Chrome)
   - открывает ссылку, получает org/project из сессии
   - решает капчу через 2captcha, создаёт ключ
   - дописывает ключ в .env, /etc/aios/*.env, .llm_keys.json
3. Шлёт Telegram-уведомление о созданном ключе.

Запуск: systemd timer (раз в час) или вручную: python run_groq_key_autopilot.py --check
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE = ROOT / "data" / "groq_autopilot_state.json"
EMAIL = "j.otalbo.t@gmail.com"
ORG = "org_01kzvcszbge5a9hf9pmprnfktp"
PROJECT = "project_01kzvct0k9e1xv3ma40n4cp87g"
RPM_THRESHOLD = 200  # средний остаток запросов/мин на ключ ниже -> создаём новый
MIN_KEYS = 6  # не создавать, если ключей уже >= этого
CAPTCHA_KEY_FILE = ROOT / "data" / ".2captcha_key"


def _read_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_name(f".{STATE.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


def _groq_keys() -> list[str]:
    keys = []
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if re.match(r"^GROQ_API_KEY(_\d+)?=", line):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
                if k.startswith("gsk_"):
                    keys.append(k)
    except Exception:
        pass
    return keys


def _remaining_requests(key: str) -> float | None:
    """Оставшиеся запросы/мин из заголовков (усредняем по 2 запросам)."""
    vals = []
    for _ in range(2):
        try:
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps({"model": "llama-3.3-70b-versatile",
                                 "messages": [{"role": "user", "content": "ping"}],
                                 "max_tokens": 1}).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=20) as r:
                h = r.headers
                rem = h.get("x-ratelimit-remaining-requests")
                if rem:
                    vals.append(float(rem))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                vals.append(0.0)
            # 401/402 и пр. — ключ мёртв, не считаем
            else:
                return None
        except Exception:
            return None
        time.sleep(0.3)
    return min(vals) if vals else None


def _captcha_key() -> str:
    try:
        return CAPTCHA_KEY_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _env(name: str) -> str:
    from tg_bot.credentials import read_systemd_credential

    if name in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    value = os.environ.get(name, "")
    if value:
        return value
    try:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _send(text: str) -> bool:
    from tg_bot.credentials import secret_from_env_or_credential

    token = secret_from_env_or_credential("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token")
    chat = _env("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps({"chat_id": int(chat), "text": text[:3800], "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30):
        pass
    return True


def _append_key(key: str, name: str) -> None:
    """Добавить ключ во все источники."""
    env = ROOT / ".env"
    lines = env.read_text(encoding="utf-8").splitlines()
    existing = [l for l in lines if l.startswith("GROQ_API_KEY_")]
    idx = len(existing) + 1
    while any(l.startswith(f"GROQ_API_KEY_{idx}=") for l in lines):
        idx += 1
    with env.open("a", encoding="utf-8") as f:
        f.write(f"\nGROQ_API_KEY_{idx}={key}\n")

    for env_file in ("/etc/aios/aios-auto-coder.env", "/etc/aios/aios-telegram-bot.env"):
        try:
            p = Path(env_file)
            src = p.read_text(encoding="utf-8")
            if f"GROQ_API_KEY_{idx}=" not in src:
                with p.open("a", encoding="utf-8") as f:
                    f.write(f"GROQ_API_KEY_{idx}={key}\n")
        except Exception:
            pass

    try:
        d = json.loads((ROOT / "data" / ".llm_keys.json").read_text(encoding="utf-8"))
        g = d.get("groq", [])
        if key not in g:
            g.append(key)
        d["groq"] = g
        (ROOT / "data" / ".llm_keys.json").write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _create_key_via_browser(ckey: str) -> str | None:
    """Полный цикл в браузере: login -> magic link из Gmail -> капча -> ключ.
    Возвращает (name, key) или None."""
    try:
        sys.path.insert(0, str(ROOT))
        import cdp_help  # noqa: F401
    except ImportError:
        # cdp_help.py может лежать в tools/
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            import cdp_help  # noqa: F401
        except ImportError:
            print("cdp_help.py не найден", flush=True)
            return None

    import asyncio
    import cdp_help as cdp

    async def _run() -> str | None:
        # 1. Вкладка /login, отправить email
        pages = cdp.list_pages()
        login_tab = next((t for t in pages if "console.groq.com/login" in t["url"]), None)
        if login_tab is None:
            t = cdp.new_page("https://console.groq.com/login")
            ws = await cdp.connect(t["webSocketDebuggerUrl"])
            await cdp.navigate(ws, "https://console.groq.com/login")
            await asyncio.sleep(5)
        else:
            ws = await cdp.connect(login_tab["webSocketDebuggerUrl"])
            await cdp.navigate(ws, "https://console.groq.com/login")
            await asyncio.sleep(4)

        # Try again если есть
        await cdp.ev(ws, "(() => { const b = [...document.querySelectorAll(\"button\")].find(x => (x.innerText||\"\").includes(\"Try again\")); if (b) b.click(); return 1; })()")
        await asyncio.sleep(2)
        r = await cdp.ev(ws, f"""
        (() => {{
          const inp = document.querySelector("#email-input");
          if (!inp) return "no input";
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
          setter.call(inp, "{EMAIL}");
          inp.dispatchEvent(new Event("input", {{bubbles: true}}));
          inp.dispatchEvent(new Event("change", {{bubbles: true}}));
          return "filled";
        }})()
        """)
        if r != "filled":
            print("login fill:", r, flush=True)
            return None
        await asyncio.sleep(1)
        await cdp.ev(ws, "(() => { const b = document.querySelector(\"button[type=submit]\"); if (b) b.click(); return 1; })()")
        print("magic-link отправлен", flush=True)

        # 2. Ждём письмо в Gmail (до 3 мин)
        gmail_ws = await cdp.connect(cdp.get_page_ws(url_filter="mail.google"))
        magic_url = None
        for _ in range(24):
            await asyncio.sleep(8)
            await cdp.navigate(gmail_ws, "https://mail.google.com/mail/u/0/#search/from%3Agroq.com+newer_than%3A1h")
            await asyncio.sleep(6)
            r = await cdp.ev(gmail_ws, """
            (() => {
              const rows = document.querySelectorAll('tr.zA');
              if (!rows.length) return null;
              rows[0].click();
              return "clicked";
            })()
            """)
            await asyncio.sleep(3)
            links = await cdp.ev(gmail_ws, """
            (() => {
              const area = document.querySelector("div.a3s") || document.querySelector("div.ii") || document.body;
              const links = [...area.querySelectorAll("a")].map(a => a.href || "").filter(h => h.includes("stytch.com/v1/magic_links/redirect"));
              return JSON.stringify(links);
            })()
            """)
            try:
                ls = json.loads(links or "[]")
                if ls:
                    magic_url = ls[0]
                    break
            except Exception:
                pass
        if not magic_url:
            print("письмо не найдено за 3 мин", flush=True)
            return None
        print("magic-link получен", flush=True)

        # 3. Открыть magic link -> /home
        t = cdp.new_page(magic_url)
        ws = await cdp.connect(t["webSocketDebuggerUrl"])
        await cdp.navigate(ws, magic_url)
        for _ in range(40):
            await asyncio.sleep(1.5)
            url = await cdp.ev(ws, "location.href") or ""
            if "console.groq.com" in url:
                break
        await asyncio.sleep(5)

        # 4. org/project из сессии
        info = await cdp.ev(ws, """
        (() => {
          const prefs = document.cookie.split("; ").find(c => c.startsWith("user-preferences="));
          let org = "", project = "";
          if (prefs) {
            try {
              const d = JSON.parse(decodeURIComponent(prefs.split("=").slice(1).join("=")));
              org = d["current-org"] || ""; project = d["current-project"] || "";
            } catch(e) {}
          }
          return JSON.stringify({org, project});
        })()
        """)
        d = json.loads(info or "{}")
        org = d.get("org") or ORG
        project = d.get("project") or PROJECT
        print(f"сессия: org={org} proj={project}", flush=True)

        # 5. Капча + создание ключа
        def cap_solve():
            req = urllib.request.Request("https://api.2captcha.com/createTask", data=json.dumps({
                "clientKey": ckey,
                "task": {"type": "TurnstileTaskProxyless", "websiteURL": "https://console.groq.com/keys", "websiteKey": "0x4AAAAAAA04hiaY8r8_QF1r"},
            }).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                tid = json.loads(r.read())["taskId"]
            for _ in range(40):
                time.sleep(8)
                req = urllib.request.Request("https://api.2captcha.com/getTaskResult", data=json.dumps({
                    "clientKey": ckey, "taskId": tid,
                }).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dd = json.loads(r.read())
                if dd.get("status") == "ready":
                    return dd["solution"]["token"]
                if dd.get("status") != "processing":
                    raise RuntimeError("captcha: " + str(dd)[:120])
            raise RuntimeError("captcha timeout")

        token = cap_solve()
        print("капча решена", flush=True)

        name = f"aios-auto-{int(time.time())}"
        fetch_js = """
        (async () => {
          const token = %s;
          const org = %s;
          const project = %s;
          const name = %s;
          const jwt = document.cookie.split("; ").find(c => c.startsWith("stytch_session_jwt="));
          const auth = jwt ? ("Bearer " + jwt.split("=").slice(1).join("=")) : null;
          if (!auth) return JSON.stringify({stage: "nojwt"});
          try {
            const vt = await fetch("/api/vb-token/create", {method: "POST", headers: {"content-type": "application/json"}, body: JSON.stringify({cfToken: token})});
            const vtBody = await vt.json();
            const vb = vtBody && (vtBody.vb_token || vtBody.vbToken || vtBody.token);
            if (!vt.ok || !vb) return JSON.stringify({stage: "vb", status: vt.status, body: JSON.stringify(vtBody).slice(0, 300)});
            const qs = project ? ("?project_id=" + project) : "";
            const url = "https://api.groq.com/platform/v1/organizations/" + org + "/api_keys" + qs;
            const resp = await fetch(url, {method: "POST", headers: {"content-type": "application/json", "authorization": auth}, body: JSON.stringify({name: name, cf_token: token, vb_token: vb})});
            const txt = await resp.text();
            return JSON.stringify({stage: "create", status: resp.status, body: txt.slice(0, 700)});
          } catch(e) { return JSON.stringify({stage: "exc", err: String(e)}); }
        })()
        """ % (json.dumps(token), json.dumps(org), json.dumps(project), json.dumps(name))
        res = await cdp.ev(ws, fetch_js, await_promise=True)
        print("создание:", res, flush=True)
        if isinstance(res, str) and '"status":200' in res:
            body = json.loads(json.loads(res)["body"])
            return body.get("exposed_secret_key", "")
        return None

    return asyncio.run(_run())


def check(alert: bool = True, force: bool = False) -> dict:
    state = _read_state()
    out = {"keys": 0, "avg_remaining": None, "action": "none", "created": None}

    keys = _groq_keys()
    out["keys"] = len(keys)

    # Снапшот лимитов для дашборда (раз в час, не чаще)
    try:
        _last_lim = float(state.get("last_limits_snapshot") or 0)
        if time.time() - _last_lim >= 3600:
            _snap = {"checked_at": time.time(), "keys": [], "avg_remaining": None}
            for _k in keys:
                _rem = _remaining_requests(_k)
                _snap["keys"].append({"tail": _k[-6:], "remaining": _rem})
            _ok = [r for r in (_x["remaining"] for _x in _snap["keys"]) if r is not None]
            if _ok:
                _snap["avg_remaining"] = round(sum(_ok) / len(_ok), 1)
            _snap_dir = ROOT / "data" / "llm"
            _snap_dir.mkdir(parents=True, exist_ok=True)
            (_snap_dir / "groq_limits.json").write_text(
                json.dumps(_snap, indent=2), encoding="utf-8")
            state["last_limits_snapshot"] = time.time()
    except Exception:
        pass

    if len(keys) <= MIN_KEYS or force:
        remaining = [_remaining_requests(k) for k in keys]
        ok = [r for r in remaining if r is not None]
        if ok:
            out["avg_remaining"] = round(sum(ok) / len(ok), 1)
        need = (len(keys) < MIN_KEYS) or (ok and sum(ok) / len(ok) < RPM_THRESHOLD)
        if need:
            ckey = _captcha_key()
            if not ckey:
                out["action"] = "no_captcha_key"
                return out
            last_create = float(state.get("last_create_at") or 0)
            if time.time() - last_create < 3600 and not force:
                out["action"] = "throttled"
                return out
            print("создаём ключ...", flush=True)
            key = _create_key_via_browser(ckey)
            if key:
                name = f"aios-auto-{int(time.time())}"
                _append_key(key, name)
                out["created"] = key[-6:]
                out["action"] = "created"
                state["last_create_at"] = time.time()
                state["last_create_key_tail"] = key[-6:]
                _write_state(state)
                if alert:
                    _send(f"🔑 <b>Groq autopilot: создан новый ключ</b>\n`{key}`\nДобавлен в .env и ротацию.")
                # рестарт сервисов
                for svc in ("aios-telegram-bot", "aios-converge", "aios-olx-autoreply"):
                    subprocess.run(["systemctl", "restart", f"{svc}.service"], capture_output=True, timeout=30)
            else:
                out["action"] = "failed"
    state["last_check_at"] = int(time.time())
    _write_state(state)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Groq key autopilot")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--force", action="store_true", help="создать ключ даже если лимиты в норме")
    parser.add_argument("--no-alert", action="store_true")
    args = parser.parse_args()

    if args.check or args.force:
        print(json.dumps(check(alert=not args.no_alert, force=args.force), ensure_ascii=False), flush=True)
        return
    while True:
        print(json.dumps(check(alert=True), ensure_ascii=False), flush=True)
        time.sleep(3600)


if __name__ == "__main__":
    main()
