#!/usr/bin/env python3
"""
Создание API-ключей Groq в текущей сессии браузера (вкладка console.groq.com/keys).
Использование: python make_keys.py <count> <prefix> <2captcha_key> <org> <project>
"""
import asyncio, json, sys, time, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import cdp_help as cdp
except ImportError:
    # cdp_help.py должен лежать рядом
    print("cdp_help.py не найден — положите рядом (см. /root/AIOS/tools/browser_cdp)")
    sys.exit(2)

COUNT = int(sys.argv[1])
PREFIX = sys.argv[2]
CAPTCHA_KEY = sys.argv[3]
ORG = sys.argv[4]
PROJECT = sys.argv[5]

FETCH_TPL = """
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
"""


def cap_solve() -> str:
    """Получить turnstile-токен через 2captcha."""
    req = urllib.request.Request("https://api.2captcha.com/createTask", data=json.dumps({
        "clientKey": CAPTCHA_KEY,
        "task": {"type": "TurnstileTaskProxyless", "websiteURL": "https://console.groq.com/keys", "websiteKey": "0x4AAAAAAA04hiaY8r8_QF1r"},
    }).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        task_id = json.loads(r.read())["taskId"]
    for _ in range(40):
        time.sleep(8)
        req = urllib.request.Request("https://api.2captcha.com/getTaskResult", data=json.dumps({
            "clientKey": CAPTCHA_KEY, "taskId": task_id,
        }).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        if d.get("status") == "ready":
            return d["solution"]["token"]
        if d.get("status") != "processing":
            raise RuntimeError("captcha error: " + str(d)[:200])
    raise RuntimeError("captcha timeout")


async def main() -> None:
    pages = cdp.list_pages()
    t = next((x for x in pages if x["url"].startswith("https://console.groq.com/keys")), None)
    if t is None:
        print("Вкладка console.groq.com/keys не найдена — откройте её в Chrome (CDP 9222)")
        return
    ws = await cdp.connect(t["webSocketDebuggerUrl"])
    made = []
    for i in range(1, COUNT + 1):
        name = f"{PREFIX}-{i}" if COUNT > 1 else PREFIX
        token = cap_solve()
        print(f"[{i}] captcha ok ({len(token)} симв.)", flush=True)
        fetch_js = FETCH_TPL % (json.dumps(token), json.dumps(ORG), json.dumps(PROJECT), json.dumps(name))
        res = await cdp.ev(ws, fetch_js, await_promise=True)
        print(f"[{i}] {res}", flush=True)
        if isinstance(res, str) and '"status":200' in res:
            try:
                body = json.loads(json.loads(res)["body"])
                made.append((name, body.get("exposed_secret_key", "")))
            except Exception as exc:  # noqa: BLE001
                print(f"[{i}] parse: {exc}", flush=True)
        else:
            print(f"[{i}] FAILED", flush=True)
            break
    print("MADE:", json.dumps(made), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
