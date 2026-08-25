"""v22 digest tests: build_digest structure + tg_text rendering."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def _patch_sections(monkeypatch, bd):
    monkeypatch.setattr(
        bd,
        "section_api",
        lambda hours: {"ok": True, "revenue_usd": 0.0, "events": 0, "by_product_usd": {}},
    )
    monkeypatch.setattr(
        bd,
        "section_whitelabel",
        lambda hours: {"ok": True, "tenants": 0, "drafts_24h": 0, "by_tenant": {}},
    )
    monkeypatch.setattr(
        bd,
        "section_funnel",
        lambda: {
            "ok": True,
            "open_bids": 0,
            "pipeline_usd": 0.0,
            "win_rate": None,
            "proposals_ready": 0,
            "proposals_ready_usd": 0.0,
        },
    )
    monkeypatch.setattr(
        bd,
        "section_olx",
        lambda: {"ok": True, "positions": 0, "qty": 0, "value_uah": 0.0, "published": 0},
    )


def test_digest_structure_and_text(monkeypatch):
    import business_digest as bd

    _patch_sections(monkeypatch, bd)
    d = bd.build_digest(24.0)
    assert set(d.keys()) == {"generated_at", "window_hours", "api", "whitelabel", "funnel", "olx"}
    assert d["window_hours"] == 24.0
    # секции живые (данные реальные read-only)
    assert d["funnel"].get("ok") is True
    assert d["whitelabel"].get("ok") is True

    text = bd.tg_text(d)
    for marker in ("Business Digest", "API", "White-label", "Фриланс", "OLX-склад", "#дайджест"):
        assert marker in text, f"missing: {marker}"


def test_digest_sections_keys(monkeypatch):
    import business_digest as bd

    _patch_sections(monkeypatch, bd)
    d = bd.build_digest(1.0)  # короткое окно — по нулям, но структура полная
    assert "revenue_usd" in d["api"]
    assert "tenants" in d["whitelabel"]
    assert "open_bids" in d["funnel"]
