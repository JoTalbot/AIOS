"""Private follow-up templates are local and never auto-sent."""
from __future__ import annotations


def test_template_store_private_and_upserts(tmp_path):
    from aios_core.followup_templates import FollowupTemplateStore

    store = FollowupTemplateStore(tmp_path)
    assert store.upsert("Первый ответ", "Здравствуйте, спасибо за обращение.")["status"] == "created"
    assert store.upsert("Первый ответ", "Обновлённый текст")["status"] == "updated"
    template = store.get("первый ответ")
    assert template["text"] == "Обновлённый текст"
    assert store.path.stat().st_mode & 0o777 == 0o600
