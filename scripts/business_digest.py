#!/usr/bin/env python3
"""AIOS Business Digest — единый TG/JSON дайджест доходных стримов (v22).

Собирает за 24ч:
  1. API-монетизация	(ledger списаний, клиенты, продукты)
  2. White-label        	(тенанты, черновики за 24ч)
  3. Фриланс-воронка   	(открытые ставки, pipeline, win-rate)
  4. OLX-склад          	(позиции, резервы, объявления)

CLI: python scripts/business_digest.py [--telegram] [--hours=24]
Cron: 9:15 daily (перед специализированными отчётами 9:30/10:00).
"""
import json
import os
import sys
import time
from pathlib import Path

BASE = "/root/AIOS"
sys.path.insert(0, BASE)
sys.path.insert(0, f"{BASE}/scripts")


def section_api(hours: float) -> dict:
    try:
        import api_usage_report as rep
        r = rep.build_report(hours)
        return {"ok": True, "revenue_usd": r["revenue_usd"], "events": r["events"],
                "by_client": r["by_client"], "by_product_usd": r["by_product_usd"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def section_whitelabel(hours: float) -> dict:
    try:
        from aios_core.whitelabel_ads import WhiteLabelAdsManager
        # white-label живёт на хосте (/root/AIOS/data), AIOS_DATA_DIR указывает
        # на docker-volume ledger — здесь нужен отдельный хостовый путь
        mgr = WhiteLabelAdsManager(
            data_dir=os.environ.get("AIOS_WL_DATA_DIR") or "/root/AIOS/data")
        tenants = mgr.list_tenants()
        since = time.time() - hours * 3600
        drafts = [d for t in tenants
                  for d in mgr.list_drafts(t["tenant_id"], limit=200)["drafts"]
                  if float(d.get("created_at", 0)) >= since]
        return {"ok": True, "tenants": len(tenants), "drafts_24h": len(drafts),
                "by_tenant": {t["company_name"]: sum(
                    1 for d in drafts if d.get("tenant_id") == t["tenant_id"])
                    for t in tenants}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def section_funnel() -> dict:
    try:
        import run_freelance_funnel as ff
        r = ff.build_report()
        return {"ok": True, "open_bids": r["open_bids"], "pipeline_usd": r["pipeline_open_usd"],
                "won": r["won"], "lost": r["lost"], "win_rate": r["win_rate_pct"],
                "proposals_ready": r.get("proposals_ready", 0),
                "proposals_ready_usd": r.get("proposals_ready_usd", 0)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def section_olx() -> dict:
    try:
        import io, contextlib
        import run_olx_pipeline as pipe
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            r = pipe.cmd_report(telegram=False)
        inv = r.get("inventory", {})
        return {"ok": True, "positions": inv.get("positions"), "qty": inv.get("total_qty"),
                "value_uah": inv.get("value_uah"),
                "published": r.get("published_ads", r.get("published")),
                "sales": r.get("sales", {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def build_digest(hours: float = 24.0) -> dict:
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "window_hours": hours,
        "api": section_api(hours),
        "whitelabel": section_whitelabel(hours),
        "funnel": section_funnel(),
        "olx": section_olx(),
    }


def tg_text(d: dict) -> str:
    L = [f"📈 <b>AIOS Business Digest</b> ({d['generated_at'][:16]} UTC)", ""]
    a = d["api"]
    if a["ok"]:
        L.append(f"💰 <b>API</b>: ${a['revenue_usd']:.2f} за {d['window_hours']:g}ч ({a['events']} запр.)")
        if a["by_product_usd"]:
            L.append("   " + ", ".join(f"{k} ${v:.2f}" for k, v in a["by_product_usd"].items()))
    else:
        L.append(f"💰 API: недоступно ({a['error'][:60]})")
    w = d["whitelabel"]
    if w["ok"]:
        L.append(f"🏷 <b>White-label</b>: {w['tenants']} тенант(а), черновиков за {d['window_hours']:g}ч: {w['drafts_24h']}")
        for c, n in w["by_tenant"].items():
            if n:
                L.append(f"   • {c}: {n}")
    f = d["funnel"]
    if f["ok"]:
        wr = f"{f['win_rate']}%" if f["win_rate"] is not None else "—"
        L.append(f"💼 <b>Фриланс</b>: {f['open_bids']} ставок (${f['pipeline_usd']:.0f}), "
                 f"win-rate {wr}, пропозалов ждёт: {f['proposals_ready']} (${f['proposals_ready_usd']:.0f})")
    o = d["olx"]
    if o["ok"]:
        pub = o.get("published") if isinstance(o.get("published"), int) else len(o.get("published") or [])
        L.append(f"🛒 <b>OLX-склад</b>: {o['positions']} позиций ({o['qty']} шт), "
                 f"на {o['value_uah'] or 0:.0f} грн; опубликовано: {pub}")
    L.append("")
    L.append("#дайджест #бизнес")
    return "\n".join(L)


def main():
    hours = 24.0
    tg = "--telegram" in sys.argv
    for arg in sys.argv:
        if arg.startswith("--hours="):
            hours = float(arg.split("=", 1)[1])
    d = build_digest(hours)
    if tg:
        from run_freelance_funnel import send_tg
        ok = send_tg(tg_text(d))
        print(json.dumps({"telegram_sent": ok}, ensure_ascii=False))
    else:
        print(tg_text(d))
        print()
        print(json.dumps(d, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
