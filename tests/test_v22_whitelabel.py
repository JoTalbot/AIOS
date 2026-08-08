"""v22 white-label tests: tenant CRUD, branded drafts, markup, quota, isolation."""
import json
import sys

import pytest

sys.path.insert(0, "/root/AIOS")


@pytest.fixture
def mgr(tmp_path):
    from aios_core.whitelabel_ads import WhiteLabelAdsManager
    return WhiteLabelAdsManager(data_dir=str(tmp_path))


@pytest.fixture
def tenant(mgr):
    r = mgr.create_tenant("avtokb", "Кропивницкий Разбор", "АвтоРазбор КБ",
                          style_footer="Гарантия 14 дней. Отправка НП.",
                          phone="+380671112233", markup_pct=15.0, ads_quota_per_day=2)
    assert r["status"] == "ok"
    return r["tenant"]


def _mock_adgen(monkeypatch, title="Радиатор ВАЗ 2109 б/у рабочий", price="950"):
    import run_olx_ad_gen as adgen
    monkeypatch.setattr(adgen, "generate", lambda part: {
        "status": "ok", "part": part, "title": title,
        "description": "Б/у, рабочее состояние. Отправка Новой Почтой.",
        "price": price})


def test_tenant_crud_and_defaults(mgr, tenant):
    assert tenant["tenant_id"] == "avtokb"
    assert tenant["markup_pct"] == 15.0
    dup = mgr.create_tenant("avtokb", "X", "Y")
    assert dup["status"] == "error"  # не перетираем существующего
    lst = mgr.list_tenants()
    assert len(lst) == 1 and lst[0]["company_name"] == "АвтоРазбор КБ"


def test_branded_draft_markup_and_footer(mgr, tenant, monkeypatch):
    _mock_adgen(monkeypatch)
    r = mgr.generate_draft("avtokb", "Радиатор ВАЗ 2109", base_price_uah=900.0)
    assert r["status"] == "ok"
    d = r["draft"]
    # наценка 15% от 900 = 1035
    assert d["price_uah"] == "1035"
    # брендовый футер
    assert "Гарантия 14 дней." in d["description"]
    assert "АвтоРазбор КБ, +380671112233" in d["description"]
    assert d["status"] == "draft" and d["tenant_id"] == "avtokb"


def test_price_fallback_to_generator(mgr, tenant, monkeypatch):
    _mock_adgen(monkeypatch, price="1400")
    r = mgr.generate_draft("avtokb", "Генератор ВАЗ 2110")
    assert r["draft"]["price_uah"] == "1400"  # без base_price — цена генератора


def test_daily_quota_enforced(mgr, tenant, monkeypatch):
    _mock_adgen(monkeypatch)
    assert mgr.generate_draft("avtokb", "Деталь 1")["status"] == "ok"
    assert mgr.generate_draft("avtokb", "Деталь 2")["status"] == "ok"
    r3 = mgr.generate_draft("avtokb", "Деталь 3")  # quota=2
    assert r3["status"] == "error" and "quota" in r3["error"]


def test_tenant_isolation(mgr, tenant, monkeypatch):
    _mock_adgen(monkeypatch)
    mgr.create_tenant("other", "Other Co", "Other")
    mgr.generate_draft("avtokb", "Деталь А")
    mine = mgr.list_drafts("avtokb")
    alien = mgr.list_drafts("other")
    assert mine["count"] == 1 and mine["drafts"][0]["tenant_id"] == "avtokb"
    assert alien["count"] == 0
    assert mgr.generate_draft("ghost", "X")["status"] == "error"
