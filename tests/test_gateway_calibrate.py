"""Tests for ShardGateway, ShardHealthMonitor and the calibration agent."""

import json
import os

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from aios_core.platforms import (
    CalibrationAdvisor,
    ShardGateway,
    ShardHealthMonitor,
    ShardRouter,
    get_platform,
    hints_to_yaml_doc,
    load_catalog_file,
)
from aios_core.platforms import descriptor as descriptor_mod

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# ShardGateway
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeClient:
    def __init__(self, calls, response=None, exc=None):
        self.calls = calls
        self._response = response or _FakeResponse(payload={"ok": True})
        self._exc = exc

    def request(self, method, url, params=None, json=None):
        if self._exc:
            raise self._exc
        self.calls.append({"method": method, "url": url, "params": params, "json": json})
        return self._response

    def close(self):
        pass


def test_gateway_local_route_marks_without_http():
    with ShardRouter(":memory:") as router:
        router.add_host("this-host", "http://this:8000")
        gateway = ShardGateway(router, host_id="this-host", client_factory=lambda: None)
        route = gateway.resolve("olx:work")
        assert route["local"] is True
        result = gateway.proxy("olx:work", "GET", "/api/v1/modules/olx/stats")
        assert result["local"] is True
        assert result["route"]["host"] == "this-host"


def test_gateway_proxies_to_remote_and_reports_errors():
    with ShardRouter(":memory:") as router:
        router.add_host("remote", "http://remote:8000")
        calls = []
        gateway = ShardGateway(
            router,
            host_id="this-host",
            client_factory=lambda: _FakeClient(
                calls,
                response=_FakeResponse(status_code=200, payload={"rows": 3}),
            ),
        )
        result = gateway.proxy(
            "olx:work",
            "POST",
            "/api/v1/modules/demo/ads/ingest",
            params={"profile": "work"},
            json_body={"ads": []},
        )
        assert result["status"] == 200
        assert result["payload"] == {"rows": 3}
        assert calls[0]["method"] == "POST"
        assert calls[0]["url"] == "http://remote:8000/api/v1/modules/demo/ads/ingest"
        assert calls[0]["params"] == {"profile": "work"}

        broken = ShardGateway(
            router,
            host_id="this-host",
            client_factory=lambda: _FakeClient(
                [],
                exc=ConnectionError("refused"),
            ),
        )
        failed = broken.proxy("olx:home", "GET", "/health")
        assert failed["status"] == 502
        assert "refused" in failed["error"]

        empty = ShardGateway(ShardRouter(":memory:"))
        assert empty.proxy("olx:x", "GET", "/x")["status"] == 409


# ---------------------------------------------------------------------------
# ShardHealthMonitor
# ---------------------------------------------------------------------------


def test_health_monitor_flips_flags_and_moves_routes():
    with ShardRouter(":memory:") as router:
        router.add_host("h1", "http://h1:8000")
        router.add_host("h2", "http://h2:8000")
        router.route_for("olx:a")
        router.route_for("olx:b")
        states = {"h1": False, "h2": True}
        monitor = ShardHealthMonitor(router, probe=lambda host: states[host["host"]])
        report = monitor.run_once()
        assert report["hosts"] == {"h1": False, "h2": True}
        assert report["healthy"] == 1
        assert report["sick"] == ["h1"]
        by_host = {h["host"]: h["healthy"] for h in router.hosts()}
        assert by_host == {"h1": False, "h2": True}
        # Все профили теперь маршрутятся только на здоровый хост.
        assert router.route_for("olx:a")["host"] == "h2"
        assert router.route_for("olx:b")["host"] == "h2"

        # Выздоровел → флаг возвращается.
        states["h1"] = True
        monitor.run_once()
        by_host = {h["host"]: h["healthy"] for h in router.hosts()}
        assert by_host["h1"] is True


def test_health_monitor_start_stop():
    with ShardRouter(":memory:") as router:
        router.add_host("h1", "http://h1:8000")
        monitor = ShardHealthMonitor(router, probe=lambda h: True)
        assert monitor.start(interval_s=0.05) is True
        assert monitor.start() is False
        import time

        time.sleep(0.12)
        assert monitor.stop() is True
        assert monitor.stop() is False


# ---------------------------------------------------------------------------
# CalibrationAdvisor
# ---------------------------------------------------------------------------

DUMP_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="Пошук" resource-id="com.demo:id/searchBar"/>
  <node text="" resource-id="com.demo:id/adCard">
    <node text="Продам велосипед у гарному стані" resource-id=""/>
    <node text="4 500 грн" resource-id=""/>
    <node text="Київ" resource-id=""/>
  </node>
  <node text="" resource-id="com.demo:id/adCard">
    <node text="iPhone 12 128GB" resource-id=""/>
    <node text="12 000 грн" resource-id=""/>
    <node text="Дніпро" resource-id=""/>
  </node>
  <node text="" resource-id="com.demo:id/promoBanner">
    <node text="Реклама" resource-id=""/>
    <node text="Тільки сьогодні" resource-id=""/>
  </node>
</hierarchy>
"""


def test_calibration_finds_card_markers_and_currencies():
    hints = CalibrationAdvisor().analyze(DUMP_XML)
    markers = hints["card_markers"]
    assert markers[0]["resource_id"] == "com.demo:id/adCard"
    assert markers[0]["occurrences"] == 2
    assert len(markers[0]["sample_titles"]) == 2
    assert hints["currencies"] == {"UAH": 2}
    assert hints["prices_seen"] == 2
    assert "найдены" in hints["hint"]


def test_calibration_empty_dump_hint():
    hints = CalibrationAdvisor().analyze("<hierarchy rotation='0'/>")
    assert hints["card_markers"] == []
    assert "не обнаружены" in hints["hint"]


def test_hints_yaml_fragment_and_descriptor_roundtrip(tmp_path):
    hints = CalibrationAdvisor().analyze(DUMP_XML)
    fragment = hints_to_yaml_doc("demo", hints)
    assert "parser_hints" in fragment
    assert "demo" in fragment

    catalog = tmp_path / "demo.yaml"
    catalog.write_text(
        yaml.safe_dump(
            {
                "name": "demo",
                "android_package": "com.demo.app",
                "extras": {"parser_hints": hints},
            }
        ),
        encoding="utf-8",
    )
    try:
        load_catalog_file(catalog)
        descriptor = get_platform("demo")
        assert (
            descriptor.extras["parser_hints"]["card_markers"][0]["resource_id"]
            == "com.demo:id/adCard"
        )
        assert descriptor.to_dict()["extras"]["parser_hints"]["currencies"] == {"UAH": 2}
    finally:
        descriptor_mod._PLATFORMS.pop("demo", None)


# ---------------------------------------------------------------------------
# CLI surfaces
# ---------------------------------------------------------------------------


def test_cli_platforms_calibrate_write_and_show(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    # Подготовим дескриптор и дамп.
    platforms_dir = tmp_path / "platforms"
    platforms_dir.mkdir()
    (platforms_dir / "demo.yaml").write_text(
        "name: demo\nandroid_package: com.demo.app\n",
        encoding="utf-8",
    )
    dump = tmp_path / "screen.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    main(["platforms", "calibrate", "--platform", "demo", "--dump", str(dump)])
    out = json.loads(capsys.readouterr().out)
    assert out["hints"]["card_markers"][0]["resource_id"] == "com.demo:id/adCard"
    assert "yaml_fragment" in out

    main(["platforms", "calibrate", "--platform", "demo", "--dump", str(dump), "--write"])
    out = json.loads(capsys.readouterr().out)
    assert out["written"].endswith("demo.yaml")
    doc = yaml.safe_load((platforms_dir / "demo.yaml").read_text())
    assert doc["extras"]["parser_hints"]["currencies"] == {"UAH": 2}


def test_cli_shards_monitor_once(tmp_path, monkeypatch, capsys):
    from aios_cli import main
    import aios_core.platforms.gateway as gateway_mod

    monkeypatch.setenv("AIOS_SHARDS_DB", str(tmp_path / "shards.sqlite"))
    # Подменяем default-probe (в CI нет сети до шардов).
    monkeypatch.setattr(gateway_mod, "default_health_probe", lambda h: True)
    main(["shards", "add", "--host", "h1", "--base-url", "http://h1:8000"])
    json.loads(capsys.readouterr().out)
    main(["shards", "monitor", "--once"])
    report = json.loads(capsys.readouterr().out)
    assert report["hosts"] == {"h1": True}
    assert report["sick"] == []


# ---------------------------------------------------------------------------
# REST gateway
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    from aios_core.api.app import AIOSAPI
    from aios_core.platforms import DevicePool, ProfileStore

    router = ShardRouter(":memory:")
    router.add_host("remote", "http://remote:8000")
    calls = []
    gateway = ShardGateway(
        router,
        host_id="local-api",
        client_factory=lambda: _FakeClient(
            calls,
            response=_FakeResponse(payload={"proxied": True}),
        ),
    )
    gateway.calls = calls
    store = ProfileStore(":memory:")
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=store,
        device_pool=DevicePool(":memory:"),
        shard_router=router,
        shard_gateway=gateway,
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, gateway, router
    store.close()


async def test_rest_shard_gateway_proxies(client):
    ac, gateway, _router = client
    bad = await ac.post("/api/v1/shards/gateway", json={"profile": "olx:work"})
    assert bad.status_code == 400

    proxied = await ac.post(
        "/api/v1/shards/gateway",
        json={
            "profile": "olx:work",
            "method": "POST",
            "path": "/api/v1/modules/demo/ads/ingest",
            "body": {"ads": []},
        },
    )
    assert proxied.status_code == 200
    assert proxied.json() == {"proxied": True}
    assert gateway.calls[0]["url"].endswith("/api/v1/modules/demo/ads/ingest")


async def test_rest_shard_gateway_local_marker(client):
    ac, gateway, router = client
    router.add_host("local-api", "http://self:8000")
    gateway.host_id = "local-api"
    # Профиль, чей HRW-роут ведёт этот... маршрутизируем явно:
    # упростим: временно уберём remote.
    router.set_healthy("remote", False)
    result = await ac.post(
        "/api/v1/shards/gateway",
        json={
            "profile": "olx:local-job",
            "path": "/api/v1/modules/olx/stats",
        },
    )
    assert result.status_code == 200
    assert result.json()["local"] is True
