"""AIOS White-Label OLX Automation — v22 «Platform» groundwork.

Автоназборка-клиент получает готовые OLX-объявления в СВОЁМ стиле
(компания, контакты, наценка, язык) — черновики на модерацию, публикация
только за approve владельца платформы (chrome-twin live path отдельный).

Тенанты: data/whitelabel/{tenant_id}.json — конфиг бренда.
Черновики: data/whitelabel_drafts.json — с tenant_id; изоляция по тенанту.
Квоты: Tenant из multitenancy.py (in-memory) + жёсткий дневной лимит
по персистентным черновикам (переживает рестарт).
"""
from __future__ import annotations

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # direct-run CLI

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aios_core.multitenancy import MultiTenantManager

logger = logging.getLogger("AIOS.WhiteLabelAds")

DEFAULT_DATA_DIR = "/root/AIOS/data"

DEFAULT_TENANT_CFG = {
    "lang": "ru",
    "style_footer": "",
    "phone": "",
    "markup_pct": 10.0,
    "ads_quota_per_day": 50,
    "active": True,
}


class WhiteLabelAdsManager:
    """Tenant-конфиги брендов + изолированные черновики объявлений."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.tenants_dir = self.data_dir / "whitelabel"
        self.drafts_file = self.data_dir / "whitelabel_drafts.json"
        self.tenants_dir.mkdir(parents=True, exist_ok=True)
        self.mtm = MultiTenantManager()  # политики квот/изоляции (in-memory)

    # ------------------------------------------------------------------
    # Tenants CRUD
    # ------------------------------------------------------------------
    def _tenant_path(self, tenant_id: str) -> Path:
        safe = "".join(c for c in tenant_id if c.isalnum() or c in ("-", "_"))
        return self.tenants_dir / f"{safe}.json"

    def create_tenant(self, tenant_id: str, name: str, company_name: str,
                      lang: str = "ru", style_footer: str = "", phone: str = "",
                      markup_pct: float = 10.0, ads_quota_per_day: int = 50) -> Dict[str, Any]:
        """Регистрирует white-label клиента (автоназборку)."""
        if self._tenant_path(tenant_id).exists():
            return {"status": "error", "error": f"tenant {tenant_id} already exists"}
        cfg = {
            "tenant_id": tenant_id,
            "name": name,
            "company_name": company_name,
            "lang": lang,
            "style_footer": style_footer,
            "phone": phone,
            "markup_pct": float(markup_pct),
            "ads_quota_per_day": int(ads_quota_per_day),
            "active": True,
            "created_at": time.time(),
        }
        self._tenant_path(tenant_id).write_text(json.dumps(cfg, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
        # in-memory политика: квота черновиков/день
        t = self.mtm.create_tenant(tenant_id, name)
        t.set_quota("ads_drafts_day", int(ads_quota_per_day))
        logger.info(f"🏷 [WhiteLabel] Tenant {tenant_id} ({company_name}) создан, наценка {markup_pct}%")
        return {"status": "ok", "tenant": cfg}

    def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        p = self._tenant_path(tenant_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def list_tenants(self) -> List[Dict[str, Any]]:
        out = []
        for f in sorted(self.tenants_dir.glob("*.json")):
            try:
                cfg = json.loads(f.read_text(encoding="utf-8"))
                out.append({k: cfg.get(k) for k in
                            ("tenant_id", "name", "company_name", "markup_pct", "active")})
            except Exception:
                continue
        return out

    # ------------------------------------------------------------------
    # Drafts
    # ------------------------------------------------------------------
    def _load_drafts(self) -> List[Dict[str, Any]]:
        if not self.drafts_file.exists():
            return []
        try:
            return json.loads(self.drafts_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_drafts(self, drafts: List[Dict[str, Any]]) -> None:
        self.drafts_file.write_text(json.dumps(drafts, ensure_ascii=False, indent=1),
                                    encoding="utf-8")

    def _drafts_today(self, tenant_id: str) -> int:
        day_start = time.time() - (time.time() % 86400)
        return sum(1 for d in self._load_drafts()
                   if d.get("tenant_id") == tenant_id and float(d.get("created_at", 0)) >= day_start)

    def generate_draft(self, tenant_id: str, part_name: str,
                       base_price_uah: Optional[float] = None) -> Dict[str, Any]:
        """Черновик объявления в стиле бренда тенанта. Публикации здесь НЕТ."""
        cfg = self.get_tenant(tenant_id)
        if not cfg:
            return {"status": "error", "error": f"unknown tenant {tenant_id}"}
        if not cfg.get("active"):
            return {"status": "error", "error": f"tenant {tenant_id} suspended"}

        # квота: персистентный дневной лимит (переживает рестарт)
        today = self._drafts_today(tenant_id)
        quota = int(cfg.get("ads_quota_per_day", 50))
        if today >= quota:
            return {"status": "error", "error": f"quota exceeded: {quota} drafts/day used",
                    "used": today, "quota": quota}
        # in-memory страховка из multitenancy
        mem_t = self.mtm.get_tenant(tenant_id)
        if mem_t is not None and not mem_t.check_quota("ads_drafts_day", 1):
            return {"status": "error", "error": "in-memory quota guard: ads_drafts_day"}

        import run_olx_ad_gen as adgen
        gen = adgen.generate(part_name)
        if gen.get("status") != "ok":
            return {"status": "error", "error": gen.get("error", "generation failed"),
                    "part": part_name}

        # цена: base_price × (1 + markup%) > цена генератора
        price = ""
        if base_price_uah:
            price = str(int(round(float(base_price_uah) * (1 + cfg.get("markup_pct", 0) / 100.0))))
        elif str(gen.get("price") or "").strip():
            price = str(gen["price"]).strip()

        # брендовый футер
        footer_parts = [str(cfg.get("style_footer") or "").strip()]
        contact = ", ".join(x for x in (str(cfg.get("company_name") or "").strip(),
                                       str(cfg.get("phone") or "").strip()) if x)
        if contact:
            footer_parts.append(contact)
        footer = "\n".join(p for p in footer_parts if p)

        description = str(gen.get("description") or "").strip()
        if footer:
            description = f"{description}\n\n{footer}" if description else footer

        draft = {
            "id": f"wld_{uuid.uuid4().hex[:10]}",
            "tenant_id": tenant_id,
            "part": part_name,
            "title": str(gen.get("title") or part_name)[:60],
            "description": description,
            "price_uah": price,
            "status": "draft",                 # draft → (owner approve) → publish
            "created_at": time.time(),
        }
        drafts = self._load_drafts()
        drafts.append(draft)
        self._save_drafts(drafts)
        if mem_t is not None:
            mem_t.record_usage(tasks=1)
        logger.info(f"🏷 [WhiteLabel] {tenant_id}: черновик '{draft['title'][:40]}' {price} грн")
        return {"status": "ok", "draft": draft, "used_today": today + 1, "quota": quota}

    def list_drafts(self, tenant_id: str, limit: int = 50) -> Dict[str, Any]:
        """Только черновики ЭТОГО тенанта (изоляция по данных)."""
        mine = [d for d in self._load_drafts() if d.get("tenant_id") == tenant_id]
        mine.sort(key=lambda d: -float(d.get("created_at", 0)))
        return {"status": "ok", "tenant_id": tenant_id, "count": len(mine),
                "drafts": mine[:limit]}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    mgr = WhiteLabelAdsManager()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "create":
        # create <id> <name> <company> [phone]
        r = mgr.create_tenant(sys.argv[2], sys.argv[3], sys.argv[4],
                              phone=sys.argv[5] if len(sys.argv) > 5 else "")
    elif cmd == "draft":
        # draft <tenant_id> <part> [price]
        r = mgr.generate_draft(sys.argv[2], sys.argv[3],
                               base_price_uah=float(sys.argv[4]) if len(sys.argv) > 4 else None)
    elif cmd == "drafts":
        r = mgr.list_drafts(sys.argv[2])
    else:
        r = {"status": "ok", "tenants": mgr.list_tenants()}
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
