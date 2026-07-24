"""Tests for Rozetka CLI subcommand integration."""

import json

import pytest

from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import load_catalog_file


@pytest.fixture
def rozetka_registered():
    """Register rozetka platform from catalog."""
    loaded = load_catalog_file("platforms/rozetka.yaml")
    yield loaded
    for d in loaded:
        descriptor_mod._PLATFORMS.pop(d.name, None)


def test_cli_rozetka_stats(tmp_path, capsys, rozetka_registered):
    """CLI rozetka stats returns JSON."""
    from aios_cli import main

    db = tmp_path / "rz.sqlite"
    main(["rozetka", "stats", "--db", str(db)])
    out = json.loads(capsys.readouterr().out)
    assert "total_ads" in out


def test_cli_rozetka_dm_send(tmp_path, capsys, rozetka_registered):
    """CLI rozetka dm-send queues reply."""
    from aios_cli import main

    db = tmp_path / "rz.sqlite"
    main(["rozetka", "dm-send", "--chat", "chat:seller", "--text", "Привет", "--db", str(db)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "queued"


def test_cli_rozetka_dm_outbox(tmp_path, capsys, rozetka_registered):
    """CLI rozetka dm-outbox lists pending replies."""
    from aios_cli import main

    db = tmp_path / "rz.sqlite"
    main(["rozetka", "dm-send", "--chat", "chat:seller", "--text", "Тест", "--db", str(db)])
    capsys.readouterr()  # consume dm-send output
    main(["rozetka", "dm-outbox", "--db", str(db)])
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) >= 1


def test_cli_rozetka_chats(tmp_path, capsys, rozetka_registered):
    """CLI rozetka chats returns list."""
    from aios_cli import main

    db = tmp_path / "rz.sqlite"
    main(["rozetka", "chats", "--db", str(db)])
    out = json.loads(capsys.readouterr().out)
    assert isinstance(out, list)
