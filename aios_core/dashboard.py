"""AIOS Web Dashboard v4 "AdminLTE-style" — full-featured SPA.

Adds endpoints for services control, OLX browsing, logs, subscriptions, analytics.
The SPA itself lives at dashboard/index.html and is served at '/'.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
from pathlib import Path
from datetime import UTC, datetime

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from .orchestrator import Orchestrator

_DASHBOARD_HTML_PATH = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

# Systemd services we manage
AIOS_SERVICES = [
    ("aios-api", "REST API", 8500),
    ("aios-mcp", "MCP Server", 8571),
    ("aios-dash", "Dashboard", 8580),
    ("aios-tg", "Telegram Bot", None),
    ("aios-olx-collector", "OLX Collector", None),
]


class AIOSDashboard:
    """Full admin dashboard."""

    def __init__(self, orchestrator: Orchestrator):
        self.orch = orchestrator
        self.ads_db = os.environ.get(
            "AIOS_OLX_HTTP_DB", "/root/AIOS/data/olx_http.sqlite"
        )
        self.subs_db = "/root/AIOS/data/olx_subs.sqlite"

    # ---------- Pages ----------
    async def index(self, request: Request) -> HTMLResponse:
        if _DASHBOARD_HTML_PATH.exists():
            html = _DASHBOARD_HTML_PATH.read_text(encoding="utf-8")
            return HTMLResponse(html)
        return HTMLResponse("<h1>Dashboard HTML missing</h1>", status_code=500)

    # ---------- System stats ----------
    async def api_stats(self, request: Request) -> JSONResponse:
        return JSONResponse(self.orch.stats())

    async def api_health(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "status": "ok",
            "version": self.orch.version,
            "time": datetime.now(UTC).isoformat(),
        })

    # ---------- Services management ----------
    def _svc_status(self, name: str) -> dict:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, text=True, timeout=5,
            )
            active = r.stdout.strip()
            r2 = subprocess.run(
                ["systemctl", "is-enabled", name],
                capture_output=True, text=True, timeout=5,
            )
            enabled = r2.stdout.strip()
            uptime = ""
            r3 = subprocess.run(
                ["systemctl", "show", name, "-p", "ActiveEnterTimestamp",
                 "--value"],
                capture_output=True, text=True, timeout=5,
            )
            uptime = r3.stdout.strip()
            return {
                "name": name, "active": active == "active",
                "state": active, "enabled": enabled == "enabled",
                "since": uptime,
            }
        except Exception as e:
            return {"name": name, "active": False, "state": "error",
                    "enabled": False, "since": "", "error": str(e)}

    async def api_services(self, request: Request) -> JSONResponse:
        result = []
        for svc, label, port in AIOS_SERVICES:
            d = self._svc_status(svc)
            d["label"] = label
            d["port"] = port
            result.append(d)
        # Also emulator
        try:
            adb = os.environ.get("ADB", "/opt/android-sdk/platform-tools/adb")
            r = subprocess.run([adb, "devices"], capture_output=True,
                               text=True, timeout=5)
            emu_online = "emulator-5554\tdevice" in r.stdout
        except Exception:
            emu_online = False
        result.append({
            "name": "emulator", "label": "Android Emulator (OLX)",
            "port": 5554, "active": emu_online, "state": "online" if emu_online else "offline",
            "enabled": True, "since": "",
        })
        return JSONResponse({"services": result})

    async def api_service_action(self, request: Request) -> JSONResponse:
        name = request.path_params["name"]
        body = await request.json()
        action = body.get("action")
        allowed = {"restart", "start", "stop"}
        if action not in allowed:
            return JSONResponse({"ok": False, "error": "bad action"}, status_code=400)
        allowed_names = [s[0] for s in AIOS_SERVICES]
        if name not in allowed_names:
            return JSONResponse({"ok": False, "error": "unknown service"}, status_code=404)
        try:
            subprocess.run(["systemctl", action, name], capture_output=True,
                           text=True, timeout=15)
            return JSONResponse({"ok": True})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    async def api_service_logs(self, request: Request) -> StreamingResponse:
        name = request.path_params["name"]
        n = int(request.query_params.get("n", "200"))
        allowed_names = [s[0] for s in AIOS_SERVICES]
        if name not in allowed_names:
            return JSONResponse({"error": "unknown"}, status_code=404)

        async def gen():
            try:
                proc = subprocess.Popen(
                    ["journalctl", "-u", name, "-n", str(n), "--no-pager"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                )
                for line in proc.stdout:
                    yield line
                proc.wait()
            except Exception as e:
                yield f"--- error: {e}\n"
        return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")

    # ---------- OLX HTTP collector ----------
    async def api_olx(self, request: Request) -> JSONResponse:
        if not os.path.exists(self.ads_db):
            return JSONResponse({"available": False})
        try:
            conn = sqlite3.connect(f"file:{self.ads_db}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                total = conn.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
                active = conn.execute(
                    "SELECT COUNT(*) FROM ads WHERE active=1"
                ).fetchone()[0]
                queries = [r[0] for r in conn.execute(
                    "SELECT query FROM ads WHERE active=1 "
                    "GROUP BY query ORDER BY COUNT(*) DESC").fetchall()]
                last_run = conn.execute(
                    "SELECT ts, parsed, inserted, deactivated "
                    "FROM collection_runs ORDER BY ts DESC LIMIT 1"
                ).fetchone()
                price_row = conn.execute(
                    "SELECT AVG(price_value), MIN(price_value), MAX(price_value) "
                    "FROM ads WHERE price_value>0 AND price_currency='UAH'"
                ).fetchone()
                new_1h = conn.execute(
                    "SELECT COUNT(*) FROM ads WHERE first_seen >= "
                    "datetime('now','-1 hour')").fetchone()[0]
                new_24h = conn.execute(
                    "SELECT COUNT(*) FROM ads WHERE first_seen >= "
                    "datetime('now','-1 day')").fetchone()[0]
                return JSONResponse({
                    "available": True,
                    "source": "http",
                    "ads_total": total, "ads_active": active,
                    "new_1h": new_1h, "new_24h": new_24h,
                    "queries_tracked": queries,
                    "last_run_ts": last_run["ts"] if last_run else None,
                    "last_run_parsed": last_run["parsed"] if last_run else 0,
                    "last_run_inserted": last_run["inserted"] if last_run else 0,
                    "last_run_deactivated": last_run["deactivated"] if last_run else 0,
                    "price_avg": price_row[0],
                    "price_min": price_row[1],
                    "price_max": price_row[2],
                })
            finally:
                conn.close()
        except Exception as e:
            return JSONResponse({"available": False, "error": str(e)})

    async def api_olx_list(self, request: Request) -> JSONResponse:
        if not os.path.exists(self.ads_db):
            return JSONResponse({"ads": [], "total": 0})
        q = request.query_params.get("query", "")
        page = max(1, int(request.query_params.get("page", "1")))
        limit = min(100, int(request.query_params.get("limit", "25")))
        offset = (page - 1) * limit
        sort = request.query_params.get("sort", "new")  # new/cheap/expensive
        min_p = request.query_params.get("min")
        max_p = request.query_params.get("max")
        only_negotiable = request.query_params.get("negotiable") == "1"
        only_business = request.query_params.get("business") == "1"
        conn = sqlite3.connect(f"file:{self.ads_db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            where = ["active=1"]
            params = []
            if q:
                where.append("(query=? OR title LIKE ? OR description LIKE ?)")
                params += [q, f"%{q}%", f"%{q}%"]
            if min_p:
                where.append("(price_value IS NULL OR price_value >= ?)")
                params.append(float(min_p))
            if max_p:
                where.append("(price_value IS NULL OR price_value <= ?)")
                params.append(float(max_p))
            if only_negotiable:
                where.append("negotiable=1")
            if only_business:
                where.append("business=1")
            wsql = " AND ".join(where)
            if sort == "cheap":
                order = "price_value IS NULL, price_value ASC"
            elif sort == "expensive":
                order = "price_value IS NULL, price_value DESC"
            else:
                order = "first_seen DESC, collected_at DESC"
            total = conn.execute(
                f"SELECT COUNT(*) FROM ads WHERE {wsql}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM ads WHERE {wsql} ORDER BY {order} "
                f"LIMIT ? OFFSET ?", params + [limit, offset]
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d["photos"] = json.loads(d.pop("photos_json") or "[]")
                out.append(d)
            return JSONResponse({
                "ads": out, "total": total, "page": page,
                "limit": limit, "pages": (total + limit - 1) // limit,
            })
        finally:
            conn.close()

    async def api_olx_queries(self, request: Request) -> JSONResponse:
        if not os.path.exists(self.ads_db):
            return JSONResponse({"queries": []})
        conn = sqlite3.connect(f"file:{self.ads_db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT query, COUNT(*) as cnt, AVG(price_value) as avg_p, "
                "MIN(price_value) as min_p, MAX(price_value) as max_p "
                "FROM ads WHERE active=1 AND price_currency='UAH' "
                "GROUP BY query ORDER BY cnt DESC"
            ).fetchall()
            return JSONResponse({
                "queries": [
                    {"query": r[0], "count": r[1], "avg": r[2], "min": r[3], "max": r[4]}
                    for r in rows
                ]
            })
        finally:
            conn.close()

    async def api_olx_analytics(self, request: Request) -> JSONResponse:
        if not os.path.exists(self.ads_db):
            return JSONResponse({"available": False})
        query = request.query_params.get("query", "")
        conn = sqlite3.connect(f"file:{self.ads_db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # Price distribution (buckets)
            if not query:
                return JSONResponse({"available": False, "error": "query required"})
            vals = [r[0] for r in conn.execute(
                "SELECT price_value FROM ads WHERE query=? AND active=1 "
                "AND price_currency='UAH' AND price_value>0 "
                "AND price_value < (SELECT AVG(price_value)*5 FROM ads "
                "                  WHERE query=? AND active=1 AND price_currency='UAH')",
                (query, query)).fetchall()]
            if not vals:
                return JSONResponse({"available": False, "error": "no data"})
            vals.sort()
            n = len(vals)
            def pct(p):
                k = (n - 1) * p
                f = int(k); c = min(f + 1, n - 1)
                return vals[f] + (vals[c] - vals[f]) * (k - f)
            # Histogram: 20 buckets between p1 and p99
            lo, hi = pct(0.05), pct(0.95)
            if hi <= lo:
                hi = lo + 1
            buckets = [0] * 20
            for v in vals:
                if lo <= v <= hi:
                    idx = min(19, int((v - lo) / (hi - lo) * 19.99))
                    buckets[idx] += 1
            bucket_labels = [
                f"{int(lo + (hi-lo)*i/20):,}-{int(lo + (hi-lo)*(i+1)/20):,}"
                for i in range(20)
            ]
            # Top 10 cheapest
            cheapest = [dict(r) for r in conn.execute(
                "SELECT id, title, price_value, url, city, user_name, business "
                "FROM ads WHERE query=? AND active=1 AND price_currency='UAH' "
                "AND price_value>0 ORDER BY price_value ASC LIMIT 10", (query,))]
            # Most expensive (top 5)
            pricy = [dict(r) for r in conn.execute(
                "SELECT id, title, price_value, url, city FROM ads "
                "WHERE query=? AND active=1 AND price_currency='UAH' "
                "AND price_value>0 ORDER BY price_value DESC LIMIT 5", (query,))]
            # New in last 24h
            new_count = conn.execute(
                "SELECT COUNT(*) FROM ads WHERE query=? AND active=1 "
                "AND first_seen >= datetime('now','-1 day')", (query,)).fetchone()[0]
            # City distribution top 8
            cities = [{"city": r[0], "count": r[1]} for r in conn.execute(
                "SELECT city, COUNT(*) c FROM ads WHERE query=? AND active=1 "
                "AND city IS NOT NULL GROUP BY city ORDER BY c DESC LIMIT 8",
                (query,)).fetchall()]
            # Business vs private
            biz = conn.execute(
                "SELECT business, COUNT(*) FROM ads WHERE query=? AND active=1 "
                "GROUP BY business", (query,)).fetchall()
            biz_count = dict(biz)
            # New over time (per day, last 7 days — using first_seen)
            daily_new = [{"day": r[0], "count": r[1]} for r in conn.execute(
                "SELECT date(first_seen), COUNT(*) FROM ads WHERE query=? "
                "AND first_seen >= datetime('now','-7 day') "
                "GROUP BY date(first_seen) ORDER BY date(first_seen)",
                (query,)).fetchall()]
            return JSONResponse({
                "available": True,
                "query": query,
                "count": n,
                "min": vals[0], "max": vals[-1],
                "avg": sum(vals) / n,
                "median": pct(0.5),
                "p10": pct(0.10), "p25": pct(0.25),
                "p75": pct(0.75), "p90": pct(0.90),
                "p95": pct(0.95),
                "histogram": {"labels": bucket_labels, "counts": buckets},
                "cheapest": cheapest,
                "priciest": pricy,
                "new_24h": new_count,
                "cities": cities,
                "business_count": biz_count.get(1, 0),
                "private_count": biz_count.get(0, 0),
                "daily_new": daily_new,
            })
        finally:
            conn.close()

    async def api_olx_trigger_collect(self, request: Request) -> JSONResponse:
        """Kick off one collection cycle by restarting the collector service
        (it runs immediately on start)."""
        try:
            subprocess.run(["systemctl", "restart", "aios-olx-collector"],
                           capture_output=True, timeout=10)
            return JSONResponse({"ok": True})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    # ---------- Telegram subscriptions ----------
    async def api_subs(self, request: Request) -> JSONResponse:
        if not os.path.exists(self.subs_db):
            return JSONResponse({"subscriptions": [], "chats": 0})
        conn = sqlite3.connect(f"file:{self.subs_db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            subs = [dict(r) for r in conn.execute(
                "SELECT s.chat_id, s.query, s.min_price, s.max_price, s.created_at, "
                "sub.username, sub.first_name FROM subscriptions s "
                "JOIN subscribers sub ON sub.chat_id=s.chat_id "
                "ORDER BY s.query, s.chat_id").fetchall()]
            chat_count = conn.execute(
                "SELECT COUNT(*) FROM subscribers WHERE enabled=1").fetchone()[0]
            return JSONResponse({"subscriptions": subs, "chats": chat_count})
        finally:
            conn.close()

    async def api_subs_action(self, request: Request) -> JSONResponse:
        body = await request.json()
        chat_id = body.get("chat_id")
        query = (body.get("query") or "").strip()
        action = body.get("action")
        sys_path = Path(__file__).resolve().parent.parent.parent
        import sys as _sys
        if str(sys_path) not in _sys.path:
            _sys.path.insert(0, str(sys_path))
        import olx_alerts
        conn = olx_alerts.init_subs_db(self.subs_db)
        if action == "add" and query:
            olx_alerts.subscribe_chat(
                conn, int(chat_id), query,
                min_price=body.get("min_price"),
                max_price=body.get("max_price"))
            return JSONResponse({"ok": True})
        if action == "remove":
            olx_alerts.unsubscribe_chat(conn, int(chat_id), query or None)
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "bad action"}, status_code=400)

    # ---------- Android / ADB control ----------
    ADB = "/opt/android-sdk/platform-tools/adb"

    def _adb(self, *args, serial=None, timeout=30, binary=False):
        cmd = [self.ADB]
        if serial:
            cmd += ["-s", str(serial)]
        cmd += list(args)
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        if binary:
            return r.returncode, r.stdout, r.stderr
        return r.returncode, r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace")

    def _default_serial(self):
        code, out, _ = self._adb("devices")
        for line in out.splitlines()[1:]:
            line = line.strip()
            if line.endswith("\tdevice") or line.endswith(" device"):
                return line.split()[0]
        return None

    async def api_android_devices(self, request: Request) -> JSONResponse:
        try:
            code, out, err = self._adb("devices", "-l")
            devs = []
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    serial = parts[0]
                    info = {"serial": serial, "status": "online"}
                    # Props (model)
                    rc, model, _ = self._adb("shell", "getprop", "ro.product.model", serial=serial, timeout=5)
                    rc2, android, _ = self._adb("shell", "getprop", "ro.build.version.release", serial=serial, timeout=5)
                    rc3, pkg, _ = self._adb("shell", "dumpsys", "window", "|", "grep", "mCurrentFocus", serial=serial, timeout=5)
                    # dumpsys window mCurrentFocus does not work with pipe via list args
                    info["model"] = model.strip()
                    info["android"] = android.strip()
                    # Foreground app via simpler cmd
                    rc4, fore, _ = self._adb("shell", "cmd", "activity", "get-foreground-activity", serial=serial, timeout=5)
                    info["foreground"] = fore.strip() if rc == 0 else ""
                    devs.append(info)
            # Screenshot dir
            shot_dir = Path("/root/AIOS/screenshots")
            shot_dir.mkdir(parents=True, exist_ok=True)
            return JSONResponse({"devices": devs, "count": len(devs)})
        except Exception as e:
            return JSONResponse({"devices": [], "count": 0, "error": str(e)})

    async def api_android_screenshot(self, request: Request) -> JSONResponse:
        serial = request.query_params.get("serial") or self._default_serial()
        if not serial:
            return JSONResponse({"ok": False, "error": "no device"}, status_code=404)
        try:
            import base64
            shot_dir = Path("/root/AIOS/screenshots")
            shot_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            fn = shot_dir / f"shot_{serial.replace(':','_')}_{ts}.png"
            # screencap -p outputs png to stdout
            r = subprocess.run(
                [self.ADB, "-s", serial, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=15,
            )
            if r.returncode != 0 or not r.stdout:
                # Fallback: pull
                self._adb("shell", "screencap", "-p", "/sdcard/screen.png", serial=serial)
                self._adb("pull", "/sdcard/screen.png", str(fn), serial=serial)
                data = fn.read_bytes()
            else:
                data = r.stdout
                fn.write_bytes(data)
            b64 = base64.b64encode(data).decode()
            return JSONResponse({"ok": True, "serial": serial,
                                 "ts": ts, "size": len(data),
                                 "image": "data:image/png;base64," + b64})
        except subprocess.TimeoutExpired:
            return JSONResponse({"ok": False, "error": "screenshot timeout"}, status_code=504)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    async def api_android_action(self, request: Request) -> JSONResponse:
        body = await request.json()
        serial = body.get("serial") or self._default_serial()
        if not serial:
            return JSONResponse({"ok": False, "error": "no device"}, status_code=404)
        action = body.get("action")
        try:
            if action == "tap":
                x, y = int(body["x"]), int(body["y"])
                c, o, e = self._adb("shell", "input", "tap", str(x), str(y), serial=serial)
            elif action == "swipe":
                c, o, e = self._adb("shell", "input", "swipe",
                                    str(int(body["x1"])), str(int(body["y1"])),
                                    str(int(body["x2"])), str(int(body["y2"])),
                                    str(int(body.get("duration", 300))), serial=serial)
            elif action == "text":
                text = body.get("text", "")
                # Use adb_type.py helper that base64-encodes (handles $, quotes, spaces)
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "adb_type", "/root/AIOS/adb_type.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                ok = mod.type_text(serial, text)
                return JSONResponse({"ok": ok, "serial": serial})
            elif action == "key":
                keycode = int(body.get("keycode", 66))  # 66=ENTER
                c, o, e = self._adb("shell", "input", "keyevent", str(keycode), serial=serial)
            elif action == "shell":
                cmd = body.get("command", "")
                if not cmd or ";" in cmd or "|" in cmd or "&&" in cmd or "rm -rf" in cmd:
                    return JSONResponse({"ok": False, "error": "dangerous chars blocked"})
                c, o, e = self._adb("shell", *cmd.split(), serial=serial, timeout=15)
                return JSONResponse({"ok": c == 0, "serial": serial, "stdout": o, "stderr": e,
                                     "exit": c})
            elif action == "launch":
                pkg = body.get("package", "ua.slando")
                c, o, e = self._adb("shell", "monkey", "-p", pkg,
                                    "-c", "android.intent.category.LAUNCHER", "1", serial=serial)
            elif action == "home":
                c, o, e = self._adb("shell", "input", "keyevent", "3", serial=serial)
            elif action == "back":
                c, o, e = self._adb("shell", "input", "keyevent", "4", serial=serial)
            elif action == "recents":
                c, o, e = self._adb("shell", "input", "keyevent", "187", serial=serial)
            elif action == "power":
                c, o, e = self._adb("shell", "input", "keyevent", "26", serial=serial)
            elif action == "uidump":
                # Pull UI hierarchy XML
                self._adb("shell", "uiautomator", "dump", "/sdcard/ui.xml", serial=serial, timeout=60)
                r = subprocess.run([self.ADB, "-s", serial, "exec-out", "cat", "/sdcard/ui.xml"],
                                   capture_output=True, timeout=15)
                if r.returncode != 0 or len(r.stdout) < 50:
                    r2 = subprocess.run([self.ADB, "-s", serial, "pull", "/sdcard/ui.xml", "/tmp/uidump.xml"],
                                        capture_output=True, timeout=10)
                    xml = Path("/tmp/uidump.xml").read_text(encoding="utf-8", errors="replace")
                else:
                    xml = r.stdout.decode("utf-8", errors="replace")
                # Parse clickable nodes for overlay
                import xml.etree.ElementTree as ET
                nodes = []
                try:
                    root = ET.fromstring(xml)
                    for node in root.iter("node"):
                        a = node.attrib
                        if a.get("clickable") == "true" or a.get("focusable") == "true" or a.get("text"):
                            try:
                                bb = a.get("bounds", "[0,0][0,0]")
                                coords = bb.strip("[]").split("][")
                                x1, y1 = map(int, coords[0].split(","))
                                x2, y2 = map(int, coords[1].split(","))
                                nodes.append({
                                    "text": (a.get("text") or a.get("content-desc") or "")[:80],
                                    "class": (a.get("class") or "").split(".")[-1],
                                    "bounds": bb,
                                    "x": (x1+x2)//2, "y": (y1+y2)//2,
                                    "clickable": a.get("clickable") == "true",
                                    "checkable": a.get("checkable") == "true",
                                    "checked": a.get("checked") == "true",
                                    "scrollable": a.get("scrollable") == "true",
                                })
                            except Exception:
                                pass
                except ET.ParseError:
                    pass
                return JSONResponse({"ok": True, "serial": serial,
                                     "xml": xml[:200000], "nodes": nodes[:500]})
            else:
                return JSONResponse({"ok": False, "error": f"unknown action: {action}"}, status_code=400)
            return JSONResponse({"ok": c == 0, "serial": serial, "stdout": o[-1000:], "stderr": e[-1000:], "exit": c})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    async def api_android_emuctl(self, request: Request) -> JSONResponse:
        """Save/load snapshot, cold boot."""
        body = await request.json()
        action = body.get("action")
        avd = body.get("avd", "AIOS_OLX")
        emu = "/opt/android-sdk/emulator/emulator"
        # Simpler: support save snapshot only via adb emu command
        try:
            if action == "save":
                name = body.get("name", "logged_in")
                c, o, e = self._adb("emu", "avd", "snapshot", "save", name, serial="emulator-5554", timeout=60)
                return JSONResponse({"ok": c == 0, "stdout": o, "stderr": e})
            if action == "list_packages":
                c, o, e = self._adb("shell", "pm", "list", "packages", "-3", serial="emulator-5554", timeout=15)
                pkgs = sorted([l.replace("package:", "").strip() for l in o.splitlines() if l.startswith("package:")])
                return JSONResponse({"ok": True, "packages": pkgs})
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
        return JSONResponse({"ok": False, "error": "bad action"}, status_code=400)

    # ---------- Routing ----------
    def create_app(self) -> Starlette:
        routes = [
            Route("/", self.index),
            Route("/api/stats", self.api_stats),
            Route("/health", self.api_health),
            Route("/api/health", self.api_health),
            Route("/api/olx", self.api_olx),
            Route("/api/olx/list", self.api_olx_list),
            Route("/api/olx/queries", self.api_olx_queries),
            Route("/api/olx/analytics", self.api_olx_analytics),
            Route("/api/olx/collect", self.api_olx_trigger_collect, methods=["POST"]),
            Route("/api/services", self.api_services),
            Route("/api/services/{name}/action", self.api_service_action,
                  methods=["POST"]),
            Route("/api/services/{name}/logs", self.api_service_logs),
            Route("/api/subs", self.api_subs),
            Route("/api/subs/action", self.api_subs_action, methods=["POST"]),
            Route("/api/android/devices", self.api_android_devices),
            Route("/api/android/screenshot", self.api_android_screenshot),
            Route("/api/android/action", self.api_android_action, methods=["POST"]),
            Route("/api/android/emu", self.api_android_emuctl, methods=["POST"]),
        ]
        return Starlette(routes=routes)


def create_dashboard(orchestrator: Orchestrator) -> Starlette:
    d = AIOSDashboard(orchestrator)
    return d.create_app()
