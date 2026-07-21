"""Tests for ParserGen (parser_hints → CardParser) and the bootup E2E pipeline."""

import json
import os
import sys

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from aios_core.platforms import (
    PlatformDescriptor,
    bootup_platform,
    build_parser,
    extract_markers,
    generate_parser_source,
    get_platform,
    parser_for,
    register_platform,
    scaffold_platform,
    write_hints_to_descriptor,
    write_parser,
)
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms.calibrate import CalibrationAdvisor

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
</hierarchy>
"""

HINTS = CalibrationAdvisor().analyze(DUMP_XML)


def _badging_ok(apk_path, package="com.boot.app", label="Boot Market"):
    return {
        "code": 0,
        "stdout": (
            f"package: name='{package}'\n"
            f"application-label:'{label}'\n"
            f"launchable-activity: name='{package}.MainActivity'\n"
            f"targetSdkVersion:'34'\n"
        ),
        "stderr": "",
    }


def _importable(tmp_path, *module_names):
    """Расширяет __path__ aios_core.modules на tmp-корень (как в репо)."""
    import aios_core.modules as modules_pkg

    extra = str(tmp_path / "aios_core" / "modules")
    if extra not in modules_pkg.__path__:
        modules_pkg.__path__.append(extra)
    for name in module_names:
        sys.modules.pop(f"aios_core.modules.{name}", None)
        sys.modules.pop(f"aios_core.modules.{name}.card_parser", None)
        sys.modules.pop(f"aios_core.modules.{name}.storage", None)
    return modules_pkg, extra


# ---------------------------------------------------------------------------
# extract_markers / build_parser
# ---------------------------------------------------------------------------

def test_extract_markers_normalizes_and_deduplicates():
    hints = {
        "card_markers": [
            {"resource_id": "com.demo:id/adCard"},
            {"resource_id": "Com.Demo:id/Main-Card!"},
            {"resource_id": "other.pkg:id/adCard"},  # дубль после нормализации
            {"resource_id": ""},
        ]
    }
    assert extract_markers(hints) == ("adcard", "maincard")


def test_extract_markers_empty_hints():
    assert extract_markers(None) == ()
    assert extract_markers({}) == ()
    assert extract_markers({"card_markers": []}) == ()


def test_build_parser_from_hints_parses_dump():
    parser = build_parser(HINTS)
    cards = parser.parse(DUMP_XML, query="велосипед")
    assert len(cards) == 2
    assert cards[0].title == "Продам велосипед у гарному стані"
    assert cards[0].price == 4500.0
    assert cards[0].currency == "UAH"
    assert cards[0].city == "Київ"
    assert cards[0].query == "велосипед"
    assert cards[1].title == "iPhone 12 128GB"


def test_build_parser_empty_hints_matches_nothing():
    parser = build_parser({})
    assert parser.parse(DUMP_XML) == []


def test_olx_card_parser_markers_still_backward_compatible():
    from aios_core.modules.olx.card_parser import (
        CARD_RESOURCE_MARKERS,
        CardParser,
    )

    assert "adlisting_adgridcard" in CARD_RESOURCE_MARKERS
    assert CardParser.CARD_RESOURCE_MARKERS == CARD_RESOURCE_MARKERS
    # Подкласс переопределяет маркеры, не трогая базовый класс:
    Custom = type("Custom", (CardParser,), {"CARD_RESOURCE_MARKERS": ("adcard",)})
    assert len(Custom().parse(DUMP_XML)) == 2
    assert CardParser().parse(DUMP_XML) == []  # OLX-маркер сюда не матчится


# ---------------------------------------------------------------------------
# codegen: generate_parser_source / write_parser / parser_for
# ---------------------------------------------------------------------------

def test_generate_parser_source_contains_class_and_markers():
    source = generate_parser_source("demo-market", HINTS, "com.demo")
    assert "class DemoMarketCardParser(" in source
    assert "'adcard'" in source
    assert "com.demo" in source


def test_generate_parser_source_without_markers_raises():
    with pytest.raises(ValueError, match="no card markers"):
        generate_parser_source("demo-market", {})


def test_write_parser_requires_scaffolded_module(tmp_path):
    with pytest.raises(ValueError, match="not scaffolded"):
        write_parser("pg-ghost", HINTS, project_root=tmp_path)


def test_write_parser_real_module_import_roundtrip(tmp_path):
    scaffold_platform("pg-demo", "com.pg.demo", project_root=tmp_path)
    files = write_parser(
        "pg-demo", HINTS, project_root=tmp_path,
        android_package="com.pg.demo",
    )
    module_dir = tmp_path / "aios_core" / "modules" / "pg_demo"
    assert str(module_dir / "card_parser.py") in files
    assert str(module_dir / "__init__.py") in files

    modules_pkg, extra = _importable(tmp_path, "pg_demo")
    try:
        from aios_core.modules.pg_demo import PgDemoCardParser

        parser = PgDemoCardParser()
        assert parser.CARD_RESOURCE_MARKERS == ("adcard",)
        cards = parser.parse(DUMP_XML)
        assert [c.title for c in cards] == [
            "Продам велосипед у гарному стані", "iPhone 12 128GB",
        ]
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.pg_demo", None)
        sys.modules.pop("aios_core.modules.pg_demo.card_parser", None)
        sys.modules.pop("aios_core.modules.pg_demo.storage", None)


def test_write_parser_overwrite_flow_is_idempotent(tmp_path):
    scaffold_platform("pg-demo", "com.pg.demo", project_root=tmp_path)
    write_parser("pg-demo", HINTS, project_root=tmp_path)
    with pytest.raises(ValueError, match="already exists"):
        write_parser("pg-demo", HINTS, project_root=tmp_path)

    files = write_parser("pg-demo", HINTS, project_root=tmp_path,
                         overwrite=True)
    init_path = (tmp_path / "aios_core" / "modules" / "pg_demo"
                 / "__init__.py")
    # Импорт не дублируется — __init__.py не входит в план повторно.
    assert str(init_path) not in files
    assert init_path.read_text(encoding="utf-8").count(
        "codegen: parser_hints"
    ) == 1


def test_parser_for_reads_hints_from_descriptor_yaml(tmp_path):
    scaffold_platform("pg-demo", "com.pg.demo", project_root=tmp_path)
    write_hints_to_descriptor(
        "pg-demo", HINTS, directory=tmp_path / "platforms",
    )
    parser = parser_for("pg-demo", directory=tmp_path / "platforms")
    assert len(parser.parse(DUMP_XML)) == 2
    with pytest.raises(ValueError, match="descriptor not found"):
        parser_for("pg-ghost", directory=tmp_path / "platforms")


def test_write_hints_to_descriptor_registers_extras(tmp_path):
    scaffold_platform("pg-demo", "com.pg.demo", project_root=tmp_path)
    written = write_hints_to_descriptor(
        "pg-demo", HINTS, directory=tmp_path / "platforms",
    )
    assert written.endswith("pg-demo.yaml")
    doc = yaml.safe_load((tmp_path / "platforms" / "pg-demo.yaml")
                         .read_text(encoding="utf-8"))
    assert doc["extras"]["parser_hints"]["card_markers"]
    with pytest.raises(ValueError, match="descriptor not found"):
        write_hints_to_descriptor(
            "pg-ghost", HINTS, directory=tmp_path / "platforms",
        )


# ---------------------------------------------------------------------------
# bootup E2E pipeline
# ---------------------------------------------------------------------------

def test_bootup_requires_apk_or_name_package(tmp_path):
    with pytest.raises(ValueError, match="either --apk or both"):
        bootup_platform(project_root=tmp_path)
    with pytest.raises(ValueError, match="either --apk or both"):
        bootup_platform(name="x", project_root=tmp_path)


def test_bootup_dry_run_full_pipeline(tmp_path):
    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    report = bootup_platform(
        apk_path="boot.apk", project_root=tmp_path,
        dump_path=str(dump), runner=_badging_ok, dry_run=True,
    )
    assert report["platform"] == "app"  # candidate из com.boot.app
    assert report["android_package"] == "com.boot.app"
    assert report["status"] == "ready"
    assert report["dry_run"] is True
    steps = report["steps"]
    assert steps["scaffold"]["mode"] == "planned"
    assert steps["register"]["mode"] == "skipped"
    assert steps["hints"]["mode"] == "planned"
    assert steps["codegen"]["mode"] == "planned"
    assert steps["verify"]["cards"] == 2
    assert "Продам велосипед у гарному стані" in \
        steps["verify"]["sample_titles"]
    # dry-run: на диске пусто.
    assert not (tmp_path / "platforms").exists()
    assert not (tmp_path / "aios_core").exists()


def test_bootup_real_run_ready_and_registered(tmp_path):
    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    modules_pkg, extra = _importable(tmp_path, "app")
    try:
        report = bootup_platform(
            apk_path="boot.apk", project_root=tmp_path,
            dump_path=str(dump), runner=_badging_ok,
        )
        try:
            assert report["status"] == "ready"
            steps = report["steps"]
            assert steps["scaffold"]["mode"] == "written"
            assert steps["register"]["mode"] == "registered"
            # scaffold сразу заявляет deny-by-default compliance:
            assert steps["hints"]["registered_extras"] == [
                "compliance", "parser_hints"]
            assert steps["codegen"]["mode"] == "written"
            assert steps["verify"]["cards"] == 2

            descriptor = get_platform("app")
            assert descriptor.android_package == "com.boot.app"
            assert descriptor.extras["parser_hints"]["card_markers"]
            assert (tmp_path / "aios_core" / "modules" / "app"
                    / "card_parser.py").exists()
            # Хранилище платформы доступно через фабрику дескриптора:
            storage = descriptor.make_storage(":memory:")
            assert storage.get_ads() == []
            storage.close()
        finally:
            descriptor_mod._PLATFORMS.pop("app", None)
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.app", None)
        sys.modules.pop("aios_core.modules.app.storage", None)


def test_bootup_injected_driver_calibration(tmp_path):
    calls = []

    def driver(package, query):
        calls.append({"package": package, "query": query})
        return DUMP_XML

    modules_pkg, extra = _importable(tmp_path, "driveo")
    try:
        report = bootup_platform(
            name="driveo", package="com.driveo.app", project_root=tmp_path,
            query="велосипед", driver=driver,
        )
        try:
            assert report["status"] == "ready"
            assert report["steps"]["calibrate"]["source"] == "driver:injected"
        finally:
            descriptor_mod._PLATFORMS.pop("driveo", None)
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.driveo", None)
        sys.modules.pop("aios_core.modules.driveo.storage", None)
    assert calls == [{"package": "com.driveo.app", "query": "велосипед"}]


def test_bootup_driver_failure_leaves_scaffolded(tmp_path):
    def driver(package, query):
        raise RuntimeError("no emulator attached")

    modules_pkg, extra = _importable(tmp_path, "nodev")
    try:
        report = bootup_platform(
            name="nodev", package="com.nodev.app", project_root=tmp_path,
            driver=driver,
        )
        try:
            assert report["status"] == "scaffolded"
            assert report["steps"]["calibrate"]["mode"] == "skipped"
            assert "no emulator attached" in \
                report["steps"]["calibrate"]["reason"]
            assert report["steps"]["codegen"]["mode"] == "skipped"
        finally:
            descriptor_mod._PLATFORMS.pop("nodev", None)
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.nodev", None)
        sys.modules.pop("aios_core.modules.nodev.storage", None)


def test_bootup_resume_on_existing_scaffold(tmp_path):
    def driver(package, query):
        raise RuntimeError("offline")

    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    modules_pkg, extra = _importable(tmp_path, "redo")
    try:
        try:
            first = bootup_platform(
                name="redo", package="com.redo.app",
                project_root=tmp_path, driver=driver,
            )
            assert first["status"] == "scaffolded"

            second = bootup_platform(
                name="redo", package="com.redo.app",
                project_root=tmp_path, dump_path=str(dump),
            )
            assert second["status"] == "ready"
            assert second["steps"]["scaffold"]["mode"] == "resumed"
            assert second["steps"]["verify"]["cards"] == 2
        finally:
            descriptor_mod._PLATFORMS.pop("redo", None)
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.redo", None)
        sys.modules.pop("aios_core.modules.redo.storage", None)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_platforms_codegen_dry_run_and_real(tmp_path, capsys):
    from aios_cli import main

    scaffold_platform("cli-demo", "ua.cli.demo", project_root=tmp_path)
    write_hints_to_descriptor(
        "cli-demo", HINTS, directory=tmp_path / "platforms",
    )

    main(["platforms", "codegen", "--platform", "cli-demo",
          "--root", str(tmp_path), "--dry-run"])
    out = json.loads(capsys.readouterr().out)
    assert any("card_parser.py" in path for path in out["planned"])
    assert not (tmp_path / "aios_core" / "modules" / "cli_demo"
                / "card_parser.py").exists()

    main(["platforms", "codegen", "--platform", "cli-demo",
          "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert any("card_parser.py" in path for path in out["written"])
    assert (tmp_path / "aios_core" / "modules" / "cli_demo"
            / "card_parser.py").exists()

    # Повтор без --force — чистая JSON-ошибка.
    main(["platforms", "codegen", "--platform", "cli-demo",
          "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "already exists" in out["error"]


def test_cli_platforms_codegen_without_hints_errors(tmp_path, capsys):
    from aios_cli import main

    scaffold_platform("cli-bare", "ua.cli.bare", project_root=tmp_path)
    main(["platforms", "codegen", "--platform", "cli-bare",
          "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "no card markers" in out["error"]

    main(["platforms", "codegen", "--platform", "cli-ghost",
          "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "descriptor not found" in out["error"]


def test_cli_platforms_bootup_end_to_end(tmp_path, capsys, monkeypatch):
    from aios_cli import main

    dump = tmp_path / "dump.xml"
    dump.write_text(DUMP_XML, encoding="utf-8")
    modules_pkg, extra = _importable(tmp_path, "booto")
    try:
        main(["platforms", "bootup", "--name", "booto",
              "--package", "ua.booto.app", "--dump", str(dump),
              "--root", str(tmp_path), "--query", "велосипед"])
        out = json.loads(capsys.readouterr().out)
        try:
            assert out["status"] == "ready"
            assert out["steps"]["verify"]["cards"] == 2
            assert out["steps"]["codegen"]["mode"] == "written"
        finally:
            descriptor_mod._PLATFORMS.pop("booto", None)
    finally:
        modules_pkg.__path__.remove(extra)
        sys.modules.pop("aios_core.modules.booto", None)
        sys.modules.pop("aios_core.modules.booto.storage", None)

    # Без входных данных — чистая JSON-ошибка, без traceback.
    main(["platforms", "bootup", "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert "either --apk or both" in out["error"]


# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------

@pytest.fixture
def hints_platform(tmp_path):
    def storage_factory(db_path):
        from aios_core.modules.olx import OLXStorage
        return OLXStorage(db_path)

    register_platform(PlatformDescriptor(
        name="hints-demo",
        android_package="ua.hints.demo",
        agent_module="hints_demo.agent",
        storage_factory=storage_factory,
    ))
    yield
    descriptor_mod._PLATFORMS.pop("hints-demo", None)


@pytest.fixture
async def hints_client(hints_platform, tmp_path):
    from aios_core.api.app import AIOSAPI
    from aios_core.platforms import DevicePool, ProfileStore

    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=ProfileStore(":memory:"),
        device_pool=DevicePool(":memory:"),
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport,
                           base_url="http://test") as ac:
        yield ac


async def test_rest_platform_hints_calibrates_and_previews(hints_client):
    response = await hints_client.post(
        "/api/v1/platforms/hints-demo/hints", json={"dump": DUMP_XML},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "hints-demo"
    assert payload["hints"]["card_markers"]
    assert payload["parser_preview"]["cards"] == 2
    assert "Продам велосипед у гарному стані" in \
        payload["parser_preview"]["sample_titles"]
    # Подсказки сохранены в runtime-дескрипторе:
    descriptor = get_platform("hints-demo")
    assert descriptor.extras["parser_hints"]["card_markers"]


async def test_rest_platform_hints_error_paths(hints_client):
    response = await hints_client.post(
        "/api/v1/platforms/no-such/hints", json={"dump": DUMP_XML},
    )
    assert response.status_code == 404

    response = await hints_client.post(
        "/api/v1/platforms/hints-demo/hints", json={},
    )
    assert response.status_code == 400


async def test_rest_platform_hints_direct_object(hints_client):
    response = await hints_client.post(
        "/api/v1/platforms/hints-demo/hints",
        json={"hints": {"card_markers": [
            {"resource_id": "ua.hints:id/itemCard", "occurrences": 3},
        ]}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["hints"]["card_markers"][0]["resource_id"] == \
        "ua.hints:id/itemCard"
    assert "parser_preview" not in payload  # без дампа превью нет
