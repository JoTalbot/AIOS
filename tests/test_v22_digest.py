"""v22 digest tests: build_digest structure + tg_text rendering."""
import sys

sys.path.insert(0, "/root/AIOS")
sys.path.insert(0, "/root/AIOS/scripts")


def test_digest_structure_and_text():
    import business_digest as bd

    d = bd.build_digest(24.0)
    assert set(d.keys()) == {"generated_at", "window_hours", "api", "whitelabel", "funnel", "olx"}
    assert d["window_hours"] == 24.0
    # секции живые (данные реальные read-only)
    assert d["funnel"].get("ok") is True
    assert d["whitelabel"].get("ok") is True

    text = bd.tg_text(d)
    for marker in ("Business Digest", "API", "White-label", "Фриланс", "OLX-склад", "#дайджест"):
        assert marker in text, f"missing: {marker}"


def test_digest_sections_keys():
    import business_digest as bd

    d = bd.build_digest(1.0)  # короткое окно — по нулям, но структура полная
    assert "revenue_usd" in d["api"]
    assert "tenants" in d["whitelabel"]
    assert "open_bids" in d["funnel"]
