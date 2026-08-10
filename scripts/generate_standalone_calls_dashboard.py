#!/usr/bin/env python3
"""
AIOS Standalone Stitch Calls CRM Dashboard Generator
Создает автономный HTML дашборд со встроенными данными 44+ контактов и диалогов.
"""

import os
import sys
import json
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.calls_crm_engine import get_contacts_with_dialogues

OUTPUT_HTML = REPO_ROOT / "data" / "stitch_calls_dashboard.html"
STATIC_HTML_SRC = REPO_ROOT / "converge" / "static" / "calls_dashboard.html"


def generate_standalone_dashboard():
    contacts = get_contacts_with_dialogues()
    contacts_json_str = json.dumps(contacts, ensure_ascii=False)

    template_code = STATIC_HTML_SRC.read_text(encoding="utf-8") if STATIC_HTML_SRC.exists() else ""

    # Внедряем предзагруженные данные прямо в HTML
    preload_script = f"""
  <script>
    window.PRELOADED_CONTACTS = {contacts_json_str};
  </script>
"""
    
    # Заменяем loadContacts на использование предзагруженных данных
    modified_code = template_code.replace(
        "async function loadContacts() {",
        f"""{preload_script}
    async function loadContacts() {{
      if (window.PRELOADED_CONTACTS && window.PRELOADED_CONTACTS.length) {{
        allContacts = window.PRELOADED_CONTACTS;
        renderContacts(allContacts);
        return;
      }}"""
    )

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(modified_code, encoding="utf-8")
    print(f"🎉 Автономный Stitch Дашборд сгенерирован: {OUTPUT_HTML} (размер: {OUTPUT_HTML.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    generate_standalone_dashboard()
