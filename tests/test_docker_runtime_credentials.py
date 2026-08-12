from __future__ import annotations

import os

from scripts.prepare_docker_runtime_credentials import prepare


def test_nonroot_runtime_credentials_and_alertmanager_config_are_group_readable(tmp_path):
    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    source.mkdir()
    (source / "telegram_token").write_text("123456:test-token-value\n", encoding="utf-8")
    (source / "telegram_owner_chat_id").write_text("123456789\n", encoding="utf-8")
    prepare(source, runtime, gid=os.getgid())

    token = runtime / "telegram_token"
    owner = runtime / "telegram_owner_chat_id"
    config = runtime / "alertmanager.yml"
    assert token.stat().st_mode & 0o777 == 0o440
    assert owner.stat().st_mode & 0o777 == 0o440
    assert config.stat().st_mode & 0o777 == 0o440
    rendered = config.read_text(encoding="utf-8")
    assert "chat_id: 123456789" in rendered
    assert "123456:test-token-value" not in rendered
